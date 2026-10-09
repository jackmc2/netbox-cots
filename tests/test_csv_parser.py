import importlib.util
from pathlib import Path
import sys
import unittest

path = Path(__file__).parents[1] / "netbox_cots" / "csv_parser.py"
spec = importlib.util.spec_from_file_location("cots_csv_parser_standalone", path)
parser = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = parser
spec.loader.exec_module(parser)


class CSVParserTests(unittest.TestCase):
    header = "role,cots,version\n"

    def test_minimal(self):
        row = parser.parse_csv(self.header + "poste,Notepad++,8.8\n")[0]
        self.assertEqual((row.role, row.cots, row.version), ("poste", "Notepad++", "8.8"))

    def test_utf8_and_semicolon(self):
        row = parser.parse_csv("\ufeffrole;cots;version\n poste ; Café ; 1.0 \n")[0]
        self.assertEqual((row.role, row.cots), ("poste", "Café"))

    def test_quoted_commas(self):
        row = parser.parse_csv(self.header + 'poste,"Produit, entreprise",1\n')[0]
        self.assertEqual(row.cots, "Produit, entreprise")

    def test_role_id(self):
        row = parser.parse_csv("role_id,cots,version\n123,Java,17\n")[0]
        self.assertEqual(row.role_id, 123)

    def test_versions_are_strings(self):
        self.assertEqual(parser.parse_csv(self.header + "poste,App,01.02\n")[0].version, "01.02")

    def test_reject_invalid_inputs(self):
        invalid = ["", self.header, "role,cots\nposte,Java\n", "role,cots,version,extra\nposte,Java,17,x\n", "role,role,cots,version\nposte,poste,Java,17\n", self.header + ",Java,17\n", self.header + "poste,,17\n", self.header + "poste,Java,\n", self.header + "poste,Java\n", self.header + "poste,Java,17,extra\n", self.header + 'poste,"Java,17\n', self.header + "poste,Ja\x00va,17\n", "role_id,cots,version\n-1,Java,17\n", "role_id,cots,version\n0,Java,17\n", "role_id,cots,version\nabc,Java,17\n", "cots,version\nJava,17\n", self.header + "poste,Java," + "x" * 101 + "\n", "role,cots,version,cots_slug\nposte,Java,17,not valid\n", "machine_type,machine,cots,version\ndevice,PC-1,Java,17\n"]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(parser.ImportFailure):
                parser.parse_csv(value)

    def test_limit(self):
        with self.assertRaises(parser.ImportFailure):
            parser.parse_csv(self.header + "poste,Java,17\nserveur,Java,17\n", max_rows=1)

    def test_tags(self):
        row = parser.parse_csv("role,cots,version,tags\nposte,Java,17,Production | Windows | Production\n")[0]
        self.assertEqual(row.tags, ("Production", "Windows"))
        self.assertEqual(parser.parse_csv(self.header + "poste,Java,17\n")[0].tags, ())

    def test_invalid_tags(self):
        for tags in ("A||B", "|A", "A|", "x" * 101, "|".join(str(i) for i in range(51))):
            with self.subTest(tags=tags), self.assertRaises(parser.ImportFailure):
                parser.parse_csv("role,cots,version,tags\nposte,Java,17," + tags + "\n")
