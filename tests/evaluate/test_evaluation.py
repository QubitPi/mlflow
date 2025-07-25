import hashlib
import io
import json
import os
import re
import signal
import subprocess
import uuid
from typing import Any, NamedTuple
from unittest import mock

import numpy as np
import pandas as pd
import pytest
import sklearn
import sklearn.compose
import sklearn.datasets
import sklearn.impute
import sklearn.linear_model
import sklearn.pipeline
import sklearn.preprocessing
from mlflow_test_plugin.dummy_evaluator import Array2DEvaluationArtifact, DummyEvaluator
from PIL import Image, ImageChops
from pyspark.ml.linalg import Vectors
from pyspark.ml.regression import LinearRegression as SparkLinearRegression
from pyspark.sql import SparkSession
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
)

import mlflow
from mlflow import MlflowClient
from mlflow.data.evaluation_dataset import EvaluationDataset, _gen_md5_for_arraylike_obj
from mlflow.data.pandas_dataset import from_pandas
from mlflow.entities import Trace, TraceData
from mlflow.exceptions import MlflowException
from mlflow.models.evaluation import (
    EvaluationArtifact,
    EvaluationResult,
    ModelEvaluator,
    evaluate,
)
from mlflow.models.evaluation.artifacts import ImageEvaluationArtifact
from mlflow.models.evaluation.base import (
    _get_model_from_deployment_endpoint_uri,
    _is_model_deployment_endpoint_uri,
    _start_run_or_reuse_active_run,
    resolve_evaluators_and_configs,
)
from mlflow.models.evaluation.evaluator_registry import _model_evaluation_registry
from mlflow.pyfunc import _ServedPyFuncModel
from mlflow.pyfunc.scoring_server.client import ScoringServerClient
from mlflow.tracing.constant import TraceMetadataKey
from mlflow.tracking.artifact_utils import get_artifact_uri
from mlflow.utils.file_utils import TempDir

from tests.tracing.helper import create_test_trace_info, get_traces
from tests.utils.test_file_utils import spark_session  # noqa: F401

INFERENCE_FILE_NAME = "inference_inputs_outputs.json"


def get_iris():
    iris = sklearn.datasets.load_iris()
    return iris.data, iris.target


def get_diabetes_dataset():
    data = sklearn.datasets.load_diabetes()
    return data.data, data.target


def get_diabetes_spark_dataset():
    data = sklearn.datasets.load_diabetes()
    spark = SparkSession.builder.master("local[*]").getOrCreate()
    rows = [
        (Vectors.dense(features), float(label)) for features, label in zip(data.data, data.target)
    ]
    return spark.createDataFrame(spark.sparkContext.parallelize(rows, 1), ["features", "label"])


def get_breast_cancer_dataset():
    data = sklearn.datasets.load_breast_cancer()
    return data.data, data.target


class RunData(NamedTuple):
    params: dict[str, Any]
    metrics: dict[str, Any]
    tags: dict[str, Any]
    artifacts: list[str]


def get_run_data(run_id):
    client = MlflowClient()
    data = client.get_run(run_id).data
    artifacts = [f.path for f in client.list_artifacts(run_id)]
    return RunData(params=data.params, metrics=data.metrics, tags=data.tags, artifacts=artifacts)


def get_run_datasets(run_id):
    client = MlflowClient()
    return client.get_run(run_id).inputs.dataset_inputs


def get_raw_tag(run_id, tag_name):
    client = MlflowClient()
    data = client.get_run(run_id).data
    return data.tags[tag_name]


def get_local_artifact_path(run_id, artifact_path):
    return get_artifact_uri(run_id, artifact_path).replace("file://", "")


@pytest.fixture(scope="module")
def iris_dataset():
    X, y = get_iris()
    eval_X = X[0::3]
    eval_y = y[0::3]
    constructor_args = {"data": eval_X, "targets": eval_y, "name": "dataset"}
    ds = EvaluationDataset(**constructor_args)
    ds._constructor_args = constructor_args
    return ds


@pytest.fixture(scope="module")
def diabetes_dataset():
    X, y = get_diabetes_dataset()
    eval_X = X[0::3]
    eval_y = y[0::3]
    constructor_args = {"data": eval_X, "targets": eval_y}
    ds = EvaluationDataset(**constructor_args)
    ds._constructor_args = constructor_args
    return ds


@pytest.fixture(scope="module")
def diabetes_spark_dataset():
    spark_df = get_diabetes_spark_dataset().sample(fraction=0.3, seed=1)
    constructor_args = {"data": spark_df, "targets": "label"}
    ds = EvaluationDataset(**constructor_args)
    ds._constructor_args = constructor_args
    return ds


@pytest.fixture(scope="module")
def breast_cancer_dataset():
    X, y = get_breast_cancer_dataset()
    eval_X = X[0::3]
    eval_y = y[0::3]
    constructor_args = {"data": eval_X, "targets": eval_y}
    ds = EvaluationDataset(**constructor_args)
    ds._constructor_args = constructor_args
    return ds


def get_pipeline_model_dataset():
    """
    The dataset tweaks the IRIS dataset by changing its first 2 features into categorical features,
    and replace some feature values with NA values.
    The dataset is prepared for a pipeline model, see `pipeline_model_uri`.
    """
    X, y = get_iris()

    def convert_num_to_label(x):
        return f"v_{round(x)}"

    f1 = np.array(list(map(convert_num_to_label, X[:, 0])))
    f2 = np.array(list(map(convert_num_to_label, X[:, 1])))
    f3 = X[:, 2]
    f4 = X[:, 3]

    f1[0::8] = None
    f2[1::8] = None
    f3[2::8] = np.nan
    f4[3::8] = np.nan

    data = pd.DataFrame(
        {
            "f1": f1,
            "f2": f2,
            "f3": f3,
            "f4": f4,
            "y": y,
        }
    )
    return data, "y"


@pytest.fixture
def pipeline_model_uri():
    return get_pipeline_model_uri()


def get_pipeline_model_uri():
    """
    Create a pipeline model that transforms and trains on the dataset returned by
    `get_pipeline_model_dataset`. The pipeline model imputes the missing values in
    input dataset, encodes categorical features, and then trains a logistic regression
    model.
    """
    data, target_col = get_pipeline_model_dataset()
    X = data.drop(target_col, axis=1)
    y = data[target_col].to_numpy()

    encoder = sklearn.preprocessing.OrdinalEncoder()
    str_imputer = sklearn.impute.SimpleImputer(missing_values=None, strategy="most_frequent")
    num_imputer = sklearn.impute.SimpleImputer(missing_values=np.nan, strategy="mean")
    preproc_pipeline = sklearn.pipeline.Pipeline(
        [
            ("imputer", str_imputer),
            ("encoder", encoder),
        ]
    )

    pipeline = sklearn.pipeline.Pipeline(
        [
            (
                "transformer",
                sklearn.compose.make_column_transformer(
                    (preproc_pipeline, ["f1", "f2"]),
                    (num_imputer, ["f3", "f4"]),
                ),
            ),
            ("clf", sklearn.linear_model.LogisticRegression()),
        ]
    )
    pipeline.fit(X, y)

    with mlflow.start_run():
        model_info = mlflow.sklearn.log_model(pipeline, name="pipeline_model")
        return model_info.model_uri


@pytest.fixture
def linear_regressor_model_uri():
    return get_linear_regressor_model_uri()


def get_linear_regressor_model_uri():
    X, y = get_diabetes_dataset()
    reg = sklearn.linear_model.LinearRegression()
    reg.fit(X, y)

    with mlflow.start_run():
        model_info = mlflow.sklearn.log_model(reg, name="reg_model")
        return model_info.model_uri


@pytest.fixture
def spark_linear_regressor_model_uri():
    return get_spark_linear_regressor_model_uri()


def get_spark_linear_regressor_model_uri():
    spark_df = get_diabetes_spark_dataset()
    reg = SparkLinearRegression()
    spark_reg_model = reg.fit(spark_df)

    with mlflow.start_run():
        model_info = mlflow.spark.log_model(spark_reg_model, artifact_path="spark_reg_model")
        return model_info.model_uri


@pytest.fixture
def multiclass_logistic_regressor_model_uri():
    return multiclass_logistic_regressor_model_uri_by_max_iter(2)


def multiclass_logistic_regressor_model_uri_by_max_iter(max_iter):
    X, y = get_iris()
    clf = sklearn.linear_model.LogisticRegression(max_iter=max_iter)
    clf.fit(X, y)

    with mlflow.start_run():
        model_info = mlflow.sklearn.log_model(clf, name=f"clf_model_{max_iter}_iters")
        return model_info.model_uri


@pytest.fixture
def binary_logistic_regressor_model_uri():
    return get_binary_logistic_regressor_model_uri()


def get_binary_logistic_regressor_model_uri():
    X, y = get_breast_cancer_dataset()
    clf = sklearn.linear_model.LogisticRegression()
    clf.fit(X, y)

    with mlflow.start_run():
        model_info = mlflow.sklearn.log_model(clf, name="bin_clf_model")
        return model_info.model_uri


@pytest.fixture
def svm_model_uri():
    return get_svm_model_url()


def get_svm_model_url():
    X, y = get_breast_cancer_dataset()
    clf = sklearn.svm.LinearSVC()
    clf.fit(X, y)

    with mlflow.start_run():
        model_info = mlflow.sklearn.log_model(clf, name="svm_model")
        return model_info.model_uri


@pytest.fixture
def iris_pandas_df_dataset():
    X, y = get_iris()
    eval_X = X[0::3]
    eval_y = y[0::3]
    data = pd.DataFrame(
        {
            "f1": eval_X[:, 0],
            "f2": eval_X[:, 1],
            "f3": eval_X[:, 2],
            "f4": eval_X[:, 3],
            "y": eval_y,
        }
    )
    constructor_args = {"data": data, "targets": "y"}
    ds = EvaluationDataset(**constructor_args)
    ds._constructor_args = constructor_args
    return ds


@pytest.fixture
def iris_pandas_df_num_cols_dataset():
    X, y = get_iris()
    eval_X = X[0::3]
    eval_y = y[0::3]
    data = pd.DataFrame(eval_X)
    data["y"] = eval_y
    constructor_args = {"data": data, "targets": "y"}
    ds = EvaluationDataset(**constructor_args)
    ds._constructor_args = constructor_args
    return ds


