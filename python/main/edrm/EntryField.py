from datetime import datetime
from typing import Any

from xml.dom.minidom import Element, Document, Node

import edrm.EDRMUtilities as eutes


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

    def serialize_definition(self, document: Document, field_list: Element) -> None:
        for sibling in field_list.childNodes:
            if sibling.nodeType == Node.ELEMENT_NODE and sibling.getAttribute("Name") == self.name:
                return

        field_element: Element = document.createElement("Field")
        field_element.setAttribute("Name", self.name)
        field_element.setAttribute("DataType", self.data_type)
        field_element.setAttribute("Key", self.key)

        field_list.appendChild(field_element)

    def serialize_value(self, document: Document, value_list: Element) -> None:
        value_element: Element = document.createElement(self.key)

        if self.value is None:
            value_text = ''
        elif isinstance(self.value, datetime):
            value_text = eutes.convert_datetime_to_string(self.value)
        elif isinstance(self.value, float):
            value_text = str(round(self.value, 4))
        else:
            value_text = str(self.value)

        value_element.appendChild(document.createTextNode(value_text))
        value_list.appendChild(value_element)