import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Union, Any

from edrm.EntryField import EntryField


def convert_datetime_to_string(date_time: datetime) -> str:
    """
    Converts a Python datetime object to a string in the format preferred by Nuix.  Note, this does not handle
    timezones correctly (always assumes +00:00)
    :param date_time: The datetime to convert
    :return: A string with the formatted date-time
    """
    str_rep = date_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    tz_rep = date_time.strftime('+00:00')
    return str_rep + tz_rep


def convert_timestamp_to_string(timestamp: float):
    """
    Convert a timestamp similar to those provided by Path stat blocks to a string.
    :param timestamp: Timestamp a
    :return:
    """
    dt = datetime.fromtimestamp(timestamp)
    return convert_datetime_to_string(dt)


def _hash_file(file: Path, hashfunction: hashlib):
    """
    Intermediate function to update the hash with the contents of the file.
    """
    BUFFER_SIZE = 65536
    with file.open('rb') as dump_file:
        while True:
            data = dump_file.read(BUFFER_SIZE)
            if not data:
                break

            hashfunction.update(data)


def hash_file(file: Path, hashfunction: hashlib, as_string: bool = True) -> Union[str, bytes]:
    """
    Generate a hash for the provided file. This will work on large files by breaking it into 64K chunks.
    :param file: File on disk to generate a hash for
    :param hashfunction: an initialized hash function to use to generate the hash
    :return: Hex representation of the hash
    """
    _hash_file(file, hashfunction)

    if as_string:
        return hashfunction.hexdigest()
    else:
        return hashfunction.digest()


def _hash_data(data: Any, hashfunction: hashlib):
    """
    Intermediate function to update a hash function with the contents of some data.
    """
    hashfunction.update(str(data))


def hash_data(data: Any, hashfunction: hashlib, as_string: bool = True) -> Union[str, bytes]:
    """
    Generate a hash for the provided data. This converts data to string prior to hashing it.
    :param data: Data to calculate a hash on
    :param hashfunction: an initialized hash function to use to generate the hash
    :param as_string: Return the hash as a hex-encoded string (true) or bytes (false)
    :return: Hex representation of the hash
    """
    _hash_data(data, hashfunction)

    if as_string:
        return hashfunction.hexdigest()
    else:
        return hashfunction.digest()


def hash_directory(directory: Path, hashfunction: hashlib, as_string: bool = True) -> Union[str, bytes]:
    if directory.is_dir():
        for root, dirs, files in directory.walk():
            for f in files:
                _hash_data(f, hashfunction)
                _hash_file(Path(root, f), hashfunction)

    if as_string:
        return hashfunction.hexdigest()
    else:
        return hashfunction.digest()


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

    return EntryField(field_key, field_name, field_type, default_value)