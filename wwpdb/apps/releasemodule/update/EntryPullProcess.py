##
# File:  EntryPullProcess.py
# Date:  24-Oct-2016
# Updates:
##
"""
Class responsible for pulling off entries

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

import sys

from wwpdb.apps.releasemodule.update.EntryUpdateBase import EntryUpdateBase


class EntryPullProcess(EntryUpdateBase):
    """ Class responsible for pulling off entries
    """
    def __init__(self, reqObj=None, entryDir=None, statusDB=None, verbose=False, log=sys.stderr):
        super(EntryPullProcess, self).__init__(reqObj=reqObj, entryDir=entryDir, statusDB=statusDB, verbose=verbose, log=log)
        #

    def run(self):
        self._setStartTime()
        self._initializePickleData()
        entryPickle = self._loadEntryPickle(self._entryId)
        if entryPickle:
            if ('start_files' in entryPickle) and entryPickle['start_files']:
                self.__rollArchivalFileBacktoSartingVersion(entryPickle['start_files'])
            #
            for item in ('em_release', 'release', 'start_files'):
                if item in entryPickle:
                    del entryPickle[item]
                #
            #
        #
        self._insertEntryMessage(errType='all', errMessage='Entry has been pulled from release.', messageType='info', uniqueFlag=True)
        self._updateDataBase()
        self._removeExistingForReleaseDirectories()
        self._finishAndDumpPickleFiles(entryPickle)

    def __rollArchivalFileBacktoSartingVersion(self, startFilesMap):
        for typeList in self._fileTypeList:
            if not typeList[3] in startFilesMap:
                continue
            #
            archiveFilePath = self._findArchiveFileName(typeList[3], typeList[4], 'next', '1')
            rtn_message = self._copyFileUtil(startFilesMap[typeList[3]], archiveFilePath)
            if rtn_message == 'ok':
                self._insertAction('Copied ' + startFilesMap[typeList[3]] + ' to ' + archiveFilePath + '.')
                self._outPutFiles.append([typeList[2], archiveFilePath])
            else:
                self._processCopyFileError(typeList[5], rtn_message, typeList[2], startFilesMap[typeList[3]], archiveFilePath, self._entryId)
            #
        #
