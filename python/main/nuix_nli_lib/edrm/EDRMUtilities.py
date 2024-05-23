import re
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Union, Any

from nuix_nli_lib import edrm

"""
Collection of utility functions for working with EDRM data.
"""


def convert_datetime_to_string(date_time: datetime) -> str:
    """
    Converts a Python datetime object to a string in the format preferred by Nuix.  Note, this does not handle
    timezones correctly (always assumes +00:00).  The formats used for storing the data-time are specified in the
    `edrm.configs` object.

    NOTE: Python can only represent a fraction of a second to six decimal digits, while Nuix prefers three.  As a result
    this method truncates the date-time string by three characters.  This means the format string should provide those
    excess three characters (such as by using the %f token or padding the end of the string).

    :param date_time: The datetime to convert
    :return: A string with the formatted date-time
    """
    str_rep = date_time.strftime(edrm.configs['date_time_format'])[:-3]
    tz_rep = date_time.strftime(edrm.configs['time_zone_format'])
    return str_rep + tz_rep


def convert_timestamp_to_string(timestamp: float) -> str:
    """
    Convert a timestamp similar to those provided by Path stat blocks to a string.  A timestamp is a floating point
    offset from the epoch.

    :param timestamp: Timestamp as a floating point number
    :return: A string with the timestamp converted to the format preferred by Nuix.  See `convert_datetime_to_string`.
    """
    dt = datetime.fromtimestamp(timestamp)
    return convert_datetime_to_string(dt)


def _hash_file(file: Path, hashfunction: hashlib) -> None:
    """
    Intermediate function to update the hash with the contents of the file.
    """
    with file.open('rb') as dump_file:
        while True:
            data = dump_file.read(edrm.configs['hash_buffer_size'])
            if not data:
                break

            hashfunction.update(data)


def hash_file(file: Path, hashfunction: hashlib, as_string: bool = True) -> Union[str, bytes]:
    """
    Generate a hash for the provided file. This will work on large files by breaking it into smaller chunks.  Use the
    `edrm.configs` object to control how large those chunks are.
    :param file: File on disk to generate a hash for
    :param hashfunction: an initialized hash function to use to generate the hash
    :param as_string: If `True`, the hash will be returned as a string, otherwise it as a bytes object.
    :return: Either a hex encoded string or a bytes object depending on the value of `as_string`
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
    hashfunction.update(str(data).encode(edrm.configs['encoding']))


def hash_data(data: Any, hashfunction: hashlib, as_string: bool = True) -> Union[str, bytes]:
    """
    Generate a hash for the provided data. This converts data to string prior to hashing it.
    :param data: Data to calculate a hash on
    :param hashfunction: an initialized hash function to use to generate the hash
    :param as_string: Return the hash as a hex-encoded string (true) or bytes (false)
    :return: Either a hex encoded string of a bytes object depending on the `as_string` value
    """
    _hash_data(data, hashfunction)

    if as_string:
        return hashfunction.hexdigest()
    else:
        return hashfunction.digest()


def hash_directory(directory: Path, hashfunction: hashlib, as_string: bool = True) -> Union[str, bytes]:
    """
    Hash the contents of a directory.  The contents of the directory includes all the non-empty files, all the files'
    names, calculated recursively through subdirectories.
    :param directory: The root directory to begin hashing from
    :param hashfunction:  an initialized hash function to use to generate the hash
    :param as_string: If `True`, the hash will be returned as a string, otherwise as bytes object.
    :return: The hash as a hex-encoded string if `as_string is true or bytes if it is false
    """
    if directory.is_dir():
        for root, dirs, files in directory.walk():
            for f in files:
                _hash_data(f, hashfunction)
                _hash_file(Path(root, f), hashfunction)

    if as_string:
        return hashfunction.hexdigest()
    else:
        return hashfunction.digest()


def generate_relative_path(entry: object, entry_map: dict[str, object]) -> str:
    """
    Generate a relative path for the provided entry.  The path is calculated by recursively walking up each parent-layer
    and adding the parent's name to the start of the path, stopping when there is no parent.  The path will include
    the entry's name.
    :param entry: An instance of the EntryInterface class to generate a relative path for
    :param entry_map: A mapping of the entries known for the EDRM file, so parent entries can be located
    :return:  A string containing the relative path to the entry from the root of the container for this EDRM file
    """
    relative_path = entry.name

    tmp_current_entry = entry
    while tmp_current_entry.parent is not None:
        tmp_current_entry = entry_map[tmp_current_entry.parent]
        relative_path = tmp_current_entry.add_as_parent_path(relative_path)

    return relative_path


ILLEGAL_UNI_CHARS = [(0x00, 0x08), (0x0B, 0x0C), (0x0E, 0x1F),
                     (0x7F, 0x84), (0x86, 0x9F),
                     (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF)]
if sys.maxunicode >= 0x10000:  # not narrow build
    ILLEGAL_UNI_CHARS.extend([(0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF),
                              (0x3FFFE, 0x3FFFF), (0x4FFFE, 0x4FFFF),
                              (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
                              (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF),
                              (0x9FFFE, 0x9FFFF), (0xAFFFE, 0xAFFFF),
                              (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
                              (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF),
                              (0xFFFFE, 0xFFFFF), (0x10FFFE, 0x10FFFF)])

ILLEGAL_UNI_RANGES = [fr'{chr(low)}-{chr(high)}' for (low, high) in ILLEGAL_UNI_CHARS]
XML_ILLEGAL_CHARS_REGEX = '[' + ''.join(ILLEGAL_UNI_RANGES) + ']'
XML_ILLEGAL_CHARS_COMPILED_RE = re.compile(XML_ILLEGAL_CHARS_REGEX)


def sanitize_xml_content(content: str) -> str:
    return XML_ILLEGAL_CHARS_COMPILED_RE.sub('_', content)


FILE_INVALID_CHARS = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '\0']
FILE_INVALID_CHARS_REGEX = '[' + ''.join(FILE_INVALID_CHARS) + ']'
FILE_INVALID_CHARS_COMPILED_RE = re.compile(FILE_INVALID_CHARS_REGEX)


def sanitize_filename(filename: str) -> str:
    output: str = FILE_INVALID_CHARS_COMPILED_RE.sub("_", filename).strip()
    output = output[:-1] if output.endswith('.') else output
    return output
