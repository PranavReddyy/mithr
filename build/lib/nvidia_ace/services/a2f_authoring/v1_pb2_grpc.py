# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

from nvidia_ace.a2f_authoring import v1_pb2 as nvidia__ace_dot_a2f__authoring_dot_v1__pb2

GRPC_GENERATED_VERSION = '1.67.1'
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
        + f' but the generated code in nvidia_ace.services.a2f_authoring.v1_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class A2FAuthoringServiceStub(object):
    """This API allows to get unique frames from Audio2Face inference (also known as authoring)
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.UploadAudioClip = channel.unary_unary(
                '/nvidia_ace.services.a2f_authoring.v1.A2FAuthoringService/UploadAudioClip',
                request_serializer=nvidia__ace_dot_a2f__authoring_dot_v1__pb2.AudioClip.SerializeToString,
                response_deserializer=nvidia__ace_dot_a2f__authoring_dot_v1__pb2.AudioClipHandle.FromString,
                _registered_method=True)
        self.GetAvatarFacePose = channel.unary_unary(
                '/nvidia_ace.services.a2f_authoring.v1.A2FAuthoringService/GetAvatarFacePose',
                request_serializer=nvidia__ace_dot_a2f__authoring_dot_v1__pb2.FacePoseRequest.SerializeToString,
                response_deserializer=nvidia__ace_dot_a2f__authoring_dot_v1__pb2.BlendShapeData.FromString,
                _registered_method=True)


class A2FAuthoringServiceServicer(object):
    """This API allows to get unique frames from Audio2Face inference (also known as authoring)
    """

    def UploadAudioClip(self, request, context):
        """Upload the audio clip to the AuthoringService to be processed.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetAvatarFacePose(self, request, context):
        """Request a single animation frame at the specified timecode.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_A2FAuthoringServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'UploadAudioClip': grpc.unary_unary_rpc_method_handler(
                    servicer.UploadAudioClip,
                    request_deserializer=nvidia__ace_dot_a2f__authoring_dot_v1__pb2.AudioClip.FromString,
                    response_serializer=nvidia__ace_dot_a2f__authoring_dot_v1__pb2.AudioClipHandle.SerializeToString,
            ),
            'GetAvatarFacePose': grpc.unary_unary_rpc_method_handler(
                    servicer.GetAvatarFacePose,
                    request_deserializer=nvidia__ace_dot_a2f__authoring_dot_v1__pb2.FacePoseRequest.FromString,
                    response_serializer=nvidia__ace_dot_a2f__authoring_dot_v1__pb2.BlendShapeData.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'nvidia_ace.services.a2f_authoring.v1.A2FAuthoringService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('nvidia_ace.services.a2f_authoring.v1.A2FAuthoringService', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class A2FAuthoringService(object):
    """This API allows to get unique frames from Audio2Face inference (also known as authoring)
    """

    @staticmethod
    def UploadAudioClip(request,
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
            '/nvidia_ace.services.a2f_authoring.v1.A2FAuthoringService/UploadAudioClip',
            nvidia__ace_dot_a2f__authoring_dot_v1__pb2.AudioClip.SerializeToString,
            nvidia__ace_dot_a2f__authoring_dot_v1__pb2.AudioClipHandle.FromString,
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
    def GetAvatarFacePose(request,
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
            '/nvidia_ace.services.a2f_authoring.v1.A2FAuthoringService/GetAvatarFacePose',
            nvidia__ace_dot_a2f__authoring_dot_v1__pb2.FacePoseRequest.SerializeToString,
            nvidia__ace_dot_a2f__authoring_dot_v1__pb2.BlendShapeData.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