def test_mlflow_evaluate_logs_traces():
    eval_data = pd.DataFrame(
        {
            "inputs": [
                "What is MLflow?",
                "What is Spark?",
            ],
            "ground_truth": ["What is MLflow?", "Not what is Spark?"],
        }
    )

    @mlflow.trace
    def model(inputs):
        return inputs

    with mlflow.start_run() as run:
        evaluate(
            model, eval_data, targets="ground_truth", extra_metrics=[mlflow.metrics.exact_match()]
        )
    assert len(get_traces()) == 1
    assert run.info.run_id == get_traces()[0].info.request_metadata[TraceMetadataKey.SOURCE_RUN]


def test_pyfunc_evaluate_logs_traces():
    class Model(mlflow.pyfunc.PythonModel):
        @mlflow.trace()
        def predict(self, context, model_input):
            return self.add(model_input, model_input)

        @mlflow.trace()
        def add(self, x, y):
            return x + y

    eval_data = pd.DataFrame(
        {
            "inputs": [1, 2, 4],
            "ground_truth": [2, 4, 8],
        }
    )

    with mlflow.start_run() as run:
        model_info = mlflow.pyfunc.log_model(name="model", python_model=Model())
        evaluate(
            model_info.model_uri,
            eval_data,
            targets="ground_truth",
            extra_metrics=[mlflow.metrics.exact_match()],
        )
    traces = get_traces()
    assert len(traces) == 1
    assert len(traces[0].data.spans) == 2
    assert run.info.run_id == traces[0].info.request_metadata[TraceMetadataKey.SOURCE_RUN]
    assert traces[0].info.request_metadata[TraceMetadataKey.MODEL_ID] == model_info.model_id


def test_classifier_evaluate(multiclass_logistic_regressor_model_uri, iris_dataset):
    y_true = iris_dataset.labels_data
    classifier_model = mlflow.pyfunc.load_model(multiclass_logistic_regressor_model_uri)
    y_pred = classifier_model.predict(iris_dataset.features_data)
    expected_accuracy_score = accuracy_score(y_true, y_pred)
    expected_metrics = {
        "accuracy_score": expected_accuracy_score,
    }
    expected_saved_metrics = {
        "accuracy_score": expected_accuracy_score,
    }

    expected_csv_artifact = confusion_matrix(y_true, y_pred)
    cm_figure = sklearn.metrics.ConfusionMatrixDisplay.from_predictions(y_true, y_pred).figure_
    img_buf = io.BytesIO()
    cm_figure.savefig(img_buf)
    img_buf.seek(0)
    expected_image_artifact = Image.open(img_buf)

    with mlflow.start_run() as run:
        eval_result = evaluate(
            multiclass_logistic_regressor_model_uri,
            iris_dataset._constructor_args["data"],
            model_type="classifier",
            targets=iris_dataset._constructor_args["targets"],
            evaluators="dummy_evaluator",
        )

    csv_artifact_name = "confusion_matrix"
    saved_csv_artifact_path = get_local_artifact_path(run.info.run_id, csv_artifact_name + ".csv")

    png_artifact_name = "confusion_matrix_image"
    saved_png_artifact_path = get_local_artifact_path(run.info.run_id, png_artifact_name) + ".png"

    _, saved_metrics, _, saved_artifacts = get_run_data(run.info.run_id)
    assert saved_metrics == expected_saved_metrics
    assert set(saved_artifacts) == {csv_artifact_name + ".csv", png_artifact_name + ".png"}

    assert eval_result.metrics == expected_metrics
    confusion_matrix_artifact = eval_result.artifacts[csv_artifact_name]
    np.testing.assert_array_equal(confusion_matrix_artifact.content, expected_csv_artifact)
    assert confusion_matrix_artifact.uri == get_artifact_uri(
        run.info.run_id, csv_artifact_name + ".csv"
    )
    np.testing.assert_array_equal(
        confusion_matrix_artifact._load(saved_csv_artifact_path), expected_csv_artifact
    )
    confusion_matrix_image_artifact = eval_result.artifacts[png_artifact_name]
    assert (
        ImageChops.difference(
            confusion_matrix_image_artifact.content, expected_image_artifact
        ).getbbox()
        is None
    )
    assert confusion_matrix_image_artifact.uri == get_artifact_uri(
        run.info.run_id, png_artifact_name + ".png"
    )
    assert (
        ImageChops.difference(
            confusion_matrix_image_artifact._load(saved_png_artifact_path),
            expected_image_artifact,
        ).getbbox()
        is None
    )

    with TempDir() as temp_dir:
        temp_dir_path = temp_dir.path()
        eval_result.save(temp_dir_path)

        with open(temp_dir.path("metrics.json")) as fp:
            assert json.load(fp) == eval_result.metrics

        with open(temp_dir.path("artifacts_metadata.json")) as fp:
            json_dict = json.load(fp)
            assert "confusion_matrix" in json_dict
            assert json_dict["confusion_matrix"] == {
                "uri": confusion_matrix_artifact.uri,
                "class_name": "mlflow_test_plugin.dummy_evaluator.Array2DEvaluationArtifact",
            }

            assert "confusion_matrix_image" in json_dict
            assert json_dict["confusion_matrix_image"] == {
                "uri": confusion_matrix_image_artifact.uri,
                "class_name": "mlflow.models.evaluation.artifacts.ImageEvaluationArtifact",
            }

        assert set(os.listdir(temp_dir.path("artifacts"))) == {
            "confusion_matrix.csv",
            "confusion_matrix_image.png",
        }

        loaded_eval_result = EvaluationResult.load(temp_dir_path)
        assert loaded_eval_result.metrics == eval_result.metrics
        loaded_confusion_matrix_artifact = loaded_eval_result.artifacts[csv_artifact_name]
        assert confusion_matrix_artifact.uri == loaded_confusion_matrix_artifact.uri
        np.testing.assert_array_equal(
            confusion_matrix_artifact.content,
            loaded_confusion_matrix_artifact.content,
        )
        loaded_confusion_matrix_image_artifact = loaded_eval_result.artifacts[png_artifact_name]
        assert confusion_matrix_image_artifact.uri == loaded_confusion_matrix_image_artifact.uri
        assert (
            ImageChops.difference(
                confusion_matrix_image_artifact.content,
                loaded_confusion_matrix_image_artifact.content,
            ).getbbox()
            is None
        )

        new_confusion_matrix_artifact = Array2DEvaluationArtifact(uri=confusion_matrix_artifact.uri)
        new_confusion_matrix_artifact._load()
        np.testing.assert_array_equal(
            confusion_matrix_artifact.content,
            new_confusion_matrix_artifact.content,
        )
        new_confusion_matrix_image_artifact = ImageEvaluationArtifact(
            uri=confusion_matrix_image_artifact.uri
        )
        new_confusion_matrix_image_artifact._load()
        np.testing.assert_array_equal(
            confusion_matrix_image_artifact.content,
            new_confusion_matrix_image_artifact.content,
        )


def test_regressor_evaluate(linear_regressor_model_uri, diabetes_dataset):
    y_true = diabetes_dataset.labels_data
    regressor_model = mlflow.pyfunc.load_model(linear_regressor_model_uri)
    y_pred = regressor_model.predict(diabetes_dataset.features_data)
    expected_mae = mean_absolute_error(y_true, y_pred)
    expected_mse = mean_squared_error(y_true, y_pred)
    expected_metrics = {
        "mean_absolute_error": expected_mae,
        "mean_squared_error": expected_mse,
    }
    expected_saved_metrics = {
        "mean_absolute_error": expected_mae,
        "mean_squared_error": expected_mse,
    }

    with mlflow.start_run() as run:
        eval_result = evaluate(
            linear_regressor_model_uri,
            diabetes_dataset._constructor_args["data"],
            model_type="regressor",
            targets=diabetes_dataset._constructor_args["targets"],
            evaluators="dummy_evaluator",
        )
    _, saved_metrics, _, _ = get_run_data(run.info.run_id)
    assert saved_metrics == expected_saved_metrics
    assert eval_result.metrics == expected_metrics


def _load_diabetes_dataset_in_required_format(format):
    data = sklearn.datasets.load_diabetes()
    if format == "numpy":
        return data.data, data.target
    elif format == "pandas":
        df = pd.DataFrame(data.data, columns=data.feature_names)
        df["label"] = data.target
        return df, "label"
    elif format == "spark":
        spark = SparkSession.builder.master("local[*]").getOrCreate()
        panda_df = pd.DataFrame(data.data, columns=data.feature_names)
        panda_df["label"] = data.target
        spark_df = spark.createDataFrame(panda_df)
        return spark_df, "label"
    elif format == "list":
        return data.data.tolist(), data.target.tolist()
    else:
        raise TypeError(
            f"`format` must be one of 'numpy', 'pandas', 'spark' or 'list', but received {format}."
        )


@pytest.mark.parametrize("data_format", ["list", "numpy", "pandas", "spark"])
def test_regressor_evaluation(linear_regressor_model_uri, data_format):
    data, target = _load_diabetes_dataset_in_required_format(data_format)

    with mlflow.start_run() as run:
        eval_result = evaluate(
            linear_regressor_model_uri,
            data=data,
            targets=target,
            model_type="regressor",
            evaluators=["default"],
        )
    _, saved_metrics, _, _ = get_run_data(run.info.run_id)

    for k, v in eval_result.metrics.items():
        assert v == saved_metrics[k]

    datasets = get_run_datasets(run.info.run_id)
    assert len(datasets) == 1
    assert len(datasets[0].tags) == 0
    assert datasets[0].dataset.source_type == "code"


def test_pandas_df_regressor_evaluation_mlflow_dataset_with_metric_prefix(
    linear_regressor_model_uri,
):
    data = sklearn.datasets.load_diabetes()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["y"] = data.target
    mlflow_df = from_pandas(df=df, source="my_src", targets="y")
    with mlflow.start_run() as run:
        eval_result = evaluate(
            linear_regressor_model_uri,
            data=mlflow_df,
            model_type="regressor",
            evaluators=["default"],
            evaluator_config={
                "default": {
                    "metric_prefix": "eval",
                }
            },
        )
    _, saved_metrics, _, _ = get_run_data(run.info.run_id)

    for k, v in eval_result.metrics.items():
        assert v == saved_metrics[k]

    datasets = get_run_datasets(run.info.run_id)
    assert len(datasets) == 1
    assert datasets[0].tags[0].value == "eval"


