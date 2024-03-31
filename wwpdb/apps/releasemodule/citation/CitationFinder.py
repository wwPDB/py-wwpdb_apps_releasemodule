##
# File:  CitationFinder.py
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

import os
import sys

try:
    import cPickle as pickle
except ImportError:
    import pickle as pickle

import copy
import operator
import time

from mmcif.api.DataCategory import DataCategory
from mmcif.api.PdbxContainers import DataContainer
from mmcif.io.PdbxWriter import PdbxWriter
from wwpdb.io.file.mmCIFUtil import mmCIFUtil
from wwpdb.utils.config.ConfigInfo import ConfigInfo
from wwpdb.utils.config.ConfigInfoApp import ConfigInfoAppCommon

from wwpdb.apps.releasemodule.citation.FetchMP import FetchMP
from wwpdb.apps.releasemodule.citation.SearchMP import SearchMP
from wwpdb.apps.releasemodule.utils.ContentDbApi import ContentDbApi
from wwpdb.apps.releasemodule.utils.StatusDbApi_v2 import StatusDbApi
from wwpdb.apps.releasemodule.utils.Utility import RunScript


class CitationFinder(object):
    """
    """

    def __init__(self, siteId="WWPDB_DEPLOY_TEST", path='.', output='citation_finder.db', log=sys.stderr, verbose=False):
        """ Initial CitationFinder class
        """
        self.__siteId = siteId
        self.__sessionPath = path
        self.__resultfile = output
        self.__lfh = log
        self.__verbose = verbose
        self.__candidateList = []
        self.__annotatorList = []
        self.__termList = []
        self.__termMap = {}
        self.__pubmedIdList = []
        self.__pubmedInfo = {}
        self.__matchResultMap = {}
        self.__annotEntryMap = {}

        self.__cI = ConfigInfo(self.__siteId)
        self.__cICommon = ConfigInfoAppCommon(self.__siteId)

    def searchPubmed(self, year=2):
        Time1 = time.time()
        self._getcandidateList(year=year)
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('__candidateList=' + str(len(self.__candidateList)))
        print(diffTime)
        #
        Time1 = time.time()
        self._getAnnotatorList()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('__annotatorList=' + str(len(self.__annotatorList)))
        print(diffTime)
        #
        Time1 = time.time()
        self._getTermList()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('__authorList=' + str(len(self.__termList)))
        print(diffTime)
        #
        Time1 = time.time()
        self._runNCBIPubmedSearch(year=year)
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('__termMap=' + str(len(self.__termMap)))
        print(diffTime)
        #
        Time1 = time.time()
        self._getPubmedIdList()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('__pubmedIdList=' + str(len(self.__pubmedIdList)))
        print(diffTime)
        #
        Time1 = time.time()
        self._runPubmedFetch()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('__pubmedInfo=' + str(len(self.__pubmedInfo)))
        print(diffTime)
        #
        Time1 = time.time()
        self._writeResultCif()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('_writeResultCif')
        print(diffTime)
        #
        Time1 = time.time()
        self._runCitationMatch()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('_runCitationMatch')
        print(diffTime)
        #
        Time1 = time.time()
        self._readCitationMatchResult()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('_readCitationMatchResult')
        print(diffTime)
        #
        Time1 = time.time()
        self._sortMatchResultMap()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('_sortMatchResultMap')
        print(diffTime)
        #
        Time1 = time.time()
        self._getMatchList()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('_getMatchList')
        print(diffTime)
        #
        Time1 = time.time()
        self._sortEntryMap()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('_sortEntryMap')
        print(diffTime)
        #
        Time1 = time.time()
        self._writeResult()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print('_writeResult')
        print(diffTime)

    def getResult(self):
        return self.__annotEntryMap

    def _getcandidateList(self, year=2):
        """ Get candidate list from database
        """
        connect = ContentDbApi(siteId=self.__siteId, verbose=True, log=self.__lfh)
        self.__candidateList = connect.getPubmedSearchList(year=year)

    def _getAnnotatorList(self):
        """ Get active annotator initial list from da_users.status database
        """
        site = 'RCSB'
        if self.__cI.get('WWPDB_SITE_LOC').lower() == 'pdbe':
            site = 'PDBe'
        elif self.__cI.get('WWPDB_SITE_LOC').lower() == 'pdbj':
            site = 'PDBj'
        elif self.__cI.get('WWPDB_SITE_LOC').lower() == 'pdbc':
            site = 'PDBc'
        #
        connect = StatusDbApi(siteId=self.__siteId, verbose=True, log=self.__lfh)
        self.__annotatorList = connect.getAnnoList(siteId=site)

    def _getTermList(self):
        """ Get Author term list
        """
        if not self.__candidateList:
            return
        #
        temp_map = {}
        for cdt in self.__candidateList:
            if 'pdbx_database_id_DOI' in cdt:
                term = str(cdt['pdbx_database_id_DOI']) + '[aid]'
                if term not in temp_map:
                    temp_map[term] = 'y'
                    self.__termList.append(term)
                #
            #
            if 'pubmed_author' not in cdt:
                continue
            #
            for term in cdt['pubmed_author']:
                if term in temp_map:
                    continue
                #
                temp_map[term] = 'y'
                self.__termList.append(term)
            #
        #

    def _runNCBIPubmedSearch(self, year=2):
        """ Run NCBI Pubmed author and DOI search
        """
        if not self.__termList:
            return
        #
        aSearch = SearchMP(siteId=self.__siteId, termList=self.__termList, log=self.__lfh, verbose=self.__verbose,
                           path=self.__sessionPath)
        aSearch.run(year=year)
        self.__termMap = aSearch.getTermMap()

    def _getPubmedIdList(self):
        """ Get unique Pubmed ID list
        """
        if not self.__termMap:
            return
        #
        tmap = {}
        for _key, plist in self.__termMap.items():
            for pid in plist:
                if pid in tmap:
                    continue
                #
                tmap[pid] = 'y'
                self.__pubmedIdList.append(pid)
            #
        #

    def _runPubmedFetch(self):
        """ Fetch pubmed information for found pubmed IDs
        """
        if not self.__pubmedIdList:
            return
        #
        pFetch = FetchMP(siteId=self.__siteId, idList=self.__pubmedIdList, log=self.__lfh, verbose=self.__verbose,
                         path=self.__sessionPath)
        pFetch.run()
        self.__pubmedInfo = pFetch.getPubmedInfoMap()

    def _writeResultCif(self):
        """ Write search result cif file
        """
        curContainer = DataContainer('citation_finder')

        curCat = self._getEntyCategory()
        if curCat:
            curContainer.append(curCat)
        #
        curCat = self._getTermPubmedIdMappingCategory()
        if curCat:
            curContainer.append(curCat)
        #
        curCat = self._getPubmedCitationCategory()
        if curCat:
            curContainer.append(curCat)
        #
        myDataList = []
        myDataList.append(curContainer)
        filename = os.path.join(self.__sessionPath, 'input.cif')
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
        cat.appendAttribute('pdbx_database_id_PubMed')
        cat.appendAttribute('pdbx_database_id_DOI')
        cat.appendAttribute('DOI_term')
        #
        row = 0
        for cdt in self.__candidateList:
            if ('structure_id' not in cdt) or ('c_title' not in cdt) or ('pubmed_author' not in cdt):
                continue
            #
            cat.setValue(str(cdt['structure_id']), 'structure_id', row)
            cat.setValue(str(cdt['c_title'].replace('#', '')), 'c_title', row)
            cat.setValue(str(','.join(cdt['pubmed_author'])), 'pubmed_author', row)
            if 'pdbx_database_id_PubMed' in cdt:
                cat.setValue(str(cdt['pdbx_database_id_PubMed']), 'pdbx_database_id_PubMed', row)
            #
            if 'pdbx_database_id_DOI' in cdt:
                cat.setValue(str(cdt['pdbx_database_id_DOI']), 'pdbx_database_id_DOI', row)
                cat.setValue(str(cdt['pdbx_database_id_DOI']) + '[aid]', 'DOI_term', row)
            #
            row += 1
        #
        return cat

    def _getTermPubmedIdMappingCategory(self):
        if not self.__termMap:
            return None
        #
        cat = DataCategory('term_pubmed_mapping')
        cat.appendAttribute('term')
        cat.appendAttribute('pubmed_ids')
        #
        row = 0
        for key, plist in self.__termMap.items():
            cat.setValue(str(key), 'term', row)
            cat.setValue(str(','.join(plist)), 'pubmed_ids', row)
            row += 1
        #
        return cat

    def _getPubmedCitationCategory(self):
        if not self.__pubmedInfo:
            return None
        #
        cat = DataCategory('pubmed_info')
        cat.appendAttribute('id')
        cat.appendAttribute('doi')
        cat.appendAttribute('title')
        #
        row = 0
        for _key, v_dict in self.__pubmedInfo.items():
            cat.setValue(str(v_dict['pdbx_database_id_PubMed']), 'id', row)
            if 'pdbx_database_id_DOI' in v_dict:
                cat.setValue(str(v_dict['pdbx_database_id_DOI']), 'doi', row)
            else:
                cat.setValue('?', 'doi', row)
            #
            cat.setValue(str(v_dict['title']), 'title', row)
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
        f.write('${BINPATH}/CitationMatch -input input.cif -output matchresult.cif\n')
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
        for rdic in rlist:
            if ('structure_id' not in rdic) or ('pubmed_id' not in rdic) or ('similarity_score' not in rdic):
                continue
            #
            structure_id = rdic['structure_id']
            pubmed_id = rdic['pubmed_id']
            similarity_score = rdic['similarity_score']
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
        r_map = self.__matchResultMap
        self.__matchResultMap = {}
        for k, r_list in r_map.items():
            if len(r_list) > 1:
                r_list.sort(key=operator.itemgetter(1))
                r_list.reverse()
            #
            self.__matchResultMap[k] = r_list
        #

    def _getMatchList(self):
        """ Find entries with potential pubmed match
        """
        if not self.__matchResultMap:
            return
        #
        for cdt in self.__candidateList:
            if 'structure_id' not in cdt:
                continue
            #
            entry_id = cdt['structure_id']
            #
            if entry_id not in self.__matchResultMap:
                continue
            #
            plist = []
            for mlist in self.__matchResultMap[entry_id]:
                if mlist[0] not in self.__pubmedInfo:
                    continue
                #
                pdir = copy.deepcopy(self.__pubmedInfo[mlist[0]])
                pdir['similarity_score'] = mlist[1]
                plist.append(pdir)
            #
            if not plist:
                continue
            #
            cdt['pubmed'] = plist
            #
            annot = 'NULL'
            if 'rcsb_annotator' in cdt:
                annot = cdt['rcsb_annotator'].upper()
            #
            if (annot == 'JY') or (annot not in self.__annotatorList):
                annot = 'OTHER'
            #
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
        a_map = self.__annotEntryMap
        self.__annotEntryMap = {}
        for k, vlist in a_map.items():
            if len(vlist) < 2:
                self.__annotEntryMap[k] = vlist
            else:
                dmap = {}
                slist = []
                for cdt in vlist:
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

    def _writeResult(self):
        print('__annotEntryMap=' + str(len(self.__annotEntryMap)))
        fb = open(self.__resultfile, 'wb')
        pickle.dump(self.__annotEntryMap, fb)
        fb.close()


def main_test():
    startTime = time.time()
    cf = CitationFinder(siteId=sys.argv[1], path=sys.argv[2], output=sys.argv[3], log=sys.stderr, verbose=False)
    year = 2
    if len(sys.argv) == 5:
        year = int(sys.argv[4])
    #
    cf.searchPubmed(year=year)
    endTime = time.time()
    ldiffTime = endTime - startTime
    print(ldiffTime)


if __name__ == '__main__':
    main_test()
