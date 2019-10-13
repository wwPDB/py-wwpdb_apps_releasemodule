##
# File:  UpdateMP.py
# Date:  08-Aug-2013
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

from wwpdb.apps.releasemodule.update.UpdateUtil  import UpdateUtil

class UpdateWorker(multiprocessing.Process):
    """
    """
    def __init__(self, path='.', siteId=None, processLabel='', taskQueue=None, resultQueue=None, \
                 pubmedInfo=None, log=sys.stderr, verbose=False):
        multiprocessing.Process.__init__(self)
        self.__sessionPath = path
        self.__siteId = siteId
        self.__processLabel = processLabel
        self.__taskQueue=taskQueue
        self.__resultQueue=resultQueue
        self.__pubmedInfoMap = pubmedInfo
        self.__lfh=log
        self.__verbose=verbose

    def runUpdateSP(self,list):
        update = UpdateUtil(path=self.__sessionPath, siteId=self.__siteId, processLabel=self.__processLabel, \
                            entryList=list, pubmedInfo=self.__pubmedInfoMap, log=self.__lfh, verbose=self.__verbose)
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

class UpdateMP(object):
    """
    """
    def __init__(self, path='.', siteId=None, entryList=None, pubmedInfo=None, log=sys.stderr, verbose=False):
        """
        """
        self.__sessionPath = path
        self.__siteId = siteId
        self.__updateList = entryList
        self.__pubmedInfoMap = pubmedInfo
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
        workers = [ UpdateWorker(path=self.__sessionPath, siteId=self.__siteId, processLabel=str(i+1), \
                    taskQueue=taskQueue, resultQueue=resultQueue, pubmedInfo=self.__pubmedInfoMap, \
                    log=self.__lfh, verbose=self.__verbose) for i in range(numProc) ]
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
