from datetime import datetime
from typing import Any

from xml.dom.minidom import Element, Document, Node

from nuix_nli_lib.edrm import EDRMUtilities as eutes


class EntryField:
    """
    Field for the EDRM XML File Entry.  A field is a single value stored on an Entry in the load file.  It consists
    of a Name, Type, and Value.  It also has a Key used to store the field in XML (it acts as the name of the XML Node
    used to store the Field's value).

    Use the FieldFactory class to generate these, as the key and key-name pairs must be managed properly.
    """
    TYPE_TEXT: str = "Text"
    TYPE_DATETIME: str = "DateTime"
    TYPE_INTEGER: str = "LongInteger"
    TYPE_LONG_TEXT: str = "LongText"
    TYPE_DECIMAL: str = "Decimal"
    TYPE_BOOLEAN: str = "Boolean"

    def __init__(self, key: str, name: str, field_type: str, default_value: Any = None):
        """
        Do Not call this method directly.  Use the FieldFactory class to generate these, as the key and key-name
        must be managed properly.

        :param key: Key used as the name for the XML Node used to store the field's value.  The key must be unique
                    within the load file, and able to be used to map a Field Name to the XML Node used to store the
                    field.
        :param name: Name of the field as it should be displayed in the final case the load file will fill.
        :param field_type: One of the EntryField.TYPE_* attributes.
        :param default_value: The value to store in the field if no value is provided.
        """
        self.__key = key
        self.__name = name
        self.__type = field_type
        self.__value = default_value

    @property
    def key(self):
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
    def data_type(self) -> str:
        """
        :return: Type of data this field will store.  It should be one of the EntryField.TYPE_* attributes.
        """
        return self.__type

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