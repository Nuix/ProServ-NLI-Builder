import json
from typing import Any, Type, Union, List, Callable
from datetime import datetime

from nuix_nli_lib.edrm import FileEntry, MappingEntry, EDRMBuilder
from nuix_nli_lib.data_types import configs

"""
This module provides classes for creating nuix_nli_lib.edrm.EntryInterface implementations for JSON files so they can
added into a Nuix case via an Nuix Logical Image (nli).  The main entry point will be the JSONFileEntry which will
consume the JSON contents and parse the results into the EDRM file structure needed for an NLI.  There are three
helper classes, JSONValueEntry, JSONArrayEntry, and JSONObjectEntry.  These classes are used to represent the basic
types in the JSON file:

JSONValueEntry
: Used to represent the contents of a JSON file when there is just a single simple value (a String, number, boolean, or 
  Null) stored in the file.  Otherwise, the when simple values are stored in arrays or objects, the same class will be 
  used to generate the value for a property, though the entry itself will not be stored.  A JSONValueEntry can have
  no child items, and the value of the item will be used as the item's native/text.  Subclass this class if you
  want to override parsing of simple data - for example to convert dates into a format accessible to Nuix.

JSONArrayEntry
: Used to represent a JSON array, as it appears anywhere in the JSON file.  Simple values stored in the array
  will be parsed using an instance of the JSONValueEntry class and stored as properties with their index used as the
  property name.  The text for a JSONArrayEntry will be a comma separated list of string representations of its simple 
  value contents (so a list made up of just complex types will have an empty text representation.)  A JSONArrayEntry 
  may have child items - any nested JSON arrays or objects, whose name will be the index into the JSON array.

JSONObjectEntry
: Used to represent a JSON object, as it appears anywhere in the JSON file.  Simple values stored in the object will be
  parsed using an instance of the JSONValueEntry class and stored as properties on the item.  Complex types will be
  stored as child items, with their name being the property name in the JSON object.  The object's native/text will be
  the key:value pair definition in the same format as a MappingEntry, covering all the simple values stored in it (such
  that an object that only contains nested complex types will have an empty text representation).
"""

def _parse_jsonpath_segments(pattern: str) -> list[str]:
    """
    Parse a non-recursive JSONPath pattern (e.g. '$.a.b[*].c') into a list of path segments,
    normalizing '[*]' array wildcards to '*'.  Assumes the pattern starts with '$.'.
    """
    rest = pattern[2:]  # strip '$.'
    rest = rest.replace('[*]', '.*')
    return rest.split('.')


def _matches_path(pattern: str, path: list[str]) -> bool:
    """
    Return True if the JSONPath pattern matches the path stack.

    Supported patterns:
      $..key        - recursive descent: matches any path whose last segment is 'key'
      $.key         - root-level key
      $.parent.key  - exact nested path
      $.arr[*].key  - 'key' inside any element of array 'arr'
    """
    if not pattern.startswith('$'):
        return False
    if pattern.startswith('$..'):
        key = pattern[3:]
        return len(path) > 0 and path[-1] == key
    if not pattern.startswith('$.'):
        return False
    segments = _parse_jsonpath_segments(pattern)
    if len(segments) != len(path):
        return False
    return all(seg == '*' or seg == p for seg, p in zip(segments, path))


def _pattern_specificity(pattern: str) -> int:
    """
    Return a specificity score for a JSONPath pattern (higher = more specific).
    Recursive descent patterns ($..key) score 0; direct-path patterns score the
    number of literal (non-wildcard) segments.
    """
    if pattern.startswith('$..'):
        return 0
    if not pattern.startswith('$.'):
        return -1
    return sum(1 for s in _parse_jsonpath_segments(pattern) if s != '*')


