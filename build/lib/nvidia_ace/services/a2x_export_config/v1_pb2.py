# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: nvidia_ace.services.a2x_export_config.v1.proto
# Protobuf Python Version: 5.27.2
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    27,
    2,
    '',
    'nvidia_ace.services.a2x_export_config.v1.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n.nvidia_ace.services.a2x_export_config.v1.proto\x12(nvidia_ace.services.a2x_export_config.v1\"\x94\x01\n\x12\x43onfigsTypeRequest\x12\\\n\x0b\x63onfig_type\x18\x01 \x01(\x0e\x32G.nvidia_ace.services.a2x_export_config.v1.ConfigsTypeRequest.ConfigType\" \n\nConfigType\x12\x08\n\x04YAML\x10\x00\x12\x08\n\x04JSON\x10\x01\"*\n\tA2XConfig\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x0f\n\x07\x63ontent\x18\x02 \x01(\t2\x9e\x01\n\x16\x41\x32XExportConfigService\x12\x83\x01\n\nGetConfigs\x12<.nvidia_ace.services.a2x_export_config.v1.ConfigsTypeRequest\x1a\x33.nvidia_ace.services.a2x_export_config.v1.A2XConfig\"\x00\x30\x01\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'nvidia_ace.services.a2x_export_config.v1_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_CONFIGSTYPEREQUEST']._serialized_start=93
  _globals['_CONFIGSTYPEREQUEST']._serialized_end=241
  _globals['_CONFIGSTYPEREQUEST_CONFIGTYPE']._serialized_start=209
  _globals['_CONFIGSTYPEREQUEST_CONFIGTYPE']._serialized_end=241
  _globals['_A2XCONFIG']._serialized_start=243
  _globals['_A2XCONFIG']._serialized_end=285
  _globals['_A2XEXPORTCONFIGSERVICE']._serialized_start=288
  _globals['_A2XEXPORTCONFIGSERVICE']._serialized_end=446
# @@protoc_insertion_point(module_scope)
