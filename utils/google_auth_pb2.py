"""
Generated protobuf classes for Google Authenticator migration format.
This is based on the format documented in the Google Authenticator source code.
"""

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

# Create the symbol database
_sym_db = _symbol_database.Default()

# Define the protobuf messages
class MigrationPayload(_message.Message):
    """Main message containing the list of OTP parameters."""
    
    __slots__ = ['otp_parameters', 'version', 'batch_size', 'batch_index', 'batch_id']
    
    DESCRIPTOR = _descriptor.Descriptor(
        name='MigrationPayload',
        full_name='MigrationPayload',
        filename=None,
        containing_type=None,
        fields=[
            _descriptor.FieldDescriptor(
                name='otp_parameters', full_name='MigrationPayload.otp_parameters', index=0,
                number=1, type=11, cpp_type=10, label=3,
                has_default_value=False, default_value=[],
                message_type=None, enum_type=None, containing_type=None,
                is_extension=False, extension_scope=None,
                options=None),
            _descriptor.FieldDescriptor(
                name='version', full_name='MigrationPayload.version', index=1,
                number=2, type=5, cpp_type=1, label=1,
                has_default_value=False, default_value=0,
                message_type=None, enum_type=None, containing_type=None,
                is_extension=False, extension_scope=None,
                options=None),
            _descriptor.FieldDescriptor(
                name='batch_size', full_name='MigrationPayload.batch_size', index=2,
                number=3, type=5, cpp_type=1, label=1,
                has_default_value=False, default_value=0,
                message_type=None, enum_type=None, containing_type=None,
                is_extension=False, extension_scope=None,
                options=None),
            _descriptor.FieldDescriptor(
                name='batch_index', full_name='MigrationPayload.batch_index', index=3,
                number=4, type=5, cpp_type=1, label=1,
                has_default_value=False, default_value=0,
                message_type=None, enum_type=None, containing_type=None,
                is_extension=False, extension_scope=None,
                options=None),
            _descriptor.FieldDescriptor(
                name='batch_id', full_name='MigrationPayload.batch_id', index=4,
                number=5, type=5, cpp_type=1, label=1,
                has_default_value=False, default_value=0,
                message_type=None, enum_type=None, containing_type=None,
                is_extension=False, extension_scope=None,
                options=None),
        ],
        extensions=[],
        nested_types=[],
        enum_types=[],
        options=None,
        is_extendable=False,
        syntax='proto2',
        extension_ranges=[],
        oneofs=[],
        serialized_start=38,
        serialized_end=169,
    )

class OtpParameters(_message.Message):
    """Parameters for an individual OTP."""
    
    __slots__ = ['secret', 'name', 'issuer', 'algorithm', 'digits', 'type']
    
    DESCRIPTOR = _descriptor.Descriptor(
        name='OtpParameters',
        full_name='OtpParameters',
        filename=None,
        containing_type=None,
        fields=[
            _descriptor.FieldDescriptor(
                name='secret', full_name='OtpParameters.secret', index=0,
                number=1, type=12, cpp_type=9, label=1,
                has_default_value=False, default_value=b"",
                message_type=None, enum_type=None, containing_type=None,
                is_extension=False, extension_scope=None,
                options=None),
            _descriptor.FieldDescriptor(
                name='name', full_name='OtpParameters.name', index=1,
                number=2, type=9, cpp_type=9, label=1,
                has_default_value=False, default_value=b"".decode('utf-8'),
                message_type=None, enum_type=None, containing_type=None,
                is_extension=False, extension_scope=None,
                options=None),
            _descriptor.FieldDescriptor(
                name='issuer', full_name='OtpParameters.issuer', index=2,
                number=3, type=9, cpp_type=9, label=1,
                has_default_value=False, default_value=b"".decode('utf-8'),
                message_type=None, enum_type=None, containing_type=None,
                is_extension=False, extension_scope=None,
                options=None),
            _descriptor.FieldDescriptor(
                name='algorithm', full_name='OtpParameters.algorithm', index=3,
                number=4, type=14, cpp_type=8, label=1,
                has_default_value=True, default_value=1,
                message_type=None, enum_type=None, containing_type=None,
                is_extension=False, extension_scope=None,
                options=None),
            _descriptor.FieldDescriptor(
                name='digits', full_name='OtpParameters.digits', index=4,
                number=5, type=14, cpp_type=8, label=1,
                has_default_value=True, default_value=1,
                message_type=None, enum_type=None, containing_type=None,
                is_extension=False, extension_scope=None,
                options=None),
            _descriptor.FieldDescriptor(
                name='type', full_name='OtpParameters.type', index=5,
                number=6, type=14, cpp_type=8, label=1,
                has_default_value=True, default_value=2,
                message_type=None, enum_type=None, containing_type=None,
                is_extension=False, extension_scope=None,
                options=None),
        ],
        extensions=[],
        nested_types=[],
        enum_types=[],
        options=None,
        is_extendable=False,
        syntax='proto2',
        extension_ranges=[],
        oneofs=[],
        serialized_start=172,
        serialized_end=338,
    )

