##
# File:  GzipMP.py
# Date:  27-Aug-2013
# Gzips:
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

from wwpdb.apps.releasemodule.update.GzipUtil  import GzipUtil

class GzipWorker(multiprocessing.Process):
    """
    """
    def __init__(self, path='.', siteId=None, processLabel='', taskQueue=None, resultQueue=None, \
                 log=sys.stderr, verbose=False):
        multiprocessing.Process.__init__(self)
        self.__sessionPath = path
        self.__siteId = siteId
        self.__processLabel = processLabel
        self.__taskQueue=taskQueue
        self.__resultQueue=resultQueue
        self.__lfh=log
        self.__verbose=verbose

    def runGzipSP(self,list):
        update = GzipUtil(path=self.__sessionPath, siteId=self.__siteId, processLabel=self.__processLabel, \
                          entryList=list, log=self.__lfh, verbose=self.__verbose)
        update.run()
        return 'OK'

    def run(self):
        while True:
            nextList=self.__taskQueue.get()
            # end of queue condition
            if nextList is None:
                break
            #
            self.__resultQueue.put(self.runGzipSP(nextList))
        #

class GzipMP(object):
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
        workers = [ GzipWorker(path=self.__sessionPath, siteId=self.__siteId, processLabel=str(i+1), taskQueue=taskQueue, \
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
            msg = resultQueue.get()
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
