##
# File:  NmrDataGenerator.py
# Date:  13-Mar-2020
# Updates:
##
"""
Base class for handle all release module activities

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2020 wwPDB

This software is provided under a Creative Commons Attribution 3.0 Unported
License described at http://creativecommons.org/licenses/by/3.0/.

"""
__docformat__ = "restructuredtext en"
__author__ = "Zukang Feng"
__email__ = "zfeng@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.07"

import os
import sys
import traceback

from wwpdb.utils.dp.RcsbDpUtility import RcsbDpUtility
from wwpdb.utils.nmr.NmrDpUtility import NmrDpUtility


class NmrDataGenerator(object):
    """
    """
    def __init__(self, siteId=None, workingDirPath=None, verbose=False, log=sys.stderr):
        """
        """
        self.__siteId = siteId
        self.__workingDirPath = workingDirPath
        self.__verbose = verbose
        self.__lfh = log

    def getNmrDataFiles(self, pdb_id, inputCifFile, outputNmrDataStrFile, outputNmrDataNetFile):
        """ Get nmr-data-str and nmr-data-nef files
        """
        self.__lfh.write("Starting %s to (%s, %s) conversion.\n" % (inputCifFile, outputNmrDataStrFile, outputNmrDataNetFile))
        #
        self.getNmrDataStrFile(pdb_id, inputCifFile, outputNmrDataStrFile)
        #
        errMsg = ""
        if os.access(outputNmrDataStrFile, os.R_OK):
            errMsg = self.getNmrDataNefFile(pdb_id, outputNmrDataStrFile, outputNmrDataNetFile)
        #
        self.__lfh.write("Finish %s to (%s, %s) conversion.\n" % (inputCifFile, outputNmrDataStrFile, outputNmrDataNetFile))
        return errMsg

    def getNmrDataStrFile(self, pdb_id, inputCifFile, outputNmrDataStrFile):
        """ Get nmr-data-str file
        """
        try:
            self.__lfh.write("Starting %s to %s conversion.\n" % (inputCifFile, outputNmrDataStrFile))
            #
            dp = RcsbDpUtility(tmpPath=self.__workingDirPath, siteId=self.__siteId, verbose=self.__verbose, log=self.__lfh)
            dp.imp(inputCifFile)
            dp.addInput(name="pdb_id", value=pdb_id)
            dp.op("annot-generte-nmr-data-str-file")
            dp.exp(outputNmrDataStrFile)
            dp.cleanup()
            #
            self.__lfh.write("Finish %s to %s conversion.\n" % (inputCifFile, outputNmrDataStrFile))
        except:  # noqa: E722 pylint: disable=bare-except
            traceback.print_exc(file=self.__lfh)
        #

    def getNmrDataNefFile(self, pdb_id, inputNmrDataStrFile, outputNmrDataNetFile):
        """ get nmr-data-nef file
        """
        try:
            # output log for converted NMR-STAR file in "nmr-str2nef-release" op
            logOutPath1 = os.path.join(self.__workingDirPath, pdb_id + "-logstrstr.json")
            # output log for converted NEF file in "nmr-str2nef-release" op
            logOutPath2 = os.path.join(self.__workingDirPath, pdb_id + "-logstrnef.json")
            # strOut = os.path.join(self.__workingDirPath, pdb_id + "temp-str.str")
            #
            for filePath in (logOutPath1, logOutPath2):
                if os.access(filePath, os.F_OK):
                    os.remove(filePath)
                #
            #
            self.__lfh.write("Starting %s to %s conversion.\n" % (inputNmrDataStrFile, outputNmrDataNetFile))
            #
            np = NmrDpUtility()
            np.setSource(inputNmrDataStrFile)
            # np.setDestination(strOut)
            np.addOutput(name="nef_file_path", value=outputNmrDataNetFile, type="file")
            np.addOutput(name="report_file_path", value=logOutPath2, type="file")
            np.addOutput(name="insert_entry_id_to_loops", value=True, type="param")
            np.setLog(logOutPath1)
            np.op("nmr-str2nef-release")
            #
            self.__lfh.write("Finish %s to %s conversion.\n" % (inputNmrDataStrFile, outputNmrDataNetFile))
        except:  # noqa: E722 pylint: disable=bare-except
            traceback.print_exc(file=self.__lfh)
            return traceback.format_exc()
        #
        return ""

    def testNEFTranslator(self, inputFile, outputFile):
        """
        """
        self.getNmrDataNefFile("1abc", inputFile, outputFile)


if __name__ == '__main__':
    dirPath = os.getcwd()
    generator = NmrDataGenerator(siteId=os.getenv("WWPDB_SITE_ID"), workingDirPath=dirPath)
    """
    generator.getNmrDataFiles(os.path.join(dirPath, "D_800120_nmr-data-str_P1.cif"), "0037", os.path.join(dirPath, "nmr-data-str.str"), \
                              os.path.join(dirPath, "nmr-data-nef.str"))
    """
    generator.testNEFTranslator(os.path.join(dirPath, "0037_nmr-data.str"), os.path.join(dirPath, "test.nef"))
