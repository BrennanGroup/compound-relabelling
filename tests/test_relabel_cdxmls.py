import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import relabel_cdxmls as relabel


class RelabelTests(unittest.TestCase):
    def write_map(self, root: Path, text: str) -> Path:
        path = root / "map.csv"
        path.write_text(text)
        return path

    def test_valid_map_is_trimmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_map(
                Path(tmp),
                "RELABEL=TRUE,,toggle\ncompound,label,notes\nLL03-05 , 133 ,example\n",
            )
            table, enabled = relabel.create_relabel_dict(path)
            self.assertTrue(enabled)
            self.assertEqual(table, {"LL03-05": "133"})

    def test_relabel_false_outputs_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_map(
                Path(tmp),
                "RELABEL=FALSE,,toggle\ncompound,label,notes\nLL03-05,133,example\n",
            )
            table, enabled = relabel.create_relabel_dict(path)
            self.assertFalse(enabled)
            self.assertEqual(table, {"LL03-05": "LL03-05"})

    def test_duplicate_compound_id_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_map(
                Path(tmp),
                "RELABEL=TRUE\ncompound,label\nA-1,1\nA-1,2\n",
            )
            with self.assertRaisesRegex(ValueError, "Duplicate compound ID"):
                relabel.create_relabel_dict(path)

    def test_duplicate_label_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_map(
                Path(tmp),
                "RELABEL=TRUE\ncompound,label\nA-1,1\nA-2,1\n",
            )
            with self.assertRaisesRegex(ValueError, "Duplicate label"):
                relabel.create_relabel_dict(path)

    def test_invalid_toggle_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_map(Path(tmp), "RELABEL=MAYBE\ncompound,label\nA-1,1\n")
            with self.assertRaisesRegex(ValueError, "RELABEL=TRUE or RELABEL=FALSE"):
                relabel.create_relabel_dict(path)

    def test_unknown_cdxml_id_fails_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scheme.cdxml"
            original = "before CMPD:UNKNOWN after"
            path.write_text(original)
            with self.assertRaisesRegex(ValueError, "Unmapped compound"):
                relabel.modify_cdxml(path, {"A-1": "1"})
            self.assertEqual(path.read_text(), original)

    def test_known_cdxml_id_is_relabelled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scheme.cdxml"
            path.write_text("before CMPD:A-1 after")
            count = relabel.modify_cdxml(path, {"A-1": "42"})
            self.assertEqual(count, 1)
            self.assertEqual(path.read_text(), "before 42 after")

    def test_latex_map_has_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            relabel.write_latex_map_csv({"A-1": "42"}, path)
            with path.open(newline="") as f:
                self.assertEqual(list(csv.reader(f)), [["compound", "label"], ["A-1", "42"]])


if __name__ == "__main__":
    unittest.main()
