##
# File:  DepictAnnotatorHistory.py
# Date:  20-Nov-2016
# Updates:
##
"""
Create HTML depiction for Annotator's release history

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
import time

from wwpdb.apps.releasemodule.utils.ModuleBaseClass import ModuleBaseClass


class DepictAnnotatorHistory(ModuleBaseClass):
    """ Class responsible for generating Annotator's release history HTML depiction.

    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        super(DepictAnnotatorHistory, self).__init__(reqObj=reqObj, verbose=verbose, log=log)
        self.__pickleData = self._loadAnnotatorPickle(self._getSelectedAnnotator())

    def DoRender(self):
        if not self.__pickleData:
            return ''
        #
        if ('eventList' not in self.__pickleData) or (not self.__pickleData['eventList']):
            return ''
        #
        myD = {}
        myD['task'] = str(self._reqObj.getValue('task'))
        myD['annotator'] = self._getSelectedAnnotator()
        myD['table_rows'] = self.__processEventList(self.__pickleData['eventList'])
        #
        return self._processTemplate('view/view_annotator_history_tmplt.html', myD)

    def __processEventList(self, eventList):
        text = ''
        bg_class = 'odd'
        for enevtDict in eventList:
            myD = {}
            myD['bg_class'] = bg_class
            for item in ('task', 'details', 'time', 'entry_ids'):
                myD[item] = ''
                if (item not in enevtDict) or (not enevtDict[item]):
                    continue
                #
                if item == 'time':
                    myD[item] = time.strftime('%Y-%b-%d %H:%M:%S', time.localtime(enevtDict[item]))
                elif item == 'entry_ids':
                    for entryId in enevtDict[item]:
                        myD[item] += '&nbsp;' + self._processTemplate('entry_header_tmplt.html', {'sessionid': self._sessionId, 'structure_id': entryId})
                    #
                else:
                    myD[item] = enevtDict[item]
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
            text += self._processTemplate('view/view_annotator_row_tmplt.html', myD)
        #
        return text
