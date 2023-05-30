##
# File:  Analysis.py
# Date:  24-Jul-2013
# Updates:
##
"""
Citation finder.

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2012 wwPDB

This software is provided under a Creative Commons Attribution 3.0 Unported
License described at http://creativecommons.org/licenses/by/3.0/.

"""
__docformat__ = "restructuredtext en"
__author__ = "Zukang Feng"
__email__ = "zfeng@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.07"

import copy

import operator
import time
import os
import sys

try:
    import cPickle as pickle
except ImportError:
    import pickle

# from mmcif.api.PdbxContainers import *
from mmcif.api.PdbxContainers import DataContainer
from mmcif.api.DataCategory import DataCategory
from mmcif.io.PdbxWriter import PdbxWriter
from wwpdb.utils.config.ConfigInfoApp import ConfigInfoAppCommon
# from wwpdb.apps.entity_transform.utils.mmCIFUtil import mmCIFUtil
from wwpdb.io.file.mmCIFUtil import mmCIFUtil
from wwpdb.apps.releasemodule.citation.MatchMP import MatchMP
# from wwpdb.apps.releasemodule.utils.Utility import *
from wwpdb.apps.releasemodule.utils.Utility import RunScript


class Analysis(object):
    """
    """

    def __init__(self, siteId="WWPDB_DEPLOY_TEST", path='.', input='result.db', log=sys.stderr, verbose=False):  # pylint: disable=redefined-builtin
        """ Initial Analysis class
        """
        self.__sessionPath = path
        self.__picklefile = input
        self.__resultfile = 'result.cif'
        self.__lfh = log
        self.__verbose = verbose
        self.__candidateList = []
        self.__termMap = {}
        self.__pubmedInfo = {}
        self.__matchResultMap = {}
        self.__annotEntryMap = {}
        #
        self._deserialize()
        #
        self.__cICommon = ConfigInfoAppCommon(siteId)

    def _deserialize(self):
        fb = open(self.__picklefile, 'rb')
        self.__candidateList = pickle.load(fb)
        self.__termMap = pickle.load(fb)
        self.__pubmedInfo = pickle.load(fb)
        fb.close()

    def _runMatchMP(self):
        mp = MatchMP(entryList=self.__candidateList, termMap=self.__termMap,
                     pubmedInfo=self.__pubmedInfo, log=self.__lfh, verbose=self.__verbose)
        mp.run()
        self.__matchResultMap = mp.getMatchResultMap()

    def _getMatchList(self):
        """ Find entries with potential pubmed match
        """
        for cdt in self.__candidateList:
            if 'structure_id' not in cdt:
                continue
            #
            entry_id = cdt['structure_id']
            #
            mList = []
            if self.__matchResultMap:
                if entry_id in self.__matchResultMap:
                    mList = self.__matchResultMap[entry_id]
                #
            # else:
            #    mUtil = MatchUtil(entry=cdt, termMap=self.__termMap, pubmedInfo=self.__pubmedInfo, \
            #                      log=self.__lfh, verbose=self.__verbose)
            #    mUtil.run()
            #    mList = mUtil.getMatchList()
            #
            if not mList:
                continue
            #
            plist = []
            for list in mList:  # pylint: disable=redefined-builtin
                if list[0] not in self.__pubmedInfo:
                    continue
                #
                pdir = copy.deepcopy(self.__pubmedInfo[list[0]])
                pdir['similarity_score'] = list[1]
                plist.append(pdir)
            #
            if not plist:
                continue
            #
            cdt['pubmed'] = plist
            #
            annot = cdt['rcsb_annotator']
            if annot in self.__annotEntryMap:
                self.__annotEntryMap[annot].append(cdt)
            else:
                clist = []
                clist.append(cdt)
                self.__annotEntryMap[annot] = clist
            #
        #

    def _sortEntryMap(self):
        if not self.__annotEntryMap:
            return
        #
        map = self.__annotEntryMap  # pylint: disable=redefined-builtin
        self.__annotEntryMap = {}
        for k, list in map.items():  # pylint: disable=redefined-builtin
            if len(list) < 2:
                self.__annotEntryMap[k] = list
            else:
                dmap = {}
                slist = []
                for cdt in list:
                    dmap[cdt['structure_id']] = cdt
                    tlist = [cdt['structure_id'], cdt['pubmed'][0]['similarity_score']]
                    slist.append(tlist)
                #
                slist.sort(key=operator.itemgetter(1))
                slist.reverse()
                #
                rlist = []
                for tlist in slist:
                    if tlist[0] not in dmap:
                        continue
                    #
                    rlist.append(dmap[tlist[0]])
                #
                self.__annotEntryMap[k] = rlist
            #
        #

    def _writeResultCif(self):
        """ Write search result cif file
        """
        curContainer = DataContainer('citation_finder')

        curCat = self._getEntyCategory()
        if curCat:
            curContainer.append(curCat)
        #
        curCat = self._getAuthorPubmedIdMappingCategory()
        if curCat:
            curContainer.append(curCat)
        #
        curCat = self._getPubmedCitationCategory()
        if curCat:
            curContainer.append(curCat)
        #
        myDataList = []
        myDataList.append(curContainer)
        filename = os.path.join(self.__sessionPath, self.__resultfile)
        ofh = open(filename, 'w')
        pdbxW = PdbxWriter(ofh)
        pdbxW.write(myDataList)
        ofh.close()

    def _getEntyCategory(self):
        if not self.__candidateList:
            return None
        #
        cat = DataCategory('entry_info')
        cat.appendAttribute('structure_id')
        cat.appendAttribute('c_title')
        cat.appendAttribute('pubmed_author')
        #
        row = 0
        for cdt in self.__candidateList:
            if 'structure_id' not in cdt or \
                    'c_title' not in cdt or \
                    'pubmed_author' not in cdt:
                continue
            #
            cat.setValue(str(cdt['structure_id']), 'structure_id', row)
            cat.setValue(str(cdt['c_title']), 'c_title', row)
            cat.setValue(str(','.join(cdt['pubmed_author'])), 'pubmed_author', row)
            row += 1
        #
        return cat

    def _getAuthorPubmedIdMappingCategory(self):
        if not self.__termMap:
            return None
        #
        cat = DataCategory('author_pubmed_mapping')
        cat.appendAttribute('author')
        cat.appendAttribute('pubmed_ids')
        #
        row = 0
        for key, list in self.__termMap.items():  # pylint: disable=redefined-builtin
            cat.setValue(str(key), 'author', row)
            cat.setValue(str(','.join(list)), 'pubmed_ids', row)
            row += 1
        #
        return cat

    def _getPubmedCitationCategory(self):
        if not self.__pubmedInfo:
            return None
        #
        cat = DataCategory('pubmed_info')
        cat.appendAttribute('id')
        cat.appendAttribute('title')
        #
        row = 0
        for _key, dir in self.__pubmedInfo.items():  # pylint: disable=redefined-builtin
            cat.setValue(str(dir['pdbx_database_id_PubMed']), 'id', row)
            cat.setValue(str(dir['title']), 'title', row)
            row += 1
        #
        return cat

    def _runCitationMatch(self):
        script = os.path.join(self.__sessionPath, 'runCitationMatch.csh')
        f = open(script, 'w')
        f.write('#!/bin/tcsh -f\n')
        f.write('#\n')
        f.write('setenv RCSBROOT   ' + self.__cICommon.get_site_annot_tools_path() + '\n')
        f.write('setenv BINPATH  ${RCSBROOT}/bin\n')
        f.write('#\n')
        f.write('${BINPATH}/CitationMatch -input ' + self.__resultfile
                + ' -output matchresult.cif\n')
        f.close()
        #
        RunScript(self.__sessionPath, 'runCitationMatch.csh', 'runCitationMatch.log')

    def _readCitationMatchResult(self):
        filename = os.path.join(self.__sessionPath, 'matchresult.cif')
        if not os.access(filename, os.F_OK):
            return
        #
        cifObj = mmCIFUtil(filePath=filename)
        rlist = cifObj.GetValue('entry_pubmed_mapping')
        if not rlist:
            return
        #
        for dir in rlist:  # pylint: disable=redefined-builtin
            if 'structure_id' not in dir or \
                    'pubmed_id' not in dir or \
                    'similarity_score' not in dir:
                continue
            #
            structure_id = dir['structure_id']
            pubmed_id = dir['pubmed_id']
            similarity_score = dir['similarity_score']
            if structure_id in self.__matchResultMap:
                self.__matchResultMap[structure_id].append([pubmed_id, similarity_score])
            else:
                self.__matchResultMap[structure_id] = [[pubmed_id, similarity_score]]
            #
        #

    def _sortMatchResultMap(self):
        if not self.__matchResultMap:
            return
        #
        map = self.__matchResultMap  # pylint: disable=redefined-builtin
        self.__matchResultMap = {}
        for k, list in map.items():  # pylint: disable=redefined-builtin
            if len(list) > 1:
                list.sort(key=operator.itemgetter(1))
                list.reverse()
            self.__matchResultMap[k] = list
        #

    def Read(self):
        self._writeResultCif()
        self._runCitationMatch()
        self._readCitationMatchResult()
        self._sortMatchResultMap()
        # self._runMatchMP()
        self._getMatchList()
        self._sortEntryMap()

    def getResult(self):
        return self.__annotEntryMap


def doMain():
    startTime = time.time()
    cf = Analysis(log=sys.stderr, verbose=False)
    cf.Read()
    dir = cf.getResult()  # pylint: disable=redefined-builtin
    endTime = time.time()
    diffTime = endTime - startTime
    print(diffTime)
    for k, dlist in list(dir.items()):
        print('annot=' + k + ': Total=' + str(len(dlist)))
        for d in dlist:
            print(d['structure_id'] + '=' + str(len(d['pubmed'])))


if __name__ == '__main__':
    doMain()