def test_pandas_df_regressor_evaluation_mlflow_dataset(linear_regressor_model_uri):
    data = sklearn.datasets.load_diabetes()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["y"] = data.target
    mlflow_df = from_pandas(df=df, source="my_src", targets="y")
    with mlflow.start_run() as run:
        eval_result = evaluate(
            linear_regressor_model_uri,
            data=mlflow_df,
            model_type="regressor",
            evaluators=["default"],
        )
    _, saved_metrics, _, _ = get_run_data(run.info.run_id)

    for k, v in eval_result.metrics.items():
        assert v == saved_metrics[k]

    datasets = get_run_datasets(run.info.run_id)
    assert len(datasets) == 1
    assert len(datasets[0].tags) == 0


def test_pandas_df_regressor_evaluation_mlflow_dataset_with_targets_from_dataset(
    linear_regressor_model_uri,
):
    data = sklearn.datasets.load_diabetes()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["y"] = data.target
    mlflow_df = from_pandas(df=df, source="my_src", targets="y")
    with mlflow.start_run() as run:
        eval_result = evaluate(
            linear_regressor_model_uri,
            data=mlflow_df,
            model_type="regressor",
            evaluators=["default"],
        )
    _, saved_metrics, _, _ = get_run_data(run.info.run_id)

    for k, v in eval_result.metrics.items():
        assert v == saved_metrics[k]

    datasets = get_run_datasets(run.info.run_id)
    assert len(datasets) == 1
    assert len(datasets[0].tags) == 0


def test_dataset_name():
    X, y = get_iris()
    d1 = EvaluationDataset(data=X, targets=y, name="a1")
    assert d1.name == "a1"
    d2 = EvaluationDataset(data=X, targets=y)
    assert d2.name == d2.hash


def test_dataset_metadata():
    X, y = get_iris()
    d1 = EvaluationDataset(data=X, targets=y, name="a1", path="/path/to/a1")
    assert d1._metadata == {
        "hash": "6bdf4e119bf1a37e7907dfd9f0e68733",
        "name": "a1",
        "path": "/path/to/a1",
    }


def test_gen_md5_for_arraylike_obj():
    def get_md5(data):
        md5_gen = hashlib.md5(usedforsecurity=False)
        _gen_md5_for_arraylike_obj(md5_gen, data)
        return md5_gen.hexdigest()

    list0 = list(range(20))
    list1 = [100] + list0[1:]
    list2 = list0[:-1] + [100]
    list3 = list0[:10] + [100] + list0[10:]

    assert len({get_md5(list0), get_md5(list1), get_md5(list2), get_md5(list3)}) == 4

    list4 = list0[:10] + [99] + list0[10:]
    assert get_md5(list3) == get_md5(list4)


def test_gen_md5_for_arraylike_obj_with_pandas_df_using_float_idx_does_not_raise_keyerror():
    float_indices = np.random.uniform(low=0.5, high=13.3, size=(10,))
    df = pd.DataFrame(np.random.randn(10, 4), index=float_indices, columns=["A", "B", "C", "D"])
    md5_gen = hashlib.md5(usedforsecurity=False)
    assert _gen_md5_for_arraylike_obj(md5_gen, df) is None


def test_dataset_hash(
    iris_dataset, iris_pandas_df_dataset, iris_pandas_df_num_cols_dataset, diabetes_spark_dataset
):
    assert iris_dataset.hash == "99329a790dc483e7382c0d1d27aac3f3"
    assert iris_pandas_df_dataset.hash == "799d4f50e2e353127f94a0e5300add06"
    assert iris_pandas_df_num_cols_dataset.hash == "3c5fc56830a0646001253e25e17bdce4"
    assert diabetes_spark_dataset.hash == "ebfb050519e7e5b463bd38b0c8d04243"


def test_trace_dataset_hash():
    # Validates that a dataset containing Traces can be hashed.
    df = pd.DataFrame(
        {
            "request": ["Hello"],
            "trace": [Trace(info=create_test_trace_info("tr"), data=TraceData([]))],
        }
    )
    dataset = EvaluationDataset(data=df)
    assert dataset.hash == "757c14bf38aa42d36b93ccd70b1ea719"
    # Hash of a dataset with a different column should be different
    df2 = pd.DataFrame(
        {
            "request": ["Hi"],
            "trace": [Trace(info=create_test_trace_info("tr"), data=TraceData([]))],
        }
    )
    dataset2 = EvaluationDataset(data=df2)
    assert dataset2.hash != dataset.hash


def test_dataset_with_pandas_dataframe():
    data = pd.DataFrame({"f1": [1, 2], "f2": [3, 4], "f3": [5, 6], "label": [0, 1]})
    eval_dataset = EvaluationDataset(data=data, targets="label")

    assert list(eval_dataset.features_data.columns) == ["f1", "f2", "f3"]
    np.testing.assert_array_equal(eval_dataset.features_data.f1.to_numpy(), [1, 2])
    np.testing.assert_array_equal(eval_dataset.features_data.f2.to_numpy(), [3, 4])
    np.testing.assert_array_equal(eval_dataset.features_data.f3.to_numpy(), [5, 6])
    np.testing.assert_array_equal(eval_dataset.labels_data, [0, 1])

    eval_dataset2 = EvaluationDataset(data=data, targets="label", feature_names=["f3", "f2"])
    assert list(eval_dataset2.features_data.columns) == ["f3", "f2"]
    np.testing.assert_array_equal(eval_dataset2.features_data.f2.to_numpy(), [3, 4])
    np.testing.assert_array_equal(eval_dataset2.features_data.f3.to_numpy(), [5, 6])


def test_dataset_with_array_data():
    features = [[1, 2], [3, 4]]
    labels = [0, 1]

    for input_data in [features, np.array(features)]:
        eval_dataset1 = EvaluationDataset(data=input_data, targets=labels)
        np.testing.assert_array_equal(eval_dataset1.features_data, features)
        np.testing.assert_array_equal(eval_dataset1.labels_data, labels)
        assert list(eval_dataset1.feature_names) == ["feature_1", "feature_2"]

    assert EvaluationDataset(
        data=input_data, targets=labels, feature_names=["a", "b"]
    ).feature_names == ["a", "b"]

    with pytest.raises(MlflowException, match="all elements must have the same length"):
        EvaluationDataset(data=[[1, 2], [3, 4, 5]], targets=labels)


def test_dataset_autogen_feature_names():
    labels = [0]
    eval_dataset2 = EvaluationDataset(data=[list(range(9))], targets=labels)
    assert eval_dataset2.feature_names == [f"feature_{i + 1}" for i in range(9)]

    eval_dataset2 = EvaluationDataset(data=[list(range(10))], targets=labels)
    assert eval_dataset2.feature_names == [f"feature_{i + 1:02d}" for i in range(10)]

    eval_dataset2 = EvaluationDataset(data=[list(range(99))], targets=labels)
    assert eval_dataset2.feature_names == [f"feature_{i + 1:02d}" for i in range(99)]

    eval_dataset2 = EvaluationDataset(data=[list(range(100))], targets=labels)
    assert eval_dataset2.feature_names == [f"feature_{i + 1:03d}" for i in range(100)]

    with pytest.raises(
        MlflowException, match="features example rows must be the same length with labels array"
    ):
        EvaluationDataset(data=[[1, 2], [3, 4]], targets=[1, 2, 3])


def test_dataset_from_spark_df(spark_session):
    spark_df = spark_session.createDataFrame([(1.0, 2.0, 3.0)] * 10, ["f1", "f2", "y"])
    with mock.patch.object(EvaluationDataset, "SPARK_DATAFRAME_LIMIT", 5):
        dataset = EvaluationDataset(spark_df, targets="y")
        assert list(dataset.features_data.columns) == ["f1", "f2"]
        assert list(dataset.features_data["f1"]) == [1.0] * 5
        assert list(dataset.features_data["f2"]) == [2.0] * 5
        assert list(dataset.labels_data) == [3.0] * 5


def test_log_dataset_tag(iris_dataset, iris_pandas_df_dataset):
    model_uuid = uuid.uuid4().hex
    with mlflow.start_run() as run:
        client = MlflowClient()
        iris_dataset._log_dataset_tag(client, run.info.run_id, model_uuid=model_uuid)
        _, _, tags, _ = get_run_data(run.info.run_id)

        logged_meta1 = {**iris_dataset._metadata, "model": model_uuid}
        logged_meta2 = {**iris_pandas_df_dataset._metadata, "model": model_uuid}

        assert json.loads(tags["mlflow.datasets"]) == [logged_meta1]

        raw_tag = get_raw_tag(run.info.run_id, "mlflow.datasets")
        assert " " not in raw_tag  # assert the tag string remove all whitespace chars.

        # Test appending dataset tag
        iris_pandas_df_dataset._log_dataset_tag(client, run.info.run_id, model_uuid=model_uuid)
        _, _, tags, _ = get_run_data(run.info.run_id)
        assert json.loads(tags["mlflow.datasets"]) == [
            logged_meta1,
            logged_meta2,
        ]

        # Test log repetitive dataset
        iris_dataset._log_dataset_tag(client, run.info.run_id, model_uuid=model_uuid)
        _, _, tags, _ = get_run_data(run.info.run_id)
        assert json.loads(tags["mlflow.datasets"]) == [
            logged_meta1,
            logged_meta2,
        ]


class FakeEvaluator1(ModelEvaluator):
    @classmethod
    def can_evaluate(cls, *, model_type, evaluator_config, **kwargs):
        raise RuntimeError()

    def evaluate(self, *, model, model_type, dataset, run_id, evaluator_config, **kwargs):
        raise RuntimeError()


class FakeEvaluator2(ModelEvaluator):
    @classmethod
    def can_evaluate(cls, *, model_type, evaluator_config, **kwargs):
        raise RuntimeError()

    def evaluate(self, *, model, model_type, dataset, run_id, evaluator_config, **kwargs):
        raise RuntimeError()


class FakeArtifact1(EvaluationArtifact):
    def _save(self, output_artifact_path):
        raise RuntimeError()

    def _load_content_from_file(self, local_artifact_path):
        raise RuntimeError()


class FakeArtifact2(EvaluationArtifact):
    def _save(self, output_artifact_path):
        raise RuntimeError()

    def _load_content_from_file(self, local_artifact_path):
        raise RuntimeError()


class PyFuncModelMatcher:
    def __eq__(self, other):
        return isinstance(other, mlflow.pyfunc.PyFuncModel)


class ModelPredictFuncMatcher:
    def __eq__(self, other):
        return callable(other)


