##
# File:  FetchMP.py
# Date:  23-Jul-2013
# Updates:
##
"""
Run NCBI pubmed fetch utility with multiprocessing option.

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
from wwpdb.utils.config.ConfigInfo import ConfigInfo

from wwpdb.apps.releasemodule.citation.FetchUtil import FetchUtil
from wwpdb.apps.releasemodule.utils.MultiProcLimit import MultiProcLimit


class FetchWorker(multiprocessing.Process):
    """
    """

    def __init__(self, path='.', processLabel='', taskQueue=None, resultQueue=None,
                 siteId=None, mpl=None, log=sys.stderr, verbose=False):
        multiprocessing.Process.__init__(self)
        self.__sessionPath = path
        self.__processLabel = processLabel
        self.__taskQueue = taskQueue
        self.__resultQueue = resultQueue
        self.__lfh = log
        self.__verbose = verbose
        self.__mpl = mpl
        self.__siteId = siteId

    def fetchEntryList(self, idList):
        fetch = FetchUtil(path=self.__sessionPath, processLabel=self.__processLabel,
                          idList=idList, siteId=self.__siteId, mpl=self.__mpl,
                          log=self.__lfh, verbose=self.__verbose)
        fetch.doFetch()
        return fetch.getPubmedInfoList()

    def run(self):
        # processName = self.name
        while True:
            nextList = self.__taskQueue.get()
            # end of queue condition
            if nextList is None:
                break
            #
            self.__resultQueue.put(self.fetchEntryList(nextList))
        #


class FetchMP(object):
    """
    """

    def __init__(self, path='.', idList=None, siteId=None, log=sys.stderr, verbose=False):
        """
        """
        self.__sessionPath = path
        self.__pubmedIdList = idList
        self.__lfh = log
        self.__verbose = verbose
        self.__pubmedInfoMap = {}
        self.__siteId = siteId
        self.__cI = ConfigInfo(self.__siteId)
        self.__apikey = self.__cI.get('NCBI_API_KEY')
        self.__apirate = self.__cI.get('NCBI_API_RATE')

    def runSequential(self):
        fetch = FetchUtil(path=self.__sessionPath, idList=self.__pubmedIdList,
                          log=self.__lfh, verbose=self.__verbose)
        fetch.doFetch()
        self.__pubmedInfoMap = fetch.getPubmedInfoMap()

    def runMultiProcessing(self):
        numBlock = int(len(self.__pubmedIdList) / 200 + 1)
        numProc = multiprocessing.cpu_count() * 2
        # Leave room for other processes
        if self.__apikey:
            if self.__apirate:
                rate = int(self.__apirate)
            else:
                rate = 8
        else:
            rate = 1
        # Extra in case processing from previous result takes more than a second, keep requests comming
        numProc = min(numProc, rate * 2)
        #
        if numBlock < numProc:
            numProc = numBlock
        #
        mpl = MultiProcLimit(rate)
        subLists = [self.__pubmedIdList[i::numProc] for i in range(numProc)]
        #
        taskQueue = multiprocessing.Queue()
        resultQueue = multiprocessing.Queue()
        #
        workers = [FetchWorker(path=self.__sessionPath, processLabel=str(i + 1), taskQueue=taskQueue,
                               resultQueue=resultQueue, log=self.__lfh, verbose=self.__verbose,
                               siteId=self.__siteId, mpl=mpl)
                   for i in range(numProc)]
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
            rlist = resultQueue.get()
            for info in rlist:
                self.__pubmedInfoMap[info['pdbx_database_id_PubMed']] = info
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

    def run(self):
        """
        """
        if not self.__pubmedIdList:
            return
        #
        if len(self.__pubmedIdList) < 201:
            self.runSequential()
        else:
            self.runMultiProcessing()
        #

    def getPubmedInfoMap(self):
        return self.__pubmedInfoMap


if __name__ == '__main__':
    f = open(sys.argv[1], 'r')
    data = f.read()
    f.close()
    #
    idlist = data.split('\n')
    print('idlist=' + str(len(idlist)))
    cf = FetchMP(idList=idlist, log=sys.stderr, verbose=False)
    cf.run()
    pdir = cf.getPubmedInfoMap()
    print('dir=' + str(len(pdir)))
    #
    # for k,v in dir.items():
    #    print v
