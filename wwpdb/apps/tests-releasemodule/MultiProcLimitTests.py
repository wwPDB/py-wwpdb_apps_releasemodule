#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `testdevel` package."""


import unittest
import logging
import time

from rcsb.utils.multiproc.MultiProcUtil import MultiProcUtil
from wwpdb.apps.releasemodule.utils.MultiProcLimit import MultiProcLimit

logging.basicConfig(level=logging.INFO, format=u'MAIN-%(asctime)s [%(levelname)s]-%(module)s.%(funcName)s: %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class TestMultiProcLimit(unittest.TestCase):
    """Tests for `testdevel` package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        pass

    def tearDown(self):
        """Tear down test fixtures, if any."""
        pass

    def workerOne(self, dataList, procName, optionsD, workingDir):
        """
            Worker method must support the following prototype -

            sucessList,resultList,diagList=workerFunc(runList=nextList,procName, optionsD, workingDir)

        """
        successList = []
        mpl = optionsD['mpl']
        for d in dataList:
            mpl.waitnext()
            logger.error(" %s value %s" % (procName, d))
            successList.append(d)

        return successList, [], []


    def test_000_multiproc(self):
        """Test to ensure we slow down tasks."""

        numProc = 10
        chunkSize = 1
        dataList = [i for i in range(1, 30)]
        rateLimit = 10
        # 29 requests, 10/second. Should take > 2.8 seconds - no delay on first
        exptime = (len(dataList) - 1) / rateLimit
        
        mpl = MultiProcLimit(rateLimit)
        optD = {'mpl': mpl}
        mpu = MultiProcUtil(verbose=True)
        mpu.setOptions(optionsD=optD)

        start = time.time()
        mpu.set(workerObj=self, workerMethod="workerOne")
        ok, failList, retLists, diagList = mpu.runMulti(dataList=dataList, numProc=numProc, numResults=1,
                                                        chunkSize=chunkSize)
        self.assertEqual(len(failList), 0)
        self.assertTrue(ok)
        end = time.time()
        self.assertGreater(end-start, exptime, 'Test ran in %s which is too fast' % (end - start))


if __name__ == '__main__':
    unittest.main()
