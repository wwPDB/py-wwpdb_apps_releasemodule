##
# File: CitationTests.py
# Date:  28-June-2021  E. Peisach
#
# Updates:
##
"""Test cases for release module"""

__docformat__ = "restructuredtext en"
__author__ = "Ezra Peisach"
__email__ = "peisach@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.01"

import os
import unittest
import sys


if __package__ is None or __package__ == "":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from commonsetup import HERE, TESTOUTPUT  # noqa:  F401 pylint: disable=import-error,unused-import
else:
    from .commonsetup import HERE, TESTOUTPUT  # noqa: F401 pylint: disable=relative-beyond-top-level

from wwpdb.apps.releasemodule.citation.SearchMP import SearchMP
from wwpdb.apps.releasemodule.citation.FetchMP import FetchMP


class CitationTests(unittest.TestCase):
    def setUp(self):
        self.__siteId = 'WWPDB_DEPLOY_TEST'

    def testSearch(self):
        """Test search for an author"""
        authorList = ['Peisach+E[au]', 'Doudna+JA[au]']

        # Spawn fork method MacOS cannot pickle an open stream (stderr), do not pass log
        aSearch = SearchMP(siteId=self.__siteId, termList=authorList, path=TESTOUTPUT, log=None)
        aSearch.run()
        termMap = aSearch.getTermMap()
        # This could fail if Ezra Peisach does not publish anything in several years
        self.assertNotEqual(termMap, {}, "Search test returned no entries")

    def testFetch(self):
        """Test fetch author"""
        idList = ['30357411', '96883512', '29174494', '28190782']
        pFetch = FetchMP(siteId=self.__siteId, idList=idList, path=TESTOUTPUT, verbose=True)
        pFetch.run()
        pubmedInfo = pFetch.getPubmedInfoMap()
        self.assertNotEqual(pubmedInfo, {}, "Failed to fetch info from NCBI")


if __name__ == '__main__':
    unittest.main()