class JSONValueEntry(MappingEntry):
    """
    MappingEntry used for JSON files which represent single values.  This is a basic implementation designed around
    storing a single value as a property, of type Strings, Booleans, Integers, and Floats.  It does not try to handle
    dates or assume any special value. This type of entry cannot have child items.
    """
    def __init__(self,
                 mapping_name: str,
                 key_name: str,
                 value: Union[int, float, str, bool, datetime, None],
                 mimetype: str = 'application/x-json-value',
                 parent_id: str = None):
        """
        :param mapping_name: The name of the item that will be used to represent the value in the Nuix case.
        :param key_name: The single value will be stored as a property, this is the name of the property.
        :param value: The value to store in the property.
        :param mimetype: The mimetype to store the item as, defaulting to 'application/x-json-value'.
        :param parent_id: The ID of this item's parent, or None to make it a Top Level Item.
        """
        self.__name = mapping_name
        self.__key_name = key_name
        super().__init__({key_name: value}, mimetype, parent_id)

    def get_name(self) -> str:
        return self.__name

    @property
    def text(self) -> str:
        return str(self.data[self.__key_name])


def get_datetime_value_generator(formats: list[str]) -> Type[JSONValueEntry]:
    local_formats = list(formats)
    class JSONDateTimeEntry(JSONValueEntry):
        def __init__(self,
                     mapping_name: str,
                     key_name: str,
                     value: Union[int, float, str],
                     mimetype: str = "application/x-datetime",
                     parent_id: str = None):
            dt = None
            v_str = str(value)
            if isinstance(value, (int, float)):
                dt = datetime.fromtimestamp(value)
            else:
                try:
                    dt = datetime.fromisoformat(v_str)
                except ValueError:
                    for format in local_formats:
                        try:
                            dt = datetime.strptime(v_str, format)
                            break
                        except ValueError:
                            pass
            dt = dt or v_str
            super().__init__(mapping_name, key_name, dt, mimetype, parent_id)
    return JSONDateTimeEntry


