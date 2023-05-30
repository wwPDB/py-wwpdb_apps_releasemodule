##
# File:  MonitorCitationUpdate.py
# Date:  21-Nov-2014
# Updates:
##
"""

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

import sys

from wwpdb.apps.releasemodule.citation.FetchUtil import FetchUtil
from wwpdb.apps.releasemodule.citation.StringUtil import calStringSimilarity
from wwpdb.apps.releasemodule.utils.Utility import isDEPLocked
from wwpdb.apps.releasemodule.utils.CombineDbApi import CombineDbApi
#


class MonitorCitationUpdate(object):
    """
    """

    def __init__(self, path='.', siteId=None, pickleFile=None, resultFile=None, verbose=False, log=sys.stderr):
        self.__sessionPath = path
        self.__siteId = siteId
        self.__pickleFile = pickleFile
        self.__resultFile = resultFile
        self.__verbose = verbose
        self.__lfh = log
        #
        self.__annotEntryMap = {}
        self.__foundAnnotEntryMap = {}
        self.__allPubmedIdList = []
        self.__pubmedInfoMap = {}
        #
        self.__annotatorList = ['BH', 'BN', 'CS', 'EP', 'GG', 'IP', 'LD', 'LT', 'MRS', 'MZ', 'SG', 'YHL']
        #
        self._deserialize()

    def _deserialize(self):
        fb = open(self.__pickleFile, 'rb')
        self.__annotEntryMap = pickle.load(fb)
        fb.close()

    def getEntryList(self):
        for ann in self.__annotatorList:
            self.__getEntryIDList(ann)
        #
        self.__getPubmedInfoMap()
        #
        # db = DBUtil(siteId=self.__siteId, verbose=self.__verbose, log=self.__lfh)
        db = CombineDbApi(siteId=self.__siteId, path=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        fw = open(self.__resultFile, 'w')
        fw.write('Annot. \t Found \t Updated\n')
        for ann in self.__annotatorList:
            if ann in self.__foundAnnotEntryMap:
                self.__printCitationUpdateStats(fw, db, ann, self.__foundAnnotEntryMap[ann])
            else:
                fw.write(ann + ' \t 0 \t 0\n')
            #
        #
        fw.close()
        #

    def __getEntryIDList(self, annotator):
        if (not self.__annotEntryMap) or (annotator not in self.__annotEntryMap):
            return
        #
        foundList = []
        for dir in self.__annotEntryMap[annotator]:  # pylint: disable=redefined-builtin
            if isDEPLocked(dir['structure_id']):
                foundList.append(dir)
                #
                for pdir in dir['pubmed']:
                    if not pdir['pdbx_database_id_PubMed'] in self.__allPubmedIdList:
                        self.__allPubmedIdList.append(pdir['pdbx_database_id_PubMed'])
                    #
                #
            #
        #
        if foundList:
            self.__foundAnnotEntryMap[annotator] = foundList
        #

    def __getPubmedInfoMap(self):
        #
        # Re-fetch NCBI pubmed server for selected pubmed entries
        #
        if not self.__allPubmedIdList:
            return
        #
        fu = FetchUtil(path=self.__sessionPath, idList=self.__allPubmedIdList, log=self.__lfh, verbose=self.__verbose)
        fu.doFetch()
        self.__pubmedInfoMap = fu.getPubmedInfoMap()

    def __printCitationUpdateStats(self, f, db, annotator, foundEntryList):
        #
        items = ['pdbx_database_id_DOI', 'title', 'journal_abbrev', 'journal_volume',
                 'page_first', 'page_last', 'year', 'journal_id_ISSN', 'author']
        #
        RelList = db.getThisWeekRelEntries(annotator)
        #
        num_hit = 0
        num_update = 0
        for dir in foundEntryList:  # pylint: disable=redefined-builtin
            #
            # Get current citation information from database
            #
            cinfo = db.getCitation(dir['structure_id'])
            #
            # Update citation information
            #
            if cinfo:
                for item in items:
                    if (item not in cinfo) or (not cinfo[item]):
                        continue
                    #
                    if item == 'title':
                        dir['c_title'] = cinfo[item]
                    else:
                        dir[item] = cinfo[item]
                    #
                #
                if ('pdbx_database_id_PubMed' in cinfo) and cinfo['pdbx_database_id_PubMed']:
                    dir['pdbx_database_id_PubMed'] = cinfo['pdbx_database_id_PubMed']
                #
            #
            # Update pubmed information
            #
            found_hit = False
            found_update = False
            for pdir in dir['pubmed']:
                pubmed_id = pdir['pdbx_database_id_PubMed']
                #
                # Update latest pubmed information
                #
                if self.__pubmedInfoMap and (pubmed_id in self.__pubmedInfoMap):
                    for item in items:
                        if item not in self.__pubmedInfoMap[pubmed_id]:
                            continue
                        #
                        pdir[item] = self.__pubmedInfoMap[pubmed_id][item]
                    #
                #
                # Update similarity score
                #
                sim = calStringSimilarity(dir['c_title'], pdir['title'])
                if sim < 0.5:
                    continue
                #
                if sim > 0.9:
                    found_hit = True
                #
                pdir['similarity_score'] = '%.3f' % sim
                #
                # Check if entry already had same pubmed information
                #
                if cinfo:
                    code = self.__compareCitationInfo(cinfo, pdir, (dir['structure_id'] in RelList))
                    if code == 'skip':
                        found_update = True
                        break
                #
            #
            if found_hit:
                if found_update:
                    if dir['structure_id'] in RelList:
                        num_hit += 1
                        num_update += 1
                    #
                else:
                    num_hit += 1
            #
            # if found_update:
            #    num_update += 1
            #
        #
        f.write(annotator + ' \t ' + str(num_hit) + ' \t ' + str(num_update) + '\n')

    def __compareCitationInfo(self, cinfo, dir, release_flag):  # pylint: disable=redefined-builtin
        code = ' '
        if ('pdbx_database_id_PubMed' not in cinfo) or ('pdbx_database_id_PubMed' not in dir):
            return code
        #
        if str(cinfo['pdbx_database_id_PubMed']) != dir['pdbx_database_id_PubMed']:
            return code
        #
        code = 'checked'
        #
        for item in ('pdbx_database_id_DOI', 'page_first', 'page_last', 'journal_volume', 'year'):
            #
            # Not allowed missing value in citation
            #
            if ((item not in cinfo) or (not cinfo[item])) and (item in dir):
                return code
            #
            # Allowed missing value in pubmed
            #
            if (item not in dir) or (not dir[item]):
                continue
            #
            if (item in cinfo) and cinfo[item] and str(cinfo[item]) != str(dir[item]):
                return code
            #
        #
        if ('similarity_score' in dir) and (
                float(dir['similarity_score']) > 0.98 or (release_flag and float(dir['similarity_score']) > 0.9)):
            code = 'skip'
        #
        return code


if __name__ == '__main__':
    monitor = MonitorCitationUpdate(path=sys.argv[1], siteId=sys.argv[2], pickleFile=sys.argv[3],
                                    resultFile=sys.argv[4], verbose=False, log=sys.stderr)
    monitor.getEntryList()
