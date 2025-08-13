##
# File:  EntryUpdateBase.py
# Date:  09-Oct-2016
# Updates:
##
"""
Base Class responsible for releasing/pulling back a entry

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

import filecmp
import ntpath
import os
import shutil
import sys
import tarfile
import time
import traceback

from wwpdb.apps.releasemodule.update.NmrDataGenerator import NmrDataGenerator
from wwpdb.apps.releasemodule.update.UpdateBase import UpdateBase
from wwpdb.apps.wf_engine.engine.WFEapplications import killAllWF
from wwpdb.io.locator.PathInfo import PathInfo
from wwpdb.utils.dp.RcsbDpUtility import RcsbDpUtility


class EntryUpdateBase(UpdateBase):
    """ Base Class responsible for releasing/pulling back a entry
    """
    def __init__(self, reqObj=None, entryDir=None, statusDB=None, verbose=False, log=sys.stderr):
        super(EntryUpdateBase, self).__init__(reqObj=reqObj, verbose=verbose, log=log)
        self._entryDir = entryDir
        self.__statusDB = statusDB
        self._entryId = self._entryDir['entry']
        self._entryMessageContent = {}
        self._fileStatus = {}
        self._blockErrorFlag = False
        self._blockEmErrorFlag = False
        self._EMEntryFlag = False
        self._pickleData = {}
        self._actionList = []
        self._outPutFiles = []
        self.__pI = PathInfo(siteId=self._siteId, sessionPath=self._sessionPath, verbose=False, log=self._lfh)
        self.__checkEMEntry()
        #
        self._processing_site = self._cI.get("SITE_NAME").upper()
        #
        # key: contentType
        # val[0]: for_release_dir value
        # val[1]: fullReleaseDirPath
        # val[2]: fullReleaseBetaDirPath
        # val[3]: fullReleaseVersionDirPath
        self._forReleaseDirPathMap = {}
        self._errorKeyWordList = []
        self._versionFileNameConversionMap = { ".cif": ("xyz", ".cif"), ".cif.xml": ("xyz", ".xml"), ".cif.xml-noatom": ("xyz-no-atom", ".xml"), \
                                               ".cif.xml-extatom": ("xyz-ext-atom", ".xml") }
        #
        # Added for DAOTHER-2996
        # For map only entry, pdb_id is not set, we will create an error message that will never match
        self.__ignoreCifError1 = '++ERROR - In block "' + self._entryDir.get('pdb_id', 'XXXX').upper() \
            + '", parent category "entity_poly_seq", of category "atom_site", is missing.'
        self.__ignoreCifError2 = '++ERROR - In block "' + self._entryDir.get('pdb_id', 'XXXX').upper() \
            + '", parent category "pdbx_poly_seq_scheme", of category "atom_site", is missing.'
        #

    def _setStartTime(self):
        self._pickleData['start_time'] = time.time()

    def _initializePickleData(self):
        for item in ('annotator', 'option', 'task'):
            self._pickleData[item] = str(self._reqObj.getValue(item))
        #
        for item in ('approval_type', 'revdat_tokens', 'obsolete_ids', 'supersede_ids', 'revision'):
            if (item in self._entryDir) and self._entryDir[item]:
                self._pickleData[item] = self._entryDir[item]
            #
        #

    def _GetAndRunCmd(self, errType, programPath, programName, inputFile, outputFile, logFile, clogFile, extraOptions, messageType='error'):
        cmd = self._getCmd(programPath + '/' + programName, inputFile, outputFile, logFile, clogFile, extraOptions)
        self._insertAction(cmd)
        self._runCmd(cmd)
        if logFile:
            self._processLogError(errType, '', os.path.join(self._sessionPath, logFile), messageType=messageType)
        #
        if clogFile:
            self._processLogError(errType, programName, os.path.join(self._sessionPath, clogFile), messageType=messageType)
        #

    def _dpUtilityApi(self, operator="", inputFileName="", outputFileNameTupList=None, option="", id_value="", id_name="pdb_id"):
        """
        """
        if outputFileNameTupList is None:
            outputFileNameTupList = []

        if (not operator) or (not inputFileName) or (not outputFileNameTupList):
            return
        #
        self._insertAction("Run RcsbDpUtility.op('" + operator + "') with input file: " + inputFileName + ".")
        outpuList = []
        for outputFileNameTup in outputFileNameTupList:
            outputFilePath = os.path.join(self._sessionPath, outputFileNameTup[0])
            outpuList.append(outputFilePath)
            #
            if not outputFileNameTup[1]:
                continue
            #
            if os.access(outputFilePath, os.F_OK):
                os.remove(outputFilePath)
            #
        #
        try:
            dp = RcsbDpUtility(tmpPath=self._sessionPath, siteId=self._siteId, verbose=self._verbose, log=self._lfh)
            dp.imp(inputFileName)
            if option:
                dp.addInput(name="option", value=option)
            #
            if id_value:
                dp.addInput(name=id_name, value=id_value)
            #
            dp.op(operator)
            dp.expList(outpuList)
            dp.cleanup()
        except:  # noqa: E722 pylint: disable=bare-except
            self._insertEntryMessage(errType="sys", errMessage=traceback.format_exc(), messageType="error", uniqueFlag=True)
            #
            traceback.print_exc(file=self._lfh)
        #

    def _extractTarFile(self, tarFileName):
        tarFilePath = os.path.join(self._sessionPath, tarFileName)
        if not os.access(tarFilePath, os.F_OK):
            return
        #
        tf = tarfile.open(tarFilePath)
        tf.extractall(path=self._sessionPath)
        os.remove(tarFilePath)

    def _insertAction(self, action):
        self._actionList.append({'time' : time.time(), 'action' : action})

    def _insertEntryMessage(self, errType=None, errMessage=None, messageType='error', uniqueFlag=False):
        if (not errType) or (not errMessage):
            return
        #
        realType = errType
        if realType in self._fileTypeMap:
            realType = self._fileTypeMap[realType][1]
        #
        if messageType == 'error':
            # """
            # if errType == 'em':
            #     self._blockEmErrorFlag = True
            # else:
            #     self._blockErrorFlag = True
            #     self._blockEmErrorFlag = True
            # #
            # """
            self._blockErrorFlag = True
            self._blockEmErrorFlag = True
            self._insertFileStatus(realType, False)
            if realType == 'cif' or realType == 'xml' or realType == 'pdb':
                self._insertFileStatus('coor', False)
            #
        #
        if realType in self._entryMessageContent:
            if uniqueFlag:
                found = False
                for messageList in self._entryMessageContent[realType]:
                    if messageList[0] == errMessage:
                        found = True
                        break
                    #
                #
                if not found:
                    self._entryMessageContent[realType].append([errMessage, messageType])
                #
            else:
                self._entryMessageContent[realType].append([errMessage, messageType])
            #
        else:
            self._entryMessageContent[realType] = [[errMessage, messageType]]
        #

    def _insertFileStatus(self, fileType, statusCode):
        self._fileStatus[fileType] = statusCode

    def _insertArchivalFile(self, contentType, formatType, fileName, initialFlag):
        if (contentType not in self._pickleData) or (not self._pickleData[contentType]):
            return
        #
        if 'updated_archival_files' in self._pickleData[contentType]:
            self._pickleData[contentType]['updated_archival_files'][formatType] = fileName
        elif initialFlag:
            self._pickleData[contentType]['updated_archival_files'] = {formatType : fileName}
        #

    def _insertAuditRevisionInfo(self, contentType, major_revision, minor_revision):
        if (contentType not in self._pickleData) or (not self._pickleData[contentType]):
            return
        #
        if 'revision' in self._pickleData[contentType]:
            self._pickleData[contentType]['revision']['major_revision'] = major_revision
            self._pickleData[contentType]['revision']['minor_revision'] = minor_revision
        else:
            self._pickleData[contentType]['revision'] = {'major_revision' : major_revision, 'minor_revision' : minor_revision}
        #

    def _readErrorKeyWordList(self):
        errorKeyWordList = []
        #
        fPath = os.path.join(self._reqObj.getValue('TemplatePath'), 'cif_xml_error_list')
        sIn = self._readFile(fPath)
        #
        lineList = sIn.split('\n')
        for line in lineList:
            if not line:
                continue
            #
            if line[0] == '#':
                continue
            #
            keylist = line.split(';')
            errorKeyWordList.append(keylist)
        #
        return errorKeyWordList

    def _getPdbReleaseInfo(self):
        pdbId = ""
        if ("pdb_id" in self._entryDir) and self._entryDir['pdb_id']:
            pdbId = self._entryDir['pdb_id'].lower()
        #
        extendedPdbId = ""
        if len(pdbId) == 4:
            extendedPdbId = "pdb_0000" + pdbId
        elif (len(pdbId) == 12) and pdbId.startswith("pdb_"):
            extendedPdbId = pdbId
        #
        forReleaseDirPathMap = {}
        contentTypeList = []
        for contentType in ( "model", "structure-factors", "nmr-chemical-shifts", "nmr-data-str", "nmr-restraints" ):
            if (not contentType in self._pickleData) or (not self._pickleData[contentType]):
                continue
            #
            contentTypeList.append(contentType)
            #
            for_release_dir = ""
            fullReleaseDirPath = ""
            fullReleaseBetaDirPath = ""
            fullReleaseVersionDirPath = ""
            if ("for_release_dir" in self._pickleData[contentType]) and self._pickleData[contentType]["for_release_dir"]:
                for_release_dir = self._pickleData[contentType]["for_release_dir"]
                if pdbId:
                    fullReleaseDirPath = os.path.join(self._topReleaseDir, for_release_dir, pdbId)
                #
                if extendedPdbId:
                    fullReleaseBetaDirPath = os.path.join(self._topReleaseBetaDir, for_release_dir, extendedPdbId)
                    fullReleaseVersionDirPath = os.path.join(self._topReleaseVersionDir, for_release_dir, extendedPdbId)
                #
            #
            forReleaseDirPathMap[contentType] = ( for_release_dir, fullReleaseDirPath, fullReleaseBetaDirPath, fullReleaseVersionDirPath )
        #
        return pdbId, extendedPdbId, forReleaseDirPathMap, contentTypeList

    def _getAuditRevisionInfo(self, contentType):
        major_revision = ''
        minor_revision = ''
        if (contentType not in self._pickleData) or (not self._pickleData[contentType]):
            return major_revision, minor_revision
        #
        if ('revision' in self._pickleData[contentType]) and self._pickleData[contentType]['revision'] and \
           ('major_revision' in self._pickleData[contentType]['revision']) and self._pickleData[contentType]['revision']['major_revision'] and \
           ('minor_revision' in self._pickleData[contentType]['revision']) and self._pickleData[contentType]['revision']['minor_revision']:
            major_revision = self._pickleData[contentType]['revision']['major_revision']
            minor_revision = self._pickleData[contentType]['revision']['minor_revision']
        #
        return major_revision, minor_revision

    def _releasingNefFile(self, pdbId, extendedPdbId):
        if not self._checkReleaseFlag('nmr-data-str'):
            return
        #
        internalStrFile = self._entryId + '_nmr-data-str_P1.str'
        internalNefFile = self._entryId + '_nmr-data-nef_P1.str'
        externalStrFile = pdbId + '_nmr-data.str'
        externalNefFile = pdbId + '_nmr-data.nef'
        betaStrFile = ""
        betaNefFile = ""
        if extendedPdbId:
            betaStrFile = extendedPdbId + '_nmr-data.str'
            betaNefFile = extendedPdbId + '_nmr-data.nef'
        #
        for fileName in (internalStrFile, internalNefFile, externalStrFile, externalNefFile, betaStrFile, betaNefFile):
            if fileName == "":
                continue
            #
            self._removeFile(os.path.join(self._sessionPath, fileName))
        #
        generator = NmrDataGenerator(siteId=self._siteId, workingDirPath=self._sessionPath, verbose=self._verbose, log=self._lfh)
        errMsg = generator.getNmrDataFiles(pdbId, self._pickleData['nmr-data-str']['session_file'], os.path.join(self._sessionPath, internalStrFile),
                                           os.path.join(self._sessionPath, internalNefFile))
        #
        for tupL in ( ( internalStrFile, '', 'nmr-data-str', ( ( pdbId, externalStrFile, 'release_file', 1, pdbId + ".release_file" ), \
                      ( extendedPdbId, betaStrFile, 'beta_release_file', 2, extendedPdbId + ".beta_release_file" ) ) ), \
                      ( internalNefFile, errMsg, 'nmr-data-nef', ( ( pdbId, externalNefFile, 'release_file', 1, pdbId + ".release_file" ), \
                      ( extendedPdbId, betaNefFile, 'beta_release_file', 2, extendedPdbId + ".beta_release_file" ) ) ) ):
            if not self._verifyGeneratingFile('nmr_data', tupL[0], errMsg=tupL[1]):
                continue
            #
            for subTupL in tupL[3]:
                if not subTupL[0]:
                    continue
                #
                self.__updateNefFileDataBlockName(subTupL[0], os.path.join(self._sessionPath, tupL[0]), os.path.join(self._sessionPath, subTupL[1]))
                self._insertReleseFile(subTupL[2], tupL[2], os.path.join(self._sessionPath, subTupL[1]), subTupL[1], \
                                       self._forReleaseDirPathMap["nmr-data-str"][subTupL[3]], subTupL[4], True)
                #
            #
        #

    def _insertReleseFile(self, releaseFileType, contentType, sourceFile, targetFile, entryDirectory, subDirectory, compressFlag):
        if (contentType not in self._pickleData) or (not self._pickleData[contentType]):
            return
        #
        if releaseFileType in self._pickleData[contentType]:
            self._pickleData[contentType][releaseFileType].append([sourceFile, targetFile, entryDirectory, subDirectory, compressFlag])
        else:
            self._pickleData[contentType][releaseFileType] = [[sourceFile, targetFile, entryDirectory, subDirectory, compressFlag]]
        #

    def _processCopyFileError(self, errType, returnType, fileType, sourceFile, targetFile, entryId):
        if returnType == 'not found':
            self._insertEntryMessage(errType=errType, errMessage="Can't find " + fileType + " file " + sourceFile + " for entry " + entryId)
        elif returnType == 'copy failed':
            self._insertEntryMessage(errType=errType, errMessage="Copy " + fileType + " file from " + sourceFile + " to " + targetFile
                                     + " for entry " + entryId + " failed.")
            #
        #

    def _dumpLocalPickle(self):
        self._pickleData['tasks'] = self._actionList
        self._pickleData['messages'] = self._entryMessageContent
        self._pickleData['file_status'] = self._fileStatus
        self._pickleData['block'] = self._blockErrorFlag
        self._pickleData['block_em'] = self._blockEmErrorFlag
        self._pickleData['output'] = self._outPutFiles
        self._dumpLocalEntryPickle(self._entryId, self._pickleData)

    def _loadLocalPickle(self):
        self._pickleData = self._loadLocalEntryPickle(self._entryId)
        if ('tasks' in self._pickleData) and self._pickleData['tasks']:
            self._actionList = self._pickleData['tasks']
        #
        if ('messages' in self._pickleData) and self._pickleData['messages']:
            self._entryMessageContent = self._pickleData['messages']
        #
        if ('file_status' in self._pickleData) and self._pickleData['file_status']:
            self._fileStatus = self._pickleData['file_status']
        #
        if ('block' in self._pickleData) and self._pickleData['block']:
            self._blockErrorFlag = self._pickleData['block']
        #
        if ('block_em' in self._pickleData) and self._pickleData['block_em']:
            self._blockEmErrorFlag = self._pickleData['block_em']
        #
        if ('output' in self._pickleData) and self._pickleData['output']:
            self._outPutFiles = self._pickleData['output']
        #

    def _finishAndDumpPickleFiles(self, entryPickle):
        self.__setFinishTime()
        self._dumpLocalPickle()
        #
        if 'history' in entryPickle:
            entryPickle['history'].append(self._pickleData)
        else:
            entryPickle['history'] = [self._pickleData]
        #
        self._dumpEntryPickle(self._entryId, entryPickle)

    def _findArchiveFileName(self, contentType, formatType, version, part):
        return self.__pI.getFilePath(dataSetId=self._entryId, wfInstanceId=None, contentType=contentType, formatType=formatType,
                                     fileSource='archive', versionId=version, partNumber=part)

    def _copyFileFromArchiveToSession(self, targetPath, contentType, formatType):
        latestArchiveFilePath = self._findArchiveFileName(contentType, formatType, 'latest', '1')
        rtn_message = self._copyFileUtil(latestArchiveFilePath, targetPath)
        if not latestArchiveFilePath:
            latestArchiveFilePath = 'not available'
        #
        if rtn_message == 'ok':
            self._insertAction('Copied ' + latestArchiveFilePath + ' to ' + targetPath + '.')
        #
        return rtn_message, latestArchiveFilePath

    def _updateDataBase(self):
        status_map = {}
        if ('status_code' in self._entryDir) and self._entryDir['status_code']:
            status = self._entryDir['status_code']
            if status == 'REREL':
                status_map['status_code'] = 'REL'
                status_map['post_rel_status'] = 'NULL'
                status_map['post_rel_recvd_coord'] = 'NULL'
                status_map['post_rel_recvd_coord_date'] = 'NULL'
            elif status != '' and status != 'RELOAD' and status != 'CITATIONUpdate' and status != 'EMHEADERUpdate':
                for item in ('status_code', 'post_rel_status', 'post_rel_recvd_coord', 'post_rel_recvd_coord_date'):
                    if (item in self._entryDir) and self._entryDir[item]:
                        status_map[item] = self._entryDir[item]
                    #
                #
            #
        #
        if (not self._blockEmErrorFlag) and ('status_code_em' in self._entryDir) and self._entryDir['status_code_em']:
            if self._entryDir['status_code_em'] == 'REREL':
                status_map['status_code_emdb'] = 'REL'
            else:
                status_map['status_code_emdb'] = self._entryDir['status_code_em']
            #
        #
        msgType = 'info'
        message = ''
        if status_map and self.__statusDB:
            message = "Update workflow DB status to " + ",".join(["'%s' = '%s'" % (k, v) for k, v in status_map.items()])
            returnVal = self.__statusDB.runUpdate(table='deposition', where={'dep_set_id' : self._entryId}, data=status_map)
            if returnVal:
                message += " successful."
            else:
                message += " failed."
                msgType = 'error'
            #
        #
        returnStatus = killAllWF(self._entryId, 'RelMod')
        if returnStatus.strip().upper() == 'OK':
            code = 'successful.'
        else:
            code = 'failed.'
            msgType = 'error'
        #
        if message:
            message += '\n'
        #
        message += 'Killing WF ' + code
        self._insertEntryMessage(errType='db', errMessage=message, messageType=msgType, uniqueFlag=True)

    def _removeExistingForReleaseDirectories(self):
        if ('pdb_id' in self._entryDir) and self._entryDir['pdb_id']:
            for entry_dir_id in ( self._entryDir['pdb_id'].lower(), 'pdb_0000' + self._entryDir['pdb_id'].lower() ):
                for subdirectory in ('added', 'modified', 'obsolete', 'reloaded'):
                    self._removeDirectory(os.path.join(self._topReleaseDir, subdirectory, entry_dir_id))
                    self._removeDirectory(os.path.join(self._topReleaseBetaDir, subdirectory, entry_dir_id))
                    self._removeDirectory(os.path.join(self._topReleaseVersionDir, subdirectory, entry_dir_id))
                #
            #
        #
        # May need specific instruction for removal emd entry
        #
        if ('emdb_id' in self._entryDir) and self._entryDir['emdb_id']:
            self._removeDirectory(os.path.join(self._topReleaseDir, 'emd', self._entryDir['emdb_id']))
        #

    def _copyUpdatedFilesFromSessionToArchive(self):
        """ Update data archive based on updated files in session directory. Only five contentType ( 'model', 'structure-factors',
            'nmr-restraints', 'nmr-chemical-shifts', 'nmr-data-str' ) files will be updated during release process
        """
        for contentType in ('model', 'structure-factors', 'nmr-restraints', 'nmr-chemical-shifts', 'nmr-data-str'):
            if (contentType not in self._pickleData) or (not self._pickleData[contentType]) or \
               ('updated_archival_files' not in self._pickleData[contentType]) or (not self._pickleData[contentType]['updated_archival_files']):
                continue
            #
            for formatType, fileName in self._pickleData[contentType]['updated_archival_files'].items():
                fn = os.path.join(self._sessionPath, fileName)
                latestArchiveFilePath = self._findArchiveFileName(contentType, formatType, 'latest', '1')
                if latestArchiveFilePath and os.access(latestArchiveFilePath, os.F_OK):
                    if filecmp.cmp(fn, latestArchiveFilePath):
                        continue
                    #
                #
                nextArchiveFilePath = self._findArchiveFileName(contentType, formatType, 'next', '1')
                if (contentType == 'model') and (formatType == 'pdbx'):
                    skipVersionNumberUpdate = False
                    if ('status_code' in self._entryDir) and (self._entryDir['status_code'] == 'CITATIONUpdate'):
                        #      or (self._entryDir['status_code'] == 'EMHEADERUpdate')):
                        skipVersionNumberUpdate = True
                    #
                    if not skipVersionNumberUpdate:
                        _head, tail = ntpath.split(nextArchiveFilePath)
                        vList = tail.split(".V")
                        if len(vList) == 2:
                            if self._processing_site == "PDBE":
                                outputList = []
                                outputList.append((fileName, False))
                                outputList.append((self._entryId + "_addversion.log", True))
                                outputList.append((self._entryId + "_addversion.clog", True))
                                self._dpUtilityApi(operator="annot-add-version-info", inputFileName=fn, outputFileNameTupList=outputList,
                                                   option="-depid " + self._entryId + " -version " + vList[1])
                                #
                                self._processLogError("", "", os.path.join(self._sessionPath, self._entryId + "_addversion.log"))
                                self._processLogError("", "AddVersionInfo", os.path.join(self._sessionPath, self._entryId + "_addversion.clog"))
                            else:
                                self._GetAndRunCmd("", "${BINPATH}", "AddVersionInfo", fileName, fileName, self._entryId + "_addversion.log",
                                                   self._entryId + "_addversion.clog", " -depid " + self._entryId + " -version " + vList[1])
                            #
                        #
                    #
                #
                rtn_message = self._copyFileUtil(fn, nextArchiveFilePath)
                if rtn_message == 'ok':
                    self._insertAction('Copied ' + fn + ' to ' + nextArchiveFilePath + '.')
                    self._outPutFiles.append([self._fileTypeMap[contentType][0], nextArchiveFilePath])
                else:
                    self._processCopyFileError(self._fileTypeMap[contentType][1], rtn_message, self._fileTypeMap[contentType][0], fn,
                                               nextArchiveFilePath, self._entryId)
                #
                if ('release' in self._pickleData[contentType]) and self._pickleData[contentType]['release']:
                    if contentType != 'nmr-data-str':
                        latestMilestoneFilePath = self._findArchiveFileName(contentType + '-release', formatType, 'latest', '1')
                        if latestMilestoneFilePath and os.access(latestMilestoneFilePath, os.F_OK) and filecmp.cmp(fn, latestMilestoneFilePath):
                            continue
                        #
                        nextMilestoneFilePath = self._findArchiveFileName(contentType + '-release', formatType, 'next', '1')
                        rtn_message = self._copyFileUtil(fn, nextMilestoneFilePath)
                        if rtn_message == 'ok':
                            self._insertAction('Copied ' + fn + ' to ' + nextMilestoneFilePath + '.')
                            self._outPutFiles.append([self._fileTypeMap[contentType][0] + ' milestone', nextMilestoneFilePath])
                        else:
                            self._processCopyFileError(self._fileTypeMap[contentType][1], rtn_message, 'milestone ' + self._fileTypeMap[contentType][0],
                                                       fn, nextMilestoneFilePath, self._entryId)
                        #
                    else:
                        for nmrDataMilestoneType in (('_nmr-data-str_P1.str', 'nmr-data-str', 'nmr-star'), ('_nmr-data-nef_P1.str', 'nmr-data-nef', 'nmr-star')):
                            fn = os.path.join(self._sessionPath, self._entryId + nmrDataMilestoneType[0])
                            if not os.access(fn, os.F_OK):
                                continue
                            #
                            latestMilestoneFilePath = self._findArchiveFileName(nmrDataMilestoneType[1] + '-release', nmrDataMilestoneType[2], 'latest', '1')
                            if latestMilestoneFilePath and os.access(latestMilestoneFilePath, os.F_OK) and filecmp.cmp(fn, latestMilestoneFilePath):
                                continue
                            #
                            nextMilestoneFilePath = self._findArchiveFileName(nmrDataMilestoneType[1] + '-release', nmrDataMilestoneType[2], 'next', '1')
                            rtn_message = self._copyFileUtil(fn, nextMilestoneFilePath)
                            if rtn_message == 'ok':
                                self._insertAction('Copied ' + fn + ' to ' + nextMilestoneFilePath + '.')
                                self._outPutFiles.append(['NMR DATA milestone', nextMilestoneFilePath])
                            else:
                                self._processCopyFileError('nmr_data', rtn_message, 'milestone NMR DATA', fn, nextMilestoneFilePath, self._entryId)
                            #
                        #
                    #
                #
            #
        #

    def _copyFileUtil(self, sourcePath, targetPath):
        """
        """
        if (not sourcePath) or (not os.access(sourcePath, os.F_OK)):
            return 'not found'
        #
        shutil.copyfile(sourcePath, targetPath)
        if not os.access(targetPath, os.F_OK):
            return 'copy failed'
        elif not filecmp.cmp(sourcePath, targetPath):
            return 'copy failed'
        #
        return 'ok'

    def _removeDirectory(self, dirPath):
        if os.access(dirPath, os.F_OK):
            self._insertAction('remove ' + dirPath)
            shutil.rmtree(dirPath)
        #

    def _getLogMessage(self, program, logfile):
        if not os.access(logfile, os.F_OK):
            return 'not found', ''
        #
        statinfo = os.stat(logfile)
        if statinfo.st_size == 0:
            return 'empty', ''
        #
        f = open(logfile, 'r')
        data = f.read()
        f.close()
        #
        status = 'found'
        msg = ''
        dataDict = {}
        t_list = data.split('\n')
        for line in t_list:
            if (not line) or (line == self.__ignoreCifError1) or (line == self.__ignoreCifError2):
                continue
            #
            if line in dataDict:
                continue
            #
            dataDict[line] = 'y'
            #
            if line == 'Finished!':
                status = 'finish'
                continue
            #
            if msg:
                msg += '\n'
            #
            msg += line
        #
        if program and msg == 'Segmentation fault':
            msg = program + ': ' + msg
        #
        return status, msg

    def _processLogError(self, errType, program, logfile, messageType='error'):
        _status, error = self._getLogMessage(program, logfile)
        if error:
            if errType:
                self._insertEntryMessage(errType=errType, errMessage=error, messageType=messageType)
            #
            if program:
                self._insertEntryMessage(errType='sys', errMessage=error, messageType=messageType, uniqueFlag=True)
            #
        #

    def _checkReleaseFlag(self, contentType):
        if (contentType not in self._pickleData) or (not self._pickleData[contentType]) or \
           ('release' not in self._pickleData[contentType]) or (not self._pickleData[contentType]['release']) or \
           ('session_file' not in self._pickleData[contentType]) or (not self._pickleData[contentType]['session_file']):
            return False
        #
        if contentType not in self._forReleaseDirPathMap:
            self._insertEntryMessage(errType=contentType, errMessage="Can not find for_release* directories.", uniqueFlag=True)
            return False
        else:
            if self._forReleaseDirPathMap[contentType][0] == "":
                self._insertEntryMessage(errType=contentType, errMessage="added/modified/obsolete subdirectory was not defined.", uniqueFlag=True)
                return False
            elif self._forReleaseDirPathMap[contentType][2] == "" or self._forReleaseDirPathMap[contentType][3] == "":
                self._insertEntryMessage(errType=contentType, errMessage="Can not find the extended PDB ID.", uniqueFlag=True)
            #
        #
        return True

    def _verifyGeneratingFile(self, fileType, fileName, errMsg=""):
        filePath = os.path.join(self._sessionPath, fileName)
        if os.access(filePath, os.F_OK):
            return True
        #
        msg = 'Generating ' + fileName + ' failed.'
        if errMsg:
            msg = 'Generating ' + fileName + ' failed:\n' + errMsg
        #
        self._insertEntryMessage(errType=fileType, errMessage=msg, uniqueFlag=True)
        return False

    def _processCheckReoprt(self, errType, reportFile, sourceFile, missingFlag, warningOnlyFlag):
        status, msg = self._getLogMessage('', os.path.join(self._sessionPath, reportFile))
        if status == 'not found':
            if missingFlag:
                self._insertEntryMessage(errType=errType, errMessage='Checking releasing ' + errType + ' failed.', messageType='warning', uniqueFlag=True)
            #
            return
        #
        if not msg:
            return
        #
        msg_length = len(msg)
        msgList = msg.split('\n')
        msg = ''
        foudValue = False
        block_flag = False
        count = 0
        for line in msgList:
            if self.__containErrorKeyWords(line):
                block_flag = True
            #
            msg += line + '\n'
            count += 1
            if (count > 500) and (msg_length > 10000):
                break
            #
            strip_line = line.strip()
            if strip_line == sourceFile + ' validates':
                continue
            elif strip_line == '':
                continue
            elif strip_line.startswith('stdin:'):
                continue
            else:
                foudValue = True
            #
        #
        if not foudValue:
            return
        #
        msgType = 'warning'
        if block_flag:
            msgType = 'error'
        #
        if warningOnlyFlag:
            msgType = 'warning'
        #
        self._insertEntryMessage(errType=errType, errMessage=msg, messageType=msgType)

    def __checkEMEntry(self):
        if ('exp_method' in self._entryDir) and ((self._entryDir['exp_method'].find("ELECTRON CRYSTALLOGRAPHY") != -1)
                                                 or (self._entryDir['exp_method'].find("ELECTRON MICROSCOPY") != -1)
                                                 or (self._entryDir['exp_method'].find("ELECTRON TOMOGRAPHY") != -1)):
            self._EMEntryFlag = True
        #
    def __updateNefFileDataBlockName(self, pdb_id, inputFilePath, outputFilePath):
        with open(outputFilePath, "w") as f_out:
            with open(inputFilePath, "r") as f_in:
                data = f_in.read()
                dataList = data.split("\n")
                if not dataList[-1]:
                    dataList = dataList[:-1]
                # 
                first = True
                for line in dataList:
                    if line.strip().startswith("data_") and first:
                        first = False
                        f_out.write("data_nef_%s\n" % pdb_id)
                    else:
                        f_out.write(line + "\n")
                    #
                #
            #
        #

    def __setFinishTime(self):
        self._pickleData['finish_time'] = time.time()


    def __containErrorKeyWords(self, line):
        for keyWordList in self._errorKeyWordList:
            count = 0
            for keyWord in keyWordList:
                if line.find(keyWord) != -1:
                    count += 1
                #
            #
            if len(keyWordList) == count and line.find('The expected type is "symop"') == -1:
                return True
            #
        #
        return False
