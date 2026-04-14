from typing import Any

from nuix_nli_lib.edrm.EntryField import EntryField

next_key_index: int = 0
""" Counter for the known set of fields, such as to provide unique names for each field node """


def next_key():
    """
    Keys, in this respect, are used as the names of XML Nodes identifying the field values for each entry in an
    EDRM load file.  Fields are first listed with their definition once, and are provided a key, which then links that
    definition to the XML node that provides the values for the document.  Each field's name must be unique within the
    context of the EDRM load file.  This method generates a unique key in a sequence.

    :return: The next key name to use in sequence, in the format "field_n"
    """
    global next_key_index
    field_id: int = next_key_index
    next_key_index += 1
    return f'field_{field_id}'


field_name_key_map: dict[str, str] = {}
"""
Maps the names of a EDRM Field to their Key, such that a Field that has already been created can be looked up to find
the Key needed for representing the Field's value.
"""


def generate_field(field_name: str, field_type: str, default_value: Any) -> EntryField:
    """
    Given the field definition as provided in the parameters, create a new EntryField with a unique Key.  If a Field
    Name already exists the existing Key will be used.  However, in all cases a new EntryField instance will be created
    as the Field will also hold the value specific to a single Entry.
    :param field_name: The name of the field as you would expect it to appear in the final Case
    :param field_type: The type of data to store in the Field.  Should be one of the edrm.EntryField.TYPE_* constants
    :param default_value: Value to provide a field for a document when it has the Field Key but no value is provided.
    :return: A new instance of EntryField with the provided parameters and a Key uniquely identifying the field (name).
    """
    if field_name in field_name_key_map:
        field_key = field_name_key_map[field_name]
    else:
        field_key = next_key()
        field_name_key_map[field_name] = field_key

    return EntryField(field_key, field_name, field_type, default_value)