##
# File:  CitationFormParser.py
# Date:  02-Jul-2013
# Updates:
##
"""
Parse submitted form

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

import copy, operator, os, string, sys, traceback

from wwpdb.apps.releasemodule.citation.FetchUtil     import FetchUtil
from wwpdb.apps.releasemodule.update.InputFormParser import InputFormParser
#

class CitationFormParser(InputFormParser):
    """ Class responsible for parsing submitted form
    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        super(CitationFormParser, self).__init__(reqObj=reqObj, verbose=verbose, log=log)
        self.__sObj        = None
        self.__sessionId   = None
        self.__sessionPath = None
        self.__manualFlag  = str(self._reqObj.getValue('citationformflag'))
        self.__citation_id = str(self._reqObj.getValue('citation_id'))
        #
        self.__pubmedList  = []
        self.__updateList  = []
        #
        self.__getSession()
        self.__getPubmedList()
        self._getIdListFromIdSelection(True)
        self.__getCitationInfo()
        self.__mergePubmedwithEntry()

    def __getSession(self):
        """ Join existing session or create new session as required.
        """
        #
        self.__sObj=self._reqObj.newSessionObj()
        self.__sessionId=self.__sObj.getId()
        self.__sessionPath=self.__sObj.getPath()
        if (self._verbose):
            self._lfh.write("------------------------------------------------------\n")
            self._lfh.write("+UpdateRcsbFile.__getSession() - creating/joining session %s\n" % self.__sessionId)
            self._lfh.write("+UpdateRcsbFile.__getSession() - session path %s\n" % self.__sessionPath)

    def __getPubmedList(self):
        if self.__manualFlag == 'yes':
            return
        #
        pubmed_ids = self._getInputString('pubmed_ids', 'pubmed ID', True)
        if not pubmed_ids:
            return
        #
        pubmed_list = self.__getSplitList(pubmed_ids)
        if not pubmed_list:
            return
        #
        self.__getPubmedInfo(pubmed_list)

    def __getSplitList(self, pubmed_ids):
        pubmed_list = pubmed_ids.split(' ')
        if len(pubmed_list) == 1:
            if pubmed_list[0].find(':') == -1:
                pubmed_list[0] = pubmed_list[0] + ':primary'
            #
        #
        input_pubmed_ids = {}
        input_citation_ids = {}
        allow_citation_ids = self.__getAllowCitationIDs()
        #
        lists = []
	for ids in pubmed_list:
            if not ids:
                continue
            #
            ids = ids.strip()
            list = ids.split(':')
            if len(list) != 2:
                self._errorContent = 'Syntax error for pubmed ID.\n'
                return []
            #
            if not list[0].isdigit():
                self._errorContent += 'Invalid pubmed ID: ' + list[0] + '.\n'
            #
            if not allow_citation_ids.has_key(list[1]) and not list[1].isdigit():
                self._errorContent += 'Invalid citation ID: ' + list[1] + '.\n'
            #
            if input_pubmed_ids.has_key(list[0]):
                self._errorContent += 'Repeat pubmed ID: ' + list[0] + '.\n'
            #
            if input_citation_ids.has_key(list[1]):
                self._errorContent += 'Repeat citation ID: ' + list[1] + '.\n'
            #
            input_pubmed_ids[list[0]] = 'y'
            input_citation_ids[list[1]] = 'y'
            if self._errorContent:
                continue
            #
            if allow_citation_ids.has_key(list[1]):
                list.append(allow_citation_ids[list[1]])
            else:
                list.append(int(list[1]) + 11)
            lists.append(list)
        #
        if self._errorContent:
            return []
        #
        if len(lists) > 1:
            lists.sort(key=operator.itemgetter(2))
        #
        return lists

    def __getAllowCitationIDs(self):
        a_c_ids = [ 'primary', 'original_data_1', 'original_data_2', 'original_data_3',
                    'original_data_4', 'original_data_5', 'original_data_6', 'original_data_7',
                    'original_data_8', 'original_data_9', 'original_data_10' ]
        allow_citation_ids = {}
        order = 0
        for id in a_c_ids:
            allow_citation_ids[id] = order
            order += 1
        #
        return allow_citation_ids

    def __getPubmedInfo(self, pubmed_info_list):
        pubmed_id_list = []
        for id_list in pubmed_info_list:
            pubmed_id_list.append(id_list[0])
        #
        fetch = FetchUtil(path=self.__sessionPath, processLabel='', idList=pubmed_id_list, \
                          log=self._lfh, verbose=self._verbose)
        fetch.doFetch()
        pubmedInfoMap = fetch.getPubmedInfoMap()
        #
        for id_list in pubmed_info_list:
            if not pubmedInfoMap or not pubmedInfoMap.has_key(id_list[0]):
                self._errorContent += 'No pumbed information for ID: ' + id_list[0] + '.\n'
                continue
            #
            dir = pubmedInfoMap[id_list[0]]
            dir['type'] = 'checkbox'
            dir['citation_id'] = id_list[1]
            dir['ordinal'] = id_list[2]
            self.__pubmedList.append(dir)
        #

    def __getCitationInfo(self): 
        for entry in self._entryList:
            clist = self._contentDB.getCitationInfo(entry['structure_id'])
            if not clist:
                continue
            #
            reformat = True
            if self.__manualFlag == 'yes':
                reformat = False
            #
            alist = self._contentDB.getCitationAuthorList(entry['structure_id'], reformat)
            if self.__manualFlag == 'yes':
                entry['citation'] = self.__getSelectedCitation(clist, alist)
            else:
                list,map = self.__mergeCitationInfo(clist, alist)
                entry['citation_id'] = list
                entry['auth_citation'] = map
            #
        #

    def __getSelectedCitation(self, clist, alist):
        c_map = {}
        for dir in clist:
            if dir['jrnl_serial_no'] == 1:
                citation_id = 'primary'
            else:
                citation_id = str(dir['jrnl_serial_no'] - 1)
            if citation_id == self.__citation_id:
                c_map = dir
                break
            #
        #
        if c_map:
            list = []
            for dir in alist:
                if dir['citation_id'] == self.__citation_id:
                    list.append(dir['name'])
                #
            #
            if list:
                c_map['author'] = list
            #
        #
        c_map['citation_id'] = self.__citation_id
        return c_map

    def __mergeCitationInfo(self, clist, alist):
        map = {}
        for dir in alist:
            if map.has_key(dir['citation_id']):
                map[dir['citation_id']] += ',' + dir['name']
            else:
                map[dir['citation_id']] = dir['name']
            #
        #
        list = []
        c_map = {}
        for dir in clist:
            if dir['jrnl_serial_no'] == 1:
                citation_id = 'primary'
            else:
                citation_id = str(dir['jrnl_serial_no'] - 1)
            if map.has_key(citation_id):
                dir['author'] = map[citation_id]
            #
            list.append(citation_id)
            c_map[citation_id] = dir
        #
        return list,c_map

    def __mergePubmedwithEntry(self):
        if self.__manualFlag == 'yes':
            return
        #
        allow_citation_ids = self.__getAllowCitationIDs()
        #
        for entry in self._entryList:
            list,cid_map = self.__getSortCitationID(entry['citation_id'], allow_citation_ids)
            p_map = {}
            for dir in self.__pubmedList:
                if cid_map.has_key(dir['citation_id']):
                    p_map[dir['citation_id']] = dir
                elif dir['ordinal'] < 11:
                    p_map[dir['citation_id']] = dir
                    list1 = []
                    list1.append(dir['citation_id'])
                    list1.append(dir['ordinal'])
                    list.append(list1)
                else:
                    p_dir,list1 = self.__getPubmedInfoCopy(dir, list)
                    p_map[p_dir['citation_id']] = p_dir
                    list.append(list1)
                #
                if len(list) > 1:
                    list.sort(key=operator.itemgetter(1))
                #
            #
            c_id_list = []
            for list1 in list:
                c_id_list.append(list1[0])
            #
            entry['citation_id'] = c_id_list
            entry['pubmed'] = p_map
        #

    def __getSortCitationID(self, list, allow_citation_ids):
        sort_cid_list = []
        cid_map = {}
        if not list:
            return sort_cid_list,cid_map
        #
        for id in list:
            if allow_citation_ids.has_key(id):
                order = allow_citation_ids[id]
            else:
                order = int(id) + 10
            list1 = []
            list1.append(id)
            list1.append(order)
            sort_cid_list.append(list1)
            cid_map[id] = order
        #
        if len(sort_cid_list) > 1:
            sort_cid_list.sort(key=operator.itemgetter(1))
        #
        return sort_cid_list,cid_map

    def __getPubmedInfoCopy(self, dir, sort_cid_list):
        p_dir = copy.deepcopy(dir)
        order = 0
        if sort_cid_list:
            order = sort_cid_list[-1][1] + 1
        #
        if order < 11:
            order = 11
        #
        citation_id = str(order - 10)
        p_dir['citation_id'] = str(order - 10)
        p_dir['ordinal'] = order
        list = []
        list.append(p_dir['citation_id'])
        list.append(order)
        return p_dir,list
