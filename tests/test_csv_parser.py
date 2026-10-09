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
    header = "machine_type,machine,cots,version\n"

    def test_minimal(self):
        row = parser.parse_csv(self.header + "device,PC-001,Notepad++,8.8\n")[0]
        self.assertEqual((row.machine_type, row.machine, row.version), ("device", "PC-001", "8.8"))

    def test_utf8_bom_semicolon_and_whitespace(self):
        row = parser.parse_csv("\ufeffmachine_type;machine;cots;version\nvirtual_machine; VM-1 ; Café ; 1.0 \n")[0]
        self.assertEqual((row.machine, row.cots), ("VM-1", "Café"))

    def test_quoted_commas(self):
        row = parser.parse_csv(self.header + 'device,PC-1,"Produit, entreprise",1\n')[0]
        self.assertEqual(row.cots, "Produit, entreprise")

    def test_id_without_name(self):
        row = parser.parse_csv("machine_type,machine_id,cots,version\ndevice,123,Java,17\n")[0]
        self.assertEqual(row.machine_id, 123)

    def test_versions_are_strings(self):
        row = parser.parse_csv(self.header + "device,PC-1,App,01.02\n")[0]
        self.assertEqual(row.version, "01.02")

    def test_reject_invalid_inputs(self):
        invalid = [
            "", self.header, "machine_type,machine,cots\ndevice,PC-1,Java\n",
            "machine_type,machine,cots,version,extra\ndevice,PC-1,Java,17,x\n",
            "machine_type,machine,machine,cots,version\ndevice,PC-1,PC-1,Java,17\n",
            self.header + "server,PC-1,Java,17\n",
            self.header + "device,,Java,17\n",
            self.header + "device,PC-1,,17\n",
            self.header + "device,PC-1,Java,\n",
            self.header + "device,PC-1,Java\n",
            self.header + "device,PC-1,Java,17,extra\n",
            self.header + 'device,PC-1,"Java,17\n',
            self.header + "device,PC-1,Ja\x00va,17\n",
            "machine_type,machine_id,cots,version\ndevice,-1,Java,17\n",
            "machine_type,machine_id,cots,version\ndevice,0,Java,17\n",
            "machine_type,machine_id,cots,version\ndevice,abc,Java,17\n",
            "machine_type,cots,version\ndevice,Java,17\n",
            self.header + "device,PC-1,Java," + "x" * 101 + "\n",
            "machine_type,machine,cots,version,cots_slug\ndevice,PC-1,Java,17,not valid\n",
        ]
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(parser.ImportFailure):
                    parser.parse_csv(value)

    def test_limit(self):
        with self.assertRaises(parser.ImportFailure):
            parser.parse_csv(self.header + "device,PC-1,Java,17\ndevice,PC-2,Java,17\n", max_rows=1)


if __name__ == "__main__":
    unittest.main()
