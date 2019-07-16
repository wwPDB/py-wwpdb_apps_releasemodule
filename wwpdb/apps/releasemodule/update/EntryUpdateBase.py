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
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import filecmp, ntpath, os, shutil, sys, time

from wwpdb.apps.releasemodule.update.UpdateBase    import UpdateBase
from wwpdb.apps.releasemodule.utils.StatusDbApi_v2 import StatusDbApi
from wwpdb.apps.wf_engine.engine.WFEapplications   import killAllWF
from wwpdb.io.locator.PathInfo                     import PathInfo

class EntryUpdateBase(UpdateBase):
    """ Base Class responsible for releasing/pulling back a entry
    """
    def __init__(self, reqObj=None, entryDir=None, statusDB=None, verbose=False, log=sys.stderr):
        super(EntryUpdateBase, self).__init__(reqObj=reqObj, verbose=verbose, log=log)
        self._entryDir=entryDir
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
        self.__pI=PathInfo(siteId=self._siteId, sessionPath=self._sessionPath, verbose=False, log=self._lfh)
        self.__checkEMEntry()
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
        for item in ( 'annotator', 'option', 'task' ):
            self._pickleData[item] = str(self._reqObj.getValue(item))
        #
        for item in ( 'approval_type', 'revdat_tokens', 'obsolete_ids',  'supersede_ids', 'revision' ):
            if (item in self._entryDir) and self._entryDir[item]:
                self._pickleData[item] = self._entryDir[item]
            #
        #

    def _GetAndRunCmd(self, errType, programPath, programName, inputFile, outputFile, logFile, clogFile, extraOptions):
        cmd = self._getCmd(programPath + '/' + programName, inputFile, outputFile, logFile, clogFile, extraOptions)
        self._insertAction(cmd)
        self._runCmd(cmd)
        if logFile:
            self._processLogError(errType, '', os.path.join(self._sessionPath, logFile))
        #
        if clogFile:
            self._processLogError(errType, programName, os.path.join(self._sessionPath, clogFile))
        # 

    def _insertAction(self, action):
        self._actionList.append( { 'time' : time.time(), 'action' : action } )

    def _insertEntryMessage(self, errType=None, errMessage=None, messageType='error', uniqueFlag=False):
        if (not errType) or (not errMessage):
             return
        #
        realType = errType
        if realType in self._fileTypeMap:
            realType = self._fileTypeMap[realType][1]
        #
        if messageType == 'error':
            if errType == 'em':
                self._blockEmErrorFlag = True
            else:
                self._blockErrorFlag = True
                self._blockEmErrorFlag = True
            #
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
            self._entryMessageContent[realType] = [ [errMessage, messageType] ]
        #

    def _insertFileStatus(self, fileType, statusCode):
        self._fileStatus[fileType] = statusCode

    def _insertArchivalFile(self, contentType, formatType, fileName, initialFlag):
        if (not contentType in self._pickleData) or (not self._pickleData[contentType]):
            return
        #
        if 'updated_archival_files' in self._pickleData[contentType]:
            self._pickleData[contentType]['updated_archival_files'][formatType] = fileName
        elif initialFlag:
            self._pickleData[contentType]['updated_archival_files'] = { formatType : fileName }
        #

    def _insertAuditRevisionInfo(self, contentType, major_revision, minor_revision):
        if (not contentType in self._pickleData) or (not self._pickleData[contentType]):
            return
        #
        if 'revision' in self._pickleData[contentType]:
            self._pickleData[contentType]['revision']['major_revision'] = major_revision
            self._pickleData[contentType]['revision']['minor_revision'] = minor_revision
        else:
            self._pickleData[contentType]['revision'] = { 'major_revision' : major_revision, 'minor_revision' : minor_revision }
        #

    def _getAuditRevisionInfo(self, contentType):
        major_revision = ''
        minor_revision = ''
        if (not contentType in self._pickleData) or (not self._pickleData[contentType]):
            return major_revision,minor_revision
        #
        if ('revision' in self._pickleData[contentType]) and self._pickleData[contentType]['revision'] and \
           ('major_revision' in self._pickleData[contentType]['revision']) and self._pickleData[contentType]['revision']['major_revision'] and \
           ('minor_revision' in self._pickleData[contentType]['revision']) and self._pickleData[contentType]['revision']['minor_revision']:
            major_revision = self._pickleData[contentType]['revision']['major_revision']
            minor_revision = self._pickleData[contentType]['revision']['minor_revision']
        #
        return major_revision,minor_revision

    def _insertReleseFile(self, contentType, sourceFile, targetFile, subdirectory, compressFlag):
        if (not contentType in self._pickleData) or (not self._pickleData[contentType]):
            return
        #
        if 'release_file' in self._pickleData[contentType]:
            self._pickleData[contentType]['release_file'].append([ sourceFile, targetFile, subdirectory, compressFlag ])
        else:
            self._pickleData[contentType]['release_file'] = [ [ sourceFile, targetFile, subdirectory, compressFlag ] ]
        #

    def _processCopyFileError(self, errType, returnType, fileType, sourceFile, targetFile, entryId):
        if returnType == 'not found':
            self._insertEntryMessage(errType=errType, errMessage="Can't find " + fileType + " file " + sourceFile + " for entry " + entryId)
        elif returnType == 'copy failed':
            self._insertEntryMessage(errType=errType, errMessage="Copy " + fileType + " file from " + sourceFile + " to " + targetFile + \
                                     " for entry " + entryId + " failed.")
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
            entryPickle['history'] = [ self._pickleData ]
        #
        self._dumpEntryPickle(self._entryId, entryPickle)

    def _findArchiveFileName(self, contentType, formatType, version, part):
        return self.__pI.getFilePath(dataSetId=self._entryId, wfInstanceId=None, contentType=contentType, formatType=formatType, \
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
        return rtn_message,latestArchiveFilePath

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
                status_map['status_code'] = status
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
            message = "Update workflow DB status to " + ",".join([ "'%s' = '%s'" % (k, v) for k, v in status_map.iteritems()])
            returnVal = self.__statusDB.runUpdate(table='deposition', where={ 'dep_set_id' : self._entryId }, data=status_map)
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
            for subdirectory in ( 'added', 'modified', 'obsolete', 'reloaded' ):
                self._removeDirectory(os.path.join(self._topReleaseDir, subdirectory, self._entryDir['pdb_id'].lower()))
                self._removeDirectory(os.path.join(self._topReleaseBetaDir, subdirectory, self._entryDir['pdb_id'].lower()))
                self._removeDirectory(os.path.join(self._topReleaseVersionDir, subdirectory, 'pdb_0000' + self._entryDir['pdb_id'].lower()))
            #
        #
        # May need specific instruction for removal emd entry
        #
        if ('emdb_id' in self._entryDir) and self._entryDir['emdb_id']:
            self._removeDirectory(os.path.join(self._topReleaseDir, 'emd', self._entryDir['emdb_id']))
        #

    def _copyUpdatedFilesFromSessionToArchive(self):
        """ Update data archive based on updated files in session directory. Only four contentType ( 'model', 'structure-factors',
            'nmr-restraints', 'nmr-chemical-shifts' ) files will be updated during release process
        """
        for contentType in ( 'model', 'structure-factors', 'nmr-restraints', 'nmr-chemical-shifts'):
            if (not contentType in self._pickleData) or (not self._pickleData[contentType]) or \
               (not 'updated_archival_files' in self._pickleData[contentType]) or (not self._pickleData[contentType]['updated_archival_files']):
                continue
            #
            for formatType,fileName in self._pickleData[contentType]['updated_archival_files'].items():
                fn = os.path.join(self._sessionPath, fileName)
                latestArchiveFilePath = self._findArchiveFileName(contentType, formatType, 'latest', '1')
                if latestArchiveFilePath and os.access(latestArchiveFilePath, os.F_OK):
                    if filecmp.cmp(fn, latestArchiveFilePath):
                        continue
                    #
                #
                nextArchiveFilePath = self._findArchiveFileName(contentType, formatType, 'next', '1')
                if (contentType == 'model') and (formatType == 'pdbx'):
                    isCitationUpdateOnly = False
                    if ('status_code' in self._entryDir) and self._entryDir['status_code'] == 'CITATIONUpdate':
                        isCitationUpdateOnly = True
                    #
                    if not isCitationUpdateOnly:
                        head,tail = ntpath.split(nextArchiveFilePath)
                        vList = tail.split('.V')
                        if len(vList) == 2:
                            self._GetAndRunCmd('', '${BINPATH}', 'AddVersionInfo', fileName, fileName, self._entryId + '_addversion.log', \
                                               self._entryId + '_addversion.clog', ' -depid ' + self._entryId + ' -version ' + vList[1])
                        #
                    #
                #
                rtn_message = self._copyFileUtil(fn, nextArchiveFilePath)
                if rtn_message == 'ok':
                    self._insertAction('Copied ' + fn + ' to ' + nextArchiveFilePath + '.')
                    self._outPutFiles.append([ self._fileTypeMap[contentType][0], nextArchiveFilePath ])
                else:
                    self._processCopyFileError(self._fileTypeMap[contentType][1], rtn_message, self._fileTypeMap[contentType][0], fn, \
                                               nextArchiveFilePath, self._entryId)
                #
                if ('release' in self._pickleData[contentType]) and self._pickleData[contentType]['release']:
                    latestMilestoneFilePath = self._findArchiveFileName(contentType+'-release', formatType, 'latest', '1')
                    if latestMilestoneFilePath and os.access(latestMilestoneFilePath, os.F_OK) and filecmp.cmp(fn, latestMilestoneFilePath):
                        continue
                    #
                    nextMilestoneFilePath = self._findArchiveFileName(contentType+'-release', formatType, 'next', '1')
                    rtn_message = self._copyFileUtil(fn, nextMilestoneFilePath)
                    if rtn_message == 'ok':
                        self._insertAction('Copied ' + fn + ' to ' + nextMilestoneFilePath + '.')
                        self._outPutFiles.append([ self._fileTypeMap[contentType][0] + ' milestone', nextMilestoneFilePath])
                    else:
                        self._processCopyFileError(self._fileTypeMap[contentType][1], rtn_message, 'milestone ' + self._fileTypeMap[contentType][0], \
                                                   fn, nextMilestoneFilePath, self._entryId)
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
            return 'not found',''
        #
        statinfo = os.stat(logfile)
        if statinfo.st_size == 0:
            return 'empty',''
        #
        f = file(logfile, 'r')
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
        return status,msg

    def _processLogError(self, errType, program, logfile):
        status,error = self._getLogMessage(program, logfile)
        if error:
            if errType:
                self._insertEntryMessage(errType=errType, errMessage=error)
            #
            if program:
                self._insertEntryMessage(errType='sys', errMessage=error, uniqueFlag=True)
            #
        #

    def __checkEMEntry(self):
        if ('exp_method' in self._entryDir) and ((self._entryDir['exp_method'].find("ELECTRON CRYSTALLOGRAPHY") != -1) or \
          (self._entryDir['exp_method'].find("ELECTRON MICROSCOPY") != -1) or (self._entryDir['exp_method'].find("ELECTRON TOMOGRAPHY") != -1)):
            self._EMEntryFlag = True
        #

    def __setFinishTime(self):
        self._pickleData['finish_time'] = time.time()