def test_evaluator_evaluation_interface(multiclass_logistic_regressor_model_uri, iris_dataset):
    with mock.patch.object(
        _model_evaluation_registry, "_registry", {"test_evaluator1": FakeEvaluator1}
    ):
        evaluator1_config = {"eval1_confg_a": 3, "eval1_confg_b": 4}
        evaluator1_return_value = EvaluationResult(
            metrics={"m1": 5, "m2": 6},
            artifacts={"a1": FakeArtifact1(uri="uri1"), "a2": FakeArtifact2(uri="uri2")},
        )
        with (
            mock.patch.object(
                FakeEvaluator1, "can_evaluate", return_value=False
            ) as mock_can_evaluate,
            mock.patch.object(
                FakeEvaluator1, "evaluate", return_value=evaluator1_return_value
            ) as mock_evaluate,
        ):
            with mlflow.start_run():
                with pytest.raises(
                    MlflowException,
                    match="The model could not be evaluated by any of the registered evaluators",
                ):
                    evaluate(
                        multiclass_logistic_regressor_model_uri,
                        data=iris_dataset._constructor_args["data"],
                        model_type="classifier",
                        targets=iris_dataset._constructor_args["targets"],
                        evaluators="test_evaluator1",
                        evaluator_config=evaluator1_config,
                    )
                mock_can_evaluate.assert_called_once_with(
                    model_type="classifier", evaluator_config=evaluator1_config
                )
                mock_evaluate.assert_not_called()
        with (
            mock.patch.object(
                FakeEvaluator1, "can_evaluate", return_value=True
            ) as mock_can_evaluate,
            mock.patch.object(
                FakeEvaluator1, "evaluate", return_value=evaluator1_return_value
            ) as mock_evaluate,
        ):
            with mlflow.start_run() as run:
                eval1_result = evaluate(
                    multiclass_logistic_regressor_model_uri,
                    iris_dataset._constructor_args["data"],
                    model_type="classifier",
                    targets=iris_dataset._constructor_args["targets"],
                    evaluators="test_evaluator1",
                    evaluator_config=evaluator1_config,
                    extra_metrics=None,
                )
                assert eval1_result.metrics == evaluator1_return_value.metrics
                assert eval1_result.artifacts == evaluator1_return_value.artifacts

                mock_can_evaluate.assert_called_once_with(
                    model_type="classifier", evaluator_config=evaluator1_config
                )
                mock_evaluate.assert_called_once_with(
                    model=PyFuncModelMatcher(),
                    model_type="classifier",
                    model_id=multiclass_logistic_regressor_model_uri.split("/")[-1],
                    dataset=iris_dataset,
                    run_id=run.info.run_id,
                    evaluator_config=evaluator1_config,
                    extra_metrics=None,
                    custom_artifacts=None,
                    predictions=None,
                )


def test_evaluate_with_multi_evaluators(
    multiclass_logistic_regressor_model_uri,
    iris_dataset,
):
    with mock.patch.object(
        _model_evaluation_registry,
        "_registry",
        {"test_evaluator1": FakeEvaluator1, "test_evaluator2": FakeEvaluator2},
    ):
        evaluator1_config = {"eval1_confg": 3}
        evaluator2_config = {"eval2_confg": 4}
        evaluator1_return_value = EvaluationResult(
            metrics={"m1": 5}, artifacts={"a1": FakeArtifact1(uri="uri1")}
        )

        evaluator2_return_value = EvaluationResult(
            metrics={"m2": 6}, artifacts={"a2": FakeArtifact2(uri="uri2")}
        )

        def get_evaluate_call_arg(model, evaluator_config):
            return {
                "model": model,
                "model_type": "classifier",
                "model_id": model.model_id,
                "dataset": iris_dataset,
                "run_id": run.info.run_id,
                "evaluator_config": evaluator_config,
                "extra_metrics": None,
                "custom_artifacts": None,
                "predictions": None,
            }

        # evaluators = None is the case evaluators unspecified, it should fetch all registered
        # evaluators, and the evaluation results should equal to the case of
        # evaluators=["test_evaluator1", "test_evaluator2"]
        for evaluators in [None, ["test_evaluator1", "test_evaluator2"]]:
            with (
                mock.patch.object(
                    FakeEvaluator1, "can_evaluate", return_value=True
                ) as mock_can_evaluate1,
                mock.patch.object(
                    FakeEvaluator1, "evaluate", return_value=evaluator1_return_value
                ) as mock_evaluate1,
                mock.patch.object(
                    FakeEvaluator2, "can_evaluate", return_value=True
                ) as mock_can_evaluate2,
                mock.patch.object(
                    FakeEvaluator2, "evaluate", return_value=evaluator2_return_value
                ) as mock_evaluate2,
            ):
                with mlflow.start_run() as run:
                    eval_result = evaluate(
                        multiclass_logistic_regressor_model_uri,
                        iris_dataset._constructor_args["data"],
                        model_type="classifier",
                        targets=iris_dataset._constructor_args["targets"],
                        evaluators=evaluators,
                        evaluator_config={
                            "test_evaluator1": evaluator1_config,
                            "test_evaluator2": evaluator2_config,
                        },
                    )
                    assert eval_result.metrics == {
                        **evaluator1_return_value.metrics,
                        **evaluator2_return_value.metrics,
                    }
                    assert eval_result.artifacts == {
                        **evaluator1_return_value.artifacts,
                        **evaluator2_return_value.artifacts,
                    }
                    mock_evaluate1.assert_called_once_with(
                        **get_evaluate_call_arg(
                            mlflow.pyfunc.load_model(multiclass_logistic_regressor_model_uri),
                            evaluator1_config,
                        )
                    )
                    mock_can_evaluate1.assert_has_calls(
                        [mock.call(model_type="classifier", evaluator_config=evaluator1_config)]
                    )
                    mock_evaluate2.assert_called_once_with(
                        **get_evaluate_call_arg(
                            mlflow.pyfunc.load_model(multiclass_logistic_regressor_model_uri),
                            evaluator2_config,
                        )
                    )
                    mock_can_evaluate2.assert_has_calls(
                        [mock.call(model_type="classifier", evaluator_config=evaluator2_config)]
                    )


def test_custom_evaluators_no_model_or_preds(multiclass_logistic_regressor_model_uri, iris_dataset):
    """
    Tests that custom evaluators are called correctly when no model or predictions are provided
    """
    with mock.patch.object(
        _model_evaluation_registry, "_registry", {"test_evaluator1": FakeEvaluator1}
    ):
        with (
            mock.patch.object(
                FakeEvaluator1, "can_evaluate", return_value=True
            ) as mock_can_evaluate,
            mock.patch.object(FakeEvaluator1, "evaluate") as mock_evaluate,
        ):
            with mlflow.start_run() as run:
                evaluate(
                    model=None,
                    data=iris_dataset._constructor_args["data"],
                    predictions=None,
                    model_type="classifier",
                    targets=iris_dataset._constructor_args["targets"],
                    evaluators="test_evaluator1",
                    evaluator_config=None,
                    extra_metrics=None,
                )

                mock_can_evaluate.assert_called_once_with(
                    model_type="classifier", evaluator_config={}
                )
                mock_evaluate.assert_called_once_with(
                    model=None,
                    dataset=iris_dataset,
                    predictions=None,
                    model_type="classifier",
                    model_id=None,
                    run_id=run.info.run_id,
                    evaluator_config={},
                    extra_metrics=None,
                    custom_artifacts=None,
                )


def test_start_run_or_reuse_active_run():
    with _start_run_or_reuse_active_run() as run_id:
        assert mlflow.active_run().info.run_id == run_id

    with mlflow.start_run() as run:
        active_run_id = run.info.run_id

        with _start_run_or_reuse_active_run() as run_id:
            assert run_id == active_run_id

        with _start_run_or_reuse_active_run() as run_id:
            assert run_id == active_run_id


def test_resolve_evaluators_and_configs():
    from mlflow.models.evaluation.evaluators.classifier import ClassifierEvaluator
    from mlflow.models.evaluation.evaluators.default import DefaultEvaluator
    from mlflow.models.evaluation.evaluators.regressor import RegressorEvaluator
    from mlflow.models.evaluation.evaluators.shap import ShapEvaluator

    def assert_equal(actual, expected):
        assert len(actual) == len(expected)
        for actual_i, expected_i in zip(actual, expected):
            assert actual_i.name == expected_i[0]
            assert isinstance(actual_i.evaluator, expected_i[1])
            assert actual_i.config == expected_i[2]

    with mock.patch.object(
        _model_evaluation_registry,
        "_registry",
        {"default": DefaultEvaluator},
    ):
        assert_equal(
            resolve_evaluators_and_configs(None, None), [("default", DefaultEvaluator, {})]
        )
        assert_equal(
            actual=resolve_evaluators_and_configs(None, {"a": 3}),
            expected=[("default", DefaultEvaluator, {"a": 3})],
        )
        assert_equal(
            actual=resolve_evaluators_and_configs(None, {"default": {"a": 3}}),
            expected=[("default", DefaultEvaluator, {"a": 3})],
        )

    # 1. evaluators is None -> only default evaluator is used
    assert_equal(
        actual=resolve_evaluators_and_configs(None, None),
        expected=[("default", DefaultEvaluator, {})],
    )
    assert_equal(
        actual=resolve_evaluators_and_configs(None, {"a": 3}),
        expected=[("default", DefaultEvaluator, {"a": 3})],
    )

    # 2. evaluators is None and model type is classifier -> builtin classifier evaluators
    #   are used instead of the default. Also dummy evaluator can evaluate classifier.
    assert_equal(
        actual=resolve_evaluators_and_configs(
            evaluators=None, evaluator_config={"a": 3}, model_type="classifier"
        ),
        expected=[
            ("classifier", ClassifierEvaluator, {"a": 3}),
            ("shap", ShapEvaluator, {"a": 3}),
            ("dummy_evaluator", DummyEvaluator, {"a": 3}),
        ],
    )

    assert_equal(
        resolve_evaluators_and_configs(
            evaluators=None,
            # config for a specific evaluator
            evaluator_config={"shap": {"a": 3}},
            model_type="classifier",
        ),
        expected=[
            ("classifier", ClassifierEvaluator, {}),
            ("shap", ShapEvaluator, {"a": 3}),
            ("dummy_evaluator", DummyEvaluator, {}),
        ],
    )

    assert_equal(
        resolve_evaluators_and_configs(
            evaluators=None,
            # config for a "default" copied to builtin evaluators
            evaluator_config={"default": {"a": 3}},
            model_type="classifier",
        ),
        expected=[
            ("classifier", ClassifierEvaluator, {"a": 3}),
            ("shap", ShapEvaluator, {"a": 3}),
            ("dummy_evaluator", DummyEvaluator, {}),
        ],
    )

    # 3. evaluators is string -> the specified evaluator is used
    assert_equal(
        actual=resolve_evaluators_and_configs("dummy_evaluator", {"a": 3}, "regressor"),
        expected=[("dummy_evaluator", DummyEvaluator, {"a": 3})],
    )
    assert_equal(
        actual=resolve_evaluators_and_configs("default", {"a": 3}),
        expected=[("default", DefaultEvaluator, {"a": 3})],
    )
    assert_equal(
        actual=resolve_evaluators_and_configs("default", {"a": 3}, "regressor"),
        expected=[
            ("regressor", RegressorEvaluator, {"a": 3}),
            ("shap", ShapEvaluator, {"a": 3}),
        ],
    )
    assert_equal(
        actual=resolve_evaluators_and_configs("regressor", {"a": 3}, "regressor"),
        expected=[("regressor", RegressorEvaluator, {"a": 3})],
    )
    assert_equal(
        actual=resolve_evaluators_and_configs("non-existing", {"a": 3}),
        expected=[],  # empty because not registered evaluator
    )

    # 4. evaluators is a list of strings -> the specified evaluators are used
    assert_equal(
        actual=resolve_evaluators_and_configs(
            evaluators=["default", "dummy_evaluator"],
            evaluator_config={"dummy_evaluator": {"a": 3}, "default": {"a": 5}},
            model_type="classifier",
        ),
        expected=[
            ("classifier", ClassifierEvaluator, {"a": 5}),
            ("shap", ShapEvaluator, {"a": 5}),
            ("dummy_evaluator", DummyEvaluator, {"a": 3}),
        ],
    )

    assert_equal(
        actual=resolve_evaluators_and_configs(
            evaluators=["regressor"],
            evaluator_config={"regressor": {"a": 5}},
            model_type="regressor",
        ),
        expected=[("regressor", RegressorEvaluator, {"a": 5})],
    )

    with pytest.raises(
        MlflowException,
        match="If `evaluators` argument is an evaluator name list, evaluator_config must",
    ):
        resolve_evaluators_and_configs(["default", "dummy_evaluator"], {"abc": {"a": 3}})


