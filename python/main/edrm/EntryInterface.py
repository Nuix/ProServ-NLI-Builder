"""
Basic interface for items that will go into an EDRM XML file
"""
from datetime import datetime
from typing import Iterable, Any, Tuple, Iterator
from xml.dom.minidom import Element, Document

from edrm.EntryField import EntryField


class EntryInterface(object):
    def __init__(self):
        self.__fields: dict[str, EntryField] = {}

    @property
    def fields(self) -> Iterable[str]:
        """
        :return: Iterable over the names of the fields with data in this entry
        """
        return self.__fields.keys()

    @property
    def identifier_field(self) -> str:
        """
        :return: A field name that identifies this entry
        """
        raise NotImplementedError

    @property
    def name(self) -> str:
        """
        :return: This entry's displayable name
        """
        raise NotImplementedError

    @property
    def time_field(self) -> str:
        """
        :return: A field name that contains the date-time for this entry's timepoint in the timeline
        """
        raise NotImplementedError

    @property
    def itemdate(self) -> datetime:
        """
        :return: A datetime object representing the official "Item Date" for this entry in the timeline.
        """
        raise NotImplementedError

    @property
    def parent(self) -> str:
        """
        :return: The unique ID of this entry's parent, if it has one.  None if this is a Top Level Item.
        """
        raise NotImplementedError

    def set_field_value(self, field_name: str, field_value: Any):
        """
        Set the value of a field in this entry.  This function assumes the field is already defined, and just adjusts
        the value stored for the field.  Use the item access (obj[field_name] = ...) to assign a new field to the entry.
        :param field_name: The name of the field whose value is to be set.
        :param field_value: The value to assign to the field.
        :return: None
        :raise KeyError: If the there is no field with the provided name
        """
        if field_name in self.fields:
            self[field_name] = field_value
        else:
            raise KeyError(f'Field {field_name} does not exist for this entry.')

    def serialize_field_definitions(self, document: Document, field_list: Element):
        """
        Add this entry's fields to the XML document.
        :param document: XML Document representing the EDRM Load File
        :param field_list: The container XML Element to hold the fields.
        :return: None
        """
        for field_name, field in self:
            field.serialize_definition(document, field_list)

    def serialize_field_values(self, document: Document, value_list: Element):
        """
        Add the values for each field to the XML document.
        :param document: XML Document representing the EDRM Load File
        :param value_list: The container XML Element to hold the field values
        :return: None
        """
        for field_name, field in self:
            field.serialize_value(document, value_list)

    def add_as_parent_path(self, existing_path: str):
        """
        Add this entry to the existing path as the path's parent, if appropriate.  The default is to do nothing,
        assuming this type of entry does not represent a physical location.  Subclasses can override this behavior.
        :param existing_path: The existing (possibly child) path to adjust with this entry as a parent
        :return: The extended path including this entry as a parent if appropriate for this type
        """
        return existing_path

    def add_doc(self, document: Document, container: Element) -> Element:
        doc_element = document.createElement('Document')
        doc_element.setAttribute('DocID', self[self.identifier_field].value)
        doc_element.setAttribute('DocType', 'File')
        doc_element.setAttribute('MimeType', self['MIME Type'].value)
        container.appendChild(doc_element)

        return doc_element

    def add_file(self, document: Document, container: Element, entry_map: dict[str, object], for_nli: bool):
        raise NotImplementedError

    def add_location_uri(self, document: Document, container: Element, entry_map: dict[str, object], for_nli: bool):
        raise NotImplementedError

    def add_location(self,
                     document: Document,
                     container: Element,
                     entry_map: dict[str, object],
                     for_nli: bool):
        location_list = document.createElement('Locations')
        container.appendChild(location_list)

        location = document.createElement('Location')
        location_list.appendChild(location)

        custodian_element = document.createElement('Custodian')
        custodian_element.appendChild(document.createTextNode('Unknown'))
        location.appendChild(custodian_element)

        description_element = document.createElement('Description')
        description_text: str = 'Location within the Container' if for_nli else 'Location on Disk'
        description_element.appendChild(document.createTextNode(description_text))
        location.appendChild(description_element)

        self.add_location_uri(document, location, entry_map, for_nli)

    def serialize_entry(self,
                        document: Document,
                        entry_container: Element,
                        entry_map: dict[str, object],
                        for_nli: bool = False):
        doc_element = self.add_doc(document, entry_container)

        value_list = document.createElement('FieldValues')
        doc_element.appendChild(value_list)
        self.serialize_field_values(document, value_list)

        self.add_file(document, doc_element, entry_map, for_nli)
        self.add_location(document, doc_element, entry_map, for_nli)

    def __iter__(self) -> Iterator[Tuple[str, Any]]:
        """
        :return: An iterable over the fields in this entry
        """
        return iter(self.__fields.items())

    def __setitem__(self, field_name: str, value: EntryField):
        """
        Assign a new, named EntryField to this object.  Use this method to assign new fields, and use the setter
        function (obj.set_field_value(field_name, value)) to assign a value to an existing field.

        :param field_name: Name of the field whose values is to be set.
        :param value: Value to assign to the field
        :return: None
        """
        self.__fields[field_name] = value

    def __getitem__(self, field_name: str) -> EntryField:
        """
        Get the value stored for a given field.

        :param field_name: Name of the field whose value should be retrieved
        :return: The value stored for the field, or None if the field hasn't been set.
        :raise KeyError: If there is no field with the provided name
        """
        return self.__fields[field_name]
