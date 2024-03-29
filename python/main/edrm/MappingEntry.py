import hashlib
from datetime import datetime
from typing import Any, Iterable, Iterator, Tuple

from edrm import FieldFactory
from edrm.EntryField import EntryField
from edrm.EntryInterface import EntryInterface


class MappingEntry(EntryInterface):
    """
    Generic data entry for key:value pair mappings, such as rows in a CSV file, database, or JSON file.

    This class can, and should be subclassed when the generic means of calculating names and item dates aren't
    suitable.  Additionally, all incoming dtae/times are assumed to be instances datetime.datetime.
    """
    def __init__(self, mapping: dict[str, Any], mimetype: str, parent_id: str):
        super().__init__()

        self.__data: dict[str, Any] = mapping
        self.__parent_id: str = parent_id

        self.__fill_initial_fields()
        self.__fill_generic_fields(mimetype)

    def __fill_initial_fields(self):
        for key, value in self.__data.items():
            if isinstance(value, bool):
                data_type = EntryField.TYPE_BOOLEAN
                _value = value
            elif isinstance(value, int):
                data_type = EntryField.TYPE_INTEGER
                _value = value
            elif isinstance(value, float):
                data_type = EntryField.TYPE_DECIMAL
                _value = value
            elif isinstance(value, datetime):
                data_type = EntryField.TYPE_DATETIME
                _value = value
            else:
                data_type = EntryField.TYPE_TEXT
                _value = str(value)

            self[key] = FieldFactory.generate_field(key, data_type, _value)

    def __fill_generic_fields(self, mimetype: str):
        self['MIME Type'] = FieldFactory.generate_field('MIME Type', EntryField.TYPE_TEXT, mimetype)
        self['SHA-1'] = FieldFactory.generate_field('SHA-1',
                                                    EntryField.TYPE_TEXT,
                                                    FieldFactory.hash_data(self.__data, hashlib.sha1()))
        self['Name'] = FieldFactory.generate_field('Name', EntryField.TYPE_TEXT, self.name)
        self['Item Date'] = FieldFactory.generate_field('Item Date', EntryField.TYPE_DATETIME, self.itemdate)

    @property
    def data(self) -> dict[str, Any]:
        return self.__data

    @property
    def identifier_field(self) -> str:
        return 'SHA-1'

    @property
    def name(self) -> str:
        """
        Attempt to locate a name in the provided dictionary of data.  If no name is present, then return the first
        value present in the data.

        :return: A string to use as the data row's display name
        """
        field_names = list(self.data.keys())
        first_field = field_names[0]

        name_fields = [f for f in field_names if 'name' in f.lower()]

        if len(name_fields) == 0:
            name_field = first_field
        else:
            name_field = name_fields[0]

        return self.__data[name_field]

    @property
    def time_field(self) -> str:
        """
        Provide a name of a field to be used as the row items <code>Item Date</code>.  The item date is a specific
        required property used to locate data and events on a timeline.

        This method will search for time / date fields in the following order:
        * If there is a field named "CreateTime" that will be used.
        * If there is a field with the word "time" (case-insensitive) in its name, it will be used.
        * If there is a field with the word "date" (case-insensitive) in its name, it will be used.

        Barring any of those options, None will be provided.

        If a specific field which would not be found in the above order then a subclass of this class should be used
        to override this property.
        :return: A field that be used as the Item Date, or None if an appropriate field can't be found.
        """
        field_names = list(self.data.keys())

        if "CreateTime" in field_names:
            return "CreateTime"

        time_fields = [f for f in field_names if "time" in f.lower()]
        if len(time_fields) > 0:
            return time_fields[0]

        date_fields = [f for f in field_names if "date" in f.lower()]
        if len(date_fields) > 0:
            return date_fields[0]

        return None

    @property
    def itemdate(self) -> datetime:
        """
        Attempt to lookup an item date or time for this mapping.  If there isn't one present, use "now"  This
        assumes that the values store for the field are either of the type datetime.datetime, or a string in the
        Python format "%Y-%m-%d %H:%M:%S.%f" (more commonly: YYYY-mm-DD HH:MM:SS.ssssss).  If neither of these is
        true an exception will be raised.

        :return: A time to use for this entry's timeline time.
        """
        time_field = self.time_field

        if time_field is None:
            return datetime.now()
        else:
            date_time = self.data.get(time_field)

            if isinstance(date_time, datetime):
                return date_time
            elif isinstance(date_time, str):
                return datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S.%f")
            else:
                raise ValueError(f"Invalid item date format: {date_time}")

    @property
    def parent(self) -> str:
        return self.__parent_id