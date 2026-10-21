"""Unit tests for Citation Finder publication grouping."""

import unittest

from wwpdb.apps.releasemodule.depict.PublicationGroups import group_entries_by_publication, is_preprint, status_needs_alert


def _entry(structure_id, doi, score, pubmed_id="1", status="REL", pdb_id="", emdb_id="", journal="", title=""):
    entry = {
        "structure_id": structure_id,
        "comb_status_code": status,
        "pubmed": [
            {
                "pdbx_database_id_DOI": doi,
                "pdbx_database_id_PubMed": pubmed_id,
                "similarity_score": score,
                "journal_abbrev": journal,
                "title": title or "Title " + structure_id,
            }
        ],
    }
    if pdb_id:
        entry["pdb_id"] = pdb_id
    if emdb_id:
        entry["emdb_id"] = emdb_id
    return entry


class PublicationGroupTests(unittest.TestCase):
    def testSameDoiGroupsInScoreOrder(self):
        low = _entry("D_2", "10.1000/ABC", "0.600", "22", status="HOLD", pdb_id="2ABC")
        high = _entry("D_1", "10.1000/abc", "0.950", "11", status="REL/PROC", pdb_id="1ABC")
        groups = group_entries_by_publication([low, high])
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group["entry_ids"], ["D_1", "D_2"])
        self.assertEqual(group["doi"], "10.1000/abc")
        self.assertEqual(group["statuses"], ["REL/PROC", "HOLD"])
        self.assertEqual(group["scores"], ["0.950", "0.600"])
        self.assertEqual(group["pdb_ids"], ["1ABC", "2ABC"])
        self.assertEqual(group["pubmed_ids"], ["11", "22"])

    def testSecondHitDoesNotCreateAGroup(self):
        entry = _entry("D_9", "10.1000/first", "0.800", "9")
        entry["pubmed"].append({"pdbx_database_id_DOI": "10.1000/second", "pdbx_database_id_PubMed": "99", "similarity_score": "0.990"})
        other = _entry("D_8", "10.1000/second", "0.700", "8")
        groups = group_entries_by_publication([entry, other])
        by_doi = {group["doi"]: group["entry_ids"] for group in groups}
        self.assertEqual(by_doi["10.1000/first"], ["D_9"])
        self.assertEqual(by_doi["10.1000/second"], ["D_8"])

    def testMissingDoiStaysSeparate(self):
        first = _entry("D_A", "", "0.800", "111")
        second = _entry("D_B", "", "0.700", "111")
        groups = group_entries_by_publication([first, second])
        self.assertEqual(len(groups), 2)
        self.assertEqual(sorted(group["entry_ids"][0] for group in groups), ["D_A", "D_B"])

    def testOmitsEmptyAccessionRows(self):
        plain = group_entries_by_publication([_entry("D_1", "10.9/x", "0.900", "1")])[0]
        self.assertEqual(plain["pdb_ids"], [])
        self.assertEqual(plain["emdb_ids"], [])
        emdb = group_entries_by_publication([_entry("D_2", "10.9/y", "0.900", "2", emdb_id="EMD-1234")])[0]
        self.assertEqual(emdb["pdb_ids"], [])
        self.assertEqual(emdb["emdb_ids"], ["EMD-1234"])

    def testExtendedPdbIdWins(self):
        entry = _entry("D_1", "10.9/x", "0.900", "1", pdb_id="1abc")
        entry["ext_pdb_id"] = "1XYZ"
        group = group_entries_by_publication([entry])[0]
        self.assertEqual(group["pdb_ids"], ["1XYZ"])

    def testBoxesFollowBestScore(self):
        low = _entry("D_A", "10.1/a", "0.600", "1")
        high = _entry("D_B", "10.1/b", "0.990", "2")
        groups = group_entries_by_publication([low, high])
        self.assertEqual([group["doi"] for group in groups], ["10.1/b", "10.1/a"])

    def testEqualScoresSortByEntryId(self):
        later = _entry("D_B", "10.1/a", "0.800", "1")
        earlier = _entry("D_A", "10.1/a", "0.800", "2")
        group = group_entries_by_publication([later, earlier])[0]
        self.assertEqual(group["entry_ids"], ["D_A", "D_B"])

    def testStatusAlert(self):
        for status in ("PROC", "REPL", "REL/PROC", "PROC/HOLD", "repl"):
            self.assertTrue(status_needs_alert(status), status)
        for status in ("REL", "HOLD", "HPUB", "AUTH", "WAIT", "", "None"):
            self.assertFalse(status_needs_alert(status), status)

    def testPreprintDetection(self):
        self.assertTrue(is_preprint("bioRxiv", "10.1101/2024.01.01"))
        self.assertTrue(is_preprint("Nucleic Acids Res.", "10.1101/2024.01.01"))
        self.assertTrue(is_preprint("", "10.64898/2026.06.04.730248"))
        self.assertTrue(is_preprint("", "10.26434/chemrxiv-123"))
        self.assertTrue(is_preprint("Research Square", ""))
        self.assertTrue(is_preprint("medRxiv", ""))
        self.assertFalse(is_preprint("Nucleic Acids Res.", "10.1093/nar/gkaf169"))
        preprint = group_entries_by_publication([_entry("D_1", "10.1101/2024.01.01", "0.8", "1", journal="bioRxiv")])[0]
        journal = group_entries_by_publication([_entry("D_2", "10.1093/nar/gkaf169", "0.8", "2", journal="Nucleic Acids Res.")])[0]
        self.assertTrue(preprint["preprint"])
        self.assertFalse(journal["preprint"])


if __name__ == "__main__":
    unittest.main()
