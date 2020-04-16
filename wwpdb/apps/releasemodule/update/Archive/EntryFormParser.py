##
# File:  EntryFormParser.py
# Date:  17-Jan-2014
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

from wwpdb.apps.releasemodule.update.InputFormParser import InputFormParser
#

class EntryFormParser(InputFormParser):
    """ Class responsible for parsing submitted form
    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        super(EntryFormParser, self).__init__(reqObj=reqObj, verbose=verbose, log=log)
        #
        if str(self._reqObj.getValue('task')) == 'Check Marked PubMed IDs':
            self._entryRequestFlag = False
        #
        self._getIdListFromIdSelection(False)
        if self._entryRequestFlag:
            self.__annotator = str(self._reqObj.getValue('annotator'))
            self.__getIdListFromStatusSelection()
            self.__getIdListFromAuthorSelection()
        #
        self.__checkErrorContent()

    def __getIdListFromStatusSelection(self):
        if self._entryList or self._errorContent:
            return
        #
        status_list = self._reqObj.getValueList('select_status')
        if not status_list:
            return
        #
        slist = ''
        for status in status_list:
            if slist:
                slist += ","
            #
            slist += "'" + status + "'"
        #
        entryListFromStatus = self._contentDB.getEntriesWithStatusList(self.__annotator, slist)
        #
        if not entryListFromStatus:
            self._errorContent += 'No entry found for status ' + ','.join(status_list) + '.\n'
            return
        #
        self._getIdListFromIdList(entryListFromStatus, True)
        if (not self._entryList) and (not self._errorContent):
            self._errorContent += 'No entry found for status ' + ','.join(status_list) + '.\n'
        #

    def __getIdListFromAuthorSelection(self):
        if self._entryList or self._errorContent:
            return
        #
        author = self._reqObj.getValue('author_name')
        if not author:
            return
        #
        entryListFromAuthor = self._contentDB.getEntriesWithAuthorName(self.__annotator, author)
        if not entryListFromAuthor:
            self._errorContent += 'No entry found for author "' + author  + '".\n'
            return
        #
        self._getIdListFromIdList(entryListFromAuthor, True)
        if (not self._entryList) and (not self._errorContent):
            self._errorContent += 'No entry found for author "' + author  + '".\n'
        #

    def __checkErrorContent(self):
        if self._entryList or self._errorContent:
            return
        #
        self._errorContent += 'No entry selected.\n'
