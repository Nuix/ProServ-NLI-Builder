"""
The Nuix NLI Library

This library contains the core logic for building Nuix Logical Image files from arbitrary data sources.  It consists of
three main modules:
- `edrm`: Provides classes that are used to create the EDRM XML load files with a hierarchical view of input data that
          are the heart of the Nuix Logical Image.
- `nli`: Provides a generator used to create the EDRM XML load file, the extra Metadata, and the native files that
         combine to form the Nuix Logical Image..
- `data_types`: Provides classes that can be used to convert specific file types, such as CSV or JSON, to a Nuix
                Logical Image.

### EDRMBuilder
At the center of the library is the `edrm.EDRMBuilder` class, which is used to build the EDRM XML load file.  It uses
subclasses of `edrm.EntryInterface` to represent the various types of data that can be added to the EDRM XML load file:
- `edrm.FileEntry`: Represents a physical file on disk.  This type of entry will have a Native file associated with it
                    as well as some metadata.
- `edrm.DirectoryEntry`: Represents a directory or folder in the final case the load file will add evidence to.  The
                          purpose of this type of entry will be to have children.  Normally it will not have a Native
                          associated with it, but can have metadata.
- `edrm.MappingEntry`: These are collections of Key:value pairs, such as might come from a database or a CSV file.  They
                        will usually be used to represent a table or other collection of data.  The key:values will be
                        stored as metadata, and will have natives with the key and value as the content.

Additional Entry types can be created by subclassing `edrm.EntryInterface` or extending one of the above existing
types.  For example, one my create a type that can have children, like a DirectoryEntry, but also have a native file
associated with it, like a FileEntry.  To do this, extend the `edrm.FileEntry` class.

The general process for using this builder:

1. Create an instance of the EDRMBuilder class.
2. Add Entries to the load file
 - Either use the `add_file`, `add_directory, and `add_mapping` methods to add entries of those specific types
 - Or generate an instance of an EntryInterface (or one of its subclasses) and use the `add_entry` method
3. Set `output_path` to the final, absolute path to save the XML file to (including the file name)
4. If this file will be used as part of an NLI file (or other container) set `as_nli` to `True`
5. call `save` to build the XML document and save to the specified location.

<code>
    builder = EDRMBuilder()                                                                           #1
    folder_id = builder.add_directory('evidence', None)                                               #2
    file_id = builder.add_file('C:/evidence/example.ps1', 'application/powershell_script', folder_id) #2
    builder.output_path = pathlib.Path(r'C:/load_files`) / 'edrm_example.xml'                         #3
    builder.as_nli = False                                                                            #4
    builder.save()                                                                                    #5
</code>

EDRM file generation can be customized in several ways:
- The `edrm.config` hash can be modified to change:
    - The `default_rowname_field`: the name of the data field used to name a particular MappingEntry row.
    - The `default_itemdate_field`: the name of a data field used to provide the Item Date for a MappingEntry row.
    - The `date_time_format`: the format string used to store all date, time, and date-time values to the EDRM XML file.
    - The `encoding`: the text encoding used to store the EDRM XML file.
    - The `custodian`: the name of the Custodian to assign entries to.  Note that this field is used for all items in
                       the EDRM XML file, and does not generate Custodians in Nuix.
    - The `hash_buffer_size`: the size of a buffer used when generating hashes from files (in bytes).

### NLIGenerator
The `nli.NLIGenerator` class is used to generate the Nuix Logical Image (NLI) file.  An NLI file is essentially a zip
file containing an EDRM XML load file, some additional metadata defining what is in the ZIP file, and any native
content to load into a Nuix case.  The `NLIGenerator` class is a thin wrapper around the `edrm.EDRMBuilder` class,
and adds additional metadata and packages the entries into the NLI ZIP container.  The process of using it is as
follows:
1. Create an instance of the NLIGenerator class.
2. Add Entries to the load file
 - Either use the `add_file`, `add_directory, and `add_mapping` methods to add entries of those specific types
 - Or generate an instance of an EntryInterface (or one of its subclasses) and use the `add_entry` method
3. call `save` to build the NLI file and save it to the specified location.

<code>
    nli = NLIGenerator()                                      #1
    l1 = nli.add_directory('Evidence_level_1')                #2
    nli.add_file('doc1.txt', 'text/plain', l1)                #2
    nli.add_file('doc2.txt', 'text/plain', l1)                #2
    l2 = nli.add_directory('Evidence_level_2', l1)            #2
    nli.add_file('doc3.txt', 'text/plain', l2)                #2
    nli.save(pathlib.Path(r'C:/work/evidence/sample.nli'))    #3
</code>

This would produce an NLI file named 'sample.nli' in the C:/work/evidence folder which would produce a structure
in the case that looks like below:

<pre>
Evidence 1
└─ sample.nli
   └─ Evidence_level_1
      ├─ doc1.txt
      ├─ doc2.txt
      └─ Evidence_level_2
         └─ doc3.txt
</pre>

### Specific Data Types
The EDRMBuilder and NLIGenerator can be used to manually build load files from arbitrary data sources.  To make working
with specific common data types easier, the library also provides classes in the `data_types` module that simplify
working with these types of data.

#### CSV Files
A CSV file can be represented in a Nuix case as a physical file containing a set of rows, each with its own metadata.
In an NLI file, that would be represented as a FileEntry (the CSV file itself) that contains children MappingEntries for
each row in the CSV file.  In this library, the `data_types.csv_file.CSVEntry` class is used to represent CSV file
itself, and `data_types.csv_file.CSVRowEntry` is used to represent each row in the CSV file.  The CSVRowEntry class
should be subclassed to provide specific requirements for mapping data to rows such as:
- providing a `name` for the row as it should appear in the Nuix case
- date-time conversions for fields if not using the standard format
- a custom mime-type for the row

When a CSVEntry is added to an NLIFactory using the `add_entry` method, the CSVEntry will also add all of its rows
to the NLIFactory, via its `add_to_builder()` method.  If the CSVEntry is added to a non-NLI EDRMBuilder, then the
`CSVEntry#add_to_builder()` method will be called instead of the EDRMBuilder's `add_entry()` method.

##### Example
In this example, a rather complete example of a CSVRowEntry is shown.  It will override the default CSVRowEntry:
- To allow for nested children under the Row
- Look up a a value to use as a unique identifier for the row (which will be used to nest children under)
- Generate a unique name for the row based on the identifier
- Provide a specific column name for the Item Date field, and customize the date-time format
- Prevent any text / native from being stored for the row.

<code>
class ProcessEntry(CSVRowEntry):
    def __init__(self, parent_csv: CSVEntry, row_index: int):
        ppid = parent_csv.data[row_index]['PPID']
        known_ppid = len([row for row in parent_csv.data if row['PID'] == ppid]) > 0
        super().__init__(parent_csv, row_index, parent_id=ppid if known_ppid else None)

    @property
    def identifier_field(self) -> str:
        return 'PID'

    def get_name(self) -> str:
        return f'({self['PID'].value}) {self['ImageFileName'].value}'

    @property
    def time_field(self) -> str:
        return 'CreateTime'

    @property
    def itemdate(self) -> datetime:
        return datetime.strptime(self['CreateTime'].value.strip(), '%Y-%m-%d %H:%M:%S.%f')

    @property
    def text(self) -> Union[str, None]:
        return None

    def add_as_parent_path(self, existing_path: str):
        return f'{self.name}/{existing_path}'
</code>

Note that to take advantage of the nested children feature, the CSVEntry would need to be subclassed to determine the
parent-child relationships.  However, this example won't show that.

Once the CSVRowEntry is created, adding a CSV file to the NLIFactory follows this process:
1. Create an instance of the CSVEntry class, providing the path to the CSV file and the name of the CSVRowEntry class
   to use to generate the rows
2. Create an instance of the NLIFactory class.
3. Add the CSVEntry to the NLIFactory using the `add_entry` method.
4. Save the NLI to disk.

<code>
    csv_entry = CSVEntry(r'C:/work/evidence/process.csv', ProcessEntry) #1
    nli = NLIGenerator()                                                #2
    nli.add_entry(csv_entry)                                            #3
    nli.save(pathlib.Path(r'C:/work/evidence/sample.nli'))              #4
</code>

#### JSON Files
JSON files can be represented in a Nuix case as a physical file containing set of nested items with properties
representing the data.  In an NLI file, that would be represented as a FileEntry (the JSON file itself) that contains
children.  JSON files can have simple values, arrays, or objects stored in them, with arrays and objects possibly
containing nested content (more simple values, arrays, or objects).  In this library, the
`data_types.json_file.JSONFileEntry` class is used to represent JSON file itself, and the following types are used to
represent the various types of data that can be stored in a JSON file:
- `data_types.json_file.JSONValueEntry`: Represents a simple value, which can be a String, number, boolean, or Null.
    When encountered as a top-level type in the JSON file the value will be used as the item's native/text.  When found
    as a child of another type, the value will be used as a property's value on the parent item.
- `data_types.json_file.JSONObjectEntry`: Represents a JSON object, which is a dictionary of key:value pairs.  The value
    can be simple values, nested arrays, or nested objects.  This creates a single item in a Nuix case to represent the
    object, with simple values being represented as properties.  Nested arrays and objects would be added as child items,
    whose name will be the key in the JSON object.  This means that all the keys in a single object may be represented
    as a mix of properties and child items.
- `data_types.json_file.JSONArrayEntry`: Represents a JSON array, which is a list of simple values, nested arrays, or
    nested objects.  This creates a single item in a Nuix case to represent the array.  Simple values stored in the
    array are represented as properties with their property name being the index into the array.  Nested arrays and
    nested objects will be represented as child items, whose name will be the index into the array.  This means that all
    the items in a single array may be represented as a mix of properties and child items.

It may be necessary to subclass one or more of these JSON types to provide additional functionality, for example to
override how names are generated, the mimetypes used, or how date-time values are converted.  For detailed
transformation of a JSON file into an NLI, it may be necessary to subclass each of the types several times, and subclass
the JSONFileEntry to provide the appropriate combination of overriden types as needed.
"""
__version__ = "1.3.0"

