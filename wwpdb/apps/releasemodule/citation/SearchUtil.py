##
# File:  SearchUtil.py
# Date:  24-Jul-2013
# Updates:
##
"""
Run NCBI pubmed author search utility.

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2013 wwPDB

This software is provided under a Creative Commons Attribution 3.0 Unported
License described at http://creativecommons.org/licenses/by/3.0/.

"""
__docformat__ = "restructuredtext en"
__author__ = "Zukang Feng"
__email__ = "zfeng@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.07"

import os
import sys

from wwpdb.utils.config.ConfigInfo import ConfigInfo

from wwpdb.apps.releasemodule.citation.SearchResultParser import SearchResultParser
# from wwpdb.apps.releasemodule.utils.Utility import *
from wwpdb.apps.releasemodule.utils.Utility import getFileName, RunScript


class SearchUtil(object):
    """
    """

    def __init__(self, path='.', processLabel='', term=None, siteId=None, log=sys.stderr, verbose=False):  # pylint: disable=unused-argument
        """
        """
        self.__sessionPath = path
        self.__processLabel = processLabel
        self.__term = term
        # self.__lfh = log
        # self.__verbose = verbose
        self.__pubmedIdList = []
        self.__cI = ConfigInfo(siteId)
        self.__apikey = self.__cI.get('NCBI_API_KEY')

    def doSearch(self, year=2):
        """ Create NCBI webservice URL and run pubmed author search webservice
        """
        # NCBI esearch URL
        if self.__apikey:
            api = "&api_key=" + self.__apikey
        else:
            api = ""
        #
        query = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + "db=pubmed&term=" + self.__term
        if self.__term.endswith("[aid]"):
            query += "&retmode=xml" + api
        else:
            query += "&reldate=%d&retmax=10000&retmode=xml" % (year * 365) + api
        #
        if self.__processLabel:
            scriptfile = 'search_' + self.__processLabel + '.csh'
            xmlfile = 'search_' + self.__processLabel + '.xml'
            logfile = 'search_command_' + self.__processLabel + '.log'
        else:
            scriptfile = getFileName(self.__sessionPath, 'search', 'csh')
            xmlfile = getFileName(self.__sessionPath, 'search', 'xml')
            logfile = getFileName(self.__sessionPath, 'search_command', 'log')
        #
        script = os.path.join(self.__sessionPath, scriptfile)
        f = open(script, 'w')
        f.write('#!/bin/tcsh -f\n')
        f.write('#\n')
        f.write('/usr/bin/curl -g "' + query + '" > ' + xmlfile + '\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, logfile)
        #
        filename = os.path.join(self.__sessionPath, xmlfile)
        if not os.access(filename, os.F_OK):
            return
        #
        parser = SearchResultParser(xmlfile=filename)
        self.__pubmedIdList = parser.getIdList()

    def getPubmedIdList(self):
        return self.__pubmedIdList


if __name__ == '__main__':
    cf = SearchUtil(term='Badger+J[au]', log=sys.stderr, verbose=False)
    cf.doSearch()
    plist = cf.getPubmedIdList()
    print(plist)
