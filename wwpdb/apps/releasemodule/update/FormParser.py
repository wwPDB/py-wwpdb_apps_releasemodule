##
# File:  FormParser.py
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

import os, sys, string, traceback

from wwpdb.apps.releasemodule.citation.FetchResultParser import UniCodeHandler
from wwpdb.apps.releasemodule.utils.DBUtil               import DBUtil
#

class FormParser(object):
    """ Class responsible for parsing submitted form
    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        self.__verbose=verbose
        self.__lfh=log
        self.__reqObj=reqObj
        self.__siteId  = str(self.__reqObj.getValue("WWPDB_SITE_ID"))
        #
        self.__errorContent = ''
        self.__updateList = []
        self.__checkIdList = []
        #
        self.__parseForm()
        self.__checkStatusConsistency()

    def getErrorContent(self):
        return self.__errorContent

    def getUpdateList(self):
        return self.__updateList

    def __parseForm(self):
        entryList = self.__reqObj.getValueList('entry')
        if not entryList:
            self.__errorContent = 'No entry selected'
            return
        #
        citation = {}
        codeHandler = UniCodeHandler()
        items = [ 'citation_id', 'title', 'journal_abbrev', 'journal_volume', 'year', 'page_first',
                  'page_last', 'pdbx_database_id_PubMed', 'pdbx_database_id_DOI' ]
        for item in items:
            angstromFlag = False
            if item == 'title':
                angstromFlag = True
            val = codeHandler.process(self.__reqObj.getRawValue(item), angstromFlag)
            if not val:
                continue
            #
            if item == 'citation_id':
                citation['id'] = val
            else:
                citation[item] = val
            #
        #
        val = str(self.__reqObj.getValue('max_author_num'))
        if val:
            max_author_num = int(val)
            list = []
            for i in range(0, max_author_num):
                val = str(self.__reqObj.getValue('name_' + str(i + 1)))
                if val:
                    list.append(val)
                #
            #
            if list:
                citation['author'] = '|'.join(list)
            #
        #
        itemMapping = {}
        itemMapping['pdbid'] = 'pdb_id'
        itemMapping['status'] = 'status_code'
        itemMapping['status_sf'] = 'status_code_sf'
        itemMapping['status_em'] = 'status_code_em'
        itemMapping['status_mr'] = 'status_code_mr'
        itemMapping['status_cs'] = 'status_code_cs'
        itemMapping['approval_type'] = 'approval_type'
        itemMapping['obsolete'] = 'obsolete_ids'
        itemMapping['supersede'] = 'supersede_ids'
        
        option = str(self.__reqObj.getValue('option'))
        citationflag = str(self.__reqObj.getValue('citationflag'))
        input_flag = str(self.__reqObj.getValue('input_flag'))
        #
        for entry in entryList:
            dir = {}
            pubmed_list = self.__reqObj.getValueList('pubmed_' + entry)
            if not pubmed_list and input_flag != 'yes' and option == 'citation_update':
                self.__errorContent += 'Entry ' + entry + ' has no pubmed id selected\n'
                continue
            #
            for k,v in itemMapping.items():
                val = str(self.__reqObj.getValue(k + '_' + entry))
                if not val:
#                   if k == 'approval_type' and (option == 'request_release' or \
#                                                option == 'status_update'):
#                       self.__errorContent += 'Entry ' + entry + ' has no approval type selected\n'
                    #
                    continue
                #
                dir[v] = val
            #
#           if self.__errorContent:
#               continue
#           #
#           # overwrite the status for 'request_release' or 'status_update' options
#           #
#           val = str(self.__reqObj.getValue('new_status_code_' + entry))
#           if val:
#               dir['status_code'] = val
            #
            # split release directory from status
            #
            has_SelectedOption = False
            has_ReleaseInfo = False
            check_flag = False
            for ext in ( '', '_sf', '_em', '_mr', '_cs' ):
                if 'status_code' + ext in dir:
                    has_SelectedOption = True
                    if dir['status_code' + ext] == 'REL_added' or dir['status_code' + ext] == 'OBS_obsolete':
                        check_flag = True
                    #
                    list = dir['status_code' + ext].split('_')
                    if len(list) == 2:
                        if list[0] == 'REL' or list[0] == 'OBS':
                            has_ReleaseInfo = True
                        #
                        dir['status_code' + ext] = list[0]
                        dir['directory' + ext] = list[1]
                    #
                #
            #
            is_RelEntry = False
            if 'directory' in dir and dir['directory'] == 'modified':
                is_RelEntry = True
            #
            #if citationflag == 'yes' and (not is_RelEntry):
            if citationflag == 'yes':
                has_SelectedOption = True
                has_ReleaseInfo = False
                check_flag = False
                dir['status_code'] = 'CITATIONUpdate'
                for status in ( 'status_code_sf', 'status_code_em', 'status_code_mr', 'status_code_cs' ):
                    if status in dir:
                        del dir[status]
                    #
                #
            #
            if (not has_SelectedOption) and (option != 'pull_release'):
                self.__errorContent += 'Entry ' + entry + ' has no release option selected\n'
            #
            if has_ReleaseInfo and ('approval_type' not in dir):
                self.__errorContent += 'Entry ' + entry + ' has no approval type selected\n'
            #
            if self.__errorContent:
                continue
            #
#           if dir.has_key('status_code'):
#               list = dir['status_code'].split('_')
#               if len(list) == 2:
#                   dir['status_code'] = list[0]
#                   dir['directory'] = list[1]
#               #
#           else:
#               for item in ( 'status_code_sf', 'status_code_mr', 'status_code_cs'):
#                   if dir.has_key(item):
#                       del dir[item]
#                   #
#               #
#               if option == 'citation_update':
#                   val = str(self.__reqObj.getValue('status_code_' + entry))
#                   if val:
#                       dir['status_code'] = val
#                   #
#               #
            #
            rev_tokens = self.__reqObj.getValueList('revdat_' + entry)
            if rev_tokens:
                dir['revdat_tokens'] = ','.join(rev_tokens)
            #
            revision = []
            list = self.__reqObj.getValueList('revision_type_' + entry)
            if list:
                for type in list:
                    dir1 = {}
                    dir1['revision_type'] = type
                    token = type.replace(' ', '_')
                    details = str(self.__reqObj.getValue('revision_detail_' + entry + '_' + token))
                    if details:
                        dir1['details'] = details
                    revision.append(dir1)
                #
            #
            if revision:
                dir['revision'] = revision
            #
            if pubmed_list:
                p_list = []
                for pubmed_id in pubmed_list:
                    p_dir = {}
                    val = str(self.__reqObj.getValue('title_' + entry + '_' + pubmed_id))
                    if val:
                        p_dir['title'] = val
                    #
                    val = str(self.__reqObj.getValue('author_' + entry + '_' + pubmed_id))
                    if val:
                        p_dir['author'] = val
                    #
                    list = pubmed_id.split('_')
                    p_dir['pdbx_database_id_PubMed'] = list[0]
                    if len(list) > 2:
                        p_dir['id'] = '_'.join(list[1:])
                    else:
                        p_dir['id'] = list[1]
                    #
                    p_list.append(p_dir)
                #
                dir['pubmed'] = p_list
            #
            dir['entry'] = entry
            if citation:
                dir['citation'] = citation
            #
            self.__updateList.append(dir)
            if check_flag:
                self.__checkIdList.append(entry)
            #
        #
        if self.__errorContent:
            self.__updateList = []
            self.__checkIdList = []
        #

    def __checkStatusConsistency(self):
        if not self.__checkIdList:
            return
        #
        db = DBUtil(siteId=self.__siteId, verbose=self.__verbose, log=self.__lfh)
        entry_list = db.getEntryInfo(self.__checkIdList)
        if not entry_list:
            return
        #
        map = {}
        for dir in entry_list:
            map[dir['structure_id']] = dir
        #
        for dir in self.__updateList:
            if dir['entry'] not in map:
                continue
            #
            status_map = {}
            value_map = {}
            not_EM_type = False
            for type in ( 'status_code', 'status_code_sf', 'status_code_em', 'status_code_mr', 'status_code_cs'):
                if type not in dir:
                    continue
                #
                if type != 'status_code_em':
                    not_EM_type = True
               #
                status_map[type] = dir[type]
                if dir[type] in value_map:
                    continue
                #
                value_map[dir[type]] = 'yes'
            #
            if len(value_map) == 1:
                if not_EM_type:
                    error = ''
                    count = 0
                    for list in ( [ 'recvd_coordinates',     'status_code', 'Coord. file'], \
                                  [ 'recvd_struct_fact',     'status_code_sf', 'SF file' ], \
                                  [ 'recvd_em_map',          'status_code_em', 'EM file' ], \
                                  [ 'recvd_nmr_constraints', 'status_code_mr', 'MR file' ], \
                                  [ 'recvd_chemical_shifts', 'status_code_cs', 'CS file' ] ):
                        if list[0] not in map[dir['entry']]:
                            continue
                        #
                        if map[dir['entry']][list[0]] != 'Y' and map[dir['entry']][list[0]] != 'y':
                            continue
                        #
                        if list[1] in dir:
                            continue
                        #
                        if error:
                            error += ', '
                        #
                        error += list[2]
                        count += 1
                    #
                    if error:
                        self.__errorContent += 'Entry ' + dir['entry'] + ': '
                        if 'OBS' in value_map:
                            self.__errorContent += 'obsolete '
                        else:
                            self.__errorContent += 'release '
                        #
                        self.__errorContent += error + ' too.\n'
                    #
                #
            else:
                self.__errorContent += 'Entry ' + dir['entry'] + ' has inconsist release status:'
                for list in ( [ 'Coord.', 'status_code' ], [ 'SF', 'status_code_sf' ], [ 'EM', 'status_code_em' ], \
                              [ 'MR', 'status_code_mr' ], [ 'CS', 'status_code_cs' ] ):
                    if list[1] not in dir:
                        continue
                    #
                    self.__errorContent += ' ' + list[0] + ':' + dir[list[1]]
                #
                self.__errorContent += '.\n'
            #
        #
        if self.__errorContent:
            self.__updateList = []
        #
            
