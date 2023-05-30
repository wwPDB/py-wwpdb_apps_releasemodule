##
# File:  FetchUtil.py
# Date:  10-Jul-2013
# Updates:
##
"""
Run NCBI pubmed fetch utility.

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
from wwpdb.apps.releasemodule.citation.FetchResultParser import FetchResultParser
from wwpdb.apps.releasemodule.utils.Utility import getFileName, RunScript


class FetchUtil(object):
    """
    """
    def __init__(self, path='.', processLabel='', idList=None, siteId=None, mpl=None, log=sys.stderr, verbose=False):  # pylint: disable=unused-argument
        """
        """
        self.__sessionPath = path
        self.__processLabel = processLabel
        self.__pubmedIdList = idList
        # self.__lfh = log
        # self.__verbose = verbose
        self.__pubmedInfoList = []
        # self.__pubmedInfoMap = {}
        self.__cI = ConfigInfo(siteId)
        self.__apikey = self.__cI.get('NCBI_API_KEY')
        self.__mpl = mpl

    def doFetch(self):
        """ Run NCBI Pubmed fetch
        """
        if not self.__pubmedIdList:
            return
        #
        uniq_list = sorted(set(self.__pubmedIdList))
        self.__pubmedIdList = uniq_list
        #
        length = len(self.__pubmedIdList)
        beg = 0
        num = 200
        while True:
            if beg >= length:
                break
            #
            end = beg + num
            if end > length:
                end = length
            ids = ','.join(self.__pubmedIdList[beg:end])
            self._runNCBIFetchCommand(ids)
            beg += num
        #

    def getPubmedInfoList(self):
        return self.__pubmedInfoList

    def getPubmedInfoMap(self):
        # return self.__pubmedInfoMap
        pubmedInfoMap = {}
        if self.__pubmedInfoList:
            for info in self.__pubmedInfoList:
                pubmedInfoMap[info['pdbx_database_id_PubMed']] = info
            #
        #
        return pubmedInfoMap

    def _runNCBIFetchCommand(self, ids):
        """ Create NCBI webservice URL and run webservice
        """
        if self.__apikey:
            api = "&api_key=" + self.__apikey
        else:
            api = ""
        # NCBI fetch URL
        query = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=" \
            + ids + "&retmode=xml&rettype=abstract" + api
        #
        if self.__processLabel:
            scriptfile = 'fetch_' + self.__processLabel + '.csh'
            xmlfile = 'fetch_' + self.__processLabel + '.xml'
            logfile = 'fetch_command_' + self.__processLabel + '.log'
        else:
            scriptfile = getFileName(self.__sessionPath, 'fetch', 'csh')
            xmlfile = getFileName(self.__sessionPath, 'fetch', 'xml')
            logfile = getFileName(self.__sessionPath, 'fetch_command', 'log')
        #
        script = os.path.join(self.__sessionPath, scriptfile)
        f = open(script, 'w')
        f.write('#!/bin/tcsh -f\n')
        f.write('#\n')
        f.write('/usr/bin/curl -g "' + query + '" > ' + xmlfile + '\n')
        f.close()
        # Speed limit requests
        if self.__mpl:
            self.__mpl.waitnext()
        RunScript(self.__sessionPath, scriptfile, logfile)
        self._readFetchResultXml(xmlfile)

    def _readFetchResultXml(self, xmlfile):
        """ Read pubmed fetch result xml file
        """
        filename = os.path.join(self.__sessionPath, xmlfile)
        if not os.access(filename, os.F_OK):
            return
        #
        parser = FetchResultParser(xmlfile=filename)
        pubmedInfo = parser.getPubmedInfoList()
        if not pubmedInfo:
            return
        #
        self.__pubmedInfoList.extend(pubmedInfo)
        #
        # for info in pubmedInfo:
        #    self.__pubmedInfoMap[info['pdbx_database_id_PubMed']] = info
        #


if __name__ == '__main__':
    cf = FetchUtil(idList=['23542341', '23326635'], log=sys.stderr, verbose=False)
    cf.doFetch()
    clist = cf.getPubmedInfoList()
    print(clist)
    cdir = cf.getPubmedInfoMap()
    print(cdir)
