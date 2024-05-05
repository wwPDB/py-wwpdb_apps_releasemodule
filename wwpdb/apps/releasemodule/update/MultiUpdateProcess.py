##
# File:  MultiUpdateProcess.py
# Date:  09-Oct-2016
# Updates:
#    2023-11-22    CS     Add logging for calling MessagingIo.autoMsg, fix Python exception handling error in __updateStatusHistory()
##
"""
Class responsible for release/pull off entries

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

import multiprocessing
import os
import sys
import time
import traceback

from rcsb.utils.multiproc.MultiProcUtil import MultiProcUtil
from wwpdb.apps.msgmodule.io.MessagingIo import MessagingIo
from wwpdb.utils.db.DBLoadUtil import DBLoadUtil
from wwpdb.utils.db.StatusHistoryUtils import StatusHistoryUtils

from wwpdb.apps.releasemodule.update.EntryPullProcess import EntryPullProcess
from wwpdb.apps.releasemodule.update.EntryUpdateProcess import EntryUpdateProcess
from wwpdb.apps.releasemodule.update.UpdateBase import UpdateBase
from wwpdb.apps.releasemodule.utils.ContentDbApi import ContentDbApi
from wwpdb.apps.releasemodule.utils.StatusDbApi_v2 import StatusDbApi
from wwpdb.apps.releasemodule.utils.Utility import getCleanValue


class MultiUpdateProcess(UpdateBase):
    """ Class responsible for release/pull off entries
    """

    def __init__(self, reqObj=None, updateList=None, verbose=False, log=sys.stderr):
        super(MultiUpdateProcess, self).__init__(reqObj=reqObj, verbose=verbose, log=log)
        self.__updateList = updateList
        self.__task = str(self._reqObj.getValue('task'))
        self.__errorContent = ''
        self.__returnContent = ''
        if self._cI.get('USE_COMPUTE_CLUSTER'):
            self.__numProc = len(self.__updateList)
        else:
            self.__numProc = int(multiprocessing.cpu_count() / 2)
        #
        #
        self.__statusHUtils = None

    def getErrorContent(self):
        return self.__errorContent

    def getReturnContent(self):
        return self.__returnContent

    def run(self):
        """
        """
        self.__initialize()
        if self.__errorContent:
            return
        #
        mpu = MultiProcUtil(verbose=True)
        mpu.set(workerObj=self, workerMethod='runMultiProcess')
        mpu.setWorkingDir(self._sessionPath)
        _ok, _failList, _retLists, _diagList = mpu.runMulti(dataList=self.__updateList, numProc=self.__numProc,
                                                            numResults=1)
        #
        if self.__task == 'Entries in release pending':
            self.__getReturnContentForPullEntries()
        else:
            self.__finalize()
        #

    def autoRun(self):
        """
        """
        for entryData in self.__updateList:
            idMap = {}
            for id_type in ('pdb_id', 'bmrb_id', 'emdb_id', 'comb_ids'):
                if (id_type in entryData) and entryData[id_type]:
                    idMap[id_type] = entryData[id_type]
                #
            #
            entryPickleFile = self._getEntryPickleFileName(entryData['entry'])
            if not os.access(entryPickleFile, os.F_OK):
                self._dumpPickle(entryPickleFile, {'id': idMap})
            #
        #
        mpu = MultiProcUtil(verbose=True)
        mpu.set(workerObj=self, workerMethod='runMultiProcess')
        mpu.setWorkingDir(self._sessionPath)
        _ok, _failList, _retLists, _diagList = mpu.runMulti(dataList=self.__updateList, numProc=self.__numProc,
                                                            numResults=1)
        #
        dbLoadFileList = []
        updatedEntryList = []
        for entryData in self.__updateList:
            pickleData = self._loadLocalEntryPickle(entryData['entry'])
            #
            _entryContent, _entrySysError, status = self._generateReturnContent(entryData, pickleData['messages'],
                                                                                pickleData['file_status'])
            if status != 'OK':
                continue
            #
            if ('model' in pickleData) and pickleData['model'] and ('session_file' in pickleData['model']) and \
                    pickleData['model']['session_file'] and os.access(pickleData['model']['session_file'], os.F_OK) and \
                    ('update' in pickleData) and pickleData['update']:
                dbLoadFileList.append(pickleData['model']['session_file'])
            #
            info = []
            for item in ('entry', 'annotator', 'comb_ids'):
                if (item in entryData) and entryData[item]:
                    info.append(entryData[item])
                else:
                    info.append(' ')
                #
            #
            updatedEntryList.append(info)
        #
        self.__loadContentDataBase(dbLoadFileList)
        #
        return updatedEntryList

    def runMultiProcess(self, dataList, procName, optionsD, workingDir):  # pylint: disable=unused-argument
        """
        """
        statusDbUtil = StatusDbApi(siteId=self._siteId, verbose=self._verbose, log=self._lfh)
        rList = []
        for entryData in dataList:
            if self.__task == 'Entries in release pending':
                pulloffProcess = EntryPullProcess(reqObj=self._reqObj, entryDir=entryData, statusDB=statusDbUtil,
                                                  verbose=self._verbose, log=self._lfh)
                pulloffProcess.run()
            else:
                updateProcess = EntryUpdateProcess(reqObj=self._reqObj, entryDir=entryData, statusDB=statusDbUtil,
                                                   verbose=self._verbose, log=self._lfh)
                updateProcess.run()
            #
            rList.append(entryData['entry'])
        #
        return rList, rList, []

    def __initialize(self):
        """
        """
        if not self.__updateList:
            self.__errorContent += 'No update list defined\n'
            return
        #
        entryIdList = []
        pullEntryIdList = []
        dbLoadFileList = []
        annoIndexPickle = self._loadAnnotatorPickle(self._getLoginAnnotator())
        entryDirs = {}
        if ('entryDir' in annoIndexPickle) and annoIndexPickle['entryDir']:
            entryDirs = annoIndexPickle['entryDir']
        #
        eventLists = []
        if ('eventList' in annoIndexPickle) and annoIndexPickle['eventList']:
            eventLists = annoIndexPickle['eventList']
        #
        for entryData in self.__updateList:
            entryData['annotator'] = str(self._reqObj.getValue('annotator'))
            entryData['option'] = str(self._reqObj.getValue('option'))
            idMap = {}
            for id_type in ('pdb_id', 'bmrb_id', 'emdb_id', 'comb_ids'):
                if (id_type in entryData) and entryData[id_type]:
                    idMap[id_type] = entryData[id_type]
                #
            #
            entryPickleFile = self._getEntryPickleFileName(entryData['entry'])
            if not os.access(entryPickleFile, os.F_OK):
                self._dumpPickle(entryPickleFile, {'id': idMap})
            #
            if self.__task == 'Entries in release pending':
                entryPickle = self._loadEntryPickle(entryData['entry'])
                if entryPickle and ('start_files' in entryPickle) and entryPickle['start_files'] and \
                        ('model' in entryPickle['start_files']) and entryPickle['start_files']['model']:
                    pullEntryIdList.append(entryData['entry'])
                    dbLoadFileList.append(entryPickle['start_files']['model'])
                #
            #
            idMap['dep_id'] = entryData['entry']
            entryDirs[entryData['entry']] = idMap
            #
            entryIdList.append(entryData['entry'])
        #
        eventLists.append({'time': time.time(), 'task': self.__task, 'entry_ids': entryIdList})
        annoIndexPickle['entryDir'] = entryDirs
        annoIndexPickle['eventList'] = eventLists
        self._dumpAnnotatorPickle(annoIndexPickle)
        self.__loadContentDataBase(dbLoadFileList)
        self.__updatePullbackEntryStatus(pullEntryIdList)

    def __getReturnContentForPullEntries(self):
        self.__returnContent = "Task: " + self.__task
        for entryData in self.__updateList:
            self.__returnContent += '\n\nEntry ' + entryData['entry']
            if ('comb_ids' in entryData) and entryData['comb_ids']:
                self.__returnContent += ' (' + entryData['comb_ids'] + ')'
            elif ('pdb_id' in entryData) and entryData['pdb_id']:
                self.__returnContent += ' (' + entryData['pdb_id'] + ')'
            #
            self.__returnContent += ': '
            #
            pickleData = self._loadLocalEntryPickle(entryData['entry'])
            entryContent, _entrySysError, _status = self._generateReturnContent({}, pickleData['messages'],
                                                                                pickleData['file_status'])
            self.__returnContent += entryContent
        #

    def __finalize(self):
        """
        """
        emdObsList = []
        pdbObsList = []
        emdList = []
        pdbList = []
        dbLoadFileList = []
        allSysErrors = []
        allContents = ''
        for entryData in self.__updateList:
            pickleData = self._loadLocalEntryPickle(entryData['entry'])
            #
            if ('status_code' in entryData) and entryData['status_code'] == 'REL' and ('release' in pickleData) and \
                    pickleData['release']:
                self.__updateStatusHistory(entryData['entry'], entryData['status_code'], entryData['annotator'])
            #
            if ('em_obsolete' in pickleData) and pickleData['em_obsolete']:
                emdObsList.append(entryData['entry'])
            elif ('obsolete' in pickleData) and pickleData['obsolete']:
                pdbObsList.append(entryData['entry'])
            elif ('em_release' in pickleData) and pickleData['em_release']:
                emdList.append(entryData['entry'])
            elif ('release' in pickleData) and pickleData['release']:
                pdbList.append(entryData['entry'])
            #
            if ('model' in pickleData) and pickleData['model'] and ('session_file' in pickleData['model']) and \
                    pickleData['model']['session_file'] and os.access(pickleData['model']['session_file'], os.F_OK) and \
                    ('update' in pickleData) and pickleData['update']:
                dbLoadFileList.append(pickleData['model']['session_file'])
            #
            allContents += '\n\nEntry ' + entryData['entry']
            if 'comb_ids' in entryData:
                allContents += ' ' + entryData['comb_ids']
            elif 'pdb_id' in entryData:
                allContents += ' ' + entryData['pdb_id']
            #
            allContents += ': '
            entryContent, entrySysError, status = self._generateReturnContent(entryData, pickleData['messages'],
                                                                              pickleData['file_status'])
            if status == 'OK':
                allContents += '<span style="color:green">OK</span>'
            elif status == 'EM-BLOCKED':
                allContents += '<span style="color:green">PDB OK</span> / <span style="color:red">EM BLOCKED</span>'
            elif status == 'BLOCKED':
                allContents += '<span style="color:red">BLOCKED</span>'
            #
            selectText, _selectMap = self._getReleaseOptionFromPickle(pickleData)
            allContents += '\n\nRelease Option: ' + selectText + entryContent
            for error in entrySysError:
                if error not in allSysErrors:
                    allSysErrors.append(error)
                #
            #
        #
        if emdObsList or pdbObsList or emdList or pdbList:
            msgOption = 'release-nopubl'
            if str(self._reqObj.getValue('option')) == 'citation_update':
                msgOption = 'release-publ'
            #
            # CS 2023-11-22 start adding log for calling communication
            #
            msgIo = MessagingIo(self._reqObj, self._verbose, self._lfh)
            if emdObsList:
                self._lfh.write("+RelMod MultiUpdateProcess.__finalize() StartMessagingIo.autoMsg on emdObsList %s" % emdObsList)
                rtrnDict = msgIo.autoMsg(emdObsList, 'obsolete', p_isEmdbEntry=True)
                self._lfh.write("+RelMod MultiUpdateProcess.__finalize() EndMessagingIo.autoMsg with rtrnDict %s" % rtrnDict)
            #
            if pdbObsList:
                self._lfh.write("+RelMod MultiUpdateProcess.__finalize() StartMessagingIo.autoMsg on pdbObsList %s" % pdbObsList)
                rtrnDict = msgIo.autoMsg(pdbObsList, 'obsolete')
                self._lfh.write("+RelMod MultiUpdateProcess.__finalize() EndMessagingIo.autoMsg with rtrnDict %s" % rtrnDict)
            #
            if emdList:
                self._lfh.write("+RelMod MultiUpdateProcess.__finalize() StartMessagingIo.autoMsg with msgOption %s on emdList %s" % (msgOption, emdList))
                rtrnDict = msgIo.autoMsg(emdList, msgOption, p_isEmdbEntry=True)
                self._lfh.write("+RelMod MultiUpdateProcess.__finalize() EndMessagingIo.autoMsg with rtrnDict %s" % rtrnDict)
            #
            if pdbList:
                self._lfh.write("+RelMod MultiUpdateProcess.__finalize() StartMessagingIo.autoMsg with msgOption %s on pdbList %s" % (msgOption, pdbList))
                rtrnDict = msgIo.autoMsg(pdbList, msgOption)
                self._lfh.write("+RelMod MultiUpdateProcess.__finalize() EndMessagingIo.autoMsg with rtrnDict %s" % rtrnDict)
            #
            # CS 2023-11-22 end
            #
        #
        self.__loadContentDataBase(dbLoadFileList)
        #
        if (not allSysErrors) and (not allContents):
            self.__errorContent += 'No update list found\n'
        else:
            self.__returnContent = "Task: " + self.__task
            if allSysErrors:
                _msgType, msgText = self._getConcatMessageContent(allSysErrors)
                self.__returnContent += '\n\nSystem related error:\n' + msgText
            #
            if allContents:
                self.__returnContent += allContents
            #
        #

    def __loadContentDataBase(self, dbLoadFileList):
        if not dbLoadFileList:
            return
        #
        dbLoader = DBLoadUtil(reqObj=self._reqObj, verbose=self._verbose, log=self._lfh)
        dbLoader.doLoading(dbLoadFileList)

    def __updatePullbackEntryStatus(self, entryIdList):
        if not entryIdList:
            return
        #
        contentDB = ContentDbApi(siteId=self._siteId, verbose=self._verbose, log=self._lfh)
        statusMap = self.__getStatusMap(contentDB.getEntryInfo("', '".join(entryIdList)))
        emStatusMap = self.__getEmStatusMap(contentDB.getEMInfo("', '".join(entryIdList)))
        for entryData in self.__updateList:
            if (entryData['entry'] in statusMap) and statusMap[entryData['entry']]:
                has_status_code = False
                for item in ('status_code', 'post_rel_status', 'post_rel_recvd_coord', 'post_rel_recvd_coord_date'):
                    if (item in statusMap[entryData['entry']]) and statusMap[entryData['entry']][item]:
                        if item == 'status_code':
                            has_status_code = True
                        #
                        entryData[item] = statusMap[entryData['entry']][item]
                    #
                #
                if has_status_code:
                    self.__updateStatusHistory(entryData['entry'], entryData['status_code'], entryData['annotator'])
                #
            #
            if (entryData['entry'] in emStatusMap) and emStatusMap[entryData['entry']]:
                entryData['status_code_em'] = emStatusMap[entryData['entry']]
            #
        #

    def __getStatusMap(self, InfoList):
        status_map = {}
        if not InfoList:
            return status_map
        #
        for dataDict in InfoList:
            pdb_id = getCleanValue(dataDict, 'pdb_id')
            if pdb_id:
                myD = {}
                for item in ('status_code', 'post_rel_status', 'post_rel_recvd_coord', 'post_rel_recvd_coord_date'):
                    if (item in dataDict) and dataDict[item]:
                        myD[item] = str(dataDict[item])
                    #
                #
                if myD:
                    status_map[dataDict['structure_id']] = myD
                #
            #
        #
        return status_map

    def __getEmStatusMap(self, InfoList):
        status_map = {}
        if not InfoList:
            return status_map
        #
        for dataDict in InfoList:
            if ('status_code_em' in dataDict) and dataDict['status_code_em']:
                status_map[dataDict['structure_id']] = dataDict['status_code_em']
            #
        #
        return status_map

    def __updateStatusHistory(self, entryId, status_code, annotator):
        try:
            if not self.__statusHUtils:
                self.__statusHUtils = StatusHistoryUtils(reqObj=self._reqObj, verbose=self._verbose, log=self._lfh)
            #
            okShLoad = False
            okShUpdate = self.__statusHUtils.updateEntryStatusHistory(entryIdList=[entryId], statusCode=status_code,
                                                                      annotatorInitials=annotator,
                                                                      details="Update by release module")
            if okShUpdate:
                okShLoad = self.__statusHUtils.loadEntryStatusHistory(entryIdList=[entryId])
            #
            if (self._verbose):
                self._lfh.write("+MultiUpdateProcess.__updateStatusHistory() %s status history database load status %r\n" % (entryId, okShLoad))
            #
        except:  # noqa: E722 pylint: disable=bare-except
            if (self._verbose):
                self._lfh.write("+MultiUpdateProcess.__updateStatusHistory() status history update and database load failed with exception\n")
                traceback.print_exc(file=self._lfh)
            #
        #
