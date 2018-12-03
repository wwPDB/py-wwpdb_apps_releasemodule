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
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

try:
    import cPickle as pickle
except ImportError:
    import pickle as pickle

import copy, operator, os, sys, string, time, traceback

from mmcif.api.PdbxContainers                  import *
from mmcif.io.PdbxWriter                      import PdbxWriter
from wwpdb.utils.config.ConfigInfo                 import ConfigInfo
from wwpdb.apps.entity_transform.utils.mmCIFUtil import mmCIFUtil
from wwpdb.apps.releasemodule.citation.FetchMP   import FetchMP
from wwpdb.apps.releasemodule.citation.SearchMP  import SearchMP
from wwpdb.apps.releasemodule.utils.ContentDbApi import ContentDbApi
from wwpdb.apps.releasemodule.utils.StatusDbApi  import StatusDbApi
from wwpdb.apps.releasemodule.utils.Utility      import *

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
        self.__authorList = []
        self.__termMap = {}
        self.__pubmedIdList = []
        self.__pubmedInfo = {}
        self.__matchResultMap = {}
        self.__annotEntryMap = {}

        self.__cI = ConfigInfo(self.__siteId)

    def searchPubmed(self):
        Time1 = time.time()
        self._getcandidateList()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '__candidateList=' + str(len(self.__candidateList))
        print diffTime
        #
        Time1 = time.time()
        self._getAnnotatorList()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '__annotatorList=' + str(len(self.__annotatorList))
        print diffTime
        #
        Time1 = time.time()
        self._getAuthorList()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '__authorList=' + str(len(self.__authorList))
        print diffTime
        #
        Time1 = time.time()
        self._runAuthorSearch()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '__termMap=' + str(len(self.__termMap))
        print diffTime
        #
        Time1 = time.time()
        self._getPubmedIdList()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '__pubmedIdList=' + str(len(self.__pubmedIdList))
        print diffTime
        #
        Time1 = time.time()
        self._runPubmedFetch()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '__pubmedInfo=' + str(len(self.__pubmedInfo))
        print diffTime
        #
        Time1 = time.time()
        self._writeResultCif()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '_writeResultCif'
        print diffTime
        #
        Time1 = time.time()
        self._runCitationMatch()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '_runCitationMatch'
        print diffTime
        #
        Time1 = time.time()
        self._readCitationMatchResult()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '_readCitationMatchResult'
        print diffTime
        #
        Time1 = time.time()
        self._sortMatchResultMap()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '_sortMatchResultMap'
        print diffTime
        #
        Time1 = time.time()
        self._getMatchList()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '_getMatchList'
        print diffTime
        #
        Time1 = time.time()
        self._sortEntryMap()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '_sortEntryMap'
        print diffTime
        #
        Time1 = time.time()
        self._writeResult()
        Time2 = time.time()
        diffTime = Time2 - Time1
        print '_writeResult'
        print diffTime

    def getResult(self):
        return self.__annotEntryMap

    def _getcandidateList(self):
        """ Get candidate list from database
        """
        connect = ContentDbApi(siteId=self.__siteId, verbose=True, log=self.__lfh)
        self.__candidateList = connect.getPubmedSearchList()

    def _getAnnotatorList(self):
        """ Get active annotator initial list from da_users.status database
        """
        site = 'RCSB'
        if self.__cI.get('WWPDB_SITE_LOC').lower() == 'pdbe':
            site = 'PDBe'
        elif self.__cI.get('WWPDB_SITE_LOC').lower() == 'pdbj':
            site = 'PDBj'
        #
        connect = StatusDbApi(siteId=self.__siteId, verbose=True, log=self.__lfh)
        self.__annotatorList = connect.getAnnoList(siteId=site)

    def _getAuthorList(self):
        """ Get Author term list
        """ 
        if not self.__candidateList:
            return
        #
        map = {}
        #list = []
        for cdt in self.__candidateList:
            #list.append(cdt['structure_id'])
            if not 'pubmed_author' in cdt:
                continue
            #
            for term in cdt['pubmed_author']:
                if term in map:
                    continue
                #
                map[term] = 'y'
                self.__authorList.append(term)
            #
        #
        #print list

    def _runAuthorSearch(self):
        """ Run NCBI Pubmed author search 
        """
        if not self.__authorList:
            return
        #
        aSearch = SearchMP(siteId = self.__siteId, termList=self.__authorList, log=self.__lfh, verbose=self.__verbose)
        aSearch.run()
        self.__termMap = aSearch.getTermMap()

    def _getPubmedIdList(self):
        """ Get unique Pubmed ID list
        """
        if not self.__termMap:
            return
        #
        map = {}
        for key,list in self.__termMap.items():
            for id in list:
                if id in map:
                    continue
                #
                map[id] = 'y'
                self.__pubmedIdList.append(id)
            #
        #

    def _runPubmedFetch(self):
        """ Fetch pubmed information for found pubmed IDs
        """
        if not self.__pubmedIdList:
            return
        #
        pFetch = FetchMP(siteId = self.__siteId, idList=self.__pubmedIdList, log=self.__lfh, verbose=self.__verbose)
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
        curCat = self._getAuthorPubmedIdMappingCategory()
        if curCat:
            curContainer.append(curCat)
        #
        curCat = self._getPubmedCitationCategory()
        if curCat:
            curContainer.append(curCat)
        #
        myDataList=[]
        myDataList.append(curContainer)
        filename = os.path.join(self.__sessionPath, 'input.cif')
        ofh = open(filename, 'w')
        pdbxW=PdbxWriter(ofh)
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
            if (not 'structure_id' in cdt) or (not 'c_title' in cdt) or (not 'pubmed_author' in cdt):
                continue
            #
            cat.setValue(str(cdt['structure_id']), 'structure_id', row)
            cat.setValue(str(cdt['c_title'].replace('#', '')), 'c_title', row)
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
        for key,list in self.__termMap.items():
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
        for key,dir in self.__pubmedInfo.items():
            cat.setValue(str(dir['pdbx_database_id_PubMed']), 'id', row)
            cat.setValue(str(dir['title']), 'title', row)
            row += 1
        #
        return cat

    def _runCitationMatch(self):
        script = os.path.join(self.__sessionPath, 'runCitationMatch.csh')
        f = file(script, 'w')
        f.write('#!/bin/tcsh -f\n')
        f.write('#\n')
        f.write('setenv RCSBROOT   ' + self.__cI.get('SITE_ANNOT_TOOLS_PATH') + '\n')
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
        for dir in rlist:
            if (not 'structure_id' in dir) or (not 'pubmed_id' in dir) or (not 'similarity_score' in dir):
                continue
            #
            structure_id = dir['structure_id']
            pubmed_id = dir['pubmed_id']
            similarity_score = dir['similarity_score']
            if  structure_id in self.__matchResultMap:
                self.__matchResultMap[structure_id].append([dir['pubmed_id'], dir['similarity_score']])
            else:
                self.__matchResultMap[structure_id] = [[dir['pubmed_id'], dir['similarity_score']]]
            #
        #

    def _sortMatchResultMap(self):
        if not self.__matchResultMap:
            return
        #
        map = self.__matchResultMap
        self.__matchResultMap = {}
        for k,list in map.items():
            if len(list) > 1:
                list.sort(key=operator.itemgetter(1))
                list.reverse()
            self.__matchResultMap[k] = list
        #

    def _getMatchList(self):
        """ Find entries with potential pubmed match
        """
        if not self.__matchResultMap:
            return
        #
        for cdt in self.__candidateList:
            if not 'structure_id' in cdt:
                continue
            #
            entry_id = cdt['structure_id']
            #
            if not entry_id in self.__matchResultMap:
                continue
            #
            plist = []
            for list in self.__matchResultMap[entry_id]:
                if not list[0] in self.__pubmedInfo:
                    continue
                #
                pdir =  copy.deepcopy(self.__pubmedInfo[list[0]])
                pdir['similarity_score'] = list[1]
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
        map = self.__annotEntryMap
        self.__annotEntryMap = {}
        for k,list in map.items():
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
                    if not tlist[0] in dmap:
                        continue
                    #
                    rlist.append(dmap[tlist[0]])
                #
                self.__annotEntryMap[k] = rlist
            #
        #

    def _writeResult(self):
        print '__annotEntryMap=' + str(len(self.__annotEntryMap))
        fb = open(self.__resultfile, 'wb')
        pickle.dump(self.__annotEntryMap, fb)
        fb.close()


if __name__ == '__main__':
    startTime=time.time()
    cf = CitationFinder(siteId=sys.argv[1], path=sys.argv[2], output=sys.argv[3], log=sys.stderr, verbose=False)
    cf.searchPubmed()
    endTime=time.time()
    diffTime = endTime - startTime
    print diffTime
