from nuix_nli_lib.edrm._types import EDRMConfigs

from nuix_nli_lib.edrm.EDRMUtilities import *
from nuix_nli_lib.edrm.EntryField import EntryField
from nuix_nli_lib.edrm.FieldFactory import *
from nuix_nli_lib.edrm.EntryInterface import EntryInterface
from nuix_nli_lib.edrm.FileEntry import FileEntry
from nuix_nli_lib.edrm.DirectoryEntry import DirectoryEntry
from nuix_nli_lib.edrm.MappingEntry import MappingEntry
from nuix_nli_lib.edrm.EDRMBuilder import EDRMBuilder


configs: EDRMConfigs = {
    'date_time_format': '%Y-%m-%dT%H:%M:%S.%f',
    'time_zone_format': '+00:00',
    'hash_buffer_size': 65536,
    'encoding': 'UTF-8',
    'custodian': 'Unknown',
    'default_itemdate_field': 'CreateTime',
    'default_rowname_field': 'Name'
}
