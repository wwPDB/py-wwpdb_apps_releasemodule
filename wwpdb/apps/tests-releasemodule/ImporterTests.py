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

import os
import unittest
import sys


if __package__ is None or __package__ == "":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from commonsetup import HERE  # noqa:  F401 pylint: disable=import-error,unused-import
else:
    from .commonsetup import HERE  # noqa: F401 pylint: disable=relative-beyond-top-level

from wwpdb.utils.session.WebRequest import InputRequest
from wwpdb.utils.config.ConfigInfo import ConfigInfo
from wwpdb.apps.releasemodule.webapp.ReleaseWebApp_v2 import ReleaseWebApp
from wwpdb.apps.releasemodule.citation.CitationFinder import CitationFinder
from wwpdb.apps.releasemodule.citation.SearchMP import SearchMP
from wwpdb.apps.releasemodule.citation.FetchMP import FetchMP
from wwpdb.apps.releasemodule.citation.MonitorCitationUpdate import MonitorCitationUpdate  # noqa: F401  pylint: disable=unused-import


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.__lfh = sys.stderr
        self.__verbose = True
        self.__siteId = 'WWPDB_DEPLOY_TEST'
        self.__cI = ConfigInfo(self.__siteId)
        self.__topPath = self.__cI.get("SITE_WEB_APPS_TOP_PATH")
        self.__topSessionPath = self.__cI.get("SITE_WEB_APPS_TOP_SESSIONS_PATH")
        self.__reqObj = InputRequest(paramDict={}, verbose=self.__verbose, log=self.__lfh)
        self.__reqObj.setValue("WWPDB_SITE_ID", self.__siteId)
        self.__reqObj.setValue("TopSessionPath", self.__topSessionPath)
        self.__reqObj.setValue("TopPath", self.__topPath)
        self.__reqObj.setDefaultReturnFormat(return_format="html")

    def testInstantiate(self):
        """Tests simple instantiation"""
        _c = CitationFinder()  # noqa: F841
        _d = ReleaseWebApp(self.__reqObj)  # noqa: F841
        _smp = SearchMP()  # noqa: F841
        _fmp = FetchMP()  # noqa: F841


if __name__ == '__main__':
    unittest.main()
