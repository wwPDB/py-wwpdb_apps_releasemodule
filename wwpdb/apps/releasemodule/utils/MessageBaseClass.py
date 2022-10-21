##
# File:  MessageBaseClass.py
# Date:  19-Nov-2016
# Updates:
##
"""
Base class for process entry messages

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

from wwpdb.apps.releasemodule.utils.ModuleBaseClass import ModuleBaseClass


class MessageBaseClass(ModuleBaseClass):
    """ Base Class responsible for process entry messages
    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        super(MessageBaseClass, self).__init__(reqObj=reqObj, verbose=verbose, log=log)
        #
        self.__coorTypeList = [['cif', 'PDBx CIF'], ['pdb', 'PDB'], ['xml', 'XML']]

    def _generateReturnContent(self, entryDir, entryMessageContent, fileStatus):
        returnContent = ''
        sysErrorContent = []
        if ('sys' in entryMessageContent) and entryMessageContent['sys']:
            sysErrorContent = entryMessageContent['sys']
        #
        entryStatus = 'OK'
        for errType in ('all', 'db'):
            if (errType in entryMessageContent) and entryMessageContent[errType]:
                msgType, msgText = self._getConcatMessageContent(entryMessageContent[errType])
                span_start = ''
                span_end = ''
                if msgType == 'error':
                    span_start = '<span style="color:red">'
                    span_end = '</span>'
                    entryStatus = 'BLOCKED'
                #
                returnContent += '\n\n' + span_start + msgText + span_end
            #
        #
        # hasPdbRelease = False
        for typeList in self._fileTypeList:
            if (not ('status_code' + typeList[1]) in entryDir) or (not entryDir['status_code' + typeList[1]]) or \
               (entryDir['status_code' + typeList[1]] == 'EMHEADERUpdate') or (typeList[5] == 'em'):
                continue
            #
            # hasPdbRelease = True
            break
        #
        for typeList in self._fileTypeList:
            legend = typeList[2]
            if (not ('status_code' + typeList[1]) in entryDir) or entryDir['status_code' + typeList[1]] == 'CITATIONUpdate':
                skip = True
                if (typeList[3] == 'em-volume') and ('emdb_release' in entryDir) and entryDir['emdb_release'] and ('status_code' in entryDir) and \
                   (entryDir['status_code'] == 'REREL' or entryDir['status_code'] == 'RELOAD' or entryDir['status_code'] == 'EMHEADERUpdate'):
                    legend = 'EM Header'
                    skip = False
                #
                if skip:
                    continue
                #
            #
            blockFlag, returnText = self.__getReturnContent(entryMessageContent, fileStatus, typeList[5])
            if blockFlag:
                # """
                # if (typeList[5] == 'em') and hasPdbRelease:
                #     if entryStatus == 'OK':
                #         entryStatus = 'EM-BLOCKED'
                #     #
                # else:
                #     entryStatus = 'BLOCKED'
                # #
                # """
                entryStatus = 'BLOCKED'
            #
            if typeList[5] == 'coor':
                if entryDir['status_code' + typeList[1]] == 'EMHEADERUpdate' and returnText == ' OK':
                    continue
                #
                for coorTypeList in self.__coorTypeList:
                    blockFlag, msg = self.__getReturnContent(entryMessageContent, fileStatus, coorTypeList[0])
                    if msg:
                        returnText += '\n' + coorTypeList[1] + ':' + msg
                        if blockFlag:
                            entryStatus = 'BLOCKED'
                        #
                    #
                #
            #
            if returnText:
                returnContent += '\n\n' + legend + ':' + returnText
            #
        #
        if ('MiscChecking' in entryMessageContent) and entryMessageContent['MiscChecking']:
            _messageType, messageText = self._getConcatMessageContent(entryMessageContent['MiscChecking'])
            returnContent += '\n\nMiscChecking report:\n\n' + messageText
        #
        if returnContent:
            return returnContent, sysErrorContent, entryStatus
        #
        return '', sysErrorContent, ''

    def _getConcatMessageContent(self, messageContent):
        """
        """
        messageType = ''
        messageText = ''
        for messageList in messageContent:
            if messageText:
                messageText += '\n'
            #
            messageText += messageList[0]
            if messageList[1] == 'error':
                messageType = messageList[1]
            elif messageList[1] == 'warning':
                if (not messageType) or (messageType == 'info'):
                    messageType = messageList[1]
            elif not messageType:
                messageType = messageList[1]
            #
        #
        return messageType, messageText

    def __getReturnContent(self, entryMessageContent, fileStatus, typeKey):
        blockFlag = False
        returnText = ''
        if (typeKey in entryMessageContent) and entryMessageContent[typeKey]:
            msgType, msgText = self._getConcatMessageContent(entryMessageContent[typeKey])
            span_start = ''
            span_end = ''
            blockMsg = ''
            if msgType == 'error':
                span_start = '<span style="color:red">'
                span_end = '</span>'
                blockFlag = True
                if typeKey == 'em':
                    blockMsg = ' ' + span_start + 'EM-BLOCKED' + span_end
                #
            #
            if (msgType == 'info') and (typeKey in fileStatus) and fileStatus[typeKey]:
                returnText = ' OK\n' + msgText
            else:
                returnText = blockMsg + '\n' + span_start + msgText + span_end
            #
        elif (typeKey in fileStatus) and fileStatus[typeKey]:
            returnText = ' OK'
        #
        return blockFlag, returnText
