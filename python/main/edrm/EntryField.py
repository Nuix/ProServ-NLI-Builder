from typing import Any

from edrm import FieldFactory


class EntryField:
    """
    Field for the EDRM XML File Entry.

    Use the FieldFactory class to generate these, as the key and key-name pairs must be managed properly.
    """
    TYPE_TEXT: str = "Text"
    TYPE_DATETIME: str = "DateTime"
    TYPE_INTEGER: str = "LongInteger"
    TYPE_LONG_TEXT: str = "LongText"
    TYPE_DECIMAL: str = "Decimal"
    TYPE_BOOLEAN: str = "Boolean"

    def __init__(self, key: str, name: str, field_type: str, default_value: Any = None):
        self.__key = key
        self.__name = name
        self.__type = field_type
        self.__value = default_value

    @property
    def key(self):
        return self.__key

    @property
    def name(self) -> str:
        return self.__name

    @property
    def data_type(self) -> str:
        return self.__type

    @property
    def value(self) -> Any:
        return self.__value

    @value.setter
    def value(self, value: Any) -> None:
        self.__value = value
