"""
Basic interface for items that will go into an EDRM XML file
"""
from datetime import datetime
from typing import Iterable, Any, Tuple, Iterator

from edrm.EntryField import EntryField


class EntryInterface:
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
        :return: A field name that contain's the date-time for this entry's timepoint in the timeline
        """
        raise NotImplementedError

    @property
    def itemdate(self) -> datetime:
        """
        :return: A datetime object representing the official "Item Date" for this entry in the timeline.
        """
        raise NotImplementedError

    @property
    def parent_id(self) -> str:
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
