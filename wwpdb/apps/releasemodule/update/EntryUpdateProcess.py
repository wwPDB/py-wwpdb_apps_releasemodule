##
# File:  EntryUpdateProcess.py
# Date:  09-Oct-2016
# Updates:
##
"""
Class responsible for updating and/or releasing entries

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

import gzip
import os
import shutil
import sys

from wwpdb.apps.releasemodule.update.EmReleaseUtil import EmReleaseUtil
from wwpdb.apps.releasemodule.update.EntryUpdateBase import EntryUpdateBase
from wwpdb.apps.releasemodule.update.ReleaseUtil import ReleaseUtil
from wwpdb.apps.releasemodule.update.ReleaseDpUtil import ReleaseDpUtil
from wwpdb.apps.releasemodule.update.UpdateUtil_v2 import UpdateUtil


class EntryUpdateProcess(EntryUpdateBase):
    """ Class responsible for updating and/or releasing entries
    """
    def __init__(self, reqObj=None, entryDir=None, statusDB=None, verbose=False, log=sys.stderr):
        super(EntryUpdateProcess, self).__init__(reqObj=reqObj, entryDir=entryDir, statusDB=statusDB, verbose=verbose, log=log)
        #
        self.__startFiles = {}
        self.__newPdbReleaseFlag = False
        self.__newPdbObsoleteFlag = False
        self.__newEmReleaseFlag = False
        self.__newEmObsoleteFlag = False
        self.__updateFlag = False
        self.__releaseFlag = False
        self.__EmEntryFlag = False
        self.__GenEmXmlHeaderFlag = False
        self.__EmXmlHeaderOnlyFlag = False
        self.__releaseDirectory = {}
        self.__emUtil = None

    def run(self):
        self.__copyArchivalFilesToSession()
        if self._blockErrorFlag:
            self.__startFiles = {}
            self.__updateEntryIndexPickle()
            return
        else:
            self._dumpLocalPickle()
        #
        if self.__EmEntryFlag:
            self.__emUtil = EmReleaseUtil(reqObj=self._reqObj, entryDir=self._entryDir, verbose=self._verbose, log=self._lfh)
            self.__emUtil.getEmReleaseInfo(self.__EmXmlHeaderOnlyFlag)
            #
            if self.__GenEmXmlHeaderFlag:
                self.__emUtil.validateXml()
            #
        #
        if self.__updateFlag:
            updateEmInfoList = []
            if self.__emUtil:
                updateEmInfoList = self.__emUtil.getEmUpdatedInfoList()
            #
            updateUtil = UpdateUtil(reqObj=self._reqObj, entryDir=self._entryDir, verbose=self._verbose, log=self._lfh)
            updateUtil.run(updateEmInfoList)
        #
        if self.__releaseFlag:
            if self._processing_site == "PDBE":
                releaseUtil = ReleaseDpUtil(reqObj=self._reqObj, entryDir=self._entryDir, verbose=self._verbose, log=self._lfh)
            else:
                releaseUtil = ReleaseUtil(reqObj=self._reqObj, entryDir=self._entryDir, verbose=self._verbose, log=self._lfh)
            #
            releaseUtil.run()
        #
        if self.__EmEntryFlag:
            self.__emUtil.run(self.__GenEmXmlHeaderFlag, self.__EmXmlHeaderOnlyFlag)
        #
        self._loadLocalPickle()
        #
        ok_flag = True
        if self._blockErrorFlag:
            ok_flag = False
        elif self._blockEmErrorFlag and self.__EmEntryFlag and self.__GenEmXmlHeaderFlag and (('pdb_id' not in self._entryDir) or (not self._entryDir['pdb_id'])):
            ok_flag = False
        #
        if ok_flag:
            if self.__updateFlag:
                self._pickleData['update'] = True
                self._updateDataBase()
                self._copyUpdatedFilesFromSessionToArchive()
            #
            if self.__releaseFlag or self.__EmEntryFlag:
                individualContent, sysErrorContent, _status = self._generateReturnContent(self._entryDir, self._entryMessageContent, self._fileStatus)
                returnContent = str(self._reqObj.getValue('task'))
                if sysErrorContent:
                    _msgType, msgText = self._getConcatMessageContent(sysErrorContent)
                    returnContent += '\n\nSystem related error:\n' + msgText
                #
                selectText, _selectMap = self._getReleaseOptionFromPickle(self._pickleData)
                returnContent += '\n\nRelease Option: ' + selectText + individualContent
                summaryfile = open(os.path.join(self._sessionPath, self._entryId + '.summary'), 'w')
                summaryfile.write(returnContent + '\n')
                summaryfile.close()
                #
                self.__copyFilesToForReleaseDirectory()
            #
            # Keep tracking for automatic sending new release reminding letter
            if (not self._blockErrorFlag) and self.__newPdbReleaseFlag and (not self.__isLegacyEntry()):
                self._pickleData['release'] = True
            #
            if (not self._blockErrorFlag) and self.__newPdbObsoleteFlag and (not self.__isLegacyEntry()):
                self._pickleData['obsolete'] = True
            #
            if (not self._blockErrorFlag) and (not self._blockEmErrorFlag) and self.__newEmReleaseFlag and (not self.__isLegacyEntry()):
                self._pickleData['em_release'] = True
            #
            if (not self._blockErrorFlag) and (not self._blockEmErrorFlag) and self.__newEmObsoleteFlag and (not self.__isLegacyEntry()):
                self._pickleData['em_obsolete'] = True
            #
        else:
            self.__startFiles = {}
        #
        self.__updateEntryIndexPickle()

    def __copyArchivalFilesToSession(self):
        self._setStartTime()
        self._initializePickleData()
        #
        for typeList in self._fileTypeList:
            if (not ('status_code' + typeList[1]) in self._entryDir) or (not self._entryDir['status_code' + typeList[1]]):
                continue
            #
            dataDict = {}
            self._pickleData['status_code' + typeList[1]] = self._entryDir['status_code' + typeList[1]]
            if (('directory' + typeList[1]) in self._entryDir) and self._entryDir['directory' + typeList[1]]:
                self._pickleData['directory' + typeList[1]] = self._entryDir['directory' + typeList[1]]
                dataDict['for_release_dir'] = self._entryDir['directory' + typeList[1]]
                if (self._entryDir['status_code' + typeList[1]] == 'REL') and (self._entryDir['directory' + typeList[1]] == 'added'):
                    if typeList[3] == 'model':
                        self.__newPdbReleaseFlag = True
                    elif typeList[3] == 'em-volume':
                        self.__newEmReleaseFlag = True
                    #
                elif (self._entryDir['status_code' + typeList[1]] == 'OBS') and (self._entryDir['directory' + typeList[1]] == 'obsolete'):
                    if (typeList[3] == 'model') and (self._entryDir['da_status_code' + typeList[1]] == 'REL'):
                        self.__newPdbObsoleteFlag = True
                    elif (typeList[3] == 'em-volume') and (self._entryDir['da_status_code' + typeList[1]] == 'REL'):
                        self.__newEmObsoleteFlag = True
                    #
                #
            #
            if typeList[3] == 'em-volume':
                self.__updateFlag = True
                if ('emdb_id' not in self._entryDir) or (not self._entryDir['emdb_id']):
                    self._insertEntryMessage(errType=typeList[5], errMessage='No EMDB ID found for EM entry ' + self._entryId + '.', uniqueFlag=True)
                    continue
                #
                if ('emdb_release' not in self._entryDir) or (not self._entryDir['emdb_release']):
                    continue
                #
                dataDict['release'] = True
                self._pickleData[typeList[3]] = dataDict
                self._insertFileStatus(typeList[5], True)
                self.__EmEntryFlag = True
                continue
            #
            targetPath = os.path.join(self._sessionPath, self._entryId + typeList[0])
            rtn_message, sourcePath = self._copyFileFromArchiveToSession(targetPath, typeList[3], typeList[4])
            if rtn_message != 'ok':
                self._processCopyFileError(typeList[5], rtn_message, typeList[2], sourcePath, targetPath, self._entryId)
                continue
            #
            self._entryDir['input_file' + typeList[1]] = self._entryId + typeList[0]
            self._entryDir['output_file' + typeList[1]] = self._entryId + typeList[0]
            #
            if self._entryDir['status_code' + typeList[1]] != 'CITATIONUpdate':
                self.__startFiles[typeList[3]] = sourcePath
            #
            dataDict['archive_file'] = sourcePath
            dataDict['session_file'] = targetPath
            #
            if (typeList[3] == 'model') and ('emdb_release' in self._entryDir) and self._entryDir['emdb_release']:
                self.__GenEmXmlHeaderFlag = True
            #
            if self._entryDir['status_code' + typeList[1]] == 'RELOAD':
                if 'revision' in self._entryDir:
                    self.__updateFlag = True
                #
                dataDict['release'] = True
                self.__releaseFlag = True
            elif self._entryDir['status_code' + typeList[1]] == 'CITATIONUpdate' or self._entryDir['status_code' + typeList[1]] == 'EMHEADERUpdate':
                self.__updateFlag = True
            else:
                dataDict['release'] = True
                self.__updateFlag = True
                self.__releaseFlag = True
            #
            self._pickleData[typeList[3]] = dataDict
            if typeList[3] == 'nmr-data-str':
                self._pickleData['nmr-data-nef'] = dataDict
            #
            self._insertFileStatus(typeList[5], True)
        #
        if ('emdb_id' in self._entryDir) and self._entryDir['emdb_id'] and ('emdb_release' in self._entryDir) and \
           self._entryDir['emdb_release'] and (not self.__EmEntryFlag) and ('status_code' in self._entryDir) and \
           (self._entryDir['status_code'] == 'REREL' or self._entryDir['status_code'] == 'OBS' or self._entryDir['status_code'] == 'EMHEADERUpdate'):
            self.__EmEntryFlag = True
            self.__EmXmlHeaderOnlyFlag = True
            self._pickleData['emdb_id'] = self._entryDir['emdb_id']
            self._pickleData['em-volume'] = {'release' : True}
            self._insertFileStatus('em', True)
        #

    def __copyFilesToForReleaseDirectory(self):
        pdbId = ''
        emdbId = ''
        for typeList in self._fileTypeList:
            if (not typeList[3] in self._pickleData) or (not self._pickleData[typeList[3]]) or \
               ('release' not in self._pickleData[typeList[3]]) or (not self._pickleData[typeList[3]]['release']) or \
               ('release_file' not in self._pickleData[typeList[3]]) or (not self._pickleData[typeList[3]]['release_file']):
                continue
            #
            if typeList[3] == 'em-volume':
                if ('emdb_id' in self._entryDir) and self._entryDir['emdb_id'] and ('emdb_release' in self._entryDir) and self._entryDir['emdb_release']:
                    emdbId = self._entryDir['emdb_id']
                #
            else:
                if ('pdb_id' in self._entryDir) and self._entryDir['pdb_id']:
                    pdbId = self._entryDir['pdb_id'].lower()
                #
            #
        #
        for typeList in self._fileTypeList:
            if (not typeList[3] in self._pickleData) or (not self._pickleData[typeList[3]]):
                continue
            #
            for releaseFileType in ( "release_file", "beta_release_file", "version_release_file" ):
                if (releaseFileType not in self._pickleData[typeList[3]]) or (not self._pickleData[typeList[3]][releaseFileType]):
                    continue
                #
                for fileList in self._pickleData[typeList[3]][releaseFileType]:
                    targetPath = os.path.join(self._sessionPath, fileList[3])
                    self.__make_directory(targetPath)
                    #
                    # Exclude EM sub-directory
                    spList = fileList[3].split("/")
                    topTargetPath = os.path.join(self._sessionPath, spList[0])
                    if fileList[2] not in self.__releaseDirectory:
                        self.__releaseDirectory[fileList[2]] =topTargetPath 
                    #
                    if (releaseFileType == "release_file") and (not os.access(os.path.join(topTargetPath, self._entryId + '.summary'), os.F_OK)):
                        self._copyFileUtil(os.path.join(self._sessionPath, self._entryId + '.summary'), os.path.join(topTargetPath, self._entryId + '.summary'))
                    #
                    if fileList[4]:
                        with open(fileList[0], 'rb') as f_in:
                            with gzip.open(os.path.join(targetPath, fileList[1] + '.gz'), 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                            #
                        #
                        if not os.access(os.path.join(targetPath, fileList[1] + '.gz'), os.F_OK):
                            self._insertEntryMessage(errType=typeList[5], errMessage="Copy " + fileList[0] + ".gz file to "
                                                     + os.path.join(targetPath, fileList[1] + '.gz') + " file failed for entry "
                                                     + self._entryId + ".", uniqueFlag=True)
                        else:
                            self._insertAction('Copied ' + fileList[0] + '.gz to ' + os.path.join(targetPath, fileList[1] + '.gz') + '.')
                        #
                    else:
                        rtn_message = self._copyFileUtil(fileList[0], os.path.join(targetPath, fileList[1]))
                        if rtn_message == 'ok':
                            self._insertAction('Copied ' + fileList[0] + ' to ' + os.path.join(targetPath, fileList[1]) + '.')
                        elif rtn_message == 'not found':
                            self._insertEntryMessage(errType=typeList[5], errMessage="Can't find " + os.path.join(targetPath, fileList[1]) + " file for entry "
                                                     + self._entryId + ".", uniqueFlag=True)
                        elif rtn_message == 'copy failed':
                            self._insertEntryMessage(errType=typeList[5], errMessage="Copy " + fileList[0] + " file to " + os.path.join(targetPath, fileList[1])
                                                     + " file failed for entry " + self._entryId + ".", uniqueFlag=True)
                        #
                    #
                #
            #
        #
        if self._blockErrorFlag:
            self._removeExistingForReleaseDirectories()
            for filePathInfo in self._outPutFiles:
                self._insertAction('remove ' + filePathInfo[1])
                self._removeFile(filePathInfo[1])
            #
            for relPath, dirPath in self.__releaseDirectory.items():
                self._removeDirectory(dirPath)
            #
        else:
            self._removeExistingForReleaseDirectories()
            for relPath, dirPath in self.__releaseDirectory.items():
                self._removeDirectory(relPath)
                self._insertAction('Copied ' + dirPath + ' to ' + relPath)
                shutil.copytree(dirPath, relPath)
                self._removeDirectory(dirPath)
            #
        #

    def __updateEntryIndexPickle(self):
        entryPickle = self._loadEntryPickle(self._entryId)
        # Keep tracking of first version files used for release
        if self.__startFiles:
            if 'start_files' not in entryPickle:
                entryPickle['start_files'] = self.__startFiles
            else:
                for fileType, fileName in self.__startFiles.items():
                    if fileType not in entryPickle['start_files']:
                        entryPickle['start_files'][fileType] = fileName
                    #
                #
            #
        #
        # update status for automatic sending new release reminding letter
        foundReleaseFlag = False
        for releaseType in ('release', 'em_release'):
            if (releaseType in entryPickle) and entryPickle[releaseType]:
                foundReleaseFlag = True
            #
        #
        for releaseType in ('release', 'em_release'):
            if foundReleaseFlag:
                # if already sent, remove automatic sending letter flag
                if (releaseType in self._pickleData) and self._pickleData[releaseType]:
                    del self._pickleData[releaseType]
                #
            elif (releaseType in self._pickleData) and self._pickleData[releaseType]:
                # add automatic sending letter flag to main entry pickle file
                entryPickle[releaseType] = self._pickleData[releaseType]
            #
        #
        self._finishAndDumpPickleFiles(entryPickle)

    def __isLegacyEntry(self):
        sList = self._entryId.split('_')
        idNum = int(sList[1])
        # if (idNum > 1000000001 and idNum < 1000200000) or (idNum > 1290000000 and idNum < 1300000001):
        if idNum > 1000000001 and idNum < 1000200000:
            return True
        #
        return False

    def __make_directory(self, dirPath):
        if not os.access(dirPath, os.F_OK):
            self._insertAction('mkdir ' + dirPath)
            os.makedirs(dirPath)
        #