configs = {}


def debug_log(message: str, flush: bool = False) -> None:
    """
    Write a message to stdout if the application is run in debug mode.  To run the application in debug mode, add
    the debug parameter to the above `configs` dictionary and set it to `True`:
    `
    from nli_lib import configs as nli_configs
    nli_configs['debug'] = True
    `
    Then any code sent to this method will be logged.  Without that, or if it is set to a falsey value, then messages
    will not be logged.

    :param message: String message to send to stdout.
    :param flush: If set to `True`, the debug message will be flushed to the stdout immediately, otherwise it will wait
                  for any cache to be filled before being logged.
    :return: None
    """
    if 'debug' in configs and configs['debug']:
        print(message, flush=flush)


def cli():
    import code

    from pathlib import Path
    from datetime import datetime

    from nuix_nli_lib import edrm
    from nuix_nli_lib import nli
    from nuix_nli_lib import data_types

    from nuix_nli_lib.edrm import EntryInterface, FileEntry, DirectoryEntry, MappingEntry, EDRMBuilder, generate_field
    from nuix_nli_lib.data_types import CSVEntry, CSVRowEntry, JSONValueEntry, JSONArrayEntry, JSONObjectEntry, \
        JSONFileEntry
    from nuix_nli_lib.nli import NLIGenerator

    banner = (
        "                                                                                                           \n" +
        "                                                                                                           \n" +
        "                                                                                                           \n" +
        "     #########      ###**###                                                                               \n" +
        "   #*#*######**###***######***#                                                                            \n" +
        " #**##**#****###*####*******####                                                                           \n" +
        " **##**#**#########*##*#**#**##*#                                                                          \n" +
        "#**#*#***##*###**#*##**###*#*##*##    ##**#####*****###    ##****        *****#  ##*### ##**#        ##*## \n" +
        "#*#**#**#   #######*##  ##*#**####   #****************##  #*****#       ##***** #*****# #*****#    ##****#*\n" +
        " #*#*#*#**#  #**##*#*  ##*##**#*#    #*******#####******# #*****#       #*****# #******  #*****#  #******# \n" +
        " #####*###### ##***  #*###*#*##*     #******#      ******##*****#       #*****# #******   ##****##*****#   \n" +
        "   #*##**#***#  ## ###*##*##**#      #*****#       *****#*#*****#       #*****# #******     #********##    \n" +
        "    #**##**##**   ***##**##**#       #*****#       ##*****#*****#       #*****# #******      ##*****#      \n" +
        "   ***######**     #####*#*#**#      #*****#       ##*****#*****#       #*****# #******     #********#     \n" +
        " #**##**##**# ##**#  #*##*###*##     #*****#       ##*****##****##      #*****# #******   ##***********#   \n" +
        "#*###*##**#  #**##*#   ####**##*#    #*****#       ##***** #*****### ##*#*****# #******  #******# *#****#  \n" +
        "#*##*#####  #####*#*##  #**##*##*#   #*****#       ##*****  ##**********#*****# #****** ##****#    #*****##\n" +
        "#*#**##*# #####*#*#*##*  #**#**#*#    #*****       #*****#   ###********#****## #****## ****##       ****##\n" +
        "**##*###**#*###* #**###**###**####     ###           ###        ##*###    ####    ###    ###          ##*  \n" +
        " ##*###*####*###**##**#*****#####                                                                          \n" +
        "  #**####*####**#*#*##*#*###**##                                                                           \n" +
        "    ##*#***#*##    ##*****#*##                                                                             \n" +
        "                                                                                                           \n" +
        "                                                                                                           \n" +
        "Nuix Logical Image Builder: the nuix_nli_lib packages and its children are available.                      \n" +
        "                                                                                                           \n" +
        "Use CTRL+Z to quit.  Start working with:                                                                   \n" +
        " --------------------------                                                                                \n" +
        " |  nli = NLIGenerator()  |                                                                                \n" +
        " --------------------------                                                                                "
        )

    namespace = {
        "Path": Path,
        "datetime": datetime,
        "edrm": edrm,
        "nli": nli,
        "data_types": data_types,
        "EntryInterface": EntryInterface,
        "FileEntry": FileEntry,
        "DirectoryEntry": DirectoryEntry,
        "MappingEntry": MappingEntry,
        "EDRMBuilder": EDRMBuilder,
        "generate_field": generate_field,
        "CSVEntry": CSVEntry,
        "CSVRowEntry": CSVRowEntry,
        "JSONValueEntry": JSONValueEntry,
        "JSONArrayEntry": JSONArrayEntry,
        "JSONObjectEntry": JSONObjectEntry,
        "JSONFileEntry": JSONFileEntry,
        "NLIGenerator": NLIGenerator,
    }

    code.interact(banner=banner, local=namespace)
