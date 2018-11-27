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
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import copy, operator, os, string, sys, traceback

from wwpdb.apps.releasemodule.utils.DBUtil       import DBUtil
from wwpdb.apps.releasemodule.utils.StatusDbApi  import StatusDbApi
from wwpdb.apps.releasemodule.utils.Utility      import getCombinationInfo
#

class InputFormParser(object):
    """ Class responsible for parsing submitted form
    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        self._verbose          = verbose
        self._lfh              = log
        self._reqObj           = reqObj
        self._errorContent     = ''
        self._entryList        = []
        self._entryRequestFlag = True
        #
        self.__siteId   = str(self. _reqObj.getValue("WWPDB_SITE_ID"))
        self._contentDB = DBUtil(siteId=self.__siteId, verbose=self._verbose, log=self._lfh)
        self._statusDB  = StatusDbApi(siteId=self.__siteId, verbose=self._verbose, log=self._lfh)
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
        message,return_list,return_map = self._statusDB.getEntryListFromIDs(entry_ids=entry_ids.upper())
        self.__processReturnResult(message, return_list, return_map, False)

    def _getIdListFromIdList(self, input_id_list, ignoreLockFlag):
        if not input_id_list:
            return
        #
        message,return_list,return_map = self._statusDB.getEntryListFromIDList(entry_ids=input_id_list)
        self.__processReturnResult(message, return_list, return_map, ignoreLockFlag)

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
 
    def __processReturnResult(self, message, return_list, return_map, ignoreLockFlag):
        if message:
            self._errorContent += message
        else:
            self._entryList = self.__processSelectedEntries(return_list, return_map, ignoreLockFlag)
        #

    def __processSelectedEntries(self, id_list, id_map, ignoreLockFlag):
        locked_id_list = []
        for depid in id_list:
            if self._entryRequestFlag and (not self.__isDEPLocked(depid, id_map)):
                if not ignoreLockFlag:
                    self._errorContent += 'Entry "' + depid + '" is unlocked.\n'
                #
                continue
            #   
            locked_id_list.append(depid)
        #
        if not locked_id_list:
            return []
        #
        return getCombinationInfo(self._contentDB.getEntryInfo(locked_id_list), id_map)

    def __isDEPLocked(self, depid, id_map):
        if not id_map.has_key(depid):
            return False
        #
        if id_map[depid].has_key('locking') and id_map[depid]['locking']:
            locking = id_map[depid]['locking'].upper()
            if locking.find('DEP') != -1:
                return True
            #
        #
        return False

    def __cleanString(self, val):
        val = val.replace(',', ' ')
        val = val.replace('\n', ' ')
        val = val.replace('\t', ' ')
        val = val.strip()
        return val
