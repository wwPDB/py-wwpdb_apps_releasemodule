##
# File:  GenerateMP.py
# Date:  20-Aug-2013
# Generates:
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

from wwpdb.apps.releasemodule.update.GenerateUtil  import GenerateUtil

class GenerateWorker(multiprocessing.Process):
    """
    """
    def __init__(self, path='.', siteId=None, processLabel='', taskQueue=None, \
                 resultQueue=None, log=sys.stderr, verbose=False):
        multiprocessing.Process.__init__(self)
        self.__sessionPath = path
        self.__siteId = siteId
        self.__processLabel = processLabel
        self.__taskQueue=taskQueue
        self.__resultQueue=resultQueue
        self.__lfh=log
        self.__verbose=verbose

    def runGenerateSP(self,list):
        generate = GenerateUtil(path=self.__sessionPath, siteId=self.__siteId, processLabel=self.__processLabel, \
                                entryList=list, log=self.__lfh, verbose=self.__verbose)
        generate.run()
        list = []
        list.append(generate.getEntryMessage())
        list.append(generate.getErrorMessage())
        return list

    def run(self):
        while True:
            nextList=self.__taskQueue.get()
            # end of queue condition
            if nextList is None:
                break
            #
            self.__resultQueue.put(self.runGenerateSP(nextList))
        #

class GenerateMP(object):
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
        workers = [ GenerateWorker(path=self.__sessionPath, siteId=self.__siteId, processLabel=str(i+1), \
                    taskQueue=taskQueue, resultQueue=resultQueue, log=self.__lfh, \
                    verbose=self.__verbose) for i in range(numProc) ]
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
            if list[1]:
                for err in list[1]:
                    if self.__errorContent and (err in self.__errorContent):
                        continue
                    #
                    self.__errorContent.append(err)
                #
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