class JSONArrayEntry(MappingEntry):
    """
    MappingEntry implementation used to store a JSON array.  A JSON array can be a mix of simple values, nested arrays,
    or nested objects.  This creates a single item in a Nuix case to represent the array.  Simple values stored in the
    array are represented as properties with their property name being the index into the array.  Nested arrays and
    objects will be represented as child items, whose name will be the index into the array.  This means that a single
    array item may represent the values store in it as a mix between properties and child items, and that the indexes
    used in both locations may be discontinuous (for example, you may have properties 0, 1, 2, 5, 7 and child item 3,
    4, and 6.)  A JSONArrayEntry may have child items.
    """
    def __init__(self,
                 mapping_name: str,
                 array: dict[str, Any],
                 mimetype: str = 'application/x-json-array',
                 child_value_generator: type["JSONValueEntry"] | None = None,
                 child_array_generator: type["JSONArrayEntry"] | None = None,
                 child_object_generator: type["JSONObjectEntry"] | None = None,
                 parent_id: str = None):
        """
        :param mapping_name: The name of the item that will be used to represent the value in the Nuix case.
        :param array: The list of values stored in the array.  Can be a mix of simple values, nested lists, and dicts.
        :param mimetype: The mimetype to store the item as, defaulting to 'application/x-json-array'.
        :param child_value_generator: The class to use for generating child JSONValueEntry objects, or None to use the default.
        :param child_array_generator: The class to use for generating child JSONArrayEntry objects, or None to use the default.
        :param child_object_generator: The class to use for generating child JSONObjectEntry objects, or None to use the default.
        :param parent_id: The ID of this item's parent, or None to make it a Top Level Item.
        """

        self.__name = mapping_name
        self.child_array_generator = child_array_generator
        self.child_object_generator = child_object_generator
        self.child_value_generator = child_value_generator
        super().__init__(array, mimetype, parent_id)

    def get_name(self) -> str:
        return self.__name

    def add_as_parent_path(self, existing_path: str):
        return f'{self.name}/{existing_path}'

    @property
    def text(self) -> str:
        return ', '.join([str(_v) for _v in self.data.values()])

    def get_child_object_generator(self, index: str) -> type["JSONObjectEntry"] | None:
        """
        Allow a JSONArrayEntry to provide its own implementation of JSONObjectEntry to use for any nested objects.  For
        example, assuming a JSON array is defined as:
        <code>
        [
          {
            "sender": "Alice",
            "message": "Hello, how are you?"
          },
          {
            "sender": "Bob",
            "message": "I'm good, thanks!"
          }
        ]
        </code>
        Then you might have a specific JSONObjectEntry implementation to handle the nested objects:
        <code>
        class MyJSONArrayEntry(JSONArrayEntry):
          @override
          def get_child_object_generator(self, index: int) -> type["JSONObjectEntry"] | None:
            return ChatMessageEntry
        <code>

        This would also support more complex JSON arrays where nested objects may have different types:
        <code>
        [
          {
            "type": "chat_message",
            "sender": "Alice",
            "message": "Hello, how are you?"
          },
          {
            "type": "call",
            "from": "Alice",
            "to": "Bob",
            "duration": 120
          }
        ]
        </code>

        In which case you may have a get_child_object_generator method that returns a different implementation based on
        the content at a specific index in the array:
        <code>
        class MyJSONArrayEntry(JSONArrayEntry):
          @override
          def get_child_object_generator(self, index: int) -> type["JSONObjectEntry"] | None:
            item_data = self.data[index]
            if item_data["type"] == "chat_message":
                return ChatMessageEntry
            elif item_data["type"] == "call":
                return CallEntry
            else:
                return None
        </code>

        If this method returns None, then the default JSONObjectEntry provided to the JSONEntry during initialization
        will be used.  The default implementation will return None.

        :param index: Index into the array used to look up the source data.  Note that this will be provided as a
                      string.  The source data for the array (self.data) is a dictionary with the indexes as keys, also
                      in a string format, as a consequence of generalizing the MappingEntry interface from which this
                      class inherits.  Thus the index passed in can be directly used to look up the source data.
        :return: An instance of JSONObjectEntry to use to generate the child item, or None to use the default
                 JSONObjectEntry.
        """
        return self.child_object_generator

    def get_child_array_generator(self, index: str) -> type["JSONArrayEntry"] | None:
        """
        Allow a JSONArrayEntry to provide its own implementation of JSONArrayEntry to use for any nested arrays.  For
        example, assuming a JSON array is defined as:
        <code>
        [
          [
            {
              "sender": "Alice",
              "message": "Hello, how are you?"
            },
            {
              "sender": "Bob",
              "message": "I'm good, thanks!"
            }
          ],
          [
            {
              "sender": "Frank",
              "message": "Hello, how are you?"
            },
            {
              "sender": "Jen",
              "message": "I'm good, thanks!"
            }
          ]
        ]
        </code>
        Then you might have a specific JSONArrayEntry implementation to handle the nested arrays as chat threads:
        <code>
        class MyJSONArrayEntry(JSONArrayEntry):
          @override
          def get_child_array_generator(self, index: int) -> type["JSONArrayEntry"] | None:
            return ChatThreadEntry
        <code>

        This would also support more complex JSON arrays where nested arrays may have different types:
        <code>
        [
          [
            {
              "type": "group_chat",
              "sender": "Alice",
              "message": "Hello, how are you?"
            },
            {
              "type": "group_chat",
              "sender": "Bob",
              "message": "I'm good, thanks!"
            }
          ],
          [
            {
              "type": "private_chat",
              "sender": "Frank",
              "message": "Hello, how are you?"
            },
            {
              "type": "private_chat",
              "sender": "Jen",
              "message": "I'm good, thanks!"
            }
          ]
        ]
        </code>

        In which case you may have a get_child_array_generator method that returns a different implementation based on
        the content at a specific index in the array:
        <code>
        class MyJSONArrayEntry(JSONArrayEntry):
          @override
          def get_child_array_generator(self, index: int) -> type["JSONArrayEntry"] | None:
            item_data = self.data[index]
            if item_data["0"]["type"] == "group_chat":
                return GroupChatThread
            elif item_data["0"]["type"] == "private_chat":
                return PrivateChatThread
            else:
                return None
        </code>

        If this method returns None, then the default JSONObjectEntry provided to the JSONEntry during initialization
        will be used.  The default implementation will return None.

        :param index: Index into the array used to look up the source data.  Note that this will be provided as a
                      string.  The source data for the array (self.data) is a dictionary with the indexes as keys, also
                      in a string format, as a consequence of generalizing the MappingEntry interface from which this
                      class inherits.  Thus the index passed in can be directly used to look up the source data.
        :return: An instance of JSONArrayEntry to use to generate the child item, or None to use the default
                 JSONArrayEntry.
        """
        return self.child_array_generator

    def get_child_value_generator(self, index: str) -> type["JSONValueEntry"] | None:
        """
        Allow a JSONArrayEntry to provide its own implementation of JSONValueEntry to use for any nested values.  For
        example, assuming a JSON array is defined as:
        <code>
        [
          "my_document.pdf",
          "file://server/files/attachments/message_12345.pdf",
          "https://my.website.com/data/12345.jpg"
        ]
        </code>
        In this case, each value in the array, although a simple string, might represent different ways of pointing to
        data to add as children.  Thus, you might have a specific JSONValueEntry implementation to handle the nested
        values:
        <code>
        class MyJSONArrayEntry(JSONArrayEntry):
          @override
          def get_child_value_generator(self, index: int) -> type["JSONValueEntry"] | None:
            source_address = self.data[index]
            if utils.matches_relative_path(source_address):
              return LoadLocalChildEntry
            elif utils.matches_file_url(source_address):
              return LoadServedChildEntry
            elif utils.matches_url(source_address):
              return DownloadURLChildEntry
            else:
              return None
        <code>

        If this method returns None, then the default JSONValueEntry provided to the JSONEntry during initialization
        will be used.  The default implementation will return None.

        :param index: Index into the array used to look up the source data.  Note that this will be provided as a
                      string.  The source data for the array (self.data) is a dictionary with the indexes as keys, also
                      in a string format, as a consequence of generalizing the MappingEntry interface from which this
                      class inherits.  Thus the index passed in can be directly used to look up the source data.
        :return: An instance of JSONValueEntry to use to generate the child item, or None to use the default
                 JSONValueEntry.
        """
        return self.child_value_generator


