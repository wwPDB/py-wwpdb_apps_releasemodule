##
# File:  DepictRequest.py
# Date:  28-Jun-2013
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

from wwpdb.apps.releasemodule.depict.DepictBase import DepictBase
from wwpdb.apps.releasemodule.utils.Utility import FindReleaseFiles


class DepictRequest(DepictBase):
    """ Class responsible for generating HTML depiction.

    """
    def __init__(self, reqObj=None, resultList=None, itemList=None, verbose=False, log=sys.stderr):
        super(DepictRequest, self).__init__(reqObj=reqObj, resultList=resultList, verbose=verbose, log=log)
        self.__items = itemList
        self.__atList = []
        #
        self.__formTemplate = str(self._reqObj.getValue('FormTemplate'))
        self.__rowTemplate = str(self._reqObj.getValue('RowTemplate'))
        self.__option = str(self._reqObj.getValue('option'))
        self.__cols = str(len(self.__items) - 1)
        #

    def DoRender(self, autoSelectionFlag=False):
        myD = self._initialOverAllDict()
        myD['table_rows'] = self.__getRows(autoSelectionFlag)
        myD['atlist'] = ' '.join(self.__atList)
        return self._processTemplate(self.__formTemplate, myD)

    def __getRows(self, autoSelectionFlag):
        text = ''
        count = 0
        for dataDict in self._resultList:
            if self.__option == 'status_update':
                dataDict['new_status_code'] = dataDict['author_release_status_code']
            elif self.__option == 'pull_release':
                if 'p_status' in dataDict:
                    dataDict['new_status_code'] = dataDict['p_status']
                elif ('author_release_status_code' in dataDict) and (dataDict['author_release_status_code'] == 'HPUB'):
                    dataDict['new_status_code'] = dataDict['author_release_status_code']
                else:
                    dataDict['new_status_code'] = 'HOLD'
                #
            #
            myD, selectedData = self._initialEntryDict(dataDict, self.__items, False, True, '&nbsp;')
            if autoSelectionFlag:
                myD['check_option'] = 'checked'
            #
            myD['comment_start'] = ''
            myD['comment_end'] = ''
            if self._skipReleaseOptionFlag:
                myD['comment_start'] = '<!--'
                myD['comment_end'] = '-->'
            #
            text += self._processTemplate(self.__rowTemplate, myD)
            if ('warning_message' in dataDict) and dataDict['warning_message']:
                text += '<tr><td style="text-align:left;" colspan="' + self.__cols + '"><font color="#FF0000">Warning: &nbsp; &nbsp; ' \
                    + dataDict['warning_message'] + ' </font></td></tr>\n'
            #
            if (self.__option != 'pull_release') and (not self._skipReleaseOptionFlag):
                text += '<tr><td style="text-align:left;" colspan="' + self.__cols + '">Release Option: &nbsp; &nbsp; ' \
                    + self._getReleaseOption(dataDict, selectedData, False) + '</td></tr>\n'
            #
            text += self.__processAuthorTitle(dataDict, count)
            if self.__option == 'pull_release':
                text += self.__getReleaseInfo(dataDict, count)
            elif (not self._newReleaseFlag) and ('pdb_id' in dataDict) and dataDict['pdb_id']:
                text += self._getRevisionInfo(dataDict['structure_id'], count, selectedData, self.__cols, '<!--', '-->', '', 'block')
            #
            # Add empty line
            #
            text += '<tr><td style="border-style:none" colspan="' + self.__cols + '">&nbsp; &nbsp; </td></tr>'
            #
            self.__atList.append('author_' + str(count))
            count += 1
        #
        return text

    def __processAuthorTitle(self, dataDict, count):
        myD = self._initialCommunicationDict(dataDict)
        myD['id'] = str(count)
        myD['cols'] = self.__cols
        #
        for item in ('author_list', 'title'):
            val = ''
            if item in dataDict:
                val = dataDict[item]
            #
            if val:
                myD[item] = val
            else:
                myD[item] = '&nbsp;'
        #
        return self._processTemplate('author_title_tmplt.html', myD)

    def __getReleaseInfo(self, dataDict, count):
        siteId = str(self._reqObj.getValue('WWPDB_SITE_ID'))
        FileInfo = FindReleaseFiles(siteId, dataDict)
        #
        myD = {}
        myD['id'] = str(count)
        myD['cols'] = self.__cols
        myD['summary'] = self.__getSummaryInfo(FileInfo)
        myD['rows'] = self.__getReleasedFilesLink(FileInfo)
        return self._processTemplate('request/release_info_tmplt.html', myD)

    def __getSummaryInfo(self, FileInfo):
        summary = ''
        if 'summary' in FileInfo:
            f = open(FileInfo['summary'], 'r')
            data = f.read()
            f.close()
            summary = data.strip()
            #
        #
        return summary

    def __getReleasedFilesLink(self, FileInfo):
        rows = ''
        if 'releasedFiles' not in FileInfo:
            return rows
        #
        num = len(FileInfo['releasedFiles'])
        num_per_line = 5
        lines = int(num / num_per_line)
        x = num % num_per_line
        m = lines
        if x == 0:
            m = lines - 1
        #
        for i in range(m + 1):
            n = num_per_line
            if i == lines:
                n = x
            #
            rows += '<tr>\n'
            for j in range(n):
                filepath = FileInfo['releasedFiles'][i * num_per_line + j]
                (_path, filename) = os.path.split(filepath)
                rows += '<td style="text-align:left;border-style:none">' \
                    + '<a href="/service/release/download_file_with_filepath?filepath=' \
                    + filepath + '" target="_blank"> ' + filename + ' </a></td>\n'
            #
            rows += '</tr>\n'
        #
        return rows