# Register message classes
_sym_db.RegisterFileDescriptor(DESCRIPTOR)
MigrationPayload = _reflection.GeneratedProtocolMessageType('MigrationPayload', (_message.Message,), {
    'DESCRIPTOR': MigrationPayload.DESCRIPTOR,
    '__module__': 'google_auth_pb2'
})
_sym_db.RegisterMessage(MigrationPayload)

OtpParameters = _reflection.GeneratedProtocolMessageType('OtpParameters', (_message.Message,), {
    'DESCRIPTOR': OtpParameters.DESCRIPTOR,
    '__module__': 'google_auth_pb2'
})
_sym_db.RegisterMessage(OtpParameters)

# Enums
Algorithm = _descriptor.EnumDescriptor(
    name='Algorithm',
    full_name='Algorithm',
    filename=None,
    file=DESCRIPTOR,
    values=[
        _descriptor.EnumValueDescriptor(
            name='ALGORITHM_UNSPECIFIED', index=0,
            number=0, options=None,
            type=None),
        _descriptor.EnumValueDescriptor(
            name='ALGORITHM_SHA1', index=1,
            number=1, options=None,
            type=None),
        _descriptor.EnumValueDescriptor(
            name='ALGORITHM_SHA256', index=2,
            number=2, options=None,
            type=None),
        _descriptor.EnumValueDescriptor(
            name='ALGORITHM_SHA512', index=3,
            number=3, options=None,
            type=None),
        _descriptor.EnumValueDescriptor(
            name='ALGORITHM_MD5', index=4,
            number=4, options=None,
            type=None),
    ],
    containing_type=None,
    options=None,
    serialized_start=340,
    serialized_end=460,
)

DigitCount = _descriptor.EnumDescriptor(
    name='DigitCount',
    full_name='DigitCount',
    filename=None,
    file=DESCRIPTOR,
    values=[
        _descriptor.EnumValueDescriptor(
            name='DIGIT_COUNT_UNSPECIFIED', index=0,
            number=0, options=None,
            type=None),
        _descriptor.EnumValueDescriptor(
            name='DIGIT_COUNT_SIX', index=1,
            number=1, options=None,
            type=None),
        _descriptor.EnumValueDescriptor(
            name='DIGIT_COUNT_EIGHT', index=2,
            number=2, options=None,
            type=None),
    ],
    containing_type=None,
    options=None,
    serialized_start=462,
    serialized_end=547,
)

OtpType = _descriptor.EnumDescriptor(
    name='OtpType',
    full_name='OtpType',
    filename=None,
    file=DESCRIPTOR,
    values=[
        _descriptor.EnumValueDescriptor(
            name='OTP_TYPE_UNSPECIFIED', index=0,
            number=0, options=None,
            type=None),
        _descriptor.EnumValueDescriptor(
            name='OTP_TYPE_HOTP', index=1,
            number=1, options=None,
            type=None),
        _descriptor.EnumValueDescriptor(
            name='OTP_TYPE_TOTP', index=2,
            number=2, options=None,
            type=None),
    ],
    containing_type=None,
    options=None,
    serialized_start=549,
    serialized_end=624,
) 