##
# File:  MatchMP.py
# Date:  23-Jul-2013
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
__author__ = "Zukang Feng"
__email__ = "zfeng@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.07"

import multiprocessing
import sys
import traceback

from wwpdb.apps.releasemodule.citation.MatchUtil import MatchUtil


class MatchWorker(multiprocessing.Process):
    """
    """

    def __init__(self, termMap=None, pubmedInfo=None, taskQueue=None, resultQueue=None,
                 log=sys.stderr, verbose=False):
        multiprocessing.Process.__init__(self)
        self.__termMap = termMap
        self.__pubmedInfo = pubmedInfo
        self.__taskQueue = taskQueue
        self.__resultQueue = resultQueue
        self.__lfh = log
        self.__verbose = verbose

    def getMatchList(self, entry):
        mUtil = MatchUtil(entry=entry, termMap=self.__termMap, pubmedInfo=self.__pubmedInfo,
                          log=self.__lfh, verbose=self.__verbose)
        mUtil.run()
        return mUtil.getMatchList()

    def run(self):
        # processName = self.name
        while True:
            nextList = self.__taskQueue.get()
            # end of queue condition
            if nextList is None:
                break
            #
            resultList = []
            for entry in nextList:
                mlist = self.getMatchList(entry)
                if not mlist:
                    continue
                #
                resultList.append([entry['structure_id'], mlist])
            #
            self.__resultQueue.put(resultList)
        #


class MatchMP(object):
    """
    """

    def __init__(self, entryList=None, termMap=None, pubmedInfo=None, log=sys.stderr, verbose=False):
        """
        """
        self.__entryList = entryList
        self.__termMap = termMap
        self.__pubmedInfo = pubmedInfo
        self.__lfh = log
        self.__verbose = verbose
        self.__matchResultMap = {}

    def run(self):
        numProc = multiprocessing.cpu_count() * 2
        #
        subLists = [self.__entryList[i::numProc] for i in range(numProc)]
        #
        taskQueue = multiprocessing.Queue()
        resultQueue = multiprocessing.Queue()
        #
        workers = [MatchWorker(termMap=self.__termMap, pubmedInfo=self.__pubmedInfo, taskQueue=taskQueue,
                               resultQueue=resultQueue, log=self.__lfh, verbose=self.__verbose) for i in range(numProc)]
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
            lists = resultQueue.get()
            if not lists:
                continue
            #
            for reslist in lists:
                self.__matchResultMap[reslist[0]] = reslist[1]
            #
        #
        try:
            for w in workers:
                w.terminate()
                w.join(1)
            #
        except:  # noqa: E722 pylint: disable=bare-except
            if self.__verbose:
                traceback.print_exc(file=self.__lfh)
            #
        #

    def getMatchResultMap(self):
        return self.__matchResultMap
