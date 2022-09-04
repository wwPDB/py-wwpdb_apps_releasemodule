##
# File:  DepictReleaseInfo.py
# Date:  20-Nov-2016
# Updates:
##
"""
Create HTML depiction for generating entry message

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

from wwpdb.apps.releasemodule.utils.MessageBaseClass import MessageBaseClass


class DepictReleaseInfo(MessageBaseClass):
    """ Class responsible for generating entry message HTML depiction.

    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        super(DepictReleaseInfo, self).__init__(reqObj=reqObj, verbose=verbose, log=log)
        self.__annPickleData = self._loadAnnotatorPickle(self._getSelectedAnnotator())

    def DoRender(self):
        if (not self.__annPickleData) or ('entryDir' not in self.__annPickleData) or (not self.__annPickleData['entryDir']):
            return ''
        #
        entryList = []
        select = str(self._reqObj.getValue('select'))
        if select == 'all':
            entryList = list(self.__annPickleData['entryDir'].keys())
        elif select == 'last':
            if ('eventList' in self.__annPickleData) and self.__annPickleData['eventList'] and \
               ('entry_ids' in self.__annPickleData['eventList'][-1]) and self.__annPickleData['eventList'][-1]['entry_ids']:
                entryList = self.__annPickleData['eventList'][-1]['entry_ids']
            #
        #
        if not entryList:
            return ''
        #
        entryList.sort()
        #
        myD = {}
        myD['task'] = str(self._reqObj.getValue('task'))
        myD['annotator'] = self._getSelectedAnnotator()
        myD['info_text'] = self.__processEntryList(self.__annPickleData['entryDir'], entryList)
        if not myD['info_text']:
            return ''
        #
        return self._processTemplate('view/view_release_info_tmplt.html', myD)

    def __processEntryList(self, entryDirs, entryList):
        text = ''
        for entryId in entryList:
            entryPickle = self._loadEntryPickle(entryId)
            if (not entryPickle) or ('history' not in entryPickle) or (not entryPickle['history']):
                continue
            #
            pickleData = entryPickle['history'][-1]
            idData = {}
            if (entryId in entryDirs) and entryDirs[entryId]:
                idData = entryDirs[entryId]
            #
            text += '\n\n<b>Entry ' + entryId
            if 'comb_ids' in idData:
                text += ' ' + idData['comb_ids']
            elif 'pdb_id' in idData:
                text += ' ' + idData['pdb_id']
            #
            text += '</b>: '
            #
            entryContent, entrySysError, status = self._generateReturnContent(pickleData, pickleData['messages'], pickleData['file_status'])
            if status == 'OK':
                text += '<span style="color:green">OK</span>'
            if status == 'EM-BLOCKED':
                text += '<span style="color:green">PDB OK</span> / <span style="color:red">EM BLOCKED</span>'
            elif status == 'BLOCKED':
                text += '<span style="color:red">BLOCKED</span>'
            #
            if ('task' in pickleData) and pickleData['task']:
                text += '\n\nTask: ' + pickleData['task']
                if ('option' in pickleData) and (pickleData['option'] != 'pull_release'):
                    selectText, _selectMap = self._getReleaseOptionFromPickle(pickleData)
                    text += '\n\nRelease Option: ' + selectText
                #
            #
            if entrySysError:
                _msgType, msgText = self._getConcatMessageContent(entrySysError)
                text += '\n\nSystem related error:\n' + msgText
            #
            text += entryContent
        #
        return text