def test_resolve_evaluators_raise_for_missing_databricks_agent_dependency():
    with pytest.raises(
        MlflowException,
        match="Databricks Agents SDK must be installed to use the `databricks-agent` model type.",
    ):
        resolve_evaluators_and_configs(
            evaluators=None, evaluator_config=None, model_type="databricks-agent"
        )


def test_evaluate_env_manager_params(multiclass_logistic_regressor_model_uri, iris_dataset):
    model = mlflow.pyfunc.load_model(multiclass_logistic_regressor_model_uri)

    with mock.patch.object(
        _model_evaluation_registry, "_registry", {"test_evaluator1": FakeEvaluator1}
    ):
        with pytest.raises(MlflowException, match="The model argument must be a string URI"):
            evaluate(
                model,
                iris_dataset._constructor_args["data"],
                model_type="classifier",
                targets=iris_dataset._constructor_args["targets"],
                evaluators=None,
                env_manager="virtualenv",
            )

        with pytest.raises(MlflowException, match="Invalid value for `env_manager`"):
            evaluate(
                multiclass_logistic_regressor_model_uri,
                iris_dataset._constructor_args["data"],
                model_type="classifier",
                targets=iris_dataset._constructor_args["targets"],
                evaluators=None,
                env_manager="manager",
            )


@pytest.mark.parametrize("env_manager", ["virtualenv", "conda"])
def test_evaluate_restores_env(tmp_path, env_manager, iris_dataset):
    class EnvRestoringTestModel(mlflow.pyfunc.PythonModel):
        def __init__(self):
            pass

        def predict(self, context, model_input, params=None):
            pred_value = 1 if sklearn.__version__ == "1.4.2" else 0

            return model_input.apply(lambda row: pred_value, axis=1)

    class FakeEvauatorEnv(ModelEvaluator):
        @classmethod
        def can_evaluate(cls, *, model_type, evaluator_config, **kwargs):
            return True

        def evaluate(self, *, model, model_type, dataset, run_id, evaluator_config, **kwargs):
            y = model.predict(pd.DataFrame(dataset.features_data))
            return EvaluationResult(metrics={"test": y[0]}, artifacts={})

    model_path = os.path.join(tmp_path, "model")

    mlflow.pyfunc.save_model(
        path=model_path,
        python_model=EnvRestoringTestModel(),
        pip_requirements=["scikit-learn==1.4.2"],
    )

    with mock.patch.object(
        _model_evaluation_registry,
        "_registry",
        {"test_evaluator_env": FakeEvauatorEnv},
    ):
        result = evaluate(
            model_path,
            iris_dataset._constructor_args["data"],
            model_type="classifier",
            targets=iris_dataset._constructor_args["targets"],
            evaluators=None,
            env_manager=env_manager,
        )
        assert result.metrics["test"] == 1


def test_evaluate_terminates_model_servers(multiclass_logistic_regressor_model_uri, iris_dataset):
    # Mock the _load_model_or_server() results to avoid starting model servers
    model = mlflow.pyfunc.load_model(multiclass_logistic_regressor_model_uri)
    client = ScoringServerClient("127.0.0.1", "8080")
    served_model_1 = _ServedPyFuncModel(model_meta=model.metadata, client=client, server_pid=1)
    served_model_2 = _ServedPyFuncModel(model_meta=model.metadata, client=client, server_pid=2)

    with (
        mock.patch.object(
            _model_evaluation_registry,
            "_registry",
            {"test_evaluator1": FakeEvaluator1},
        ),
        mock.patch.object(FakeEvaluator1, "can_evaluate", return_value=True),
        mock.patch.object(
            FakeEvaluator1, "evaluate", return_value=EvaluationResult(metrics={}, artifacts={})
        ),
        mock.patch("mlflow.pyfunc._load_model_or_server") as server_loader,
        mock.patch("os.kill") as os_mock,
    ):
        server_loader.side_effect = [served_model_1, served_model_2]
        evaluate(
            multiclass_logistic_regressor_model_uri,
            iris_dataset._constructor_args["data"],
            model_type="classifier",
            targets=iris_dataset._constructor_args["targets"],
            evaluators=None,
            env_manager="virtualenv",
        )
        assert os_mock.call_count == 1
        os_mock.assert_has_calls([mock.call(1, signal.SIGTERM)])


def test_evaluate_stdin_scoring_server():
    X, y = sklearn.datasets.load_iris(return_X_y=True)
    X = X[::5]
    y = y[::5]
    model = sklearn.linear_model.LogisticRegression()
    model.fit(X, y)

    with mlflow.start_run():
        model_info = mlflow.sklearn.log_model(model, name="model")

    with mock.patch("mlflow.pyfunc.check_port_connectivity", return_value=False):
        mlflow.evaluate(
            model_info.model_uri,
            X,
            targets=y,
            model_type="classifier",
            evaluators=["default"],
            env_manager="virtualenv",
        )


@pytest.mark.parametrize("model_type", ["regressor", "classifier"])
def test_targets_is_required_for_regressor_and_classifier_models(model_type):
    with pytest.raises(MlflowException, match="The targets argument must be specified"):
        mlflow.evaluate(
            "models:/test",
            data=pd.DataFrame(),
            model_type=model_type,
        )


def test_evaluate_xgboost_classifier():
    import xgboost as xgb

    X, y = sklearn.datasets.load_iris(return_X_y=True, as_frame=True)
    X = X[::5]
    y = y[::5]
    data = xgb.DMatrix(X, label=y)
    model = xgb.train({"objective": "multi:softmax", "num_class": 3}, data, num_boost_round=5)

    with mlflow.start_run() as run:
        model_info = mlflow.xgboost.log_model(model, name="model")
        mlflow.evaluate(
            model_info.model_uri,
            X.assign(y=y),
            targets="y",
            model_type="classifier",
        )

    run = mlflow.get_run(run.info.run_id)
    assert "accuracy_score" in run.data.metrics
    assert "recall_score" in run.data.metrics
    assert "precision_score" in run.data.metrics
    assert "f1_score" in run.data.metrics


def test_evaluate_lightgbm_regressor():
    import lightgbm as lgb

    X, y = sklearn.datasets.load_diabetes(return_X_y=True, as_frame=True)
    X = X[::5]
    y = y[::5]
    data = lgb.Dataset(X, label=y)
    model = lgb.train({"objective": "regression"}, data, num_boost_round=5)

    with mlflow.start_run() as run:
        model_info = mlflow.lightgbm.log_model(model, name="model")
        mlflow.evaluate(
            model_info.model_uri,
            X.assign(y=y),
            targets="y",
            model_type="regressor",
        )

    run = mlflow.get_run(run.info.run_id)
    assert "mean_absolute_error" in run.data.metrics
    assert "mean_squared_error" in run.data.metrics
    assert "root_mean_squared_error" in run.data.metrics