class JSONObjectEntry(MappingEntry):
    """
    MappingEntry implementation used to store a JSON object.  A JSON object is represented in memory as a dictionary,
    and contains key:value pairs.  The value can be simple values, nested arrays, or nested objects.  This creates a
    single item in a Nuix case to represent the object, with simple values being represented as properties.  Nested
    arrays and objects would be added as child items, whose name will be the key in the JSON object.  This means that
    all the keys in a single object may be represented as a mix of properties and child items.  A JSONObjectEntry may
    have child items.
    """
    def __init__(self,
                 mapping_name: str,
                 obj: dict[str, Any],
                 mimetype: str = 'application/x-json-object',
                 child_value_generator: type["JSONValueEntry"] | None = None,
                 child_array_generator: type["JSONArrayEntry"] | None = None,
                 child_object_generator: type["JSONObjectEntry"] | None = None,
                 parent_id: str = None):
        """
        :param mapping_name: The name of the item that will be used to represent the value in the Nuix case.
        :param obj: The dictionary containing the key:value pairs.  The values can be simple values, lists, or dictionaries
        :param mimetype: The mimetype to store the item as, defaulting to 'application/x-json-object'.
        :param child_value_generator: The class to use for generating child JSONValueEntry objects, or None to use the default.
        :param child_array_generator: The class to use for generating child JSONArrayEntry objects, or None to use the default.
        :param child_object_generator: The class to use for generating child JSONObjectEntry objects, or None to use the default.
        :param parent_id: The ID of this item's parent, or None to make it a Top Level Item.'
        """
        self.__name = mapping_name
        self.child_array_generator = child_array_generator
        self.child_object_generator = child_object_generator
        self.child_value_generator = child_value_generator
        super().__init__(obj, mimetype, parent_id)

    def get_name(self) -> str:
        return self.__name

    def add_as_parent_path(self, existing_path: str):
        return f'{self.name}/{existing_path}'

    def get_child_object_generator(self, child_key: str) -> type["JSONObjectEntry"] | None:
        """
        Allow a JSONObjectEntry to contain different mappings dependent on the key used to identify the child entry.
        For example, assuming a JSON object is defined as:
        <code>
        {
          "chat_message": {
            "sender": "Alice",
            "message": "Hello, how are you?"
          },
          "document": {
            "name": "document.pdf",
            "size": 12345
          },
          "call": {
            "from": "Alice",
            "to": "Bob",
            "duration": 120
          }
        }
        </code>
        Then you might have different JSONObjectEntry implementations, and override this method to return the correct
        implementation based on the key used to identify the object:
        <code>
        class MyJSONObjectEntry(JSONObjectEntry):
          @override
          def get_child_object_generator(self, child_key: str) -> type["JSONObjectEntry"] | None:
            if child_key == "chat_message":
              return ChatMessageEntry
            elif child_key == "document":
              return DocumentEntry
            elif child_key == "call":
              return CallEntry
            else:
              return None
        <code>

        If this method returns None, then the default JSONObjectEntry provided to the JSONEntry during initialization
        will be used.  The default implementation will return None.

        :param child_key: The name of the key used to identify the type of child object to return an Entry for.
        :return: An instance of JSONObjectEntry to use to generate the child item, or None to use the default
                 JSONObjectEntry.
        """
        return self.child_object_generator

    def get_child_array_generator(self, child_key: str) -> type["JSONArrayEntry"] | None:
        """
        Allow a JSONObjectEntry to contain different mappings dependent on the key used to identify the child entry.
        For example, assuming a JSON object is defined as:
        <code>
        {
          "chat_messages": [
            {
              "sender": "Alice",
              "message": "Hello, how are you?"
            },
            {
              "sender": "Bob",
              "message": "I'm good, thanks!"
            }
          ],
          "documents": [
            {
              "name": "document.pdf",
              "size": 12345
            },
            {
              "name": "document2.pdf",
              "size": 18445
            }
          ],
          "calls": [
            {
              "from": "Alice",
              "to": "Bob",
              "duration": 120
            },
            {
              "from": "Bob",
              "to": "Alice",
              "duration": 90
            }
          ]
        }
        </code>
        Then you might have different JSONArrayEntry implementations, and override this method to return the correct
        implementation based on the key used to identify the array:
        <code>
        class MyJSONObjectEntry(JSONObjectEntry):
          @override
          def get_child_array_generator(self, child_key: str) -> type["JSONArrayEntry"] | None:
            if child_key == "chat_messages":
              return ChatMessagesEntry
            elif child_key == "documents":
              return DocumentsEntry
            elif child_key == "calls":
              return CallsEntry
            else:
              return None
        <code>

        If this method returns None, then the default JSONArrayEntry provided to the JSONEntry during initialization
        will be used.

        :param child_key: The name of the key used to identify the type of child object to return an Entry for.
        :return: An instance of JSONArrayEntry to use to generate the child item, or None to use the default
                 JSONArrayEntry.
        """
        return self.child_array_generator

    def get_child_value_generator(self, child_key: str) -> type["JSONValueEntry"] | None:
        """
        Allow a JSONObjectEntry to contain different definitions dependent on the key used to identify the child entry.
        For example, assuming a JSON object is defined as:
        <code>
        {
          "sender": "a-5443",
          "response_to": null,
          "sent_time": "2023-01-01T00:00:00Z",
          "message": "Hello, how are you?"
          "attachment": "/files/attachments/message_12345.pdf"
        }
        </code>
        Then you might have different JSONValueEntry implementations: (a) One for "sender" may lookup a user by id and
        return a name instead of the id, (b) One for "response_to" may lookup a different chat and add this as a child
        to it, (c) One for "sent_time" may convert the string to a date, and (d) one for "attachment" may load the file
        as a child FileEntry.
        <code>
        class MyJSONObjectEntry(JSONObjectEntry):
          @override
          def get_child_value_generator(self, child_key: str) -> type["JSONValueEntry"] | None:
            if child_key == "sender":
              return UserIdToNameLookupEntry
            elif child_key == "response_to":
              return RespondToChatEntry
            elif child_key == "sent_time":
              return SentTimeEntry
            elif child_key == "attachment":
              return AttachFileAsChildEntry
            else:
              return None
        <code>

        If this method returns None, then the default JSONValueEntry provided to the JSONEntry during initialization
        will be used.  The default implementation will return None.

        :param child_key: The name of the key used to identify the type of child object to return an Entry for.
        :return: An instance of JSONValueEntry to use to generate the child item, or None to use the default
                 JSONValueEntry.
        """
        return self.child_value_generator

