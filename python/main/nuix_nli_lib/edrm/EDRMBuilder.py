from pathlib import Path
from typing import Any
from copy import deepcopy

from xml.dom.minidom import getDOMImplementation, Element, Document

from nuix_nli_lib.edrm import DirectoryEntry, EntryInterface, FileEntry, MappingEntry
from nuix_nli_lib import edrm


class EDRMBuilder:
    """
    Build and save an EDRM XML v1.2 XML load file.

    The goal is build a file which is generally compatible with the EDRM XML v1.2 specifications:
    https://edrm.net/resources/frameworks-and-standards/edrm-xml/1-2-schema/.  Though the written file will be a valid
    EDRM file, this tool is geared towards writing a file that will work as part of a Nuix Logical Image file (NLI), and
    as such certain formats will be enforced, key fields will be assigned that Nuix uses, but which may not be
    required or specifically known about for EDRM in general.

     To that end, there is a property: `as_nli` which will take a boolean value.  When true, locations and paths will
     be configured as a relative to the top of the expected NLI file rather than absolute or their natural paths on
     disk.

     This builder takes three basic types of Entries, each of which is a subclass of EntryInterface class:

     FileEntry:
     Represents a physical file on disk.  This type of entry will have a Native file associated with it
     and generally will not have child items.

     DirectoryEntry:
     Represents a directory or folder in the final case the load file will add evidence to.  The purpose of this type
     of entry will be to have children.  Normally it will not have a Native associated with it.

     MappingEntry:
     These are collections of Key:value pairs, such as might come from a database or a CSV file.  They will usually be
     a child to some other entry, will not have children themselves.  The purpose of this type of Entry is to be a
     vehicle for Fields (data values) rather than content (Text, or Binary).  However content can be provided.  When
     as_nli is False, this type will generally not have a Native associated with it, and will assign its content to an
     InlineContent node.  When as_nli is True, the content will be written to a file to use as a Native.

     The general process for using this builder:

     1. Create an instance of the EDRMBuilder class.
     2. Add Entries to the load file
      - Either use the `add_file`, `add_directory, and `add_mapping` methods to add entries of those specific types
      - Or generate an instance of an EntryInterface (or one of its subclasses) and use the `add_entry` method
     3. Set `output_path` to the final, absolute path to save the XML file to (including the file name)
     4. If this file will be used as part of an NLI file (or other container) set `as_nli` to `True`
     5. call `save` to build the XML document and save to the specified location.

     <code>
     builder = EDRMBuilder()                                                                       #1
     file_id = builder.add_file(r'C:/evidence/example.ps1', 'application/powershell_script', None) #2
     builder.output_path = pathlib.Path(r'C:/load_files`) / 'edrm_example.xml'                     #3
     builder.as_nli = False                                                                        #4
     builder.save()                                                                                #5
     </code>

    """
    def __init__(self):
        self.__output_path: Path = Path("./output.xml").resolve().absolute()
        self.__as_nli: bool = False

        self.__entries: dict[str, EntryInterface] = {}
        self.__families: dict[str, list[str]] = {}

    @property
    def output_path(self) -> Path:
        """
        :return: The full path, including the file name and extension, to which the EDRM load file will be written.
        """
        return self.__output_path

    @output_path.setter
    def output_path(self, output_path: Path) -> None:
        """
        Assign the full path, including the file name, to which the EDRM load file will be written.
        :param output_path:  Path to the output file.  It must not be None, should be an absolute path.
        :return: None
        """
        self.__output_path = output_path

    @property
    def as_nli(self) -> bool:
        """
        :return: True if the load file will be used as part of a Nuix Logical Image file (or other container).
        """
        return self.__as_nli

    @as_nli.setter
    def as_nli(self, as_nli: bool) -> None:
        """
        Set this EDRM load file as targeting a Nuix Logical Image file (or other container).
        :param as_nli: True to target an NLI, False for a standalone EDRM load file
        :return:  None
        """
        self.__as_nli = as_nli

    @property
    def entry_map(self) -> dict[str, EntryInterface]:
        """
        Retrieve a dictionary mapping each EntryInterface to its id.  Note: the returned dictionary cannot be used to
        modify the builder's collection of entries.
        :return: dictionary of strings representing an entry's id to the corresponding EntryInterface object
        """
        return deepcopy(self.__entries)

    def add_entry(self, entry: EntryInterface) -> str:
        """
        Add an implementation of the EntryInterface class to the EDRM load file.  Use this method when using a custom
        implementation of the EntryInterface class.  Alternative add_file, add_directory, and add_mapping methods
        perform the same task, but use the standard Entry types.
        :param entry: An entry in the EDRM load file.
        :return: The unique (within the load file) id for the added Entry.  Note, this ID must be produced by the
                 passed-in EntryInterface instance, it is not generated by this method.
        """
        entry_id = entry[entry.identifier_field].value
        self.__entries[entry_id] = entry
        parent_id = entry.parent

        if entry_id not in self.__families.keys():
            self.__families[entry_id] = []

        if parent_id is not None:
            family = self.__families.get(parent_id, [])
            family.append(entry_id)
            self.__families[parent_id] = family

        return entry_id

    def add_file(self, file_path: str, mimetype: str, parent_id: str = None) -> str:
        """
        Add a generic file as an entry in the EDRM load file.  Use this method as a convenience when you don't need
        a custom implementation of a FileEntry class.
        :param file_path: The full path to the native source file the entry will be used to reference
        :param mimetype: The mimetype to use for the file
        :param parent_id: Optional id of the new entry's parent.  When set, this item will be added into the parent
                          item's family structure as a child of the parent (and sibling to any existing children to the
                          parent)
        :return: The newly created entry's unique (within the scope of the load file) id.
        """
        return self.add_entry(FileEntry(file_path, mimetype, parent_id))

    def add_directory(self, directory: str, parent_id: str = None) -> str:
        """
        Add a generic directory as an entry in the EDRM load file.  This will generate a folder or directory
        in the final case the load file will populate.  Use this method as a convenience when you don't need
        a custom implementation of a DirectoryEntry class.  Directories should be added one layer at a time, with
        nested directories using the ID of their parent directory as the `parent_id` parameter to ensure the desired
        folder structure is generated within the case.
        :param directory: The name of the directory to add
        :param parent_id: Optional id of the new entry's parent.  When set, this item will be added into the parent
                          item's family structure as a child of the parent (and sibling to any existing children to the
                          parent)
        :return: The newly created entry's unique (within the scope of the load file) id.
        """
        return self.add_entry(DirectoryEntry(directory, parent_id))

    def add_mapping(self, mapping: dict[str, Any], mimetype: str, parent_id: str = None) -> str:
        """
        Add a dictionary as a generic mapping entry to the load file.  This will generate an entry containing the
        dictionary's contents as Fields.  Use this method as a convenience when you don't need a custom implementation
        of a MappingEntry class.
        :param mapping: The data to add as Fields to a new Entry
        :param mimetype: Mimetype to assign to the generated mapping entry
        :param parent_id: Optional ID of the new entry's parent.  When set, this item will be added into the  parent
                          item's family structure as a child of the parent (and sibling to any existing children to the
                          parent)
        :return: The newly created entry's unique (within the scope of the load file) id.
        """
        return self.add_entry(MappingEntry(mapping, mimetype, parent_id))

    def __add_folder(self, doc_id: str, document: Document, container: Element, families):
        """
        Internal method that recursively adds Folder elements to the XML document.
        """
        if self.__entries.get(doc_id).parent is not None:
            # If this isn't a top level item, add it as a document
            doc_element = document.createElement('Document')
            doc_element.setAttribute('DocId', doc_id)
            container.appendChild(doc_element)

        if doc_id not in families:
            # If this is not the top of a family, no need to continue
            return

        family = families.pop(doc_id)
        if len(family) > 0:
            # Add this document's family as contained documents and folders
            folder_element = document.createElement('Folder')
            folder_element.setAttribute('FolderName', doc_id)
            container.appendChild(folder_element)

            for child in self.__families[doc_id]:
                self.__add_folder(child, document, folder_element, families)

    def build(self) -> Document:
        """
        Create the EDRM load file document, but do not save it to disk.  Call this method only after setting the
        `as_nli` flag and adding all desired entries.  This is useful when the target location for saving the load file
        is not to disk, or if there is additional customization of the load file needed.  This file will be called from
        the `save()` method, so if the target is to save the file to disk without customization, there is no need to
        call this method explicitly.

        :return: Document containing the serialized load file contents.
        """
        impl = getDOMImplementation()
        doc = impl.createDocument(None, 'Root', None)
        root = doc.documentElement

        root.setAttribute('MajorVersion', '1')
        root.setAttribute('MinorVersion', '2')
        root.setAttribute('Description', 'EDRM XML Load File')
        root.setAttribute('Locale', 'US')
        root.setAttribute('DataInterchangeType', 'Update')

        field_list = doc.createElement("Fields")
        root.appendChild(field_list)
        for entry_id, entry in self.__entries.items():
            print(f"\tSerializing Fields for {entry_id}: {entry.name}", flush=True)
            entry.serialize_field_definitions(doc, field_list)

        batch_element = doc.createElement('Batch')
        root.appendChild(batch_element)
        doc_list = doc.createElement('Documents')
        batch_element.appendChild(doc_list)

        for entry_id, entry in self.__entries.items():
            print(f"\tSerializing File {entry_id}: {entry.name}", flush=True)
            entry.serialize_entry(doc, doc_list, self.__entries, self.as_nli)

        relationship_list = doc.createElement('Relationships')
        batch_element.appendChild(relationship_list)
        for parent_id, family in self.__families.items():
            print(f"\tBuilding Relationships {parent_id} of {len(family)} items", flush=True)
            for child_id in family:
                relationship = doc.createElement('Relationship')
                relationship.setAttribute('Type', 'Container')
                relationship.setAttribute('ParentDocId', parent_id)
                relationship.setAttribute('ChildDocId', child_id)
                relationship_list.appendChild(relationship)

        folders_list = doc.createElement('Folders')
        batch_element.appendChild(folders_list)

        working_families = deepcopy(self.__families)
        for entry_id in self.__families.keys():
            print(f"\tStructuring Family Folder for {entry_id}", flush=True)
            if entry_id in working_families:
                self.__add_folder(entry_id, doc, folders_list, working_families)

        return doc

    def save(self, doc: Document = None):
        """
        Save the EDRM load file document to the disk.  The `doc` argument is the DOM object containing the EDRM load
        file XML content.  It is optional, and if not provided, the `build()` method will be called to create it.
        For most cases, this method should be called without the parameter.

        This method should be called only after the `output_path` property and `as_nli` flag have been set and all
        desired entries are stored.  The result will be a fully realized EDRM XML Load File in the location specified
        by the`output_path` property.

        :param doc: The optional DOM object containing the EDRM load file XML content to be saved.  Use this argument
                    if you need to customize the load file before saving.  If so, call the `build()` method to generate
                    the load file, modify it, then call this save(doc) method (or store the XML another way).
        :return: None
        """
        if doc is None:
            print(f"Building EDRM file with {len(self.__entries)} entries", flush=True)
            doc = self.build()

        with self.output_path.open(mode='w', encoding=edrm.configs['encoding']) as load_file:
            print(f"Saving EDRM XML to {str(self.output_path)}", flush=True)
            doc.writexml(load_file, encoding=edrm.configs['encoding'], standalone=True, addindent='  ', newl='\n')