def test_evaluate_with_targets_error_handling():
    import lightgbm as lgb

    X, y = sklearn.datasets.load_diabetes(return_X_y=True, as_frame=True)
    X = X[::5]
    y = y[::5]
    lgb_data = lgb.Dataset(X, label=y)
    model = lgb.train({"objective": "regression"}, lgb_data, num_boost_round=5)
    ERROR_TYPE_1 = (
        "The top-level targets parameter should not be specified since a Dataset "
        "is used. Please only specify the targets column name in the Dataset. For example: "
        "`data = mlflow.data.from_pandas(df=X.assign(y=y), targets='y')`. "
        "Meanwhile, please specify `mlflow.evaluate(..., targets=None, ...)`."
    )
    ERROR_TYPE_2 = (
        "The targets column name must be specified in the provided Dataset "
        "for regressor models. For example: "
        "`data = mlflow.data.from_pandas(df=X.assign(y=y), targets='y')`"
    )
    ERROR_TYPE_3 = "The targets argument must be specified for regressor models."

    pandas_dataset_no_targets = X
    mlflow_dataset_no_targets = mlflow.data.from_pandas(df=X.assign(y=y))
    mlflow_dataset_with_targets = mlflow.data.from_pandas(df=X.assign(y=y), targets="y")

    with mlflow.start_run():
        with pytest.raises(MlflowException, match=re.escape(ERROR_TYPE_1)):
            mlflow.evaluate(
                model=model,
                data=mlflow_dataset_with_targets,
                model_type="regressor",
                targets="y",
            )

        with pytest.raises(MlflowException, match=re.escape(ERROR_TYPE_1)):
            mlflow.evaluate(
                model=model,
                data=mlflow_dataset_no_targets,
                model_type="regressor",
                targets="y",
            )

        with pytest.raises(MlflowException, match=re.escape(ERROR_TYPE_1)):
            mlflow.evaluate(
                model=model,
                data=mlflow_dataset_with_targets,
                model_type="question-answering",
                targets="y",
            )

        with pytest.raises(MlflowException, match=re.escape(ERROR_TYPE_1)):
            mlflow.evaluate(
                model=model,
                data=mlflow_dataset_no_targets,
                model_type="question-answering",
                targets="y",
            )

        with pytest.raises(MlflowException, match=re.escape(ERROR_TYPE_2)):
            mlflow.evaluate(
                model=model,
                data=mlflow_dataset_no_targets,
                model_type="regressor",
            )

        with pytest.raises(MlflowException, match=re.escape(ERROR_TYPE_3)):
            mlflow.evaluate(
                model=model,
                data=pandas_dataset_no_targets,
                model_type="regressor",
            )


def test_evaluate_with_predictions_error_handling():
    import lightgbm as lgb

    X, y = sklearn.datasets.load_diabetes(return_X_y=True, as_frame=True)
    X = X[::5]
    y = y[::5]
    lgb_data = lgb.Dataset(X, label=y)
    model = lgb.train({"objective": "regression"}, lgb_data, num_boost_round=5)
    mlflow_dataset_with_predictions = mlflow.data.from_pandas(
        df=X.assign(y=y, model_output=y),
        targets="y",
        predictions="model_output",
    )
    with mlflow.start_run():
        with pytest.raises(
            MlflowException,
            match="The predictions parameter should not be specified in the Dataset since a model "
            "is specified. Please remove the predictions column from the Dataset.",
        ):
            mlflow.evaluate(
                model=model,
                data=mlflow_dataset_with_predictions,
                model_type="regressor",
            )


def test_evaluate_with_function_input_single_output():
    import lightgbm as lgb

    X, y = sklearn.datasets.load_diabetes(return_X_y=True, as_frame=True)
    X = X[::5]
    y = y[::5]
    data = lgb.Dataset(X, label=y)
    model = lgb.train({"objective": "regression"}, data, num_boost_round=5)

    def fn(X):
        return model.predict(X)

    with mlflow.start_run() as run:
        mlflow.evaluate(
            fn,
            X.assign(y=y),
            targets="y",
            model_type="regressor",
        )
    run = mlflow.get_run(run.info.run_id)
    assert "mean_absolute_error" in run.data.metrics
    assert "mean_squared_error" in run.data.metrics
    assert "root_mean_squared_error" in run.data.metrics


def test_evaluate_with_loaded_pyfunc_model():
    import lightgbm as lgb

    X, y = sklearn.datasets.load_diabetes(return_X_y=True, as_frame=True)
    X = X[::5]
    y = y[::5]
    data = lgb.Dataset(X, label=y)
    model = lgb.train({"objective": "regression"}, data, num_boost_round=5)

    with mlflow.start_run() as run:
        model_info = mlflow.lightgbm.log_model(model, name="model")
        loaded_model = mlflow.pyfunc.load_model(model_info.model_uri)
        mlflow.evaluate(
            loaded_model,
            X.assign(y=y),
            targets="y",
            model_type="regressor",
        )

    run = mlflow.get_run(run.info.run_id)
    assert "mean_absolute_error" in run.data.metrics
    assert "mean_squared_error" in run.data.metrics
    assert "root_mean_squared_error" in run.data.metrics


def test_evaluate_with_static_dataset_input_single_output():
    X, y = sklearn.datasets.load_diabetes(return_X_y=True, as_frame=True)
    X = X[::5]
    y = y[::5]
    with mlflow.start_run() as run:
        mlflow.evaluate(
            data=X.assign(y=y, model_output=y),
            targets="y",
            predictions="model_output",
            model_type="regressor",
        )

    run = mlflow.get_run(run.info.run_id)
    assert "mean_absolute_error" in run.data.metrics
    assert "mean_squared_error" in run.data.metrics
    assert "root_mean_squared_error" in run.data.metrics


def test_evaluate_with_static_mlflow_dataset_input():
    X, y = sklearn.datasets.load_diabetes(return_X_y=True, as_frame=True)
    X = X[::5]
    y = y[::5]
    data = mlflow.data.from_pandas(
        df=X.assign(y=y, model_output=y), targets="y", predictions="model_output"
    )
    with mlflow.start_run() as run:
        mlflow.evaluate(
            data=data,
            model_type="regressor",
        )

    run = mlflow.get_run(run.info.run_id)
    assert "mean_absolute_error" in run.data.metrics
    assert "mean_squared_error" in run.data.metrics
    assert "root_mean_squared_error" in run.data.metrics


def test_evaluate_with_static_dataset_error_handling_pandas_dataframe():
    X, y = sklearn.datasets.load_diabetes(return_X_y=True, as_frame=True)
    X = X[::5]
    y = y[::5]
    with mlflow.start_run():
        with pytest.raises(MlflowException, match="The data argument cannot be None."):
            mlflow.evaluate(
                data=None,
                targets="y",
                model_type="regressor",
            )

        with pytest.raises(
            MlflowException,
            match="The specified pandas DataFrame does not contain the specified predictions"
            " column 'prediction'.",
        ):
            mlflow.evaluate(
                data=X.assign(y=y, model_output=y),
                targets="y",
                predictions="prediction",
                model_type="regressor",
            )


def test_evaluate_with_static_dataset_error_handling_pandas_dataset():
    X, y = sklearn.datasets.load_diabetes(return_X_y=True, as_frame=True)
    X = X[::5]
    y = y[::5]
    dataset_with_predictions = mlflow.data.from_pandas(
        df=X.assign(y=y, model_output=y), targets="y", predictions="model_output"
    )
    dataset_no_predictions = mlflow.data.from_pandas(df=X.assign(y=y, model_output=y), targets="y")
    ERROR_MESSAGE = (
        "The top-level predictions parameter should not be specified since a Dataset is "
        "used. Please only specify the predictions column name in the Dataset. For example: "
        "`data = mlflow.data.from_pandas(df=X.assign(y=y), predictions='y')`"
        "Meanwhile, please specify `mlflow.evaluate(..., predictions=None, ...)`."
    )
    with mlflow.start_run():
        with pytest.raises(MlflowException, match=re.escape(ERROR_MESSAGE)):
            mlflow.evaluate(
                data=dataset_with_predictions,
                model_type="regressor",
                predictions="model_output",
            )

        with pytest.raises(MlflowException, match=re.escape(ERROR_MESSAGE)):
            mlflow.evaluate(
                data=dataset_no_predictions,
                model_type="regressor",
                predictions="model_output",
            )


def test_binary_classification_missing_minority_class_exception_override(
    binary_logistic_regressor_model_uri, breast_cancer_dataset, monkeypatch
):
    monkeypatch.setenv("_MLFLOW_EVALUATE_SUPPRESS_CLASSIFICATION_ERRORS", True)

    ds_targets = breast_cancer_dataset._constructor_args["targets"]
    # Simulate a missing target label
    ds_targets = np.where(ds_targets == 0, 1, ds_targets)

    with mlflow.start_run() as run:
        eval_result = evaluate(
            binary_logistic_regressor_model_uri,
            breast_cancer_dataset._constructor_args["data"],
            model_type="classifier",
            targets=ds_targets,
            evaluators=["default"],
        )
    _, saved_metrics, _, _ = get_run_data(run.info.run_id)

    for key, saved_val in saved_metrics.items():
        eval_val = eval_result.metrics[key]
        # some nan fields are due to the class imbalance.
        # for example, the roc_auc_score metric will return
        # nan since we override all classes to `1` here
        if np.isnan(saved_val):
            assert np.isnan(eval_val)
        else:
            assert eval_val == saved_val


def test_multiclass_classification_missing_minority_class_exception_override(
    multiclass_logistic_regressor_model_uri, iris_dataset, monkeypatch
):
    monkeypatch.setenv("_MLFLOW_EVALUATE_SUPPRESS_CLASSIFICATION_ERRORS", True)

    ds_targets = iris_dataset._constructor_args["targets"]
    # Simulate a missing target label
    ds_targets = np.where(ds_targets == 0, 1, ds_targets)

    with mlflow.start_run() as run:
        eval_result = evaluate(
            multiclass_logistic_regressor_model_uri,
            iris_dataset._constructor_args["data"],
            model_type="classifier",
            targets=ds_targets,
            evaluators=["default"],
        )
    _, saved_metrics, _, saved_artifacts = get_run_data(run.info.run_id)

    assert saved_metrics == eval_result.metrics
    assert "shap_beeswarm_plot.png" not in saved_artifacts


@pytest.mark.parametrize(
    ("model", "is_endpoint_uri"),
    [
        ("endpoints:/test", True),
        ("endpoints:///my-chat", True),
        ("models:/test", False),
        (None, False),
    ],
)
def test_is_model_deployment_endpoint_uri(model, is_endpoint_uri):
    assert _is_model_deployment_endpoint_uri(model) == is_endpoint_uri


_DUMMY_CHAT_RESPONSE = {
    "id": "1",
    "object": "text_completion",
    "created": "2021-10-01T00:00:00.000000Z",
    "model": "gpt-4o-mini",
    "choices": [
        {
            "index": 0,
            "message": {
                "content": "This is a response",
                "role": "assistant",
            },
            "finish_reason": "length",
        }
    ],
    "usage": {
        "prompt_tokens": 1,
        "completion_tokens": 1,
        "total_tokens": 2,
    },
}

_TEST_QUERY_LIST = ["What is MLflow?", "What is Spark?"]
_TEST_GT_LIST = [
    "MLflow is an open-source platform for machine learning (ML).",
    "Apache Spark is an open-source, distributed computing system.",
]


