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
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import copy, cPickle, operator, os, sys, string, traceback

from wwpdb.apps.releasemodule.citation.FetchUtil  import FetchUtil
from wwpdb.apps.releasemodule.citation.StringUtil import calStringSimilarity
from wwpdb.apps.releasemodule.utils.DBUtil        import DBUtil
from wwpdb.apps.releasemodule.utils.Utility       import isDEPLocked
from wwpdb.utils.rcsb.PathInfo                    import PathInfo
#

class ReadCitationFinderResult(object):
    """ Class responsible for handling citation finder result file.

    """
    def __init__(self, path='.', siteId=None, pickleFile=None, verbose=False, log=sys.stderr):
        self.__sessionPath = path
        self.__siteId      = siteId
        self.__pickleFile  = pickleFile
        self.__verbose     = verbose
        self.__lfh         = log
        #
        self.__annotEntryMap  = {}
        self.__foundEntryList = []
        self.__pubmedInfoMap  = {}
        #
        self._deserialize()

    def _deserialize(self):
        fb = open(self.__pickleFile, 'rb')
        self.__annotEntryMap = cPickle.load(fb)
        fb.close()

    def getEntryList(self, annotator):
        self.__getEntryIDList(annotator)
        self.__getPubmedInfoMap()
        self.__updateEntryList(annotator)
        return self.__foundEntryList

    def __getEntryIDList(self, annotator):
        if not self.__annotEntryMap:
            return
        #
        annList = []
        annList.append(annotator)
        annList.append('NULL')
        annList.append('UNASSIGN')
        #if self.__annotEntryMap.has_key(annotator):
        #    self.__foundEntryList = self.__annotEntryMap[annotator]
        #
        #for ann in ('NULL', 'UNASSIGN'): 
        for ann in annList:
            if not self.__annotEntryMap.has_key(ann):
                continue
            #
            for dir in self.__annotEntryMap[ann]:
                if isDEPLocked(dir['structure_id']):
                    self.__foundEntryList.append(dir)
                #
            #
        #

    def __getPubmedInfoMap(self):
        if not self.__foundEntryList:
            return
        #
        map = {}
        idlist = []
        for dir in self.__foundEntryList:
            for pdir in dir['pubmed']:
                if map.has_key(pdir['pdbx_database_id_PubMed']):
                    continue
                #
                map[pdir['pdbx_database_id_PubMed']] = 'y'
                idlist.append(pdir['pdbx_database_id_PubMed'])
            #
        #
        if not idlist:
            return
        #
        # Re-fetch NCBI pubmed server for selected pubmed entries
        #
        fu = FetchUtil(path=self.__sessionPath, idList=idlist, log=self.__lfh, \
                       verbose=self.__verbose)
        fu.doFetch()
        self.__pubmedInfoMap = fu.getPubmedInfoMap()

    def __updateEntryList(self, annotator):
        """ Merge matched pubmed information into entry information
        """
        if not self.__foundEntryList:
            return
        #
        items = [ 'pdbx_database_id_DOI', 'title', 'journal_abbrev', 'journal_volume',
                  'page_first', 'page_last', 'year', 'journal_id_ISSN', 'author' ]
        #
        db = DBUtil(siteId=self.__siteId,verbose=self.__verbose,log=self.__lfh)
        RelList = db.getThisWeekRelEntries(annotator)
        #
        rlist = []
        dmap = {}
        for dir in self.__foundEntryList:
            #
            # Get current citation information from database
            #
            cinfo = db.getCitation(dir['structure_id'])
            #
            # Update citation information
            #
            if cinfo:
                for item in items:
                    if not cinfo.has_key(item) or not cinfo[item]:
                        continue
                    #
                    if item == 'title':
                        dir['c_title'] = cinfo[item]
                    else:
                        dir[item] = cinfo[item]
                    #
                #
                if cinfo.has_key('pdbx_database_id_PubMed') and cinfo['pdbx_database_id_PubMed']:
                    dir['pdbx_database_id_PubMed'] = cinfo['pdbx_database_id_PubMed']
                #
            #
            # Get marked unwanted pubmed ID list
            #
            unwanted_pubmed_list = self.__getUnwantedPubMedIDList(dir['structure_id'])
            #
            # Update pubmed information
            #
            plist = []
            check_option = ' '
            for pdir in dir['pubmed']:
                pubmed_id = pdir['pdbx_database_id_PubMed']
                if pubmed_id in unwanted_pubmed_list:
                    continue
                #
                # Update latest pubmed information
                #
                if self.__pubmedInfoMap and self.__pubmedInfoMap.has_key(pubmed_id):
                    for item in items:
                        if not self.__pubmedInfoMap[pubmed_id].has_key(item):
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
                pdir['similarity_score'] = '%.3f' % sim
                #
                # Check if entry already had same pubmed information
                #
                if cinfo:
                    code = self.__compareCitationInfo(cinfo, pdir, (dir['structure_id'] in RelList))
                    #
                    # Skip already updated entry
                    #
                    if code == 'skip':
                        plist = []
                        break
                    elif code == 'checked':
                        check_option = code
                    #
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
            # update entry info
            #
            idlist = []
            idlist.append(dir['structure_id'])
            entryinfo = db.getEntryInfo(idlist)
            if entryinfo:
                for k,v in entryinfo[0].items():
                    if v:
                        dir[k] = v
                    #
                #
            #
            if dir.has_key('rcsb_annotator') and str(dir['rcsb_annotator']) != '' and \
               dir['rcsb_annotator'].upper() != 'NULL' and dir['rcsb_annotator'].upper() != 'UNASSIGN' and \
               dir['rcsb_annotator'] != annotator:
                continue
            #
            dir['pubmed'] = plist
            dir['check_option'] = check_option
            dmap[dir['structure_id']] = dir
            list = []
            list.append(dir['structure_id'])
            list.append(plist[0]['pdbx_database_id_PubMed'])
            list.append(plist[0]['similarity_score'])
            rlist.append(list)
        #
        self.__foundEntryList = []
        if not rlist:
            return
        #
        self.__sortEntryList(rlist, dmap)

    def __getUnwantedPubMedIDList(self, structure_id):
        pubmed_id_list = []
        pI = PathInfo(siteId=self.__siteId, sessionPath=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        archiveDirPath = pI.getDirPath(dataSetId=structure_id, wfInstanceId=None, contentType='model', formatType='pdbx', \
                                       fileSource='archive', versionId='latest', partNumber=1)
        pickle_file = os.path.join(archiveDirPath, 'marked_pubmed_id.pic')
        if not os.access(pickle_file, os.F_OK):
            return pubmed_id_list
        #
        fb = open(pickle_file, 'rb')
        pubmed_id_list = cPickle.load(fb)
        fb.close()
        return pubmed_id_list

    def __compareCitationInfo(self, cinfo, dir, release_flag):
        code = ' '
        if not cinfo.has_key('pdbx_database_id_PubMed') or \
           not dir.has_key('pdbx_database_id_PubMed'):
            return code
        #
        if str(cinfo['pdbx_database_id_PubMed']) != dir['pdbx_database_id_PubMed']:
            return code
        #
        code = 'checked'
        #
        for item in ( 'pdbx_database_id_DOI', 'page_first', 'page_last', \
                      'journal_volume', 'year'):
            #
            # Not allowed missing value in citation
            #
            if ((not cinfo.has_key(item)) or (not cinfo[item])) and dir.has_key(item):
                return code
            #
            # Allowed missing value in pubmed
            #
            if not dir.has_key(item) or not dir[item]:
                continue
            #
            if cinfo.has_key(item) and cinfo[item] and str(cinfo[item]) != str(dir[item]):
                return code
            #
        #
        if dir.has_key('similarity_score') and (float(dir['similarity_score']) > 0.98 or \
           (release_flag and float(dir['similarity_score']) > 0.9)):
            code = 'skip'
        #
        return code

    def __sortMatchedList(self, in_list):
        matchlist = []
        dmap = {}
        for dir in in_list: 
            dmap[dir['pdbx_database_id_PubMed']] = dir
            list = []
            list.append(dir['pdbx_database_id_PubMed'])
            list.append(dir['similarity_score'])
            matchlist.append(list)
        #
        matchlist.sort(key=operator.itemgetter(1))
        matchlist.reverse()
        #
        out_list = []
        for list in matchlist:
            out_list.append(dmap[list[0]])
        return out_list

    def __sortEntryList(self, rlist, dmap):
        """ Sort entries based on highest similarity score
        """
        if len(rlist) > 1:
            rlist.sort(key=operator.itemgetter(2))
            rlist.reverse()
        #
        self.__foundEntryList = []
        score = rlist[0][2]
        tlist = []
        for list in rlist:
            if list[2] != score:
                if tlist:
                    if len(tlist) > 1:
                        tlist.sort(key=operator.itemgetter(1))
                        tlist.reverse()
                    #
                    for list1 in tlist:
                        self.__foundEntryList.append(dmap[list1[0]])
                    #
                #
                tlist = []
            #
            tlist.append(list)
        #
        if tlist:
            if len(tlist) > 1:
                tlist.sort(key=operator.itemgetter(1))
                tlist.reverse()
            #
            for list1 in tlist:
                self.__foundEntryList.append(dmap[list1[0]])
            #
        #

if __name__ == '__main__':
    cReader = ReadCitationFinderResult(pickleFile=sys.argv[1], verbose=False, log=sys.stderr)
    list = cReader.getEntryList(sys.argv[2])
    for id in list:
        print id
