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
__author__ = "Zukang Feng"
__email__ = "zfeng@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.07"

import os
import sys
#
from wwpdb.utils.config.ConfigInfo import ConfigInfo
from wwpdb.io.file.mmCIFUtil import mmCIFUtil


class JournalAbbrev(object):
    """
    """
    def __init__(self, reqObj=None, ciffile=None, verbose=False, log=sys.stderr):  # pylint: disable=unused-argument
        """
        """
        self.__reqObj = reqObj
        self.__ciffile = ciffile
        # self.__lfh = log
        # self.__verbose = verbose
        self.__jalist = []
        self.__jamaps = {}
        self.__issnmaps = {}
        self.__getCIFile()
        self.__getJAList()

    def __getCIFile(self):
        if not self.__reqObj:
            return
        #
        self.__siteId = str(self.__reqObj.getValue("WWPDB_SITE_ID"))
        self.__cI = ConfigInfo(self.__siteId)
        self.__ciffile = os.path.join(self.__cI.get('SITE_ANNOT_TOOLS_PATH'), 'data', 'ascii', 'ndb_refn.cif')

    def __getJAList(self):
        Map = {}
        cifObj = mmCIFUtil(filePath=self.__ciffile)
        nlist = cifObj.GetValue('ndb_refn')
        for Dir in nlist:
            if 'issn' not in Dir:
                if Dir['publication'] != 'TO BE PUBLISHED':
                    continue
                #
            #
            if Dir['issn'] != 'ISSN' and Dir['issn'] != 'ESSN':
                continue
            #
            cs = Dir['publication'].strip()
            if cs.find('\n') != -1 or cs[0:6] == 'THESIS':
                continue
            #
            if cs in Map:
                if ('issn_code' in Dir) and Dir['issn_code'].strip():
                    self.__issnmaps[Dir['issn_code'].strip()] = Map[cs]
                #
                continue
            #
            pcs = self.__processJournalAbbrev(cs)
            Map[cs] = pcs
            self.__jalist.append(pcs)
            cs1 = self.__standardJournalAbbrev(pcs)
            self.__jamaps[cs1] = pcs
            if ('issn_code' in Dir) and Dir['issn_code'].strip():
                self.__issnmaps[Dir['issn_code'].strip()] = pcs
            #
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

    def __standardJournalAbbrev(self, abbrev):
        inlist = abbrev.lower().strip().replace('\n', ' ').replace('.', ' ').replace(',', ' ').split(' ')
        outlist = []
        for val in inlist:
            if not val:
                continue
            #
            outlist.append(val)
        #
        return ' '.join(outlist)

    def GetList(self):
        return self.__jalist

    def GetQuoterList(self):
        rlist = []
        for abbrev in self.__jalist:
            rlist.append('"' + abbrev + '"')
        #
        return rlist

    def GetJoinList(self, delimiter):
        return delimiter.join(self.__jalist)

    def GetJoinQuoterList(self, delimiter):
        return delimiter.join(self.GetQuoterList())

    def FindJournalAbbrev(self, abbrev):
        std_abbrev = self.__standardJournalAbbrev(abbrev)
        if std_abbrev in self.__jamaps:
            return self.__jamaps[std_abbrev]
        #
        return ''

    def FindJournalAbbrevWithISSN(self, issn):
        if issn.strip() in self.__issnmaps:
            return self.__issnmaps[issn.strip()]
        #
        return ''


if __name__ == '__main__':
    jc = JournalAbbrev(ciffile='/net/wwpdb_da/da_top/tools-centos-6/packages/annotation/data/ascii/ndb_refn.cif', verbose=True, log=sys.stderr)
    print((jc.GetJoinQuoterList(',\n')))
