##
# File:  DepictEntryHistory.py
# Date:  19-Nov-2016
# Updates:
##
"""
Create HTML depiction for release module.

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
import time

from wwpdb.apps.releasemodule.utils.ModuleBaseClass import ModuleBaseClass


class DepictEntryHistory(ModuleBaseClass):
    """ Class responsible for generating HTML depiction.
    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        super(DepictEntryHistory, self).__init__(reqObj=reqObj, verbose=verbose, log=log)

    def get(self):
        myD = {}
        myD['identifier'] = str(self._reqObj.getValue('identifier'))
        myD['table_rows'] = self.__getEntryHistory()
        return myD

    def getText(self):
        entryPickle = self._loadEntryPickle(str(self._reqObj.getValue('identifier')))
        if not entryPickle:
            return ''
        #
        if ('history' not in entryPickle) or (not entryPickle['history']):
            return ''
        #
        return self.__getHistoryDetails(entryPickle)

    def __getEntryHistory(self):
        entryPickle = self._loadEntryPickle(str(self._reqObj.getValue('identifier')))
        if not entryPickle:
            return ''
        #
        if ('history' not in entryPickle) or (not entryPickle['history']):
            return ''
        #
        text = ''
        bg_class = 'odd'
        count = 0
        for pickleData in entryPickle['history']:
            myD = {}
            myD['sessionid'] = self._sessionId
            myD['identifier'] = str(self._reqObj.getValue('identifier'))
            myD['bg_class'] = bg_class
            selectedText, _selectedMap = self._getReleaseOptionFromPickle(pickleData)
            myD['options'] = selectedText
            myD['count'] = str(count)
            for item in ('annotator', 'task', 'details', 'block', 'start_time', 'finish_time'):
                myD[item] = ''
                if item == 'block':
                    myD[item] = '<span style="color:red">Failed</span>'
                    if (item in pickleData) and (pickleData[item] is False):
                        myD[item] = '<span style="color:green">Successful</span>'
                    #
                    continue
                elif (item not in pickleData) or (not pickleData[item]):
                    continue
                #
                if (item == 'start_time') or (item == 'finish_time'):
                    myD[item] = time.strftime('%Y-%b-%d %H:%M:%S', time.localtime(pickleData[item]))
                else:
                    myD[item] = pickleData[item]
                #
            #
            if myD['task'] == 'Entries in release pending':
                myD['details'] = '(removed from release)'
            #
            if bg_class == 'odd':
                bg_class = 'even'
            else:
                bg_class = 'odd'
            #
            count += 1
            text += self._processTemplate('view/view_entry_row_tmplt.html', myD)
        #
        return text

    def __getHistoryDetails(self, entryPickle):
        index = int(str(self._reqObj.getValue('index')))
        text = ''
        text += self.__getInputFiles(entryPickle, index)
        text += self.__getOutputFiles(entryPickle['history'][index])
        text += self.__getTaskList(entryPickle['history'][index])
        return text

    def __getInputFiles(self, entryPickle, index):
        fileList = []
        for typeList in self._fileTypeList:
            if ('option' in entryPickle['history'][index]) and (entryPickle['history'][index]['option'] == 'pull_release'):
                if ('start_files' not in entryPickle) or (not entryPickle['start_files']) or \
                   (typeList[3] not in entryPickle['start_files']) or (not entryPickle['start_files'][typeList[3]]):
                    continue
                #
                fileList.append([typeList[2], entryPickle['start_files'][typeList[3]]])
            else:
                if (not typeList[3] in entryPickle['history'][index]) or (not entryPickle['history'][index][typeList[3]]) or \
                   ('archive_file' not in entryPickle['history'][index][typeList[3]]) or \
                   (not entryPickle['history'][index][typeList[3]]['archive_file']):
                    continue
                #
                fileList.append([typeList[2], entryPickle['history'][index][typeList[3]]['archive_file']])
            #
        #
        if not fileList:
            return ''
        #
        text = self._processTemplate('view/view_entry_detail_one_column_row_tmplt.html', {'value':
                                     '<b>Input Files (Files copied from achive directory)</b>'})
        text += self._processTemplate('view/view_entry_detail_one_two_columns_row_tmplt.html',
                                      {'value1': '<b>File Type</b>', 'value2' : '<b>File Name</b>'})
        for fileInfo in fileList:
            text += self._processTemplate('view/view_entry_detail_one_two_columns_row_tmplt.html',
                                          {'value1' : fileInfo[0], 'value2': fileInfo[1]})
        #
        text += self._processTemplate('view/view_entry_detail_one_column_row_no_border_tmplt.html', {'value' : '&nbsp;'})
        return text

    def __getOutputFiles(self, pickleData):
        if ('output' not in pickleData) or (not pickleData['output']):
            return ''
        #
        text = self._processTemplate('view/view_entry_detail_one_column_row_tmplt.html', {'value':
                                     '<b>Output Files (Files put back to achive directory)</b>'})
        text += self._processTemplate('view/view_entry_detail_one_two_columns_row_tmplt.html',
                                      {'value1' : '<b>File Type</b>', 'value2' : '<b>File Name</b>'})
        for fileInfo in pickleData['output']:
            text += self._processTemplate('view/view_entry_detail_one_two_columns_row_tmplt.html',
                                          {'value1': fileInfo[0], 'value2': fileInfo[1]})
        #
        text += self._processTemplate('view/view_entry_detail_one_column_row_no_border_tmplt.html', {'value': '&nbsp;'})
        return text

    def __getTaskList(self, pickleData):
        if ('tasks' not in pickleData) or (not pickleData['tasks']):
            return ''
        #
        text = self._processTemplate('view/view_entry_detail_one_column_row_tmplt.html', {'value': '<b>Process Steps</b>'})
        text += self._processTemplate('view/view_entry_detail_one_two_columns_row_tmplt.html',
                                      {'value1': '<b>Start Time</b>', 'value2' : '<b>Action</b>'})
        for task in pickleData['tasks']:
            text += self._processTemplate('view/view_entry_detail_one_two_columns_row_tmplt.html',
                                          {'value1': time.strftime('%Y-%b-%d %H:%M:%S', time.localtime(task['time'])),
                                           'value2': task['action']})
            #
        #
        text += self._processTemplate('view/view_entry_detail_one_column_row_no_border_tmplt.html', {'value': '&nbsp;'})
        return text
