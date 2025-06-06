# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

import unity_catalog_prompt_messages_pb2 as unity__catalog__prompt__messages__pb2

GRPC_GENERATED_VERSION = '1.71.0'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in unity_catalog_prompt_service_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class UnityCatalogPromptServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.CreatePrompt = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/CreatePrompt',
                request_serializer=unity__catalog__prompt__messages__pb2.CreatePromptRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.CreatePromptResponse.FromString,
                _registered_method=True)
        self.UpdatePrompt = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/UpdatePrompt',
                request_serializer=unity__catalog__prompt__messages__pb2.UpdatePromptRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.UpdatePromptResponse.FromString,
                _registered_method=True)
        self.DeletePrompt = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/DeletePrompt',
                request_serializer=unity__catalog__prompt__messages__pb2.DeletePromptRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.DeletePromptResponse.FromString,
                _registered_method=True)
        self.GetPrompt = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/GetPrompt',
                request_serializer=unity__catalog__prompt__messages__pb2.GetPromptRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.GetPromptResponse.FromString,
                _registered_method=True)
        self.SearchPrompts = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/SearchPrompts',
                request_serializer=unity__catalog__prompt__messages__pb2.SearchPromptsRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.SearchPromptsResponse.FromString,
                _registered_method=True)
        self.CreatePromptVersion = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/CreatePromptVersion',
                request_serializer=unity__catalog__prompt__messages__pb2.CreatePromptVersionRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.CreatePromptVersionResponse.FromString,
                _registered_method=True)
        self.UpdatePromptVersion = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/UpdatePromptVersion',
                request_serializer=unity__catalog__prompt__messages__pb2.UpdatePromptVersionRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.UpdatePromptVersionResponse.FromString,
                _registered_method=True)
        self.DeletePromptVersion = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/DeletePromptVersion',
                request_serializer=unity__catalog__prompt__messages__pb2.DeletePromptVersionRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.DeletePromptVersionResponse.FromString,
                _registered_method=True)
        self.GetPromptVersion = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/GetPromptVersion',
                request_serializer=unity__catalog__prompt__messages__pb2.GetPromptVersionRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.GetPromptVersionResponse.FromString,
                _registered_method=True)
        self.SearchPromptVersions = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/SearchPromptVersions',
                request_serializer=unity__catalog__prompt__messages__pb2.SearchPromptVersionsRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.SearchPromptVersionsResponse.FromString,
                _registered_method=True)
        self.SetPromptAlias = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/SetPromptAlias',
                request_serializer=unity__catalog__prompt__messages__pb2.SetPromptAliasRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.SetPromptAliasResponse.FromString,
                _registered_method=True)
        self.DeletePromptAlias = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/DeletePromptAlias',
                request_serializer=unity__catalog__prompt__messages__pb2.DeletePromptAliasRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.DeletePromptAliasResponse.FromString,
                _registered_method=True)
        self.GetPromptVersionByAlias = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/GetPromptVersionByAlias',
                request_serializer=unity__catalog__prompt__messages__pb2.GetPromptVersionByAliasRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.GetPromptVersionByAliasResponse.FromString,
                _registered_method=True)
        self.SetPromptTag = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/SetPromptTag',
                request_serializer=unity__catalog__prompt__messages__pb2.SetPromptTagRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.SetPromptTagResponse.FromString,
                _registered_method=True)
        self.DeletePromptTag = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/DeletePromptTag',
                request_serializer=unity__catalog__prompt__messages__pb2.DeletePromptTagRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.DeletePromptTagResponse.FromString,
                _registered_method=True)
        self.SetPromptVersionTag = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/SetPromptVersionTag',
                request_serializer=unity__catalog__prompt__messages__pb2.SetPromptVersionTagRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.SetPromptVersionTagResponse.FromString,
                _registered_method=True)
        self.DeletePromptVersionTag = channel.unary_unary(
                '/mlflow.unitycatalog.UnityCatalogPromptService/DeletePromptVersionTag',
                request_serializer=unity__catalog__prompt__messages__pb2.DeletePromptVersionTagRequest.SerializeToString,
                response_deserializer=unity__catalog__prompt__messages__pb2.DeletePromptVersionTagResponse.FromString,
                _registered_method=True)


class UnityCatalogPromptServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def CreatePrompt(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def UpdatePrompt(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DeletePrompt(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetPrompt(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SearchPrompts(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def CreatePromptVersion(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def UpdatePromptVersion(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DeletePromptVersion(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetPromptVersion(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SearchPromptVersions(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SetPromptAlias(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DeletePromptAlias(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetPromptVersionByAlias(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SetPromptTag(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DeletePromptTag(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SetPromptVersionTag(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DeletePromptVersionTag(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_UnityCatalogPromptServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'CreatePrompt': grpc.unary_unary_rpc_method_handler(
                    servicer.CreatePrompt,
                    request_deserializer=unity__catalog__prompt__messages__pb2.CreatePromptRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.CreatePromptResponse.SerializeToString,
            ),
            'UpdatePrompt': grpc.unary_unary_rpc_method_handler(
                    servicer.UpdatePrompt,
                    request_deserializer=unity__catalog__prompt__messages__pb2.UpdatePromptRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.UpdatePromptResponse.SerializeToString,
            ),
            'DeletePrompt': grpc.unary_unary_rpc_method_handler(
                    servicer.DeletePrompt,
                    request_deserializer=unity__catalog__prompt__messages__pb2.DeletePromptRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.DeletePromptResponse.SerializeToString,
            ),
            'GetPrompt': grpc.unary_unary_rpc_method_handler(
                    servicer.GetPrompt,
                    request_deserializer=unity__catalog__prompt__messages__pb2.GetPromptRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.GetPromptResponse.SerializeToString,
            ),
            'SearchPrompts': grpc.unary_unary_rpc_method_handler(
                    servicer.SearchPrompts,
                    request_deserializer=unity__catalog__prompt__messages__pb2.SearchPromptsRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.SearchPromptsResponse.SerializeToString,
            ),
            'CreatePromptVersion': grpc.unary_unary_rpc_method_handler(
                    servicer.CreatePromptVersion,
                    request_deserializer=unity__catalog__prompt__messages__pb2.CreatePromptVersionRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.CreatePromptVersionResponse.SerializeToString,
            ),
            'UpdatePromptVersion': grpc.unary_unary_rpc_method_handler(
                    servicer.UpdatePromptVersion,
                    request_deserializer=unity__catalog__prompt__messages__pb2.UpdatePromptVersionRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.UpdatePromptVersionResponse.SerializeToString,
            ),
            'DeletePromptVersion': grpc.unary_unary_rpc_method_handler(
                    servicer.DeletePromptVersion,
                    request_deserializer=unity__catalog__prompt__messages__pb2.DeletePromptVersionRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.DeletePromptVersionResponse.SerializeToString,
            ),
            'GetPromptVersion': grpc.unary_unary_rpc_method_handler(
                    servicer.GetPromptVersion,
                    request_deserializer=unity__catalog__prompt__messages__pb2.GetPromptVersionRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.GetPromptVersionResponse.SerializeToString,
            ),
            'SearchPromptVersions': grpc.unary_unary_rpc_method_handler(
                    servicer.SearchPromptVersions,
                    request_deserializer=unity__catalog__prompt__messages__pb2.SearchPromptVersionsRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.SearchPromptVersionsResponse.SerializeToString,
            ),
            'SetPromptAlias': grpc.unary_unary_rpc_method_handler(
                    servicer.SetPromptAlias,
                    request_deserializer=unity__catalog__prompt__messages__pb2.SetPromptAliasRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.SetPromptAliasResponse.SerializeToString,
            ),
            'DeletePromptAlias': grpc.unary_unary_rpc_method_handler(
                    servicer.DeletePromptAlias,
                    request_deserializer=unity__catalog__prompt__messages__pb2.DeletePromptAliasRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.DeletePromptAliasResponse.SerializeToString,
            ),
            'GetPromptVersionByAlias': grpc.unary_unary_rpc_method_handler(
                    servicer.GetPromptVersionByAlias,
                    request_deserializer=unity__catalog__prompt__messages__pb2.GetPromptVersionByAliasRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.GetPromptVersionByAliasResponse.SerializeToString,
            ),
            'SetPromptTag': grpc.unary_unary_rpc_method_handler(
                    servicer.SetPromptTag,
                    request_deserializer=unity__catalog__prompt__messages__pb2.SetPromptTagRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.SetPromptTagResponse.SerializeToString,
            ),
            'DeletePromptTag': grpc.unary_unary_rpc_method_handler(
                    servicer.DeletePromptTag,
                    request_deserializer=unity__catalog__prompt__messages__pb2.DeletePromptTagRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.DeletePromptTagResponse.SerializeToString,
            ),
            'SetPromptVersionTag': grpc.unary_unary_rpc_method_handler(
                    servicer.SetPromptVersionTag,
                    request_deserializer=unity__catalog__prompt__messages__pb2.SetPromptVersionTagRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.SetPromptVersionTagResponse.SerializeToString,
            ),
            'DeletePromptVersionTag': grpc.unary_unary_rpc_method_handler(
                    servicer.DeletePromptVersionTag,
                    request_deserializer=unity__catalog__prompt__messages__pb2.DeletePromptVersionTagRequest.FromString,
                    response_serializer=unity__catalog__prompt__messages__pb2.DeletePromptVersionTagResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'mlflow.unitycatalog.UnityCatalogPromptService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('mlflow.unitycatalog.UnityCatalogPromptService', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class UnityCatalogPromptService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def CreatePrompt(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/CreatePrompt',
            unity__catalog__prompt__messages__pb2.CreatePromptRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.CreatePromptResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def UpdatePrompt(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/UpdatePrompt',
            unity__catalog__prompt__messages__pb2.UpdatePromptRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.UpdatePromptResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def DeletePrompt(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/DeletePrompt',
            unity__catalog__prompt__messages__pb2.DeletePromptRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.DeletePromptResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def GetPrompt(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/GetPrompt',
            unity__catalog__prompt__messages__pb2.GetPromptRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.GetPromptResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def SearchPrompts(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/SearchPrompts',
            unity__catalog__prompt__messages__pb2.SearchPromptsRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.SearchPromptsResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def CreatePromptVersion(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/CreatePromptVersion',
            unity__catalog__prompt__messages__pb2.CreatePromptVersionRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.CreatePromptVersionResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def UpdatePromptVersion(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/UpdatePromptVersion',
            unity__catalog__prompt__messages__pb2.UpdatePromptVersionRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.UpdatePromptVersionResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def DeletePromptVersion(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/DeletePromptVersion',
            unity__catalog__prompt__messages__pb2.DeletePromptVersionRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.DeletePromptVersionResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def GetPromptVersion(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/GetPromptVersion',
            unity__catalog__prompt__messages__pb2.GetPromptVersionRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.GetPromptVersionResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def SearchPromptVersions(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/SearchPromptVersions',
            unity__catalog__prompt__messages__pb2.SearchPromptVersionsRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.SearchPromptVersionsResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def SetPromptAlias(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/SetPromptAlias',
            unity__catalog__prompt__messages__pb2.SetPromptAliasRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.SetPromptAliasResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def DeletePromptAlias(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/DeletePromptAlias',
            unity__catalog__prompt__messages__pb2.DeletePromptAliasRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.DeletePromptAliasResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def GetPromptVersionByAlias(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/GetPromptVersionByAlias',
            unity__catalog__prompt__messages__pb2.GetPromptVersionByAliasRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.GetPromptVersionByAliasResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def SetPromptTag(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/SetPromptTag',
            unity__catalog__prompt__messages__pb2.SetPromptTagRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.SetPromptTagResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def DeletePromptTag(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/DeletePromptTag',
            unity__catalog__prompt__messages__pb2.DeletePromptTagRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.DeletePromptTagResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def SetPromptVersionTag(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/SetPromptVersionTag',
            unity__catalog__prompt__messages__pb2.SetPromptVersionTagRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.SetPromptVersionTagResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def DeletePromptVersionTag(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/mlflow.unitycatalog.UnityCatalogPromptService/DeletePromptVersionTag',
            unity__catalog__prompt__messages__pb2.DeletePromptVersionTagRequest.SerializeToString,
            unity__catalog__prompt__messages__pb2.DeletePromptVersionTagResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
