from typing import Any

from edrm.EntryField import EntryField

next_key_index: int = 0


def next_key():
    global next_key_index
    field_id: int = next_key_index
    next_key_index += 1
    return f'field_{field_id}'


field_name_key_map: dict[str, str] = {}


def generate_field(field_name: str, field_type: str, default_value: Any) -> EntryField:
    if field_name in field_name_key_map:
        field_key = field_name_key_map[field_name]
    else:
        field_key = next_key()
        field_name_key_map[field_name] = field_key

    return EntryField(field_key, field_name, field_type, default_value)