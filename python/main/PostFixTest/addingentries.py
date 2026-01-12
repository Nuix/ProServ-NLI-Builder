

# fileentry = FileEntry(Path(r'C:\Work\PostFix\Export\Items\[Unnamed Unrecognised Item].txt'), mime_type='text/plain')
#
# nli = NLIGenerator()
# nli.add_entry(fileentry)
# nli.save(Path(r'C:\Work\NLIBuilder\BuiltNLI'))
#
# dict[str, Any] = {''}
# mapping_entry = MappingEntry()
#
#
# def test_file_with_mapping(self):
#     builder = EDRMBuilder()
#     builder.as_nli = False
#     builder.output_path = self.output_path / 'file_and_map_test.xml'
#     file_id = builder.add_file(self.sample_file, "application/powershell_script")
#     map_id = builder.add_mapping(self.sample_mapping, "application/x-database-table-row", file_id)
#     builder.save()
#from nuix_nli_lib.test import emailFileEntry
sample_mapping = {'Message-ID':"CH3PR12MB872512DFFBC8EA1A50DB5A85EDAAA@CH3PR12MB8725.namprd12.prod.outlook.com", "To" : "Victor Renfield <victor.renfield@csiventuresoutlook.onmicrosoft.com>", "From" : "Colonel Mustard <cmustard@csiventuresoutlook.onmicrosoft.com>", "BCC" : "linda.pei@nuix.com"}
entry = EmailFileEntry(sample_mapping,"message/rfc822")
nli = NLISubclass()
nli.add_entry(entry)
sample_mapping2 = {'Message-ID':"CH3PR12MB872512DFFBC8EA1A50DB5A85EDAAA@CH3PR12MB8725.namprd12.prod.outlook.com", "To" : "Victor Renfield <victor.renfield@csiventuresoutlook.onmicrosoft.com>", "From" : "Colonel Mustard <cmustard@csiventuresoutlook.onmicrosoft.com>", "BCC" : "bccTest@mapping.com"}
entry2 = EmailFileEntry(sample_mapping2,"message/rfc822")
nli.add_entry(entry2)
nli.edrm_builder

nli.edrm_builder.entry_map


nli.save(Path(r'C:\Work\NLIBuilder\BuiltNLI'))

sample_mapping3 = {'Message-ID':"CH3PR12MB872512DFFBC8EA1A50DB5A85EDAAA@CH3PR12MB8726.namprd12.prod.outlook.com", "To" : "Victor Renfield <victor.renfield@csiventuresoutlook.onmicrosoft.com>", "From" : "Colonel Mustard <cmustard@csiventuresoutlook.onmicrosoft.com>", "BCC" : "bccTest@mapping.com"}
entry3 = EmailFileEntry(sample_mapping3,"message/rfc822")
edrm = nli.edrm_builder
nli.add_entry(entry3)
sample_mapping4 = {'Message-ID':"CH3PR12MB872512DFFBC8EA1A50DB5A85EDAAA@CH3PR12MB8727.namprd12.prod.outlook.com", "To" : "Victor Renfield <victor.renfield@csiventuresoutlook.onmicrosoft.com>", "From" : "Colonel Mustard <cmustard@csiventuresoutlook.onmicrosoft.com>", "BCC" : "bccTest@mapping.com"}
entry4 = EmailFileEntry(sample_mapping4,"message/rfc822")
edrm = nli.edrm_builder
nli.add_entry(entry4)

nli.__edrm_builder.entry_map


builder = EDRMBuilder()
builder.as_nli = True
builder.output_path = Path(r'C:\Work\PostFix\CSV\Output')
#file_id = builder.add_file(Path(r'C:\Work\PostFix\CSV\BCC.eml'), "message/rfc822")
sample_mapping = {'Message-ID':"<CH3PR12MB872512DFFBC8EA1A50DB5A85EDAAA@CH3PR12MB8725.namprd12.prod.outlook.com>", "To" : "Victor Renfield <victor.renfield@csiventuresoutlook.onmicrosoft.com>", "From" : "Colonel Mustard <cmustard@csiventuresoutlook.onmicrosoft.com>", "BCC" : "linda.pei@nuix.com"}
sample_mapping2 = {'Message-ID':"<CH3PR12MB872512DFFBC8EA1A50DB5A85EDAAA@CH3PR12MB8725.namprd12.prod.outlook.com>", "To" : "Victor Renfield <victor.renfield@csiventuresoutlook.onmicrosoft.com>", "From" : "Colonel Mustard <cmustard@csiventuresoutlook.onmicrosoft.com>", "BCC" : "bccTest@mapping.com"}

map_id = builder.add_mapping(sample_mapping, "message/rfc822")
map_id = builder.add_mapping(sample_mapping2, "message/rfc822")
builder.save()