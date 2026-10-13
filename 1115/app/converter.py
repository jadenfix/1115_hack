"""Pydantic v2 JSON payloads for the project's pinned Temporal SDK."""
from typing import Any, Optional, Type
from pydantic import TypeAdapter
from pydantic_core import to_json
from temporalio.api.common.v1 import Payload
from temporalio.converter import (
    CompositePayloadConverter, DataConverter, DefaultPayloadConverter,
    EncodingPayloadConverter, JSONPlainPayloadConverter,
)

class PydanticJSONConverter(EncodingPayloadConverter):
    @property
    def encoding(self) -> str:
        return "json/plain"

    def to_payload(self, value: Any) -> Payload:
        return Payload(metadata={"encoding": self.encoding.encode()}, data=to_json(value))

    def from_payload(self, payload: Payload, type_hint: Optional[Type] = None) -> Any:
        return TypeAdapter(type_hint or Any).validate_json(payload.data)

class PydanticPayloadConverter(CompositePayloadConverter):
    def __init__(self):
        super().__init__(*(PydanticJSONConverter() if isinstance(c, JSONPlainPayloadConverter) else c
                          for c in DefaultPayloadConverter.default_encoding_payload_converters))

data_converter = DataConverter(payload_converter_class=PydanticPayloadConverter)
