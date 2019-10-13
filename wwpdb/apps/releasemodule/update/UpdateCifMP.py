##
# File:  UpdateCifMP.py
# Date:  14-July-2015
# Updates:
##
"""

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2013 wwPDB

This software is provided under a Creative Commons Attribution 3.0 Unported
License described at http://creativecommons.org/licenses/by/3.0/.

"""
__docformat__ = "restructuredtext en"
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import os,sys,multiprocessing,traceback

from wwpdb.utils.config.ConfigInfo                      import ConfigInfo
from wwpdb.apps.releasemodule.utils.Utility           import *

class UpdateCifUtil(object):
    """
    """
    def __init__(self, path='.', siteId=None, processLabel='', entryList=None, verbose=False, log=sys.stderr):
        """
        """
        self.__sessionPath  = path
        self.__siteId       = siteId
        self.__processLabel = processLabel
        self.__updateList   = entryList
        self.__verbose      = verbose
        self.__lfh          = log
        #
        self.__cI = ConfigInfo(self.__siteId)
        self.__rcsbRoot = self.__cI.get('SITE_ANNOT_TOOLS_PATH')
        self.__compRoot = self.__cI.get('SITE_CC_CVS_PATH')
        #
        self.__entryErrorContent = {}
        self.__errorContent = ''
        #

    def run(self):
        if len(self.__updateList) == 0:
            return
        #
        for ciffile in self.__updateList:
            scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('update_model_cif')
            #
            script = os.path.join(self.__sessionPath, scriptfile)
            f = open(script, 'w')
            f.write('#!/bin/tcsh -f\n')
            f.write('#\n')
            f.write('setenv RCSBROOT ' + self.__rcsbRoot + '\n')
            f.write('setenv COMP_PATH ' + self.__compRoot + '\n')
            f.write('setenv BINPATH ${RCSBROOT}/bin\n')
            f.write('#\n')
            f.write('${BINPATH}/UpdateValidateCategories -input ' + ciffile + ' -output ' + ciffile + ' -log ' + logfile + '\n')
            f.write('#\n')
            f.close()
            #
            RunScript(self.__sessionPath, scriptfile, clogfile)
        #

    def getEntryMessage(self):
        return self.__entryErrorContent

    def getErrorMessage(self):
        return self.__errorContent

    def __getAuxiliaryFileNames(self, prefix):
        if self.__processLabel:
            scriptfile = prefix + '_' + self.__processLabel + '.csh'
            logfile    = prefix + '_' + self.__processLabel + '.log'
            clogfile   = prefix + '_command_' + self.__processLabel + '.log'
        else:
            scriptfile = getFileName(self.__sessionPath, prefix, 'csh')
            logfile    = getFileName(self.__sessionPath, prefix, 'log')
            clogfile   = getFileName(self.__sessionPath, prefix + '_command', 'log')
        #
        return scriptfile,logfile,clogfile

class UpdateCifWorker(multiprocessing.Process):
    """
    """
    def __init__(self, path='.', siteId=None, processLabel='', taskQueue=None, resultQueue=None, log=sys.stderr, verbose=False):
        multiprocessing.Process.__init__(self)
        self.__sessionPath = path
        self.__siteId = siteId
        self.__processLabel = processLabel
        self.__taskQueue=taskQueue
        self.__resultQueue=resultQueue
        self.__lfh=log
        self.__verbose=verbose

    def runUpdateSP(self,list):
        update = UpdateCifUtil(path=self.__sessionPath, siteId=self.__siteId, processLabel=self.__processLabel, \
                            entryList=list, log=self.__lfh, verbose=self.__verbose)
        update.run()
        list = []
        list.append(update.getEntryMessage())
        list.append(update.getErrorMessage())
        return list

    def run(self):
        while True:
            nextList=self.__taskQueue.get()
            # end of queue condition
            if nextList is None:
                break
            #
            self.__resultQueue.put(self.runUpdateSP(nextList))
        #

class UpdateCifMP(object):
    """
    """
    def __init__(self, path='.', siteId=None, entryList=None, log=sys.stderr, verbose=False):
        """
        """
        self.__sessionPath = path
        self.__siteId = siteId
        self.__updateList = entryList
        self.__lfh = log
        self.__verbose = verbose
        self.__entryErrorContent = {}
        self.__errorContent = []

    def run(self):
        """
        """
        if not self.__updateList:
            return
        #
        numProc = multiprocessing.cpu_count() * 2
        #
        subLists = [self.__updateList[i::numProc] for i in range(numProc)]
        #
        taskQueue = multiprocessing.Queue()
        resultQueue = multiprocessing.Queue()
        #
        workers = [ UpdateCifWorker(path=self.__sessionPath, siteId=self.__siteId, processLabel=str(i+1), taskQueue=taskQueue, \
                    resultQueue=resultQueue, log=self.__lfh, verbose=self.__verbose) for i in range(numProc) ]
        #
        for w in workers:
            w.start()
        #
        for subList in subLists:
            taskQueue.put(subList)
        #
        for i in range(numProc):
            taskQueue.put(None)
        #
        for i in range(len(subLists)):
            list = resultQueue.get()
            if list[0]:
                for k,v in list[0].items():
                    self.__entryErrorContent[k] = v
                #
            #
            if list[1] and (not list[1] in self.__errorContent):
                self.__errorContent.append(list[1])
            #
        #
        try:
            for w in workers:
                w.terminate()
                w.join(1)
            #
        except:
            if self.__verbose:
                traceback.print_exc(file=self.__lfh)
            #
        #

    def getEntryMessage(self):
        return self.__entryErrorContent

    def getErrorMessage(self):
        return self.__errorContent
