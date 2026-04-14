import csv
import mimetypes
from operator import indexOf
from pathlib import Path

from nuix_nli_lib.data_types import CSVEntry, configs as dt_configs
from nuix_nli_lib.nli import NLIGenerator
from nuix_nli_lib import configs as nli_configs

nli_configs['debug'] = debug_mode
source_data = Path(evidence_path)

entry = CSVEntry(str(source_data), mimetype=TelepathyEntry.FILE_MIME_TYPE, row_generator=TelepathyEntry, delimiter=';')
generator = NLIGenerator()
generator.add_entry(entry)
source_data_dir = source_data.parent
media_dir = source_data_dir / 'media'

with source_data.open(mode='r', encoding=dt_configs['encoding']) as chat_file:
    chat_reader = csv.reader(chat_file, delimiter=';')
    field_names = next(chat_reader)
    message_id_field = indexOf(field_names, 'Message ID')
    has_media_field = indexOf(field_names, 'Has_media')
    media_path_field = indexOf(field_names, 'Media save directory')
    for msg in chat_reader:
        msg_id = msg[message_id_field]
        has_media = msg[has_media_field].lower() == 'true'
        media_path = msg[media_path_field]
        if has_media:
            media_file = Path(media_path).name
            media_full_path = media_dir / media_file
            guessed_mimetype = mimetypes.guess_type(str(media_full_path))[0]
            try:
                generator.add_file(str(media_full_path), guessed_mimetype, msg_id)
            except Exception as e:
                error_dict = {'message_id': msg_id,
                              'media_path': media_path,
                              'guessed_mimetype': guessed_mimetype,
                              'error_message': "Unable to store attachment to message"
                                               f"{': Source path is empty' if len(media_path) == 0 else ''}",
                              'error_code': str(e)
                              }
                generator.add_mapping(error_dict, 'application/x-nli-error', msg_id)

generator.save(Path(output_file_path))
