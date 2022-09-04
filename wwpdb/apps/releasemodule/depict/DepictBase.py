##
# File:  DepictBase.py
# Date:  02-Oct-2016
# Updates:
##
"""
Create HTML depiction for release module.

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
    from urllib.parse import quote as u_quote
except ImportError:
    from urllib import quote as u_quote

from wwpdb.apps.releasemodule.depict.ReleaseOption_v2 import ReleaseOption
from wwpdb.apps.releasemodule.utils.ModuleBaseClass import ModuleBaseClass
from wwpdb.io.locator.PathInfo import PathInfo


class DepictBase(ModuleBaseClass):
    """ Class responsible for generating HTML depiction.

    """
    def __init__(self, reqObj=None, resultList=None, verbose=False, log=sys.stderr):
        super(DepictBase, self).__init__(reqObj=reqObj, verbose=verbose, log=log)
        self._resultList = resultList
        self._IdList = []
        #
        self._pI = PathInfo(siteId=self._siteId, sessionPath=self._sessionPath, verbose=self._verbose, log=self._lfh)
        #
        self._newReleaseFlag = False
        self.__newReleaseEmFlag = False
        self.__reObsoleteFlag = False
        self.__reObsoleteEmFlag = False
        self._skipReleaseOptionFlag = False
        #
        # self.__revdatTokenList = self._getItemList('revdat_token_list')
        # self.__revisionTypeList = self._getItemList('revision_type_list')
        self.__cleanupEmOnlyEntries()

    def _initialOverAllDict(self):
        myD = {}
        myD['task'] = str(self._reqObj.getValue('task'))
        myD['sessionid'] = self._sessionId
        myD['owner'] = str(self._reqObj.getValue('owner'))
        myD['annotator'] = str(self._reqObj.getValue('annotator'))
        myD['begin_select_all_comment'] = '<!--'
        myD['end_select_all_comment'] = '-->'
        if self._siteId == 'WWPDB_DEPLOY_DEPGRP1_RU' or self._siteId == 'WWPDB_DEPLOY_DEPGRP2_RU':  # or self._siteId == 'WWPDB_DEPLOY_TEST_RU':
            myD['begin_select_all_comment'] = ''
            myD['end_select_all_comment'] = ''
        #
        return myD

    def _initialEntryDict(self, dataDict, items, statusFlag, requestFlag, defaultValue):
        model_release_date = ''
        if ('date_of_RCSB_release' in dataDict) and dataDict['date_of_RCSB_release']:
            model_release_date = str(dataDict['date_of_RCSB_release']).replace('00:00:00', '').strip()
        #
        isWdrnEntry = False
        if ('status_code' in dataDict) and (dataDict['status_code'].upper() == 'WDRN'):
            isWdrnEntry = True
        #
        isEmEntry = False
        if ('status_code_em' in dataDict) and dataDict['status_code_em'] and (dataDict['status_code_em'] != 'WDRN'):
            isEmEntry = True
        #
        self._newReleaseFlag = False
        if ((not model_release_date) or model_release_date == self._rel_date) and (not isWdrnEntry):
            self._newReleaseFlag = True
        #
        self.__reObsoleteFlag = False
        if ('status_code' in dataDict) and dataDict['status_code'] == 'OBS' and (not self._newReleaseFlag):
            self.__reObsoleteFlag = True
        #
        em_release_date = ''
        if ('date_of_EM_release' in dataDict) and dataDict['date_of_EM_release'] and ('status_code_em' in dataDict) and \
           (dataDict['status_code_em'] == 'REL' or dataDict['status_code_em'] == 'OBS'):
            em_release_date = str(dataDict['date_of_EM_release']).replace('00:00:00', '').strip()
        #
        self.__newReleaseEmFlag = False
        if (not em_release_date) or em_release_date == self._rel_date:
            self.__newReleaseEmFlag = True
        #
        release_date = ''
        if ('pdb_id' in dataDict) and dataDict['pdb_id']:
            release_date = model_release_date
        else:
            release_date = em_release_date
        #
        self.__reObsoleteEmFlag = False
        if ('status_code_em' in dataDict) and dataDict['status_code_em'] == 'OBS' and (not self.__newReleaseEmFlag):
            self.__reObsoleteEmFlag = True
        #
        myD = {}
        if not requestFlag:
            myD['warning_comment_start'] = '<!--'
            myD['warning_comment_end'] = '-->'
            myD['warning_message'] = ''
            if ('warning_message' in dataDict) and dataDict['warning_message']:
                myD['warning_comment_start'] = ''
                myD['warning_comment_end'] = ''
                myD['warning_message'] = dataDict['warning_message']
            #
        #
        myD['status_color'] = '#000000'
        self._skipReleaseOptionFlag = False
        color_status_code = ''
        if ('status_code' in dataDict) and dataDict['status_code']:
            color_status_code = dataDict['status_code']
            if (color_status_code == 'WDRN') and isEmEntry:
                color_status_code = dataDict['status_code_em']
            #
        elif ('status_code_em' in dataDict) and dataDict['status_code_em']:
            color_status_code = dataDict['status_code_em']
        #
        if (
            color_status_code == 'PROC'
            or color_status_code == 'WAIT'
            or color_status_code == 'AUCO'
            or color_status_code == 'REPL'
            or color_status_code == 'POLC'
            or color_status_code == 'WDRN'
        ) and requestFlag:
            self._skipReleaseOptionFlag = True
            myD['status_color'] = '#FF0000'
        #
        if ('post_rel_recvd_coord' in dataDict) and (dataDict['post_rel_recvd_coord'].upper() == "Y"):
            myD['status_color'] = '#FF0000'
        #
        hasPickleFlag, selectedData = self.__processEntryPickleFile(dataDict['structure_id'])
        for item in items:
            if item == 'annotator':
                myD[item] = str(self._reqObj.getValue('annotator'))
            elif item == 'entry_header':
                myD[item] = self.__getEntryHeaderTemplate(hasPickleFlag, dataDict['structure_id'])
            elif item == 'stop_sign':
                myD[item] = self.__getStopSignIcon(dataDict)
                if myD[item]:
                    self._skipReleaseOptionFlag = True
                    if requestFlag:
                        myD['status_color'] = '#FF0000'
                    #
                #
            elif item == 'urlmethod':
                myD[item] = self.__getUrlMethod(dataDict)
            elif item == 'locklabel':
                myD[item] = self.__getCommunicationLockLabel(dataDict)
            elif item == 'major_issue':
                myD[item] = self.__getMajorIssue(dataDict)
            elif item == 'status_warning':
                myD[item] = self.__getStatusWarningIcon(dataDict)
            elif item == 'exp_data':
                myD[item] = self.__getExpStatus(dataDict)
            elif item == 'date_of_RCSB_release':
                myD[item] = release_date
            elif item == 'status_code' and statusFlag:
                myD[item] = color_status_code
            elif (item in dataDict) and dataDict[item]:
                myD[item] = dataDict[item]
            elif item == 'check_option':
                myD[item] = ''
            else:
                myD[item] = defaultValue
            #
        #
        return myD, selectedData

    def _initialCommunicationDict(self, dataDict):
        myD = {}
        myD['annotator'] = str(self._reqObj.getValue('annotator'))
        myD['structure_id'] = dataDict['structure_id']
        myD['urlmethod'] = self.__getUrlMethod(dataDict)
        myD['locklabel'] = self.__getCommunicationLockLabel(dataDict)
        myD['major_issue'] = self.__getMajorIssue(dataDict)
        return myD

    def _getReleaseOption(self, dataDict, selectedData, citationFlag):
        return ReleaseOption(dataDict, selectedData, citationFlag, self._newReleaseFlag, self.__reObsoleteFlag,
                             self.__newReleaseEmFlag, self.__reObsoleteEmFlag, self._rel_date)

    def _getRevisionInfo(self, structure_id, count, selectedData, cols, begin_comment, end_comment, style, display):  # pylint: disable=unused-argument
        return ''
        # myD = {}
        # myD['structure_id'] = structure_id
        # myD['count'] = str(count)
        # myD['cols'] = cols
        # myD['begin_comment'] = begin_comment
        # myD['end_comment'] = end_comment
        # myD['class'] = ''
        # myD['style'] = style
        # myD['display'] = display
        # myD['revdat'] = self.__processRevdatTemplate(structure_id, selectedData)
        # myD['revision_type'] = self.__processRevisionTypeTemplate(structure_id, selectedData)
        # return self._processTemplate('revision_history_tmplt.html', myD)

    def _getItemList(self, fn):
        """ Get Item List
        """
        tPath = self._reqObj.getValue("TemplatePath")
        fPath = os.path.join(tPath, fn)
        ifh = open(fPath, 'r')
        sIn = ifh.read()
        ifh.close()
        #
        tmp_list = sIn.split('\n')
        item_list = []
        for v in tmp_list:
            v = v.strip()
            if v:
                item_list.append(v)
            #
        #
        return item_list

    def __cleanupEmOnlyEntries(self):
        for cdir in self._resultList:
            if ('pdb_id' not in cdir) or (not cdir['pdb_id']):
                if 'status_code' in cdir:
                    del cdir['status_code']
                #
            #
        #

    def __processEntryPickleFile(self, structure_id):
        entryPickle = self._loadEntryPickle(structure_id)
        if not entryPickle:
            return False, {}
        #
        hasPickleFlag = True
        selectedData = self.__getSelectedDataFromEntryPickle(entryPickle)
        return hasPickleFlag, selectedData

    def __getEntryHeaderTemplate(self, hasPickleFlag, structure_id):
        if hasPickleFlag:
            return self._processTemplate('entry_header_tmplt.html', { 'sessionid' : self._sessionId, 'structure_id' : structure_id })
        #
        return structure_id

    def __getStopSignIcon(self, dataDict):
        expFileTypeList = [ [ 'recvd_struct_fact',     'structural factor', 'structure-factors',   'pdbx'   ],
                            [ 'recvd_nmr_constraints', 'NMR restraints',    'nmr-restraints',      'pdb-mr' ],
                            [ 'recvd_chemical_shifts', 'chemical shifts',   'nmr-chemical-shifts', 'pdbx'   ] ]
        #
        warning = ''
        for typeList in expFileTypeList:
            expFile = self._pI.getFilePath(dataSetId=dataDict['structure_id'], wfInstanceId=None, contentType=typeList[2],
                                           formatType=typeList[3], versionId='latest', partNumber='1')
            if expFile and os.access(expFile, os.F_OK):
                if (typeList[0] in dataDict) and (dataDict[typeList[0]] == 'Y' or dataDict[typeList[0]] == 'y'):
                    continue
                #
                if warning:
                    warning += '\\n'
                #
                warning += "Found " + typeList[1] + " file but \\\'_pdbx_database_status." + typeList[0] + "\\\' was not set to \\\'Y\\\'"
            else:
                if (typeList[0] in dataDict) and (dataDict[typeList[0]] == 'Y' or dataDict[typeList[0]] == 'y'):
                    if warning:
                        warning += '\\n'
                    #
                    warning += "Found \\\'_pdbx_database_status." + typeList[0] + "=" + dataDict[typeList[0]] \
                        + "\\\' but can not find " + typeList[1] + " file"
                #
            #
        #
        if not warning:
            return warning
        #
        myD = {}
        myD['icon'] = 'stop'
        myD['message'] = 'For entry ' + dataDict['structure_id'] + ':\\n' + warning
        return self._processTemplate('icon_tmplt.html', myD)

    def __getUrlMethod(self, dataDict):
        if ('exp_method' in dataDict) and dataDict['exp_method']:
            return u_quote(dataDict['exp_method'])
        #
        return ''

    def __getCommunicationLockLabel(self, dataDict):
        if ('status_code' not in dataDict) or ('locking' not in dataDict) or (str(dataDict['locking']).upper() == 'WFM') or \
           (str(dataDict['status_code']).upper() in ( 'DEP', 'OBS', 'REL', 'WDRN' )):
            return ''
        #
        return '&allowunlock=yes'

    def __getMajorIssue(self, dataDict):
        warning_message = ''
        if ('major_issue' in dataDict) and dataDict['major_issue'] == 'YES':
            warning_message = 'Major issue'
        #
        if ('notify' in dataDict) and dataDict['notify']:
            for mTuple in ( ( 'N', 'New message' ), ( 'T', 'Todo message'), ( '*', 'Note message' ), ( 'B', 'BMRB message' ) ):
                if dataDict['notify'].find(mTuple[0]) == -1:
                    continue
                #
                if warning_message:
                    warning_message += '\\n'
                #
                warning_message += mTuple[1]
            #
        #
        if not warning_message:
            return warning_message
        #
        return self._processTemplate('icon_tmplt.html', {'icon' : 'warning', 'message' : 'Entry ' + dataDict['structure_id'] + ' has:\\n' + warning_message})

    def __getStatusWarningIcon(self, dataDict):
        warning = ''
        if ('pdb_id' in dataDict) and dataDict['pdb_id']:
            if ('status_code' in dataDict) and dataDict['status_code'] and ('wf_status_code' in dataDict) and \
               dataDict['wf_status_code'] and str(dataDict['status_code']) != str(dataDict['wf_status_code']):
                warning = "Status code in da_internal database \\\'" + str(dataDict['status_code']) \
                    + "\\\' != status code WF database \\\'" + str(dataDict['wf_status_code']) + "\\\'"
            #
        #
        if ('status_code_em' in dataDict) and dataDict['status_code_em'] and ('wf_status_code_em' in dataDict) and \
           dataDict['wf_status_code_em'] and str(dataDict['status_code_em']) != str(dataDict['wf_status_code_em']):
            if warning:
                warning += '\\n'
            #
            warning += "EM status code in da_internal database \\\'" + str(dataDict['status_code_em']) \
                + "\\\' != EM status code WF database \\\'" + str(dataDict['wf_status_code_em']) + "\\\'"
        #
        if ('post_rel_recvd_coord' in dataDict) and (dataDict['post_rel_recvd_coord'].upper() == 'Y'):
            if warning:
                warning += '\\n'
            #
            warning += "Post release coordinate replacement"
        #
        if not warning:
            return warning
        #
        myD = {}
        myD['icon'] = 'warning'
        myD['message'] = 'For entry ' + dataDict['structure_id'] + ':\\n' + warning
        return self._processTemplate('icon_tmplt.html', myD)

    def __getExpStatus(self, dataDict):
        exp_list = [ [ 'recvd_struct_fact',     'status_code_sf', 'SF' ],
                     [ 'recvd_em_map',          'status_code_em', 'EM' ],
                     [ 'recvd_nmr_constraints', 'status_code_mr', 'MR' ],
                     [ 'recvd_chemical_shifts', 'status_code_cs', 'CS' ],
                     [ 'recvd_nmr_data',  'status_code_nmr_data', 'NMR DATA' ] ]
        #
        text = ''
        for t_list in exp_list:
            if not t_list[0] in dataDict:
                continue
            #
            if dataDict[t_list[0]] != 'Y' and dataDict[t_list[0]] != 'y':
                continue
            #
            if text:
                text += ' <br /> '
            #
            status = ''
            if t_list[1] in dataDict:
                status = dataDict[t_list[1]]
            #
            text += t_list[2] + ': ' + status
            #
        #
        if not text:
            text = '&nbsp;'
        #
        return text

    def __getSelectedDataFromEntryPickle(self, entryPickle):
        if ('history' not in entryPickle) or (not entryPickle['history']):
            return {}
        #
        pickleList = entryPickle['history']
        pickleList.reverse()
        for pickleData in pickleList:
            if ('option' not in pickleData) or (not pickleData['option']) or (pickleData['option'] == 'pull_release'):
                continue
            #
            selectedData = {}
            for item in ('approval_type', 'obsolete_ids', 'supersede_ids'):
                if (item in pickleData) and pickleData[item]:
                    selectedData[item] = pickleData[item]
                #
            #
            if ('revdat_tokens' in pickleData) and pickleData['revdat_tokens']:
                tokenList = pickleData['revdat_tokens'].split(',')
                for token in tokenList:
                    selectedData[token] = 'checked'
                #
            #
            if ('revision' in pickleData) and pickleData['revision']:
                for rDict in pickleData['revision']:
                    if ('revision_type' not in rDict) or (not rDict['revision_type']):
                        continue
                    #
                    selectedData[rDict['revision_type']] = 'checked'
                    if ('details' in rDict) and rDict['details']:
                        selectedData['detail ' + rDict['revision_type']] = rDict['details']
                    #
                #
            #
            _selectedText, selectedOptions = self._getReleaseOptionFromPickle(pickleData)
            if selectedOptions:
                selectedData['pre_select'] = selectedOptions
            #
            return selectedData
        #
        return {}

    # def __processRevdatTemplate(self, structure_id, selectedDict):
    #     text = '<tr>\n'
    #     count = 0
    #     for token in self.__revdatTokenList:
    #         if count == 9:
    #             text += '</tr>\n<tr>\n'
    #             count = 0
    #         #
    #         myD = {}
    #         myD['structure_id'] = structure_id
    #         myD['value'] = token
    #         myD['check_option'] = ''
    #         if (token in selectedDict) and selectedDict[token]:
    #             myD['check_option'] = selectedDict[token]
    #         #
    #         text += self._processTemplate('revdat_tmplt.html', myD)
    #         count += 1
    #     #
    #     text += '</tr>\n'
    #     return text

    # def __processRevisionTypeTemplate(self, structure_id, selectedDict):
    #     text = ''
    #     for value in self.__revisionTypeList:
    #         myD = {}
    #         myD['structure_id'] = structure_id
    #         myD['value'] = value
    #         myD['check_option'] = ''
    #         if (value in selectedDict) and selectedDict[value]:
    #             myD['check_option'] = selectedDict[value]
    #         #
    #         myD['detail_value'] = ''
    #         if (('detail ' + value) in selectedDict) and selectedDict['detail ' + value]:
    #             myD['detail_value'] = selectedDict['detail ' + value]
    #         #
    #         myD['type'] = value.replace(' ', '_')
    #         text += self._processTemplate('revision_type_tmplt.html', myD)
    #     #
    #     return text
