import hashlib
import platform
import tempfile
from datetime import datetime
from pathlib import Path
import shutil
from typing import Any
from xml.dom.minidom import getDOMImplementation, Document, Element

from nuix_nli_lib import edrm, debug_log, configs as nli_configs
from nuix_nli_lib.edrm import DirectoryEntry, EDRMBuilder, EntryInterface, EntryField, FileEntry, MappingEntry, EDRMUtilities as eutes
from nuix_nli_lib.nli import NLIGenerator

class NLISubclass(NLIGenerator):
    """
    Subclass for NLIGenerator specific to the journal email use case. Adds a method to access the edrm_builder via a
    method
    """
    def __init__(self):
        super().__init__()

    @property
    def edrm_builder(self):
        return self._NLIGenerator__edrm_builder

    def add_entry(self, entry: EntryInterface) -> str:
        """
        Subclass method to add an entry to the NLI for journal emails, specifically the EmailFileEntry (a subclass of
        Mapping Entry which uses Message ID as the identifier instead of SHA-1).
        This method checks if the Message ID already exists in the entry_map, if it does it merges the metadata instead
        of creating a new record.
        :param entry:
        :return:
        """
        field = entry.identifier_field
        newmessageID = entry[field].value
        entry_map = self.edrm_builder.entry_map
        if newmessageID in entry_map: #Check if the Message ID already exists in the entry map
            print("Key exists in the dictionary.")
            origEntry = entry_map[newmessageID]
            mergekey = list( origEntry.fields | entry.fields)
            for m in mergekey: #Iterate through all keys that appear in both entries
                print(m)
                if origEntry[m].value != entry[m].value: #If the entries don't match, merge the values, otherwise do nothing
                    newvalue = f"{str(origEntry[m].value)};{str(entry[m].value)}"
                    newField = EntryField(origEntry[m].key, origEntry[m].name, origEntry[m].data_type, newvalue)
                    origEntry[m] = newField #Update origEntry
            return super().add_entry(origEntry) #Add the potentially updated original entry into the entry map
        else: #Otherwise treat like a normal entry
            return super().add_entry(entry)
