##
# File: ImportTests.py
# Date:  06-Oct-2018  E. Peisach
#
# Updates:
##
"""Test cases for release module"""

__docformat__ = "restructuredtext en"
__author__ = "Ezra Peisach"
__email__ = "peisach@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.01"

import platform
import os
import unittest

#####################  setup DepUi test environment here from emdb translator############
HERE = os.path.abspath(os.path.dirname(__file__))
TOPDIR = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TESTOUTPUT = os.path.join(HERE, 'test-output', platform.python_version())
if not os.path.exists(TESTOUTPUT):
    os.makedirs(TESTOUTPUT)
mockTopPath = os.path.join(TOPDIR, 'wwpdb', 'mock-data')
rwMockTopPath = os.path.join(TESTOUTPUT)

# Must create config file before importing ConfigInfo
from wwpdb.utils.testing.SiteConfigSetup import SiteConfigSetup
from wwpdb.utils.testing.CreateRWTree import CreateRWTree
# Copy site-config and selected items
crw = CreateRWTree(mockTopPath, TESTOUTPUT)
crw.createtree(['site-config', 'depuiresources', 'emdresources'])
# Use populate r/w site-config using top mock site-config
SiteConfigSetup().setupEnvironment(rwMockTopPath, rwMockTopPath)

# Setup DepUI specific directories
from wwpdb.utils.config.ConfigInfo import ConfigInfo
import os.path
cI = ConfigInfo()
FILE_UPLOAD_TEMP_DIR = os.path.join(
    cI.get("SITE_DEPOSIT_STORAGE_PATH"),
    "deposit",
    "temp_files")
if not os.path.exists(FILE_UPLOAD_TEMP_DIR):
    os.makedirs(FILE_UPLOAD_TEMP_DIR)

# Django envivonment setup
#os.environ['DJANGO_SETTINGS_MODULE'] = "wwpdb.apps.deposit.settings"
os.environ['IN_ANNOTATION'] = "no"
################################################
from wwpdb.apps.releasemodule.webapp.ReleaseWebApp_v2 import ReleaseWebApp
from wwpdb.apps.releasemodule.citation.CitationFinder import CitationFinder
from wwpdb.apps.releasemodule.citation.SearchMP import SearchMP
from wwpdb.apps.releasemodule.citation.FetchMP import FetchMP
from wwpdb.apps.releasemodule.citation.MonitorCitationUpdate import MonitorCitationUpdate


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.__siteId = 'WWPDB_DEPLOY_TEST'
        pass

    def testInstantiate(self):
        """Tests simple instantiation"""
        c = CitationFinder()
        #d = ReleaseWebApp(reqObj)

    def testSearch(self):
        """Test search for an author"""
        authorList = ['Peisach+E[au]', 'Doudna+JA[au]']
        aSearch = SearchMP(siteId=self.__siteId, termList=authorList, path=TESTOUTPUT)
        aSearch.run()
        termMap = aSearch.getTermMap()
        # This could fail if Ezra Peisach does not publish anything in several years
        self.assertNotEqual(termMap, {}, "Search test returned no entries")

    def testFetch(self):
        """Test fetch author"""
        idList=['30357411', '96883512', '29174494', '28190782']
        pFetch = FetchMP(siteId=self.__siteId, idList=idList, path=TESTOUTPUT)
        pFetch.run()
        pubmedInfo = pFetch.getPubmedInfoMap()
        self.assertNotEqual(pubmedInfo, {}, "Failed to fetch info from NCBI")

if __name__ == '__main__':
    unittest.main()