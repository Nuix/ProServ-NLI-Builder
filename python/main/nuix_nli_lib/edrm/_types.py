from __future__ import annotations

from typing import Protocol, TypedDict, runtime_checkable


@runtime_checkable
class HashProtocol(Protocol):
    """Structural protocol matching the public interface of hashlib hash objects.

    Any object returned by ``hashlib.md5()``, ``hashlib.sha1()``, etc. satisfies this
    protocol.  Using ``HashProtocol`` as a parameter type instead of the private
    ``hashlib._Hash`` keeps the annotation portable across CPython, PyPy, and future
    Python releases.
    """

    def update(self, data: bytes) -> None:
        ...

    def hexdigest(self) -> str:
        ...

    def digest(self) -> bytes:
        ...


class EDRMConfigs(TypedDict):
    """Typed structure for EDRM configuration parameters.

    date_time_format:
    Format string for writing date-time values to the file.  This format will be applied to all date-time fields.  The
    format string should follow Python's format codes:
    https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes.  This format string is
    generally not complete — the ``%f`` code produces 6 decimal places, but Nuix expects just three, so the last
    three digits will be trimmed from the end of the formatted string.  This is important to understand if you change
    this format.

    time_zone_format:
    Currently a stand-in for a potential time-zone format string.  As this tool targets Nuix, and Nuix keeps times in
    GMT, this string is hard-coded as ``+00:00``.  In the future, or to support other tools, this could be changed.

    hash_buffer_size:
    Number of bytes to read per chunk when generating hashes on files.  This value prevents run-away memory use when
    generating hashes on large files.

    encoding:
    Encoding used to write the EDRM XML file and any other string output this tool puts to disk.

    custodian:
    Default custodian used to assign entries to.  Each entry will be assigned to the same custodian.  Note: this
    custodian is meaningful only in the context of the EDRM file and does not generate or assign the custodian in
    Nuix.

    default_itemdate_field:
    Name of the field that will be used when generating a MappingEntry's Item Date field.  This is the field that
    will be used to place the item on a timeline, if present.

    default_rowname_field:
    Name of the field that will be used when generating a MappingEntry's Name.  This is the field which will be used
    to display the MappingEntry in the Nuix case.
    """

    date_time_format: str
    time_zone_format: str
    hash_buffer_size: int
    encoding: str
    custodian: str
    default_itemdate_field: str
    default_rowname_field: str
