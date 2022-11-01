##
# File:  ReadCitationFinderResult.py
# Date:  03-Jul-2013
# Updates:
##
"""
Read and handle citation finder result file.

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

try:
    import cPickle as pickle
except ImportError:
    import pickle as pickle

import operator
import os
import sys
from wwpdb.io.locator.PathInfo import PathInfo

from wwpdb.apps.releasemodule.citation.FetchUtil import FetchUtil
from wwpdb.apps.releasemodule.citation.StringUtil import calStringSimilarity
from wwpdb.apps.releasemodule.utils.CombineDbApi import CombineDbApi


#

class ReadCitationFinderResult(object):
    """ Class responsible for handling citation finder result file.

    """

    def __init__(self, path='.', dbUtil=None, siteId=None, pickleFile=None, verbose=False, log=sys.stderr):
        self.__sessionPath = path
        self.__dbUtil = dbUtil
        self.__siteId = siteId
        self.__pickleFile = pickleFile
        self.__verbose = verbose
        self.__lfh = log
        #
        self.__annotEntryMap = {}
        self.__foundEntryList = []
        self.__entryIdList = []
        self.__pubmedInfoMap = {}
        self.__validEntryList = []
        #
        self.__items = ('pdbx_database_id_DOI', 'pdbx_database_id_PubMed', 'title', 'journal_abbrev', 'journal_volume',
                        'page_first', 'page_last', 'year', 'journal_id_ISSN', 'author', 'author_list')
        #
        self._deserialize()

    def _deserialize(self):
        if not os.access(self.__pickleFile, os.F_OK):
            return
        #
        fb = open(self.__pickleFile, 'rb')
        self.__annotEntryMap = pickle.load(fb)
        fb.close()

    def getEntryList(self, annotator):
        self.__getEntryIDList(annotator)
        self.__getPubmedInfoMap()
        self.__updateEntryList(annotator)
        return self.__validEntryList

    def __getEntryIDList(self, annotator):
        if not self.__annotEntryMap:
            return
        #
        if annotator == 'ALL':
            for ann, dataList in list(self.__annotEntryMap.items()):
                for dataDict in dataList:
                    self.__entryIdList.append(dataDict['structure_id'])
                    self.__foundEntryList.append(dataDict)
                #
            #
        else:
            annList = []
            annList.append(annotator)
            annList.append('NULL')
            annList.append('UNASSIGN')
            for ann in annList:
                if ann not in self.__annotEntryMap:
                    continue
                #
                for dataDict in self.__annotEntryMap[ann]:
                    self.__entryIdList.append(dataDict['structure_id'])
                    self.__foundEntryList.append(dataDict)
                #
            #
        #

    def __getPubmedInfoMap(self):
        if not self.__foundEntryList:
            return
        #
        uniqueMap = {}
        idlist = []
        for dataDict in self.__foundEntryList:
            if ('pubmed' not in dataDict) or (not dataDict['pubmed']):
                continue
            #
            for pdir in dataDict['pubmed']:
                if ('pdbx_database_id_PubMed' not in pdir) or (not pdir['pdbx_database_id_PubMed']) or (
                        pdir['pdbx_database_id_PubMed'] in uniqueMap):
                    continue
                #
                uniqueMap[pdir['pdbx_database_id_PubMed']] = 'y'
                idlist.append(pdir['pdbx_database_id_PubMed'])
            #
        #
        if not idlist:
            return
        #
        # Re-fetch NCBI pubmed server for selected pubmed entries
        #
        fu = FetchUtil(path=self.__sessionPath, idList=idlist, log=self.__lfh, verbose=self.__verbose)
        fu.doFetch()
        self.__pubmedInfoMap = fu.getPubmedInfoMap()

    def __updateEntryList(self, annotator):
        """ Merge matched pubmed information into entry information
        """
        if not self.__foundEntryList:
            return
        #
        if not self.__dbUtil:
            self.__dbUtil = CombineDbApi(siteId=self.__siteId, path=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        #
        RelList = self.__dbUtil.getFunctionCall(False, 'getThisWeekRelEntries', [annotator])
        if not RelList:
            RelList = []
        #
        EntryInfoMap = self.__dbUtil.getEntryInfoMap(self.__entryIdList)
        EntryCitationInfoMap = self.__dbUtil.getEntryCitationInfoMap(self.__entryIdList)
        #
        rlist = []
        dmap = {}
        for oldDir in self.__foundEntryList:
            if ('pubmed' not in oldDir) or (not oldDir['pubmed']):
                continue
            #
            # Get current entry information from database
            #
            if (not EntryInfoMap) or (not oldDir['structure_id'] in EntryInfoMap) or (
                    not EntryInfoMap[oldDir['structure_id']]):
                continue
            #
            currDir = EntryInfoMap[oldDir['structure_id']]
            if ('rcsb_annotator' in currDir) and str(currDir['rcsb_annotator']) != '' and currDir[
                'rcsb_annotator'].upper() != 'NULL' and \
                    currDir['rcsb_annotator'].upper() != 'UNASSIGN' and currDir[
                'rcsb_annotator'].upper() != annotator and annotator != 'OTHER' and \
                    annotator != 'ALL':
                continue
            #
            isDEPLocked = False
            if ('locking' in currDir) and currDir['locking']:
                locking = currDir['locking'].upper()
                if locking.find('DEP') != -1:
                    isDEPLocked = True
                #
            #
            if not isDEPLocked:
                continue
            #
            # Get existing citation information
            #
            currDir = self.__getCitationInfo(EntryInfoMap[oldDir['structure_id']], oldDir)
            #
            # Get current citation information from database
            #
            if EntryCitationInfoMap \
               and (oldDir['structure_id'] in EntryCitationInfoMap) \
               and EntryCitationInfoMap[oldDir['structure_id']]:
                currDir = self.__getCitationInfo(currDir, EntryCitationInfoMap[oldDir['structure_id']])
            #
            # Get marked unwanted pubmed ID list
            #
            unwanted_pubmed_list = self.__getUnwantedPubMedIDList(oldDir['structure_id'])
            #
            # Update pubmed information
            #
            plist = []
            check_option = ' '
            for pdir in oldDir['pubmed']:
                pubmed_id = pdir['pdbx_database_id_PubMed']
                if pubmed_id in unwanted_pubmed_list:
                    continue
                #
                # Update latest pubmed information
                #
                if self.__pubmedInfoMap and (pubmed_id in self.__pubmedInfoMap):
                    for item in self.__items:
                        if item not in self.__pubmedInfoMap[pubmed_id]:
                            continue
                        #
                        pdir[item] = self.__pubmedInfoMap[pubmed_id][item]
                    #
                #
                # Update similarity score
                #
                sim = 0.0
                if ('c_title' in currDir) and currDir['c_title'] and ('title' in pdir) and pdir['title']:
                    sim = calStringSimilarity(currDir['c_title'], pdir['title'])
                #
                skip_flag = False
                if sim < 0.5:
                    skip_flag = True
                #
                pdir['similarity_score'] = '%.3f' % sim
                pdir['sort_score'] = '%.3f' % sim
                #
                # Check if entry already had same pubmed information
                #
                if EntryCitationInfoMap and (oldDir['structure_id'] in EntryCitationInfoMap) and EntryCitationInfoMap[oldDir['structure_id']]:
                    code = self.__compareCitationInfo(EntryCitationInfoMap[oldDir['structure_id']], pdir, (currDir['structure_id'] in RelList))
                    #
                    # Skip already updated entry
                    #
                    if code == 'skip':
                        plist = []
                        break
                    elif code == 'checked':
                        pdir['sort_score'] = '%.3f' % (1.0 + sim)
                        skip_flag = False
                        if sim > 0.5:
                            check_option = code
                        #
                    #
                #
                if skip_flag:
                    continue
                #
                pdir['type'] = 'radio'
                pdir['citation_id'] = 'primary'
                plist.append(pdir)
            #
            if not plist:
                continue
            #
            # sort matched list
            #
            if len(plist) > 1:
                plist = self.__sortMatchedList(plist)
            #
            currDir['pubmed'] = plist
            currDir['check_option'] = check_option
            dmap[currDir['structure_id']] = currDir
            t_list = []
            t_list.append(currDir['structure_id'])
            t_list.append(plist[0]['pdbx_database_id_PubMed'])
            t_list.append(plist[0]['sort_score'])
            rlist.append(t_list)
        #
        if not rlist:
            return
        #
        self.__sortEntryList(rlist, dmap)

    def __getCitationInfo(self, currDir, cinfo):
        """
        """
        for item in self.__items:
            if (item not in cinfo) or (not cinfo[item]):
                continue
            #
            if item == 'title':
                currDir['c_title'] = cinfo[item]
            else:
                currDir[item] = cinfo[item]
            #
        #
        return currDir

    def __getUnwantedPubMedIDList(self, structure_id):
        pubmed_id_list = []
        pI = PathInfo(siteId=self.__siteId, sessionPath=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        archiveDirPath = pI.getDirPath(dataSetId=structure_id, wfInstanceId=None, contentType='model',
                                       formatType='pdbx',
                                       fileSource='archive', versionId='latest', partNumber=1)
        pickle_file = os.path.join(archiveDirPath, 'marked_pubmed_id.pic')
        if not os.access(pickle_file, os.F_OK):
            return pubmed_id_list
        #
        fb = open(pickle_file, 'rb')
        pubmed_id_list = pickle.load(fb)
        fb.close()
        return pubmed_id_list

    def __compareCitationInfo(self, cinfo, pdir, release_flag):
        code = ' '
        if ('pdbx_database_id_PubMed' not in cinfo) or ('pdbx_database_id_PubMed' not in pdir):
            if ('pdbx_database_id_PubMed' in pdir) and pdir['pdbx_database_id_PubMed'] and \
                    ('pdbx_database_id_DOI' in pdir) and pdir['pdbx_database_id_DOI'] and \
                    ('pdbx_database_id_DOI' in cinfo) and cinfo['pdbx_database_id_DOI'] and \
                    (pdir['pdbx_database_id_DOI'] == cinfo['pdbx_database_id_DOI']):
                return 'checked'
            #
            return code
        #
        if str(cinfo['pdbx_database_id_PubMed']) != pdir['pdbx_database_id_PubMed']:
            return code
        #
        code = 'checked'
        #
        for item in ('pdbx_database_id_DOI', 'page_first', 'page_last', 'journal_volume', 'year'):
            #
            # Not allowed missing value in citation
            #
            if ((item not in cinfo) or (not cinfo[item])) and (item in pdir):
                return code
            #
            # Allowed missing value in pubmed
            #
            if (item not in pdir) or (not pdir[item]):
                continue
            #
            if (item in cinfo) and cinfo[item] and str(cinfo[item]) != str(pdir[item]):
                return code
            #
        #
        if ('similarity_score' in pdir) and (float(pdir['similarity_score']) > 0.98 or (release_flag and float(pdir['similarity_score']) > 0.9)):
            code = 'skip'
        #
        return code

    def __sortMatchedList(self, in_list):
        matchlist = []
        dmap = {}
        for tdir in in_list:
            dmap[tdir['pdbx_database_id_PubMed']] = tdir
            tlist = []
            tlist.append(tdir['pdbx_database_id_PubMed'])
            tlist.append(tdir['sort_score'])
            matchlist.append(tlist)
        #
        matchlist.sort(key=operator.itemgetter(1))
        matchlist.reverse()
        #
        out_list = []
        for tlist in matchlist:
            out_list.append(dmap[tlist[0]])
        return out_list

    def __sortEntryList(self, rlist, dmap):
        """ Sort entries based on highest similarity score
        """
        if len(rlist) > 1:
            rlist.sort(key=operator.itemgetter(2))
            rlist.reverse()
        #
        self.__validEntryList = []
        score = rlist[0][2]
        tlist = []
        for llist in rlist:
            if llist[2] != score:
                if tlist:
                    if len(tlist) > 1:
                        tlist.sort(key=operator.itemgetter(1))
                        tlist.reverse()
                    #
                    for list1 in tlist:
                        self.__validEntryList.append(dmap[list1[0]])
                    #
                #
                tlist = []
            #
            tlist.append(llist)
        #
        if tlist:
            if len(tlist) > 1:
                tlist.sort(key=operator.itemgetter(1))
                tlist.reverse()
            #
            for list1 in tlist:
                self.__validEntryList.append(dmap[list1[0]])
            #
        #


if __name__ == '__main__':
    cReader = ReadCitationFinderResult(pickleFile=sys.argv[1], verbose=False, log=sys.stderr)
    clist = cReader.getEntryList(sys.argv[2])
    for cid in clist:
        print(cid)