@pytest.mark.parametrize(
    ("input_data", "feature_names", "targets"),
    [
        # String input column
        (
            pd.DataFrame({"inputs": _TEST_QUERY_LIST, "ground_truth": _TEST_GT_LIST}),
            None,
            "ground_truth",
        ),
        # String input column with feature_names
        (
            pd.DataFrame({"question": _TEST_QUERY_LIST, "ground_truth": _TEST_GT_LIST}),
            ["question"],
            "ground_truth",
        ),
        # Dictionary input column that contains message history
        (
            pd.DataFrame(
                {
                    "inputs": [
                        {
                            "messages": [{"content": q, "role": "user"}],
                            "max_tokens": 10,
                        }
                        for q in _TEST_QUERY_LIST
                    ],
                    "ground_truth": _TEST_GT_LIST,
                }
            ),
            None,
            "ground_truth",
        ),
        # List of string
        (
            _TEST_QUERY_LIST,
            None,
            _TEST_GT_LIST,
        ),
        # List of string with feature_names
        (
            _TEST_QUERY_LIST,
            ["question"],
            _TEST_GT_LIST,
        ),
        # List of string with feature_names and w/o targets
        (
            _TEST_QUERY_LIST,
            ["question"],
            None,
        ),
        # List of dictionary with feature_names
        (
            [
                {
                    "messages": [{"content": q, "role": "user"}],
                    "max_tokens": 10,
                }
                for q in _TEST_QUERY_LIST
            ],
            None,
            _TEST_GT_LIST,
        ),
    ],
)
@mock.patch("mlflow.deployments.get_deploy_client")
def test_evaluate_on_chat_model_endpoint(mock_deploy_client, input_data, feature_names, targets):
    mock_deploy_client.return_value.predict.return_value = _DUMMY_CHAT_RESPONSE
    mock_deploy_client.return_value.get_endpoint.return_value = {"task": "llm/v1/chat"}

    with mlflow.start_run():
        eval_result = mlflow.evaluate(
            model="endpoints:/chat",
            data=input_data,
            model_type="question-answering",
            feature_names=feature_names,
            targets=targets,
            inference_params={"max_tokens": 10, "temperature": 0.5},
        )

    # Validate the endpoint is called with correct payloads
    call_args_list = mock_deploy_client.return_value.predict.call_args_list
    expected_calls = [
        mock.call(
            endpoint="chat",
            inputs={
                "messages": [{"content": "What is MLflow?", "role": "user"}],
                "max_tokens": 10,
                "temperature": 0.5,
            },
        ),
        mock.call(
            endpoint="chat",
            inputs={
                "messages": [{"content": "What is Spark?", "role": "user"}],
                "max_tokens": 10,
                "temperature": 0.5,
            },
        ),
    ]
    assert call_args_list == expected_calls

    # Validate the evaluation metrics
    expected_metrics_subset = {"toxicity/v1/ratio", "ari_grade_level/v1/mean"}
    if targets:
        expected_metrics_subset.add("exact_match/v1")
    assert expected_metrics_subset.issubset(set(eval_result.metrics.keys()))

    # Validate the model output is passed to the evaluator in the correct format (string)
    eval_results_table = eval_result.tables["eval_results_table"]
    assert eval_results_table["outputs"].equals(pd.Series(["This is a response"] * 2))


_DUMMY_COMPLETION_RESPONSE = {
    "id": "1",
    "object": "text_completion",
    "created": "2021-10-01T00:00:00.000000Z",
    "model": "gpt-4o-mini",
    "choices": [{"index": 0, "text": "This is a response", "finish_reason": "length"}],
    "usage": {
        "prompt_tokens": 1,
        "completion_tokens": 1,
        "total_tokens": 2,
    },
}


@pytest.mark.parametrize(
    ("input_data", "feature_names"),
    [
        (pd.DataFrame({"inputs": _TEST_QUERY_LIST}), None),
        (pd.DataFrame({"question": _TEST_QUERY_LIST}), ["question"]),
        (pd.DataFrame({"inputs": [{"prompt": q} for q in _TEST_QUERY_LIST]}), None),
        (_TEST_QUERY_LIST, None),
        ([{"prompt": q} for q in _TEST_QUERY_LIST], None),
    ],
)
@mock.patch("mlflow.deployments.get_deploy_client")
def test_evaluate_on_completion_model_endpoint(mock_deploy_client, input_data, feature_names):
    mock_deploy_client.return_value.predict.return_value = _DUMMY_COMPLETION_RESPONSE
    mock_deploy_client.return_value.get_endpoint.return_value = {"task": "llm/v1/completions"}

    with mlflow.start_run():
        eval_result = mlflow.evaluate(
            model="endpoints:/completions",
            data=input_data,
            inference_params={"max_tokens": 10},
            model_type="text",
            feature_names=feature_names,
        )

    # Validate the endpoint is called with correct payloads
    call_args_list = mock_deploy_client.return_value.predict.call_args_list
    expected_calls = [
        mock.call(endpoint="completions", inputs={"prompt": "What is MLflow?", "max_tokens": 10}),
        mock.call(endpoint="completions", inputs={"prompt": "What is Spark?", "max_tokens": 10}),
    ]
    assert call_args_list == expected_calls

    # Validate the evaluation metrics
    expected_metrics_subset = {
        "toxicity/v1/ratio",
        "ari_grade_level/v1/mean",
        "flesch_kincaid_grade_level/v1/mean",
    }
    assert expected_metrics_subset.issubset(set(eval_result.metrics.keys()))

    # Validate the model output is passed to the evaluator in the correct format (string)
    eval_results_table = eval_result.tables["eval_results_table"]
    assert eval_results_table["outputs"].equals(pd.Series(["This is a response"] * 2))


@mock.patch("mlflow.deployments.get_deploy_client")
def test_evaluate_on_model_endpoint_without_type(mock_deploy_client):
    # An endpoint that does not have endpoint type. For such endpoint, we simply
    # pass the input data to the endpoint without any modification and return
    # the response as is.
    mock_deploy_client.return_value.get_endpoint.return_value = {}
    mock_deploy_client.return_value.predict.return_value = "This is a response"

    input_data = pd.DataFrame(
        {
            "inputs": [
                {
                    "messages": [{"content": q, "role": "user"}],
                    "max_tokens": 10,
                }
                for q in _TEST_QUERY_LIST
            ],
            "ground_truth": _TEST_GT_LIST,
        }
    )

    with mlflow.start_run():
        eval_result = mlflow.evaluate(
            model="endpoints:/random",
            data=input_data,
            model_type="question-answering",
            targets="ground_truth",
            inference_params={"max_tokens": 10, "temperature": 0.5},
        )

    # Validate the endpoint is called with correct payloads
    call_args_list = mock_deploy_client.return_value.predict.call_args_list
    expected_calls = [
        mock.call(
            endpoint="random",
            inputs={
                "messages": [{"content": "What is MLflow?", "role": "user"}],
                "max_tokens": 10,
                "temperature": 0.5,
            },
        ),
        mock.call(
            endpoint="random",
            inputs={
                "messages": [{"content": "What is Spark?", "role": "user"}],
                "max_tokens": 10,
                "temperature": 0.5,
            },
        ),
    ]
    assert call_args_list == expected_calls

    # Validate the evaluation metrics
    expected_metrics_subset = {"toxicity/v1/ratio", "ari_grade_level/v1/mean", "exact_match/v1"}
    assert expected_metrics_subset.issubset(set(eval_result.metrics.keys()))

    # Validate the model output is passed to the evaluator in the correct format (string)
    eval_results_table = eval_result.tables["eval_results_table"]
    assert eval_results_table["outputs"].equals(pd.Series(["This is a response"] * 2))


@mock.patch("mlflow.deployments.get_deploy_client")
def test_evaluate_on_model_endpoint_invalid_payload(mock_deploy_client):
    # An endpoint that does not have endpoint type. For such endpoint, we simply
    # pass the input data to the endpoint without any modification and return
    # the response as is.
    mock_deploy_client.return_value.get_endpoint.return_value = {}
    mock_deploy_client.return_value.predict.side_effect = ValueError("Invalid payload")

    input_data = pd.DataFrame(
        {
            "inputs": [{"invalid": "payload"}],
        }
    )

    with pytest.raises(MlflowException, match="Failed to call the deployment endpoint"):
        mlflow.evaluate(
            model="endpoints:/random",
            data=input_data,
            model_type="question-answering",
            inference_params={"max_tokens": 10, "temperature": 0.5},
        )


@pytest.mark.parametrize(
    ("input_data", "error_message"),
    [
        # Extra input columns
        (
            pd.DataFrame(
                {
                    "inputs": _TEST_QUERY_LIST,
                    "extra_input": ["a", "b"],
                    "ground_truth": _TEST_GT_LIST,
                }
            ),
            "The number of input columns must be 1",
        ),
        # Missing input columns
        (
            pd.DataFrame({"ground_truth": _TEST_GT_LIST}),
            "The number of input columns must be 1",
        ),
        # Input column not str or dict
        (
            pd.DataFrame({"inputs": [1, 2], "ground_truth": _TEST_GT_LIST}),
            "Invalid input data type",
        ),
    ],
)
def test_evaluate_on_model_endpoint_invalid_input_data(input_data, error_message):
    with mock.patch("mlflow.deployments.get_deploy_client") as mock_deploy_client:
        mock_deploy_client.return_value.get_endpoint.return_value = {"task": "llm/v1/chat"}

        with pytest.raises(MlflowException, match=error_message):
            with mlflow.start_run():
                mlflow.evaluate(
                    model="endpoints:/chat",
                    data=input_data,
                    model_type="question-answering",
                    targets="ground_truth",
                    inference_params={"max_tokens": 10, "temperature": 0.5},
                )


