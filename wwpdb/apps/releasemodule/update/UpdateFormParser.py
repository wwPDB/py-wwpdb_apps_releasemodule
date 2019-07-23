##
# File:  UpdateFormParser.py
# Date:  30-Sept-2016
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
from wwpdb.apps.releasemodule.utils.CombineDbApi         import CombineDbApi
#

class UpdateFormParser(object):
    """ Class responsible for parsing submitted form
    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        self.__verbose=verbose
        self.__lfh=log
        self.__reqObj=reqObj
        self.__siteId  = str(self.__reqObj.getValue("WWPDB_SITE_ID"))
        #
        self.__codeHandler = UniCodeHandler()
        self.__errorContent = ''
        self.__updateList = []
        self.__checkIdMap = {}
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
        keepCitationList = self.__reqObj.getValueList('keep_citation')
        citation = self.__parseManualInputCitation(keepCitationList)
        #
        keepCitationMap = self.__getKeepCitationMap(keepCitationList)
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
        #
        statusMapping = {}
        statusMapping['status_code'] = 'da_status_code'
        statusMapping['status_code_em'] = 'da_status_code_em'
        statusMapping['wf_status_code'] = 'wf_status_code'
        statusMapping['wf_status_code_em'] = 'wf_status_code_em'
        dbUtil = CombineDbApi(siteId=self.__siteId, verbose=self.__verbose, log=self.__lfh)
        ret_map = dbUtil.getEntryInfoMap(entryList)
        #
        option = str(self.__reqObj.getValue('option'))
        citationflag = str(self.__reqObj.getValue('citationflag'))
        input_flag = str(self.__reqObj.getValue('input_flag'))
        #
        for entry in entryList:
            dataDict = {}
            #
            # merge emdb_id, bmrb_id and comb_ids
            #
            if (entry in ret_map) and ret_map[entry]:
                for item in ( 'bmrb_id', 'comb_ids', 'emdb_id', 'exp_method', 'emdb_release', 'post_rel_status', 'post_rel_recvd_coord', 'post_rel_recvd_coord_date' ):
                    if (item in ret_map[entry]) and ret_map[entry][item]:
                        dataDict[item] = ret_map[entry][item]
                    #
                #
                for k,v in statusMapping.items():
                    if (k in ret_map[entry]) and ret_map[entry][k]:
                        dataDict[v] = ret_map[entry][k]
                    #
                #
            #
            pubmed_list = self.__reqObj.getValueList('pubmed_' + entry)
            if not pubmed_list and input_flag != 'yes' and option == 'citation_update':
                self.__errorContent += 'Entry ' + entry + ' has no pubmed id selected\n'
                continue
            #
            for k,v in itemMapping.items():
                val = str(self.__reqObj.getValue(k + '_' + entry))
                if not val:
                    continue
                #
                dataDict[v] = val
            #
            # split release directory from status
            #
            has_SelectedOption = False
            has_ReleaseInfo = False
            check_flag = False
            for ext in ( '', '_sf', '_em', '_mr', '_cs' ):
                if ('status_code' + ext) in dataDict:
                    has_SelectedOption = True
                    if dataDict['status_code' + ext] == 'REL_added' or dataDict['status_code' + ext] == 'OBS_obsolete':
                        check_flag = True
                    #
                    t_list = dataDict['status_code' + ext].split('_')
                    if len(t_list) == 2:
                        if t_list[0] == 'REL' or t_list[0] == 'OBS':
                            has_ReleaseInfo = True
                        #
                        dataDict['status_code' + ext] = t_list[0]
                        dataDict['directory' + ext] = t_list[1]
                    #
                #
            #
            if citationflag == 'yes':
                has_SelectedOption = True
                dataDict['status_code'] = 'CITATIONUpdate'
            #
            if ('status_code' in dataDict) and (dataDict['status_code'] == 'CITATIONUpdate' or dataDict['status_code'] == 'EMHEADERUpdate'):
                removeList = [ 'status_code_sf', 'status_code_mr', 'status_code_cs', 'directory', 'directory_sf', \
                               'directory_mr', 'directory_cs', 'obsolete_ids', 'supersede_ids' ]
                #
                if dataDict['status_code'] == 'CITATIONUpdate':
                    removeList.append('status_code_em')
                    removeList.append('directory_em')
                #
                has_ReleaseInfo = False
                check_flag = False
                for status in removeList:
                    if status in dataDict:
                        del dataDict[status]
                    #
                #
            #
            if (not has_SelectedOption) and (option != 'pull_release'):
                self.__errorContent += 'Entry ' + entry + ' has no release option selected\n'
            #
            if has_ReleaseInfo and (not 'approval_type' in dataDict):
                self.__errorContent += 'Entry ' + entry + ' has no approval type selected\n'
            #
            if self.__errorContent:
                continue
            #
            if ('status_code' in dataDict) and (dataDict['status_code'] == 'REREL' or dataDict['status_code'] == 'OBS'):
                rev_tokens = self.__reqObj.getValueList('revdat_' + entry)
                if rev_tokens:
                    dataDict['revdat_tokens'] = ','.join(rev_tokens)
                #
                revision = []
                rev_type_list = self.__reqObj.getValueList('revision_type_' + entry)
                if rev_type_list:
                    for rev_type in rev_type_list:
                        dir1 = {}
                        dir1['revision_type'] = rev_type
                        token = rev_type.replace(' ', '_')
                        details = str(self.__reqObj.getValue('revision_detail_' + entry + '_' + token))
                        if details:
                            dir1['details'] = details
                        revision.append(dir1)
                    #
                #
                if revision:
                    dataDict['revision'] = revision
                #
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
                    t_list = pubmed_id.split('_')
                    p_dir['pdbx_database_id_PubMed'] = t_list[0]
                    if len(t_list) > 2:
                        p_dir['id'] = '_'.join(t_list[1:])
                    else:
                        p_dir['id'] = t_list[1]
                    #
                    if (entry in keepCitationMap) and (t_list[1] in keepCitationMap[entry]):
                        p_dir['insert_flag'] = 'Y'
                    else:
                        p_dir['insert_flag'] = 'N'
                    #
                    author_list_number_val = str(self.__reqObj.getValue('citation_author_list_number_' + entry + '_' + pubmed_id))
                    if author_list_number_val:
                        author_list = []
                        author_list_number = int(author_list_number_val)
                        for i in xrange (0, author_list_number):
                            #name = str(self.__reqObj.getValue('c_author_name_' + entry + '_' + pubmed_id + '_' + str(i)))
                            name = self.__codeHandler.process(self.__reqObj.getRawValue('c_author_name_' + entry + '_' + pubmed_id + '_' + str(i)), False)
                            if not name:
                                continue
                            #
                            orcid = str(self.__reqObj.getValue('c_author_orcid_' + entry + '_' + pubmed_id + '_' + str(i)))
                            a_dir = {}
                            a_dir['id'] = p_dir['id']
                            a_dir['name'] = name
                            a_dir['orcid'] = orcid
                            author_list.append(a_dir)
                            #
                        #
                        if author_list:
                            p_dir['author_list'] = author_list
                        #
                    #
                    p_list.append(p_dir)
                #
                dataDict['pubmed'] = p_list
            #
            dataDict['entry'] = entry
            if citation:
                dataDict['citation'] = citation
            #
            self.__updateList.append(dataDict)
            if check_flag and (entry in ret_map) and ret_map[entry]:
                self.__checkIdMap[entry] = ret_map[entry]
            #
        #
        if self.__errorContent:
            self.__updateList = []
            self.__checkIdMap = {}
        #

    def __checkStatusConsistency(self):
        if not self.__checkIdMap:
            return
        #
        for dataDict in self.__updateList:
            if not dataDict['entry'] in self.__checkIdMap:
                continue
            #
            status_map = {}
            value_map = {}
            not_EM_type = False
            #for status_type in ( 'status_code', 'status_code_sf', 'status_code_em', 'status_code_mr', 'status_code_cs'):
            for status_type in ( 'status_code', 'status_code_sf', 'status_code_mr', 'status_code_cs'):
                if not status_type in dataDict:
                    continue
                #
                if status_type != 'status_code_em':
                    not_EM_type = True
               #
                status_map[status_type] = dataDict[status_type]
                if dataDict[status_type] in value_map:
                    continue
                #
                value_map[dataDict[status_type]] = 'yes'
            #
            if len(value_map) == 1:
                reobsolete = str(self.__reqObj.getValue('reobsolete_' + dataDict['entry']))
                checkFlag = False
                if not_EM_type:
                    checkFlag = True
                    if ('OBS' in value_map) and reobsolete == 'yes':
                        checkFlag = False
                    #
                #
                if checkFlag:
                    error = ''
                    count = 0
#                   for t_list in ( [ 'recvd_coordinates',     'status_code', 'Coord. file'], \
#                                   [ 'recvd_struct_fact',     'status_code_sf', 'SF file' ], \
#                                   [ 'recvd_em_map',          'status_code_em', 'EM file' ], \
#                                   [ 'recvd_nmr_constraints', 'status_code_mr', 'MR file' ], \
#                                   [ 'recvd_chemical_shifts', 'status_code_cs', 'CS file' ] ):
#                   removed checking EM consistency because of rare release/obsolete policy
                    for t_list in ( [ 'recvd_coordinates',     'status_code', 'Coord. file'], \
                                    [ 'recvd_struct_fact',     'status_code_sf', 'SF file' ], \
                                    [ 'recvd_nmr_constraints', 'status_code_mr', 'MR file' ], \
                                    [ 'recvd_chemical_shifts', 'status_code_cs', 'CS file' ] ):
                        if not t_list[0] in self.__checkIdMap[dataDict['entry']]:
                            continue
                        #
                        if self.__checkIdMap[dataDict['entry']][t_list[0]] != 'Y' and self.__checkIdMap[dataDict['entry']][t_list[0]] != 'y':
                            continue
                        #
                        if t_list[1] in dataDict:
                            continue
                        #
                        if error:
                            error += ', '
                        #
                        error += t_list[2]
                        count += 1
                    #
                    if error:
                        self.__errorContent += 'Entry ' + dataDict['entry'] + ': '
                        if 'OBS' in value_map:
                            self.__errorContent += 'obsolete '
                        else:
                            self.__errorContent += 'release '
                        #
                        self.__errorContent += error + ' too.\n'
                    #
                #
            else:
                self.__errorContent += 'Entry ' + dataDict['entry'] + ' has inconsist release status:'
#               for t_list in ( [ 'Coord.', 'status_code' ], [ 'SF', 'status_code_sf' ], [ 'EM', 'status_code_em' ], \
#                               [ 'MR', 'status_code_mr' ], [ 'CS', 'status_code_cs' ] ):
#               removed checking EM consistency because of rare release/obsolete policy
                for t_list in ( [ 'Coord.', 'status_code' ], [ 'SF', 'status_code_sf' ], [ 'MR', 'status_code_mr' ], [ 'CS', 'status_code_cs' ] ):
                    if not t_list[1] in dataDict:
                        continue
                    #
                    self.__errorContent += ' ' + t_list[0] + ':' + dataDict[t_list[1]]
                #
                self.__errorContent += '.\n'
            #
        #
        if self.__errorContent:
            self.__updateList = []
        #

    def __parseManualInputCitation(self, keepCitationList):
        """ Parse manually input citation information
        """
        citation = {}
        items = [ 'citation_id', 'title', 'journal_abbrev', 'journal_volume', 'year', 'page_first',
                  'page_last', 'pdbx_database_id_PubMed', 'pdbx_database_id_DOI' ]
        for item in items:
            angstromFlag = False
            if item == 'title':
                angstromFlag = True
            #
            val = self.__codeHandler.process(self.__reqObj.getRawValue(item), angstromFlag)
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
            t_list = []
            author_list = []
            for i in xrange (0, max_author_num):
                #name = str(self.__reqObj.getValue('name_' + str(i + 1)))
                name = self.__codeHandler.process(self.__reqObj.getRawValue('name_' + str(i + 1)), False)
                if not name:
                    continue
                #
                t_list.append(name)
                #
                orcid = str(self.__reqObj.getValue('orcid_' + str(i + 1)))
                a_dir = {}
                a_dir['id'] = citation['id']
                a_dir['name'] = name
                a_dir['orcid'] = orcid
                author_list.append(a_dir)
            #
            if t_list:
                citation['author'] = '|'.join(t_list)
                if len(t_list) == 1:
                    citation['single_author'] = 'Y'
                #
                citation['author_list'] = author_list
            #
        #
        if ('id' in citation) and citation['id'] and (len(keepCitationList) == 1) and (keepCitationList[0] == citation['id']):
            citation['insert_flag'] = 'Y'
        else:
            citation['insert_flag'] = 'N'
        #
        return citation

    def __getKeepCitationMap(self, keepCitationList):
        """
        """
        keepCitationMap = {}
        if not keepCitationList:
            return keepCitationMap
        #
        for keepCitation in keepCitationList:
            t_list = keepCitation.split(':')
            if len(t_list) != 2:
                continue
            #
            if t_list[0] in keepCitationMap:
                keepCitationMap[t_list[0]].append(t_list[1])
            else:
                keepCitationMap[t_list[0]] = [ t_list[1] ]
            #
        #
        return keepCitationMap
