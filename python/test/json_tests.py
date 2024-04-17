from pathlib import Path
import unittest

from nuix_nli_lib.data_types import JSONFileEntry
from nuix_nli_lib.nli.nli_generator import NLIGenerator


class NLITests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.simple_str: Path = Path("./resources/simple_str.json")
        self.simple_int: Path = Path("./resources/simple_int.json")
        self.simple_float: Path = Path("./resources/simple_float.json")
        self.simple_boolean: Path = Path("./resources/simple_boolean.json")
        self.list_mixed: Path = Path("./resources/list_mixed.json")
        self.object_mixed: Path = Path("./resources/object_mixed.json")
        self.object_complex: Path = Path("./resources/object_complex.json")

        self.output_path: Path = Path(r'C:\projects\proserv\nli\json')
        self.output_path.mkdir(parents=True, exist_ok=True)

    def test_simple_str(self):
        entry = JSONFileEntry(str(self.simple_str))
        nli = NLIGenerator()
        nli.add_entry(entry)
        nli.save(self.output_path / "simple_str.nli")

    def test_simple_int(self):
        entry = JSONFileEntry(str(self.simple_int))
        nli = NLIGenerator()
        nli.add_entry(entry)
        nli.save(self.output_path / "simple_int.nli")

    def test_simple_float(self):
        entry = JSONFileEntry(str(self.simple_float))
        nli = NLIGenerator()
        nli.add_entry(entry)
        nli.save(self.output_path / "simple_float.nli")

    def test_simple_bool(self):
        entry = JSONFileEntry(str(self.simple_boolean))
        nli = NLIGenerator()
        nli.add_entry(entry)
        nli.save(self.output_path / "simple_bool.nli")

    def test_object_complex(self):
        entry = JSONFileEntry(str(self.object_complex))
        nli = NLIGenerator()
        nli.add_entry(entry)
        nli.save(self.output_path / "object_complex.nli")
