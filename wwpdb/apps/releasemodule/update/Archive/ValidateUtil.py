##
# File:  ValidateUtil.py
# Date:  04-Sep-2013
# Updates:
##
"""
New Validation utility

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

import os, string, sys, traceback

from wwpdb.utils.dp.RcsbDpUtility     import RcsbDpUtility

class ValidateUtil(object):
    """ Class responsible for new validation
    """
    def __init__(self, path='.', siteId=None, entryList=None, verbose=False, log=sys.stderr):
        """
        """
        self.__sessionPath  = path
        self.__siteId       = siteId
        self.__updateList   = entryList
        self.__verbose      = verbose
        self.__lfh          = log
        #

    def run(self):
        if len(self.__updateList) == 0:
            return
        #
        for pdbid in self.__updateList:
            ofpdf = os.path.join(self.__sessionPath, pdbid + '-valrpt.pdf')
            ofxml = os.path.join(self.__sessionPath, pdbid + '-valdata.xml')
            workPath = os.path.join(self.__sessionPath, 'tmp_validation_' + pdbid)
            coorFile = os.path.join(self.__sessionPath, pdbid + '.cif')
            sfFile   = os.path.join(self.__sessionPath, 'r' + pdbid + 'sf.ent')
            dp = RcsbDpUtility(tmpPath=self.__sessionPath, siteId=self.__siteId, verbose=True)
            dp.setWorkingDir(workPath)
            dp.imp(coorFile)
            dp.addInput(name='sf_file_path', value=sfFile)
            dp.op('annot-wwpdb-validate-2')
            logFile = os.path.join(self.__sessionPath, pdbid + '-validation.log')
            if os.access(logFile, os.F_OK):
                os.remove(logFile)
            #
            dp.expLog(logFile)
            dp.expList(dstPathList=[ofpdf,ofxml])
        #
