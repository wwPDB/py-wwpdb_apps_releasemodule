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
__author__ = "Zukang Feng"
__email__ = "zfeng@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.07"

import copy
import operator
import sys

from wwpdb.apps.releasemodule.citation.FetchUtil import FetchUtil
from wwpdb.apps.releasemodule.citation.SearchMP import SearchMP
from wwpdb.apps.releasemodule.update.InputFormParser_v2 import InputFormParser
#


class CitationFormParser(InputFormParser):
    """ Class responsible for parsing submitted form
    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        super(CitationFormParser, self).__init__(reqObj=reqObj, verbose=verbose, log=log)
        self.__sObj = None
        self.__sessionId = None
        self.__sessionPath = None
        self.__manualFlag = str(self._reqObj.getValue('citationformflag'))
        self.__citation_id = str(self._reqObj.getValue('citation_id'))
        #
        self.__pubmedList = []
        self.__selected_citation_id_list = []
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
        self.__sObj = self._reqObj.newSessionObj()
        self.__sessionId = self.__sObj.getId()
        self.__sessionPath = self.__sObj.getPath()
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
        input_pubmed_doi_ids = {}
        input_citation_ids = {}
        doi_id_list = []
        doi_term_list = []
        allow_citation_ids = self.__getAllowCitationIDs()
        #
        lists = []
        for ids in pubmed_list:
            if not ids:
                continue
            #
            ids = ids.strip()
            split_id_list = ids.split(':')
            if len(split_id_list) != 2:
                self._errorContent = 'Syntax error for Pubmed or DOI ID.\n'
                return []
            #
            # foundError = False
            if (not split_id_list[0].isdigit()) and (split_id_list[0].find('/') == -1):
                self._errorContent += 'Invalid Pubmed or DOI ID: ' + split_id_list[0] + '.\n'
                # foundError = True
            #
            if split_id_list[0].find('/') != -1:
                doi_id_list.append(split_id_list[0])
                doi_term_list.append(split_id_list[0] + "[aid]")
            #
            if (not split_id_list[1] in allow_citation_ids) and (not split_id_list[1].isdigit()):
                self._errorContent += 'Invalid citation ID: ' + split_id_list[1] + '.\n'
            #
            if split_id_list[0] in input_pubmed_doi_ids:
                self._errorContent += 'Repeat Pubmed or DOI ID: ' + split_id_list[0] + '.\n'
            #
            if split_id_list[1] in input_citation_ids:
                self._errorContent += 'Repeat citation ID: ' + split_id_list[1] + '.\n'
            #
            input_pubmed_doi_ids[split_id_list[0]] = 'y'
            input_citation_ids[split_id_list[1]] = 'y'
            if self._errorContent:
                continue
            #
            if split_id_list[1] in allow_citation_ids:
                split_id_list.append(allow_citation_ids[split_id_list[1]])
            else:
                split_id_list.append(int(split_id_list[1]) + 11)
            #
            self.__selected_citation_id_list.append(split_id_list[1])
            lists.append(split_id_list)
        #
        if self._errorContent:
            return []
        #
        if len(lists) > 1:
            lists.sort(key=operator.itemgetter(2))
        #
        if len(doi_id_list) == 0:
            return lists
        #
        aSearch = SearchMP(path=self.__sessionPath, siteId=self._siteId, termList=doi_term_list, log=self._lfh, verbose=self._verbose)
        aSearch.run()
        termMap = aSearch.getTermMap()
        #
        updatedList = []
        for sub_list in lists:
            if sub_list[0] in doi_id_list:
                if (sub_list[0] + "[aid]") in termMap:
                    sub_list[0] = termMap[sub_list[0] + "[aid]"][0]
                    updatedList.append(sub_list)
                else:
                    self._errorContent += 'No pubmed information for ID: ' + sub_list[0] + '.\n'
                #
            else:
                updatedList.append(sub_list)
            #
        #
        return updatedList

    def __getAllowCitationIDs(self):
        a_c_ids = ['primary', 'original_data_1', 'original_data_2', 'original_data_3',
                   'original_data_4', 'original_data_5', 'original_data_6', 'original_data_7',
                   'original_data_8', 'original_data_9', 'original_data_10']
        allow_citation_ids = {}
        order = 0
        for a_c_id in a_c_ids:
            allow_citation_ids[a_c_id] = order
            order += 1
        #
        return allow_citation_ids

    def __getPubmedInfo(self, pubmed_info_list):
        pubmed_id_list = []
        for id_list in pubmed_info_list:
            pubmed_id_list.append(id_list[0])
        #
        fetch = FetchUtil(path=self.__sessionPath, processLabel='', idList=pubmed_id_list, log=self._lfh, verbose=self._verbose)
        fetch.doFetch()
        pubmedInfoMap = fetch.getPubmedInfoMap()
        #
        for id_list in pubmed_info_list:
            if (not pubmedInfoMap) or (not id_list[0] in pubmedInfoMap):
                self._errorContent += 'No pubmed information for ID: ' + id_list[0] + '.\n'
                continue
            #
            pdir = pubmedInfoMap[id_list[0]]
            pdir['type'] = 'checkbox'
            pdir['citation_id'] = id_list[1]
            pdir['ordinal'] = id_list[2]
            self.__pubmedList.append(pdir)
        #

    def __getCitationInfo(self):
        for entry in self._entryList:
            clist = self._dbUtil.getFunctionCall(False, 'getCitationInfo', [entry['structure_id']])
            if not clist:
                # continue
                #  insert empty primary citation so that it wouldn't crash the UI
                #
                myD = {}
                myD['jrnl_serial_no'] = 1
                clist = []
                clist.append(myD)
            #
            reformat = True
            if self.__manualFlag == 'yes':
                reformat = False
            #
            alist = self._dbUtil.getCitationAuthorList(entry['structure_id'], reformat)
            if self.__manualFlag == 'yes':
                entry['citation'] = self.__getSelectedCitation(clist, alist)
            else:
                m_list, m_map = self.__mergeCitationInfo(clist, alist)
                entry['citation_id'] = m_list
                entry['auth_citation'] = m_map
            #
        #

    def __getSelectedCitation(self, clist, alist):
        c_map = {}
        for c_dir in clist:
            if c_dir['jrnl_serial_no'] == 1:
                citation_id = 'primary'
            else:
                citation_id = str(c_dir['jrnl_serial_no'] - 1)
            if citation_id == self.__citation_id:
                c_map = c_dir
                break
            #
        #
        if c_map:
            list = []  # pylint: disable=redefined-builtin
            for c_dir in alist:
                if ('citation_id' not in c_dir) or ('name' not in c_dir) or (not c_dir['name']):
                    continue
                #
                if c_dir['citation_id'] == self.__citation_id:
                    myD = {}
                    for item in ('name', 'orcid'):
                        myD[item] = ''
                        if (item in c_dir) and c_dir[item]:
                            myD[item] = c_dir[item]
                        #
                    #
                    list.append(myD)
                #
            #
            if list:
                c_map['author'] = list
            #
        #
        c_map['citation_id'] = self.__citation_id
        return c_map

    def __mergeCitationInfo(self, clist, alist):
        map = {}  # pylint: disable=redefined-builtin
        for dir in alist:  # pylint: disable=redefined-builtin
            if dir['citation_id'] in map:
                map[dir['citation_id']] += ',' + dir['name']
            else:
                map[dir['citation_id']] = dir['name']
            #
        #
        list = []  # pylint: disable=redefined-builtin
        c_map = {}
        for dir in clist:
            if int(dir['jrnl_serial_no']) == 1:
                citation_id = 'primary'
            else:
                citation_id = str(int(dir['jrnl_serial_no']) - 1)
            #
            if citation_id not in self.__selected_citation_id_list:
                continue
            #
            if citation_id in map:
                dir['author'] = map[citation_id]
            #
            list.append(citation_id)
            c_map[citation_id] = dir
        #
        return list, c_map

    def __mergePubmedwithEntry(self):
        if self.__manualFlag == 'yes':
            return
        #
        allow_citation_ids = self.__getAllowCitationIDs()
        #
        for entry in self._entryList:
            list, cid_map = self.__getSortCitationID(entry['citation_id'], allow_citation_ids)  # pylint: disable=redefined-builtin
            p_map = {}
            for dir in self.__pubmedList:  # pylint: disable=redefined-builtin
                if dir['citation_id'] in cid_map:
                    p_map[dir['citation_id']] = dir
                elif dir['ordinal'] < 11:
                    p_map[dir['citation_id']] = dir
                    list1 = []
                    list1.append(dir['citation_id'])
                    list1.append(dir['ordinal'])
                    list.append(list1)
                else:
                    p_dir, list1 = self.__getPubmedInfoCopy(dir, list)
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

    def __getSortCitationID(self, list_in, allow_citation_ids):
        sort_cid_list = []
        cid_map = {}
        if not list_in:
            return sort_cid_list, cid_map
        #
        for lid in list_in:
            if lid in allow_citation_ids:
                order = allow_citation_ids[lid]
            else:
                order = int(lid) + 10
            list1 = []
            list1.append(lid)
            list1.append(order)
            sort_cid_list.append(list1)
            cid_map[lid] = order
        #
        if len(sort_cid_list) > 1:
            sort_cid_list.sort(key=operator.itemgetter(1))
        #
        return sort_cid_list, cid_map

    def __getPubmedInfoCopy(self, srcdir, sort_cid_list):
        p_dir = copy.deepcopy(srcdir)
        order = 0
        if sort_cid_list:
            order = sort_cid_list[-1][1] + 1
        #
        if order < 11:
            order = 11
        #
        # citation_id = str(order - 10)
        p_dir['citation_id'] = str(order - 10)
        p_dir['ordinal'] = order
        rlist = []
        rlist.append(p_dir['citation_id'])
        rlist.append(order)
        return p_dir, rlist