@pytest.mark.parametrize(
    "model_input",
    [
        # Case 1: Single chat dictionary.
        # This is an expected input format from the Databricks RAG Evaluator.
        {
            "messages": [{"content": "What is MLflow?", "role": "user"}],
            "max_tokens": 10,
        },
        # Case 2: List of chat dictionaries.
        # This is not a typical input format from either default or Databricks RAG evaluators,
        # but we support it for compatibility with the normal Pyfunc models.
        [
            {"messages": [{"content": "What is MLflow?", "role": "user"}]},
            {"messages": [{"content": "What is Spark?", "role": "user"}]},
        ],
        # Case 3: DataFrame with a column of dictionaries
        pd.DataFrame(
            {
                "inputs": [
                    {
                        "messages": [{"content": "What is MLflow?", "role": "user"}],
                        "max_tokens": 10,
                    },
                    {
                        "messages": [{"content": "What is Spark?", "role": "user"}],
                    },
                ]
            }
        ),
        # Case 4: DataFrame with a column of strings
        pd.DataFrame(
            {
                "inputs": ["What is MLflow?", "What is Spark?"],
            }
        ),
    ],
)
@mock.patch("mlflow.deployments.get_deploy_client")
def test_model_from_deployment_endpoint(mock_deploy_client, model_input):
    mock_deploy_client.return_value.predict.return_value = _DUMMY_CHAT_RESPONSE
    mock_deploy_client.return_value.get_endpoint.return_value = {"task": "llm/v1/chat"}

    model = _get_model_from_deployment_endpoint_uri("endpoints:/chat")

    response = model.predict(model_input)

    if isinstance(model_input, dict):
        assert mock_deploy_client.return_value.predict.call_count == 1
        # Chat response should be unwrapped
        assert response == "This is a response"
    else:
        assert mock_deploy_client.return_value.predict.call_count == 2
        assert pd.Series(response).equals(pd.Series(["This is a response"] * 2))


def test_import_evaluation_dataset():
    # This test is to validate both imports work at the same time
    from mlflow.models.evaluation import EvaluationDataset
    from mlflow.models.evaluation.base import EvaluationDataset  # noqa: F401


def test_evaluate_shows_server_stdout_and_stderr_on_error(
    linear_regressor_model_uri, diabetes_dataset
):
    with mlflow.start_run():
        server_proc = subprocess.Popen(
            ["echo", "test1324"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        with mock.patch(
            "mlflow.pyfunc.backend.PyFuncBackend.serve",
            return_value=server_proc,
        ) as mock_serve:
            with pytest.raises(MlflowException, match="test1324"):
                evaluate(
                    linear_regressor_model_uri,
                    diabetes_dataset._constructor_args["data"],
                    model_type="regressor",
                    targets=diabetes_dataset._constructor_args["targets"],
                    evaluators="dummy_evaluator",
                    env_manager="virtualenv",
                )
            mock_serve.assert_called_once()


def test_env_manager_set_on_served_pyfunc_model(multiclass_logistic_regressor_model_uri):
    model = mlflow.pyfunc.load_model(multiclass_logistic_regressor_model_uri)
    client = ScoringServerClient("127.0.0.1", "8080")
    served_model_1 = _ServedPyFuncModel(model_meta=model.metadata, client=client, server_pid=1)
    served_model_1.env_manager = "virtualenv"
    assert served_model_1.env_manager == "virtualenv"


def test_metrics_logged_to_model_on_evaluation(
    multiclass_logistic_regressor_model_uri, iris_dataset
):
    with mlflow.start_run():
        # Log the model and retrieve its model_id
        model_info = mlflow.sklearn.log_model(
            mlflow.pyfunc.load_model(multiclass_logistic_regressor_model_uri), name="model"
        )
        model_id = model_info.model_id

        # Evaluate the model using its model_id
        eval_result = mlflow.evaluate(
            model=model_info.model_uri,
            data=iris_dataset._constructor_args["data"],
            model_type="classifier",
            targets=iris_dataset._constructor_args["targets"],
            evaluators=["default"],
        )

        # Retrieve metrics logged to the model
        logged_model_metrics = mlflow.get_logged_model(model_id).metrics

        # Ensure metrics are logged to the model
        assert eval_result.metrics == {metric.key: metric.value for metric in logged_model_metrics}

        # Validate that all metrics have the correct model_id in their metadata
        assert all(metric.model_id == model_id for metric in logged_model_metrics)


def test_evaluate_with_model_id(iris_dataset):
    # Create and log a model
    with mlflow.start_run():
        model = sklearn.linear_model.LogisticRegression()
        model.fit(iris_dataset._constructor_args["data"], iris_dataset._constructor_args["targets"])
        model_info = mlflow.sklearn.log_model(model, name="model")
        model_id = model_info.model_id

    # Evaluate the model with the specified model ID
    with mlflow.start_run():
        result = evaluate(
            model_info.model_uri,
            iris_dataset._constructor_args["data"],
            model_type="classifier",
            targets=iris_dataset._constructor_args["targets"],
            model_id=model_id,
        )

        # Verify metrics were logged
        assert result.metrics is not None
        assert len(result.metrics) > 0

        # Verify metrics are linked to the model ID
        logged_model = mlflow.get_logged_model(model_id)
        assert logged_model is not None
        assert logged_model.model_id == model_id

        # Convert metrics list to a dictionary for easier lookup
        logged_metrics = {metric.key: metric.value for metric in logged_model.metrics}

        # Verify each metric from the evaluation result matches the logged model metrics
        for metric_name, metric_value in result.metrics.items():
            assert metric_name in logged_metrics, (
                f"Metric {metric_name} not found in logged model metrics"
            )
            assert logged_metrics[metric_name] == metric_value, (
                f"Metric {metric_name} value mismatch: "
                f"expected {metric_value}, got {logged_metrics[metric_name]}"
            )


def test_evaluate_model_id_consistency_check(multiclass_logistic_regressor_model_uri, iris_dataset):
    """
    Test that an error is thrown when the specified model_id contradicts the model's associated ID.
    """
    # Create a model with a known model ID
    with mlflow.start_run():
        model = sklearn.linear_model.LogisticRegression()
        model.fit(iris_dataset._constructor_args["data"], iris_dataset._constructor_args["targets"])
        model_info = mlflow.sklearn.log_model(
            model,
            name="model",
        )
        model_uri = model_info.model_uri
        model_id = model_info.model_uuid

        # Test that specifying matching model_id works
        evaluate(
            model_uri,
            iris_dataset._constructor_args["data"],
            targets=iris_dataset._constructor_args["targets"],
            model_type="classifier",
            model_id=model_id,
        )

        # Test that specifying different model_id raises
        with pytest.raises(
            MlflowException,
            match=(
                r"The specified value of the 'model_id' parameter '.*' "
                r"contradicts the model_id '.*' associated with the model\. Please ensure "
                r"they match or omit the 'model_id' parameter\."
            ),
        ):
            evaluate(
                model_uri,
                iris_dataset._constructor_args["data"],
                targets=iris_dataset._constructor_args["targets"],
                model_type="classifier",
                model_id="different_model_id",
            )

        # Test that not specifying model_id works
        evaluate(
            model_uri,
            iris_dataset._constructor_args["data"],
            targets=iris_dataset._constructor_args["targets"],
            model_type="classifier",
        )


def test_evaluate_log_metrics_to_active_model(iris_dataset):
    # Set active model
    mlflow.set_active_model(name="my-model")
    active_model_id = mlflow.get_active_model_id()

    model = sklearn.linear_model.LogisticRegression()
    model.fit(iris_dataset._constructor_args["data"], iris_dataset._constructor_args["targets"])
    eval_df = pd.DataFrame(
        {
            "inputs": iris_dataset._constructor_args["data"].tolist(),
            "targets": iris_dataset._constructor_args["targets"],
            "predictions": model.predict(iris_dataset._constructor_args["data"]),
        }
    )

    eval_dataset = mlflow.data.from_pandas(
        df=eval_df,
        name="eval_dataset",
        targets="targets",
        predictions="predictions",
    )

    # Evaluate the model without model_id, active model_id should be used
    with mlflow.start_run():
        result = evaluate(
            data=eval_dataset,
            model_type="classifier",
        )

        # Verify metrics were logged
        assert result.metrics is not None
        assert len(result.metrics) > 0

        # Verify metrics are linked to the active model ID
        logged_model = mlflow.get_logged_model(active_model_id)
        assert logged_model is not None
        assert logged_model.model_id == active_model_id

        # Convert metrics list to a dictionary for easier lookup
        logged_metrics = {metric.key: metric.value for metric in logged_model.metrics}

        # Verify each metric from the evaluation result matches the logged model metrics
        assert logged_metrics.items() <= result.metrics.items()


def test_mlflow_evaluate_logs_traces_to_active_model():
    eval_data = pd.DataFrame(
        {
            "inputs": [
                "What is MLflow?",
                "What is Spark?",
            ],
            "ground_truth": ["What is MLflow?", "Not what is Spark?"],
        }
    )

    @mlflow.trace
    def model(inputs):
        return inputs

    # no model_id used when no active model is set or passed
    evaluate(model, eval_data, targets="ground_truth", extra_metrics=[mlflow.metrics.exact_match()])
    traces = get_traces()
    assert len(traces) == 1
    assert TraceMetadataKey.MODEL_ID not in traces[0].info.request_metadata

    # no active model set and pass model_id explicitly
    assert mlflow.get_active_model_id() is None
    model_id = mlflow.create_external_model(name="my-model").model_id
    evaluate(
        model,
        eval_data,
        targets="ground_truth",
        extra_metrics=[mlflow.metrics.exact_match()],
        model_id=model_id,
    )
    traces = get_traces()
    assert len(traces) == 2
    assert traces[0].info.request_metadata[TraceMetadataKey.MODEL_ID] == model_id

    # set active model
    with mlflow.set_active_model(name="my-model") as active_model:
        model_id = active_model.model_id
        evaluate(
            model, eval_data, targets="ground_truth", extra_metrics=[mlflow.metrics.exact_match()]
        )
        traces = get_traces()
        assert len(traces) == 3
        assert traces[0].info.request_metadata[TraceMetadataKey.MODEL_ID] == model_id

        # pass model_id explicitly takes precedence over active model
        assert mlflow.get_active_model_id() is not None
        another_model_id = mlflow.create_external_model(name="another-model").model_id
        evaluate(
            model,
            eval_data,
            targets="ground_truth",
            extra_metrics=[mlflow.metrics.exact_match()],
            model_id=another_model_id,
        )
        traces = get_traces()
        assert len(traces) == 4
        assert traces[0].info.request_metadata[TraceMetadataKey.MODEL_ID] == another_model_id

        # model_id of the passed model takes precedence over active model
        assert mlflow.get_active_model_id() is not None
        model_info = mlflow.pyfunc.log_model(
            name="model",
            python_model=model,
            input_example="What is MLflow?",
        )
        evaluate(
            model_info.model_uri,
            eval_data,
            targets="ground_truth",
            extra_metrics=[mlflow.metrics.exact_match()],
        )
        traces = get_traces()
        assert len(traces) == 5
        assert traces[0].info.request_metadata[TraceMetadataKey.MODEL_ID] == model_info.model_id
    # TODO: test registered ModelVersion's model_id works after it's supported
