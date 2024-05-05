##
# File:  InputFormParser.py
# Date:  07-Aug-2016
# Updates:
##
"""
Parse submitted form

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2016 wwPDB

This software is provided under a Creative Commons Attribution 3.0 Unported
License described at http://creativecommons.org/licenses/by/3.0/.

"""
__docformat__ = "restructuredtext en"
__author__ = "Zukang Feng"
__email__ = "zfeng@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.07"

import sys

from wwpdb.apps.releasemodule.utils.CombineDbApi import CombineDbApi
#


class InputFormParser(object):
    """ Class responsible for parsing submitted form
    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        self._verbose = verbose
        self._lfh = log
        self._reqObj = reqObj
        self._errorContent = ''
        self._entryList = []
        self._entryRequestFlag = True
        #
        self._sObj = self._reqObj.newSessionObj()
        self._sessionId = self._sObj.getId()
        self._sessionPath = self._sObj.getPath()

        self._siteId = str(self._reqObj.getValue("WWPDB_SITE_ID"))
        self._dbUtil = CombineDbApi(siteId=self._siteId, path=self._sessionPath, verbose=self._verbose, log=self._lfh)
        #

    def getErrorContent(self):
        return self._errorContent

    def getEntryList(self):
        return self._entryList

    def _getIdListFromIdSelection(self, messageFlag):
        entry_ids = self._getInputString('entry_ids', 'entry ID', messageFlag)
        if not entry_ids:
            return
        #
        message, return_list = self._dbUtil.getEntryInfoFromInputIDs(entry_ids.upper())
        self._processReturnResult(message, return_list, False)

#   def _getIdListFromIdList(self, input_id_list, ignoreLockFlag):
#       if not input_id_list:
#           return
#       #
#       self.__processReturnResult('', self._dbUtil.getEntryInfo(input_id_list), ignoreLockFlag)

    def _getInputString(self, keyword, message, messageFlag):
        input_str = str(self._reqObj.getValue(keyword)).strip()
        if not input_str:
            if messageFlag:
                self._errorContent += 'No ' + message + ' defined.\n'
            #
            return ''
        #
        input_str = self.__cleanString(input_str)
        if not input_str:
            self._errorContent += 'No ' + message + ' defined.\n'
            return ''
        #
        return input_str

    def _processReturnResult(self, message, return_list, ignoreLockFlag):
        if message:
            self._errorContent += message
        #
        if not return_list:
            return
        #
        for entry in return_list:
            if self._entryRequestFlag and (not self.__isDEPLocked(entry)):
                if not ignoreLockFlag:
                    self._errorContent += 'Entry "' + entry['structure_id'] + '" is unlocked.\n'
                #
                continue
            #
            self._entryList.append(entry)
        #

    def __isDEPLocked(self, entry):
        if ('locking' in entry) and entry['locking']:
            locking = entry['locking'].upper()
            if locking.find('DEP') != -1:
                return True
            #
        #
        return False

    def __cleanString(self, val):
        val = val.replace(',', ' ')
        val = val.replace('\n', ' ')
        val = val.replace('\r', ' ')
        val = val.replace('\t', ' ')
        val = val.strip()
        return val
