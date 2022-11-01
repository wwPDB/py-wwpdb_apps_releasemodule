##
# File:  DepictRemovalMark.py
# Date:  20-Apr-2015
# Updates:
##
"""
Create HTML depiction for marked pubmed ID page.

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

try:
    import cPickle as pickle
except ImportError:
    import pickle as pickle

import os
import sys

from wwpdb.io.locator.PathInfo import PathInfo


class DepictRemovalMark(object):
    """ Class responsible for generating marked pubmed ID result HTML depiction.

    """
    def __init__(self, reqObj=None, resultList=None, verbose=False, log=sys.stderr):
        self.__verbose = verbose
        self.__lfh = log
        self.__reqObj = reqObj
        self.__resultList = resultList
        self.__sessionId = str(self.__reqObj.getSessionId())
        self.__sessionPath = str(self.__reqObj.getValue('sessionPath'))
        self.__siteId = str(self.__reqObj.getValue("WWPDB_SITE_ID"))
        #

    def DoRender(self):
        myD = {}
        myD['task'] = str(self.__reqObj.getValue('task'))
        myD['sessionid'] = self.__sessionId
        myD['owner'] = str(self.__reqObj.getValue('owner'))
        myD['annotator'] = str(self.__reqObj.getValue('annotator'))
        myD['table_rows'] = self.__getTableRows()
        #
        return self.__processTemplate('citation_finder/remove_marked_pubmed_form_tmplt.html', myD)

    def __getTableRows(self):
        text = ''
        flag = True
        pI = PathInfo(siteId=self.__siteId, sessionPath=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        for dir in self.__resultList:  # pylint: disable=redefined-builtin
            myD = {}
            myD['structure_id'] = dir['structure_id']
            myD['comb_ids'] = dir['comb_ids']
            myD['no_marked_pubmed_ids'] = ''
            myD['table_rows'] = ''
            if flag:
                myD['bgclass'] = 'even'
                flag = False
            else:
                myD['bgclass'] = 'odd'
                flag = True
            #
            archiveDirPath = pI.getDirPath(dataSetId=dir['structure_id'], wfInstanceId=None, contentType='model', formatType='pdbx',
                                           fileSource='archive', versionId='latest', partNumber=1)
            pickle_file = os.path.join(archiveDirPath, 'marked_pubmed_id.pic')
            pubmed_id_list = []
            if os.access(pickle_file, os.F_OK):
                fb = open(pickle_file, 'rb')
                pubmed_id_list = pickle.load(fb)
                fb.close()
            #
            if pubmed_id_list:
                table_rows = ''
                for pmid in pubmed_id_list:
                    myD1 = {}
                    myD1['structure_id'] = dir['structure_id']
                    myD1['pubmed_id'] = pmid
                    table_rows += self.__processTemplate('citation_finder/remove_marked_pubmed_row_tmplt.html', myD1)
                #
                myD['table_rows'] = table_rows
            else:
                myD['no_marked_pubmed_ids'] = 'No pubmed citation marked as unwanted.'
            #
            text += self.__processTemplate('citation_finder/remove_marked_pubmed_entry_tmplt.html', myD)
        #
        return text

    def __processTemplate(self, fn, parameterDict=None):
        """ Read the input HTML template data file and perform the key/value substitutions in the
            input parameter dictionary.

            :Params:
                ``parameterDict``: dictionary where
                key = name of subsitution placeholder in the template and
                value = data to be used to substitute information for the placeholder

            :Returns:
                string representing entirety of content with subsitution placeholders now replaced with data
        """
        if parameterDict is None:
            parameterDict = {}
        tPath = self.__reqObj.getValue("TemplatePath")
        fPath = os.path.join(tPath, fn)
        ifh = open(fPath, 'r')
        sIn = ifh.read()
        ifh.close()
        return (sIn % parameterDict)
