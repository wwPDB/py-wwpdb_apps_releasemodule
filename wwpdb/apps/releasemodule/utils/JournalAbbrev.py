##
# File:  JournalAbbrev.py
# Date:  30-Jun-2014
# Updates:
##
"""
Read Journal Abbrev. information from  ndb_refn.cif

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2014 wwPDB

This software is provided under a Creative Commons Attribution 3.0 Unported
License described at http://creativecommons.org/licenses/by/3.0/.

"""
__docformat__ = "restructuredtext en"
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import os,sys
#
from wwpdb.utils.config.ConfigInfo                 import ConfigInfo
from wwpdb.apps.entity_transform.utils.mmCIFUtil import mmCIFUtil

class JournalAbbrev(object):
    """
    """
    def __init__(self, reqObj=None, ciffile=None, verbose=False, log=sys.stderr):
        """
        """
        self.__reqObj    = reqObj
        self.__ciffile   = ciffile
        self.__lfh       = log
        self.__verbose   = verbose
        self.__jalist = []
        self.__getCIFile()
        self.__getJAList()

    def __getCIFile(self):
        if not self.__reqObj:
            return
        #
        self.__siteId  = str(self.__reqObj.getValue("WWPDB_SITE_ID"))
        self.__cI=ConfigInfo(self.__siteId)
        self.__ciffile = os.path.join(self.__cI.get('SITE_ANNOT_TOOLS_PATH'), 'data', 'ascii', 'ndb_refn.cif')

    def __getJAList(self):
        map = {}
        cifObj = mmCIFUtil(filePath=self.__ciffile)
        list = cifObj.GetValue('ndb_refn')
        for dir in list:
            if not 'issn' in dir:
                if dir['publication'] != 'TO BE PUBLISHED':
                    continue
                #
            #
            if dir['issn'] != 'ISSN' and dir['issn'] != 'ESSN':
                continue
            #
            cs = dir['publication'].strip()
            if cs.find('\n') != -1 or cs[0:6] == 'THESIS':
                continue
            #
            if cs in map:
                continue
            #
            map[cs] = 'yes'
            cs  = self.__processJournalAbbrev(cs)
            self.__jalist.append(cs)
        #
        self.__jalist.sort()

    def __processJournalAbbrev(self, abbrev):
        cs = abbrev.lower()
        newabbrev = ''
        upper_flag = True
        for c in cs:
            if upper_flag:
                newabbrev += c.upper()
            else:
                newabbrev += c
            #
            if c < 'a' or c > 'z':
                upper_flag = True
            else:
                upper_flag = False
            #
        #
        return newabbrev

    def GetList(self):
        return self.__jalist

    def GetQuoterList(self):
        list = []
        for abbrev in self.__jalist:
            list.append('"' + abbrev + '"')
        #
        return list

    def GetJoinList(self, delimiter):
        return delimiter.join(self.__jalist)

    def GetJoinQuoterList(self, delimiter):
        return delimiter.join(self.GetQuoterList())

if __name__ == '__main__':
    c=JournalAbbrev(ciffile='/net/wwpdb_da/da_top/tools-centos-6/packages/annotation/data/ascii/ndb_refn.cif', verbose=True, log=sys.stderr)
    print c.GetJoinQuoterList(',\n')
