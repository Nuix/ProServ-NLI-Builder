"""
JSON File

## An object
{
  "key1": "simple value",
  "key2": {
    "key3": "nested value",
    "key4": [
      "list value 1",
      "list value 2"
    ]
  }
}

## A list
[
  "list value 1",
  "list value 2",
  {
    "key1": "simple value",
    "key2": {
      "key3": "nested value"○x
    }
  }
]

## A simple value
"simple value"


For this use-case
If a JSON file has a simple value, then it will be supplied as a mapping with a single key-value pair:
"Value = <value>" and the name will be "JSON value"

If a JSON file is a List, then it will be supplied as a mapping with a name "JSON list" and the values stored as:
"<index> = <value>"

If a JSON file is an object, then it will be supplied as a mapping.  The mapping's name will be "JSON object", and the
values stored as:
"<key> = <value>"

Values inside a JSON object or list will be stored based on type:
* If a simple value, store the value itself in an appropriate type
* If a list, add the values as a new child mapping whose name is the key in parent mapping (index for a parent list)
* If an object, add the key-value pairs as a new child mapping whose name is the key in parent mapping (index for a parent list)

A JSON value will consist of a series of mappings.  The mapping's name will be the path of the key values that lead to
the map.  If a value is
"""
import json
from typing import Any, Type, Union

from nuix_nli_lib.edrm import FileEntry, MappingEntry, EDRMBuilder, EntryInterface
from nuix_nli_lib.data_types import configs


class JSONValueEntry(MappingEntry):
    def __init__(self,
                 mapping_name: str,
                 key_name: str,
                 value: Union[int, float, str, bool, None],
                 mimetype: str = 'application/x-json-value',
                 parent_id: str = None):
        self.__name = mapping_name
        super().__init__({key_name: value}, mimetype, parent_id)

    def get_name(self) -> str:
        return self.__name

    @property
    def text(self) -> str:
        return str(self.data['Value'])


class JSONArrayEntry(MappingEntry):
    def __init__(self,
                 mapping_name: str,
                 array: dict[str, Any],
                 mimetype: str = 'application/x-json-array',
                 parent_id: str = None):

        self.__name = mapping_name
        super().__init__(array, mimetype, parent_id)

    def get_name(self) -> str:
        return self.__name

    def add_as_parent_path(self, existing_path: str):
        return f'{self.name}/{existing_path}'

    @property
    def text(self) -> str:
        return str([str(_v) for _v in self.data.values()])


class JSONObjectEntry(MappingEntry):
    def __init__(self,
                 mapping_name: str,
                 obj: dict[str, Any],
                 mimetype: str = 'application/x-json-object',
                 parent_id: str = None):
        self.__name = mapping_name
        super().__init__(obj, mimetype, parent_id)

    def get_name(self) -> str:
        return self.__name

    def add_as_parent_path(self, existing_path: str):
        return f'{self.name}/{existing_path}'


class JSONFileEntry(FileEntry):
    def __init__(self,
                 json_file_path: str,
                 mimetype: str = 'application/json',
                 parent_id: str = None,
                 simple_value_generator: Type[JSONValueEntry] = JSONValueEntry,
                 array_value_generator: Type[JSONArrayEntry] = JSONArrayEntry,
                 object_value_generator: Type[Any] = JSONObjectEntry):
        super().__init__(json_file_path, mimetype, parent_id)

        self.__simple_value_generator: Type[JSONValueEntry] = simple_value_generator or JSONValueEntry
        self.__array_value_generator: Type[JSONArrayEntry] = array_value_generator or JSONArrayEntry
        self.__object_value_generator: Type[JSONObjectEntry] = object_value_generator or JSONObjectEntry

        with self.file_path.open(mode="r", encoding=configs['encoding']) as json_file:
            self.__json = json.load(json_file)

    @property
    def json(self):
        return self.__json

    def add_as_parent_path(self, existing_path: str):
        return f'{self.name}/{existing_path}'

    def __add_object(self, builder: EDRMBuilder, name: str, obj: dict, parent_id: str):
        _contents: dict[str, Any] = {}
        _objects: dict[str, dict[str, Any]] = {}
        _arrays: dict[str, list[Any]] = {}

        for key, value in obj.items():
            if isinstance(value, dict):
                _objects[key] = value
            elif isinstance(value, list):
                _arrays[key] = value
            else:
                _contents[key] = value

        object_entry = self.__object_value_generator(name, _contents, parent_id=parent_id)
        object_id = object_entry[object_entry.identifier_field].value

        for key, value in _objects.items():
            self.__add_object(builder, key, value, parent_id=object_id)

        for key, value in _arrays.items():
            self.__add_array(builder, key, value, parent_id=object_id)

        builder.add_entry(object_entry)

    def __add_array(self, builder: EDRMBuilder, name: str, array: list, parent_id: str) -> JSONArrayEntry:
        _contents: dict[str, Any] = {}
        _objects: dict[str, dict[str, Any]] = {}
        _arrays: dict[str, list[Any]] = {}
        for idx, itm in enumerate(array):
            if isinstance(itm, dict):
                _objects[str(idx)] = itm
            elif isinstance(itm, list):
                _arrays[str(idx)] = itm
            else:
                _contents[str(idx)] = itm

        array_entry = self.__array_value_generator(name, _contents, parent_id=parent_id)
        array_id = array_entry[array_entry.identifier_field].value

        for obj_name, obj in _objects.items():
            self.__add_object(builder, obj_name, obj, parent_id=array_id)

        for ary_name, ary in _arrays.items():
            self.__add_array(builder, ary_name, ary, parent_id=array_id)

        builder.add_entry(array_entry)

        return array_entry

    def __add_value(self,
                    builder: EDRMBuilder,
                    mapping_name: str,
                    key_name: str,
                    value: Union[int, float, str, bool, None],
                    parent_id: str) -> JSONValueEntry:

        entry = self.__simple_value_generator(mapping_name, key_name, value, parent_id=parent_id)
        builder.add_entry(entry)
        return entry

    def add_to_builder(self, builder: EDRMBuilder) -> str:
        my_id = builder.add_entry(self)

        if isinstance(self.json, dict):
            self.__add_object(builder, 'JSON Object', self.json, my_id)
        elif isinstance(self.json, list):
            self.__add_array(builder, 'JSON Array', self.json, my_id)
        else:
            self.__add_value(builder, 'JSON Value', 'Value', self.json, my_id)

        return my_id
