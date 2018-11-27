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
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import copy, cPickle, operator, os, sys, string, time, traceback

from mmcif.api.PdbxContainers                  import *
from mmcif.io.PdbxWriter                      import PdbxWriter
from wwpdb.utils.config.ConfigInfo                 import ConfigInfo
from wwpdb.apps.entity_transform.utils.mmCIFUtil import mmCIFUtil
from wwpdb.apps.releasemodule.citation.MatchMP   import MatchMP
from wwpdb.apps.releasemodule.citation.MatchUtil import MatchUtil
from wwpdb.apps.releasemodule.utils.Utility      import *

class Analysis(object):
    """
    """
    def __init__(self, siteId="WWPDB_DEPLOY_TEST", path='.', input='result.db', log=sys.stderr, verbose=False):
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
        self.__cI = ConfigInfo(siteId)

    def _deserialize(self):
        fb = open(self.__picklefile, 'rb')
        self.__candidateList = cPickle.load(fb)
        self.__termMap = cPickle.load(fb)
        self.__pubmedInfo = cPickle.load(fb)
        fb.close()

    def _runMatchMP(self):
        mp = MatchMP(entryList=self.__candidateList, termMap=self.__termMap, \
                     pubmedInfo=self.__pubmedInfo, log=self.__lfh, verbose=self.__verbose)
        mp.run()
        self.__matchResultMap = mp.getMatchResultMap()

    def _getMatchList(self):
        """ Find entries with potential pubmed match
        """
        for cdt in self.__candidateList:
            if not cdt.has_key('structure_id'):
                continue
            #
            entry_id = cdt['structure_id']
            #
            mList = []
            if self.__matchResultMap:
                if self.__matchResultMap.has_key(entry_id):
                    mList = self.__matchResultMap[entry_id]
                #
            #else:
            #    mUtil = MatchUtil(entry=cdt, termMap=self.__termMap, pubmedInfo=self.__pubmedInfo, \
            #                      log=self.__lfh, verbose=self.__verbose)
            #    mUtil.run()
            #    mList = mUtil.getMatchList()
            #
            if not mList:
                continue
            #
            plist = []
            for list in mList:
                if not self.__pubmedInfo.has_key(list[0]):
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
            annot = cdt['rcsb_annotator']
            if self.__annotEntryMap.has_key(annot):
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
                    if not dmap.has_key(tlist[0]):
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
        myDataList=[]
        myDataList.append(curContainer)
        filename = os.path.join(self.__sessionPath, self.__resultfile)
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
            if not cdt.has_key('structure_id') or \
               not cdt.has_key('c_title') or \
               not cdt.has_key('pubmed_author'):
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
        f.write('${BINPATH}/CitationMatch -input ' + self.__resultfile + \
                ' -output matchresult.cif\n')
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
            if not dir.has_key('structure_id') or \
               not dir.has_key('pubmed_id') or \
               not dir.has_key('similarity_score'):
                continue
            #
            structure_id = dir['structure_id']
            pubmed_id = dir['pubmed_id']
            similarity_score = dir['similarity_score']
            if self.__matchResultMap.has_key(structure_id):
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

    def Read(self):
        self._writeResultCif()
        self._runCitationMatch()
        self._readCitationMatchResult()
        self._sortMatchResultMap()
        #self._runMatchMP()
        self._getMatchList()
        self._sortEntryMap()

    def getResult(self):
        return self.__annotEntryMap

if __name__ == '__main__':
    startTime=time.time()
    cf = Analysis(log=sys.stderr, verbose=False)
    cf.Read()
    dir = cf.getResult()
    endTime=time.time()
    diffTime = endTime - startTime
    print diffTime
    for k,list in dir.items():
        print 'annot='+k+': Total='+str(len(list))
        for d in list:
            print d['structure_id'] + '=' + str(len(d['pubmed']))
