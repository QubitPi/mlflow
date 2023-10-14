.. _quickstart-rest-docker:

Quickstart: Running Machine Learning Model as REST API in Docker Container
==========================================================================


In this quickstart, we will:


Deploying a trained machine learning model behind a REST API endpoint is an common problem that needs to be solved on
the last mile to getting the model into production. The MLflow package provides a nice abstraction layer that makes
deployment via Docker quite easy.


Defining and Storing the Model as a Python Function in MLflow
-------------------------------------------------------------

The model inference logic is wrapped in a class that inherits from :class:`.PythonModel`. There are two
functions to implement:

1. *load_context()* loads the model artifacts
2. *predict()* runs model inference on the given input and returns the model's output; the input format will be pandas
   DataFrame and the output will be a pandas Series of predicted result.

For example

.. code-block:: python

    import mlflow.pyfunc
    import pandas


    class MyModel(mlflow.pyfunc.PythonModel):
        def __init__(self):
            self.model = None

        def load_context(self, context):
            pretrained_model = "my-model"
            this.model = load_model(pretrained_model)

        def predict(self, context, model_input):
            inputs = []
            for _, row in model_input.iterrows():
                inputs.append(row["input_column"])

            return pandas.Series(self.model(inputs))

Next, we save the model locally to a preferred directory. For instance, "my-model-dir/". We would also need to include a
conda environment specifying its dependencies:

.. code-block:: python

    conda_env = {
        "channels": ["defaults"],
        "dependencies": [
            "python=3.10.7",
            "pip",
            {
                "pip": ["mlflow", "<other python packages if needed>"],
            },
        ],
        "name": "my_model_env",
    }

    # Save the MLflow Model
    mlflow_pyfunc_model_path = "my-model-dir"
    mlflow.pyfunc.save_model(
        path=mlflow_pyfunc_model_path, python_model=MyModel(), conda_env=conda_env
    )

In the end, we should have a file called `MyModel.py` with

.. code-block:: python

    import mlflow.pyfunc
    import pandas


    class MyModel(mlflow.pyfunc.PythonModel):
        def __init__(self):
            self.model = None

        def load_context(self, context):
            pretrained_model = "my-model"
            this.model = load_model(pretrained_model)

        def predict(self, context, model_input):
            inputs = []
            for _, row in model_input.iterrows():
                inputs.append(row["input_column"])

            return pandas.Series(self.model(inputs))


    if __name__ == "__main__":
        conda_env = {
            "channels": ["defaults"],
            "dependencies": [
                "python=3.10.7",
                "pip",
                {
                    "pip": ["mlflow", "<other python packages if needed>"],
                },
            ],
            "name": "my_model_env",
        }

        # Save the MLflow Model
        mlflow_pyfunc_model_path = "my-model-dir"
        mlflow.pyfunc.save_model(
            path=mlflow_pyfunc_model_path, python_model=MyModel(), conda_env=conda_env
        )

Testing the Model
-----------------

In case we would like to unit test our model in CI/CD:

.. code-block:: python

    loaded_model = mlflow.pyfunc.load_model(mlflow_pyfunc_model_path)

    # Evaluate the model
    import pandas

    test_data = pandas.DataFrame(
        {
            "input_column": ["input1...", "input2...", "input3..."],
            "another_input_column": [...],
        }
    )
    test_predictions = loaded_model.predict(test_data)
    print(test_predictions)

Serving the Model in Docker Container via REST API
--------------------------------------------------

`build_docker <cli.html#mlflow-models-build-docker>`_ and run container:

.. code-block:: bash

    mlflow models build-docker --name "docker-image-name"

.. note::
    If we see the error of
    `requests.exceptions.ConnectionError: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))`
    from the command above, we can try
    `this workaround <https://github.com/docker/docker-py/issues/3059#issuecomment-1294369344>`_::

        sudo ln -s "$HOME/.docker/run/docker.sock" /var/run/docker.sock

    and then re-run the command

.. code-block:: bash

    export MY_MODEL_PATH=/abs/path/to/my-model-dir
    docker run --rm \
      -p 5001:8080 \
      -v $MY_MODEL_PATH:/opt/ml/model \
      "docker-image-name"
