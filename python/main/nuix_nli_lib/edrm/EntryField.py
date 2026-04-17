import warnings
from datetime import datetime
from enum import StrEnum
from typing import Any, Union

from xml.dom.minidom import Element, Document, Node

from nuix_nli_lib.edrm import EDRMUtilities as eutes


class FieldType(StrEnum):
    """
    Enumeration of valid EDRM field data types.  Using ``FieldType`` values instead of raw strings catches typos at
    development time rather than when Nuix rejects the resulting NLI at import.

    Because ``FieldType`` extends ``StrEnum``, every member compares equal to its string value, so existing code that
    passes the constants to XML serialisation or string comparisons continues to work without modification.
    """
    TEXT = "Text"
    DATETIME = "DateTime"
    INTEGER = "LongInteger"
    LONG_TEXT = "LongText"
    DECIMAL = "Decimal"
    BOOLEAN = "Boolean"


class _EntryFieldMeta(type):
    """Metaclass that fires a DeprecationWarning when the legacy TYPE_* class attributes are accessed."""

    _DEPRECATED_ALIASES = {
        'TYPE_TEXT': FieldType.TEXT,
        'TYPE_DATETIME': FieldType.DATETIME,
        'TYPE_INTEGER': FieldType.INTEGER,
        'TYPE_LONG_TEXT': FieldType.LONG_TEXT,
        'TYPE_DECIMAL': FieldType.DECIMAL,
        'TYPE_BOOLEAN': FieldType.BOOLEAN,
    }

    def __getattr__(cls, name: str):
        if name in _EntryFieldMeta._DEPRECATED_ALIASES:
            canonical = name.removeprefix('TYPE_')
            warnings.warn(
                f"EntryField.{name} is deprecated; use FieldType.{canonical} directly",
                DeprecationWarning,
                stacklevel=2,
            )
            return _EntryFieldMeta._DEPRECATED_ALIASES[name]
        raise AttributeError(f"type object '{cls.__name__}' has no attribute '{name}'")


class EntryField(metaclass=_EntryFieldMeta):
    """
    Field for the EDRM XML File Entry.  A field is a single value stored on an Entry in the load file.  It consists
    of a Name, Type, and Value.  It also has a Key used to store the field in XML (it acts as the name of the XML Node
    used to store the Field's value).

    Use the FieldFactory class to generate these, as the key and key-name pairs must be managed properly.
    """
    # FieldType enum — the canonical way to specify a field's data type.
    FieldType = FieldType

    # Deprecated string aliases kept for backwards compatibility.  New code should use FieldType members directly.
    # Accessing these attributes emits a DeprecationWarning at runtime via the _EntryFieldMeta metaclass.
    # TYPE_TEXT, TYPE_DATETIME, TYPE_INTEGER, TYPE_LONG_TEXT, TYPE_DECIMAL, TYPE_BOOLEAN

    def __init__(self, key: str, name: str, field_type: Union[FieldType, str], default_value: Any = None):
        """
        Do Not call this method directly.  Use the FieldFactory class to generate these, as the key and key-name
        must be managed properly.

        :param key: Key used as the name for the XML Node used to store the field's value.  The key must be unique
                    within the load file, and able to be used to map a Field Name to the XML Node used to store the
                    field.
        :param name: Name of the field as it should be displayed in the final case the load file will fill.
        :param field_type: A ``FieldType`` enum member (preferred) or one of the legacy ``EntryField.TYPE_*`` strings.
                           Passing a plain ``str`` instead of a ``FieldType`` member is deprecated; pass a
                           ``FieldType`` member directly.
        :param default_value: The value to store in the field if no value is provided.
        """
        if not isinstance(field_type, FieldType):
            warnings.warn(
                f"Passing a plain str ({field_type!r}) as field_type is deprecated; "
                f"use a FieldType member directly (e.g. FieldType('{field_type}'))",
                DeprecationWarning,
                stacklevel=2,
            )
        self.__key = key
        self.__name = name
        self.__type = field_type
        self.__value = default_value

    @property
    def key(self) -> str:
        """
        :return: Key used as the name for the XML Node used to store the field's value.  The key must be unique
                 within the load file, and able to be used to map a Field Name to the XML Node used to store the
                 field.
        """
        return self.__key

    @property
    def name(self) -> str:
        """
        :return: Name of the field as it should be displayed in the final case the load file will fill.
        """
        return self.__name

    @property
    def data_type(self) -> FieldType:
        """
        :return: Type of data this field will store as a ``FieldType`` member.

        .. note::
            In rare cases where ``EntryField`` was constructed directly with a plain ``str`` argument (a deprecated
            usage), this property may return a ``str`` rather than a ``FieldType`` member.  Callers should always
            construct ``EntryField`` via ``FieldFactory`` and pass a ``FieldType`` member to ensure the return type
            contract is upheld.
        """
        return self.__type  # type: ignore[return-value]  # plain-str path is deprecated; see __init__

    @property
    def value(self) -> Any:
        """
        :return: The current value of the field.  It should be of a type appropriate for that assigned by the
                 `data_type` property.
        """
        return self.__value

    @value.setter
    def value(self, value: Any) -> None:
        """
        :param value: The current value of the field.  It should be of a type appropriate for that assigned by the
                      `data_type` property.
        :return: None
        """
        self.__value = value

    def serialize_definition(self, document: Document, field_list: Element) -> None:
        """
        Fields are stored in two parts in the EDRM file.  At the top of the file, their definitions are stored,
        providing the name and key mapping, as well as the type of the value stored in the field.  This function is
        responsible for writing that definition to the EDRM XML file.

        This method ensures a field with the provided name is only stored in the XML file once.

        :param document: The DOM document to write the definition to.
        :param field_list: The container DOM element to add the definition to.
        :return: None
        """
        for sibling in field_list.childNodes:
            if sibling.nodeType == Node.ELEMENT_NODE and sibling.getAttribute("Name") == self.name:
                return

        field_element: Element = document.createElement("Field")
        field_element.setAttribute("Name", self.name)
        field_element.setAttribute("DataType", self.data_type)
        field_element.setAttribute("Key", self.key)

        field_list.appendChild(field_element)

    def serialize_value(self, document: Document, value_list: Element) -> None:
        """
        Fields are stored in two parts in the EDRM file.  For each Entry in the file which has a value for a given
        field, the Field and its value are written, using the Field's Key as the XML Node name.  This function is
        responsible for writing that value to the EDRM XML file.

        :param document: The DOM document to write the value to.
        :param value_list: The DOM element to add the value to.
        :return: None
        """
        value_element: Element = document.createElement(self.key)

        if self.value is None:
            value_text = ''
        elif isinstance(self.value, datetime):
            value_text = eutes.convert_datetime_to_string(self.value)
        elif isinstance(self.value, float):
            value_text = str(round(self.value, 4))
        else:
            value_text = eutes.sanitize_xml_content(str(self.value))

        value_element.appendChild(document.createTextNode(value_text))
        value_list.appendChild(value_element)