class JSONFileEntry(FileEntry):
    """
    EntryInterface implementation used to store a JSON file.  The JSON file will consist of three types of data:
    * Simple data, like string, numbers, and booleans
    * Arrays that will contain sequential values consisting of any of the three types of values.
    * Objects that will contain key-value pairs, where the keys are strings and the values will contain any of the three
      types of values.

    A JSONFileEntry will add one child item.  If the file contains just a single simple value, then the item
    will produce a single child of a type based on JSONValueEntry, with the item in the case named "JSON Value" and
    the value stored in the property "Value".

    If the file contains a JSON array, the JSON file will have a single child of type JSONArrayEntry, with an item in
    the case named "JSON Array", and the values stored either as properties (for simple types), child items (for nested
    arrays and objects), or a combination with names of the properties and child items being the item's index in the
    array.

    If the file contains a JSON object, the JSON file will have a single child of type JSONObjectEntry, with an item in
    the case named "JSON Object".  Values will be stored either as properties (for simple types), as child items
    (for nested arrays and objects), or a combination.  Property and child names will be the keys from the object.

    The JSONFileEntry has a `add_to_builder` method that should be used to self-construct the contents of the Entry.
    """
    def __init__(self,
                 json_file_path: str,
                 mimetype: str = 'application/json',
                 parent_id: str = None,
                 simple_value_generator: Type[JSONValueEntry]|None = JSONValueEntry,
                 array_value_generator: Type[JSONArrayEntry]|None = JSONArrayEntry,
                 object_value_generator: Type[Any]|None = JSONObjectEntry,
                 type_map: dict[str, type] | None = None):
        """
        :param json_file_path: Full path, as a String, to the JSON file to be added.
        :param mimetype: Mimetype to assign to the JSON file, defaults to 'application/json'.
        :param parent_id: The ID of this item's parent, or None to make it a Top Level Item.'
        :param simple_value_generator: Subclass of JSONValueEntry to use as a simple value generator, or None to use the default.
        :param array_value_generator: Subclass of JSONArrayEntry to use as an array value generator, or None to use the default.
        :param object_value_generator: Subclass of JSONObjectEntry to use as an object value generator, or None to use the default.
        :param type_map: Optional dict mapping JSONPath patterns to entry classes.  Matched classes take precedence over
                         the class-delegation system.  Supported patterns:
                           ``$..key``        - any node named 'key' anywhere in the document (recursive descent)
                           ``$.key``         - root-level key
                           ``$.parent.key``  - exact nested path
                           ``$.arr[*].key``  - 'key' inside every element of array 'arr'
                         When multiple patterns match the same node the most specific (longest literal path) wins.
                         Values must be subclasses of JSONValueEntry, JSONArrayEntry, or JSONObjectEntry.
        """
        super().__init__(json_file_path, mimetype, parent_id)

        self.__simple_value_generator: Type[JSONValueEntry] = simple_value_generator or JSONValueEntry
        self.__array_value_generator: Type[JSONArrayEntry] = array_value_generator or JSONArrayEntry
        self.__object_value_generator: Type[JSONObjectEntry] = object_value_generator or JSONObjectEntry

        _valid_bases = (JSONValueEntry, JSONArrayEntry, JSONObjectEntry)
        for pattern, cls in (type_map or {}).items():
            if not (isinstance(cls, type) and issubclass(cls, _valid_bases)):
                raise TypeError(
                    f"type_map value for '{pattern}' must be a subclass of JSONValueEntry, "
                    f"JSONArrayEntry, or JSONObjectEntry; got {cls!r}"
                )
        self.__type_map: dict[str, type] = dict(type_map) if type_map else {}

        with self.file_path.open(mode="r", encoding=configs['encoding']) as json_file:
            self.__json = json.load(json_file)

    @property
    def json(self):
        return self.__json

    def add_as_parent_path(self, existing_path: str):
        return f'{self.name}/{existing_path}'

    def __resolve_type(self, path: list[str]) -> type | None:
        """
        Find the best-matching entry class from type_map for the given traversal path.
        When multiple patterns match, the most specific one (highest literal-segment count) wins.
        Returns None when type_map is empty or no pattern matches.
        """
        if not self.__type_map:
            return None
        best_cls = None
        best_specificity = -1
        for pattern, cls in self.__type_map.items():
            if _matches_path(pattern, path):
                spec = _pattern_specificity(pattern)
                if spec > best_specificity:
                    best_specificity = spec
                    best_cls = cls
        return best_cls

    def __child_generators(self, child_path: list[str],
                            entry_obj_gen: Type[JSONObjectEntry] | None,
                            entry_arr_gen: Type[JSONArrayEntry] | None,
                            entry_val_gen: Type[JSONValueEntry] | None,
                            default_obj_gen: Type[JSONObjectEntry],
                            default_arr_gen: Type[JSONArrayEntry],
                            default_val_gen: Type[JSONValueEntry],
                            ) -> tuple[Type[JSONObjectEntry], Type[JSONArrayEntry], Type[JSONValueEntry]]:
        """
        Determine the three generators for a child node.

        Priority (highest first):
          1. type_map match at child_path
          2. Per-key getter on the parent entry (entry_*_gen)
          3. Inherited defaults (default_*_gen)
        """
        obj_gen = entry_obj_gen or default_obj_gen
        arr_gen = entry_arr_gen or default_arr_gen
        val_gen = entry_val_gen or default_val_gen

        resolved = self.__resolve_type(child_path)
        if resolved is not None:
            if issubclass(resolved, JSONObjectEntry):
                obj_gen = resolved
            elif issubclass(resolved, JSONArrayEntry):
                arr_gen = resolved
            elif issubclass(resolved, JSONValueEntry):
                val_gen = resolved

        return obj_gen, arr_gen, val_gen

    def __add_object(self, builder: EDRMBuilder, name: str, obj: dict, parent_id: str,
                     object_generator: Type[JSONObjectEntry] | None = None,
                     array_generator: Type[JSONArrayEntry] | None = None,
                     value_generator: Type[JSONValueEntry] | None = None,
                     current_path: list[str] | None = None) -> JSONObjectEntry:
        if current_path is None:
            current_path = []
        if object_generator is None:
            object_generator = self.__object_value_generator
        if array_generator is None:
            array_generator = self.__array_value_generator
        if value_generator is None:
            value_generator = self.__simple_value_generator

        _contents: dict[str, Any] = {}
        _objects: dict[str, dict[str, Any]] = {}
        _arrays: dict[str, list[Any]] = {}

        for key, value in obj.items():
            if isinstance(value, dict):
                _objects[key] = value
            elif isinstance(value, list):
                _arrays[key] = value
            else:
                _, _, key_val_gen = self.__child_generators(
                    current_path + [key], None, None, None,
                    object_generator, array_generator, value_generator)
                val_value = key_val_gen(key, 'Value', value)
                _contents[key] = val_value['Value'].value

        object_entry = object_generator(name, _contents, parent_id=parent_id)
        object_id = object_entry[object_entry.identifier_field].value

        for key, value in _objects.items():
            child_path = current_path + [key]
            child_obj_gen, child_arr_gen, child_val_gen = self.__child_generators(
                child_path,
                object_entry.get_child_object_generator(key),
                object_entry.get_child_array_generator(key),
                object_entry.get_child_value_generator(key),
                object_generator, array_generator, value_generator)
            self.__add_object(builder, key, value, parent_id=object_id,
                              object_generator=child_obj_gen,
                              array_generator=child_arr_gen,
                              value_generator=child_val_gen,
                              current_path=child_path)

        for key, value in _arrays.items():
            child_path = current_path + [key]
            child_obj_gen, child_arr_gen, child_val_gen = self.__child_generators(
                child_path,
                object_entry.get_child_object_generator(key),
                object_entry.get_child_array_generator(key),
                object_entry.get_child_value_generator(key),
                object_generator, array_generator, value_generator)
            self.__add_array(builder, key, value, parent_id=object_id,
                             object_generator=child_obj_gen,
                             array_generator=child_arr_gen,
                             value_generator=child_val_gen,
                             current_path=child_path)

        builder.add_entry(object_entry)

        return object_entry

    def __add_array(self, builder: EDRMBuilder, name: str, array: list, parent_id: str,
                    object_generator: Type[JSONObjectEntry] | None = None,
                    array_generator: Type[JSONArrayEntry] | None = None,
                    value_generator: Type[JSONValueEntry] | None = None,
                    current_path: list[str] | None = None) -> JSONArrayEntry:
        if current_path is None:
            current_path = []
        if object_generator is None:
            object_generator = self.__object_value_generator
        if array_generator is None:
            array_generator = self.__array_value_generator
        if value_generator is None:
            value_generator = self.__simple_value_generator

        _contents: dict[str, Any] = {}
        _objects: dict[str, dict[str, Any]] = {}
        _arrays: dict[str, list[Any]] = {}

        for idx, itm in enumerate(array):
            if isinstance(itm, dict):
                _objects[str(idx)] = itm
            elif isinstance(itm, list):
                _arrays[str(idx)] = itm
            else:
                _, _, key_val_gen = self.__child_generators(
                    current_path + [str(idx)], None, None, None,
                    object_generator, array_generator, value_generator)
                itm_value = key_val_gen(str(idx), 'Value', itm)
                _contents[str(idx)] = itm_value['Value'].value

        array_entry = array_generator(name, _contents, parent_id=parent_id)
        array_id = array_entry[array_entry.identifier_field].value

        for obj_name, obj in _objects.items():
            child_path = current_path + [obj_name]
            child_obj_gen, child_arr_gen, child_val_gen = self.__child_generators(
                child_path,
                array_entry.get_child_object_generator(obj_name),
                array_entry.get_child_array_generator(obj_name),
                array_entry.get_child_value_generator(obj_name),
                object_generator, array_generator, value_generator)
            self.__add_object(builder, obj_name, obj, parent_id=array_id,
                              object_generator=child_obj_gen,
                              array_generator=child_arr_gen,
                              value_generator=child_val_gen,
                              current_path=child_path)

        for ary_name, ary in _arrays.items():
            child_path = current_path + [ary_name]
            child_obj_gen, child_arr_gen, child_val_gen = self.__child_generators(
                child_path,
                array_entry.get_child_object_generator(ary_name),
                array_entry.get_child_array_generator(ary_name),
                array_entry.get_child_value_generator(ary_name),
                object_generator, array_generator, value_generator)
            self.__add_array(builder, ary_name, ary, parent_id=array_id,
                             object_generator=child_obj_gen,
                             array_generator=child_arr_gen,
                             value_generator=child_val_gen,
                             current_path=child_path)

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
