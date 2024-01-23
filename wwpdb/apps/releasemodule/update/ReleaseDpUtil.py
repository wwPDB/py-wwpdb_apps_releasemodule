##
# File:  ReleaseDpUtil.py
# Date:  20-Mar-2020
# Updates:
##
"""
Class responsible for generating and checking release files

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

import os
import sys
import tarfile

from wwpdb.apps.releasemodule.update.EntryUpdateBase import EntryUpdateBase
from wwpdb.apps.releasemodule.update.NmrDataGenerator import NmrDataGenerator


class ReleaseDpUtil(EntryUpdateBase):
    """ Class responsible for generating and checking release files
    """
    def __init__(self, reqObj=None, entryDir=None, verbose=False, log=sys.stderr):
        """
        """
        super(ReleaseDpUtil, self).__init__(reqObj=reqObj, entryDir=entryDir, statusDB=None, verbose=verbose, log=log)
        #
        self.__pdbId = self._entryDir['pdb_id'].lower()
        # self.__dictRoot = os.path.abspath(self._cICommon.get_mmcif_dict_path())
        self.__errorKeyWordList = []
        #
        self.__readErrorKeyWordList()

    def run(self):
        """
        """
        self._loadLocalPickle()
        if self._blockErrorFlag:
            return
        #
        self.__releasingModelFiles()
        self.__releasingSfFile()
        self.__releasingMrFile()
        self.__releasingCsFile()
        self.__releasingNefFile()
        if self._blockErrorFlag:
            if ("status_code_em" in self._pickleData) and self._pickleData["status_code_em"]:
                self._insertFileStatus("em", False)
            #
        #
        self._dumpLocalPickle()

    def __readErrorKeyWordList(self):
        """
        """
        fPath = os.path.join(self._reqObj.getValue("TemplatePath"), "cif_xml_error_list")
        sIn = self.__readFile(fPath)
        #
        lineList = sIn.split("\n")
        for line in lineList:
            if not line:
                continue
            #
            if line[0] == "#":
                continue
            #
            keylist = line.split(";")
            self.__errorKeyWordList.append(keylist)
        #

    def __readFile(self, filePath):
        """
        """
        ifh = open(filePath, "r")
        data = ifh.read()
        ifh.close()
        #
        return data

    def __releasingModelFiles(self):
        """
        """
        if not self.__checkReleaseFlag("model"):
            return
        #
        self.__releasingCIFFile()
        self.__releasingXMLFiles()
        self.__runMiscChecking()
        #
        if self._entryDir["status_code"] == "RELOAD":
            return
        #
        if ("big_entry" in self._pickleData) and self._pickleData["big_entry"]:
            self.__releasingPdbBundleFile()
            self.__releasingBioAssemblyFiles("GenBioCIFFile", "cif")
        else:
            self.__releasingPDBFile()
            self.__releasingBioAssemblyFiles("GenBioCIFFile", "cif")
            self.__releasingBioAssemblyFiles("GenBioPDBFile", "pdb")
        #

    def __releasingCIFFile(self):
        """
        """
        cifFile = self.__pdbId + ".cif"
        logFile = "generate_cif_v5_" + self._entryId + ".log"
        clogFile = "generate_cif_command_v5_" + self._entryId + ".log"
        outputList = []
        outputList.append((cifFile, True))
        outputList.append((logFile, True))
        outputList.append((clogFile, True))
        self._dpUtilityApi(operator="annot-cif-to-public-pdbx", inputFileName=self._pickleData["model"]["session_file"],
                           outputFileNameTupList=outputList)
        #
        if not self.__verifyGeneratingFile("cif", cifFile):
            return
        #
        self._insertFileStatus("cif", True)
        self._insertReleseFile("model", os.path.join(self._sessionPath, cifFile), cifFile, "", True)
        self.__checkCIFFile("cif", cifFile, "_v5", False)

    def __releasingXMLFiles(self):
        """
        """
        cifFile = self.__pdbId + ".cif"
        if not os.access(os.path.join(self._sessionPath, cifFile), os.F_OK):
            return
        #
        outputList = []
        for xmlType in ((".cif.xml", ".xml"), (".cif.xml-noatom", "-noatom.xml"), (".cif.xml-extatom", "-extatom.xml")):
            outputList.append((self.__pdbId + xmlType[0], True))
        #
        logFile = "generate_xml_v5_" + self._entryId + ".log"
        clogFile = "generate_xml_command_v5_" + self._entryId + ".log"
        outputList.append((logFile, True))
        outputList.append((clogFile, True))
        #
        self._dpUtilityApi(operator="annot-public-pdbx-to-xml", inputFileName=os.path.join(self._sessionPath, cifFile), outputFileNameTupList=outputList)
        #
        self._processLogError("xml", "", os.path.join(self._sessionPath, logFile))
        self._processLogError("xml", "mmcif2XML", os.path.join(self._sessionPath, clogFile))
        #
        self._insertFileStatus("xml", True)
        for xmlType in ((".cif.xml", ".xml"), (".cif.xml-noatom", "-noatom.xml"), (".cif.xml-extatom", "-extatom.xml")):
            if not self.__verifyGeneratingFile("xml", self.__pdbId + xmlType[0]):
                continue
            #
            self._insertReleseFile("model", os.path.join(self._sessionPath, self.__pdbId + xmlType[0]), self.__pdbId + xmlType[1], "", True)
            #
            if xmlType[0].endswith(".xml-noatom"):
                self.__checkXMLFile(self.__pdbId + xmlType[0], "v5")
            #
        #

    def __runMiscChecking(self):
        """
        """
        outputFile = self._entryId + "_MiscChecking.txt"
        logFile = self._entryId + "_MiscChecking.log"
        clogFile = self._entryId + "_MiscChecking_command.log"
        outputList = []
        outputList.append((outputFile, True))
        outputList.append((logFile, True))
        outputList.append((clogFile, True))
        self._dpUtilityApi(operator="annot-misc-checking", inputFileName=self._pickleData["model"]["session_file"],
                           outputFileNameTupList=outputList, option="-released")
        #
        self._processLogError("", "", os.path.join(self._sessionPath, logFile))
        self._processLogError("", "MiscChecking", os.path.join(self._sessionPath, clogFile))
        #
        if not os.access(os.path.join(self._sessionPath, outputFile), os.F_OK):
            return
        #
        data = self.__readFile(os.path.join(self._sessionPath, outputFile))
        if data:
            self._insertEntryMessage(errType="MiscChecking", errMessage=data, messageType="warning", uniqueFlag=True)
        #

    def __releasingPDBFile(self):
        """
        """
        pdbFile = self._entryId + "_model_P1.pdb"
        logFile = "generate_pdb_" + self._entryId + ".log"
        clogFile = "generate_pdb_command_" + self._entryId + ".log"
        outputList = []
        outputList.append((pdbFile, True))
        outputList.append((logFile, True))
        outputList.append((clogFile, True))
        self._dpUtilityApi(operator="annot-get-pdb-file", inputFileName=self._pickleData["model"]["session_file"], outputFileNameTupList=outputList)
        #
        self._processLogError("pdb", "", os.path.join(self._sessionPath, logFile))
        self._processLogError("pdb", "maxit", os.path.join(self._sessionPath, clogFile))
        #
        if not self.__verifyGeneratingFile("pdb", pdbFile):
            return
        #
        self._insertFileStatus("pdb", True)
        self._insertArchivalFile("model", "pdb", pdbFile, False)
        self._insertReleseFile("model", os.path.join(self._sessionPath, pdbFile), "pdb" + self.__pdbId + ".ent", "", False)
        self.__checkPDBFile(pdbFile)

    def __releasingPdbBundleFile(self):
        """
        """
        tarFile = self.__pdbId + "-pdb-bundle.tar.gz"
        logFile = "generate_bundle_" + self._entryId + ".log"
        clogFile = "generate_bundle_command_" + self._entryId + ".log"
        #
        outputList = []
        outputList.append((tarFile, True))
        outputList.append((logFile, True))
        outputList.append((clogFile, True))
        self._dpUtilityApi(operator="annot-get-pdb-bundle", inputFileName=self._pickleData["model"]["session_file"],
                           outputFileNameTupList=outputList, id_value=self.__pdbId)
        #
        self._processLogError("pdb", "", os.path.join(self._sessionPath, logFile), messageType="warning")
        self._processLogError("pdb", "GetPdbBundle", os.path.join(self._sessionPath, clogFile), messageType="warning")
        #
        if not os.access(os.path.join(self._sessionPath, tarFile), os.F_OK):
            self._insertEntryMessage(errType="pdb", errMessage="PDB bundle file(s) will not be generated.", messageType="warning", uniqueFlag=True)
            return
        else:
            statinfo = os.stat(os.path.join(self._sessionPath, tarFile))
            if statinfo.st_size < 15000:
                tarObj = tarfile.open(name=os.path.join(self._sessionPath, tarFile), mode="r:gz")
                namelist = tarObj.getnames()
                if not namelist:
                    self._insertEntryMessage(errType="pdb", errMessage="Generating pdb bundle file(s) failed.", messageType="warning", uniqueFlag=True)
                    return
                #
            #
        #
        self._insertReleseFile("model", os.path.join(self._sessionPath, tarFile), tarFile, "", False)

    def __releasingBioAssemblyFiles(self, program, fileType):
        """
        """
        indexFile = self.__pdbId + "_" + program + ".index"
        self._removeFile(os.path.join(self._sessionPath, indexFile))
        #
        tarFile = self.__pdbId + "-assembly-" + fileType + ".tar.gz"
        logFile = "generate_biol_" + self._entryId + "_" + program + ".log"
        clogFile = "generate_biol_command_" + self._entryId + "_" + program + ".log"
        outputList = []
        outputList.append((tarFile, True))
        outputList.append((logFile, True))
        outputList.append((clogFile, True))
        #
        if fileType == "cif":
            self._dpUtilityApi(operator="annot-get-biol-cif-file", inputFileName=self._pickleData["model"]["session_file"],
                               outputFileNameTupList=outputList, id_value=self.__pdbId)
        else:
            self._dpUtilityApi(operator="annot-get-biol-pdb-file", inputFileName=self._pickleData["model"]["session_file"],
                               outputFileNameTupList=outputList, id_value=self.__pdbId)
        #
        self._extractTarFile(tarFile)
        self._processLogError(fileType, "", os.path.join(self._sessionPath, logFile))
        self._processLogError(fileType, program, os.path.join(self._sessionPath, clogFile))
        #
        if not os.access(os.path.join(self._sessionPath, indexFile), os.F_OK):
            self._insertEntryMessage(errType=fileType, errMessage="Generating bio-assembly file(s) failed.", uniqueFlag=True)
            return
        #
        data = self.__readFile(os.path.join(self._sessionPath, indexFile))
        #
        for fileName in data.split("\n"):
            if not fileName:
                continue
            #
            self._insertReleseFile("model", os.path.join(self._sessionPath, fileName), fileName, "", True)
        #

    def __releasingSfFile(self):
        if not self.__checkReleaseFlag("structure-factors"):
            return
        #
        self._insertReleseFile("structure-factors", self._pickleData["structure-factors"]["session_file"], self.__pdbId + "-sf.cif", "", False)
        self.__checkingExperimentalDataFile("CheckSFFile", "sf", self._pickleData["structure-factors"]["session_file"])
        if self._entryDir["status_code_sf"] == "REL":
            dList = self._pickleData["structure-factors"]["session_file"].split("/")
            self.__checkCIFFile("sf", dList[-1], "", True)
        #

    def __releasingMrFile(self):
        if not self.__checkReleaseFlag("nmr-restraints"):
            return
        #
        self._insertReleseFile("nmr-restraints", self._pickleData["nmr-restraints"]["session_file"], self.__pdbId + ".mr", "", False)
        self.__checkingExperimentalDataFile("CheckMRFile", "mr", self._pickleData["nmr-restraints"]["session_file"])

    def __releasingCsFile(self):
        if not self.__checkReleaseFlag("nmr-chemical-shifts"):
            return
        #
        strFile = self.__pdbId + "_cs.str"
        clogFile = "str_logfile_" + self._entryId + ".log"
        outputList = []
        outputList.append((strFile, True))
        outputList.append((clogFile, True))
        self._dpUtilityApi(operator="annot-pdbx2nmrstar", inputFileName=self._pickleData["nmr-chemical-shifts"]["session_file"],
                           outputFileNameTupList=outputList, id_value=self.__pdbId)
        #
        self._processLogError("cs", "GenNMRStarCSFile" , os.path.join(self._sessionPath, clogFile))
        #
        if not self.__verifyGeneratingFile("cs", strFile):
            return
        #
        self._insertReleseFile("nmr-chemical-shifts", os.path.join(self._sessionPath, strFile), strFile, "", False)
        self.__checkingExperimentalDataFile("CheckCSFile", "cs", self._pickleData["nmr-chemical-shifts"]["session_file"])

    def __releasingNefFile(self):
        if not self.__checkReleaseFlag('nmr-data-str'):
            return
        #
        internalStrFile = self._entryId + '_nmr-data-str_P1.str'
        internalNefFile = self._entryId + '_nmr-data-nef_P1.str'
        externalStrFile = self.__pdbId + '_nmr-data.str'
        externalNefFile = self.__pdbId + '_nmr-data.nef'
        for fileName in (internalStrFile, internalNefFile, externalStrFile, externalNefFile):
            self._removeFile(os.path.join(self._sessionPath, fileName))
        #
        generator = NmrDataGenerator(siteId=self._siteId, workingDirPath=self._sessionPath, verbose=self._verbose, log=self._lfh)
        errMsg = generator.getNmrDataFiles(self.__pdbId, self._pickleData['nmr-data-str']['session_file'], os.path.join(self._sessionPath, internalStrFile),
                                           os.path.join(self._sessionPath, internalNefFile))
        #
        if not self.__verifyGeneratingFile('nmr_data', internalStrFile):
            return
        #
        self._copyFileUtil(os.path.join(self._sessionPath, internalStrFile), os.path.join(self._sessionPath, externalStrFile))
        self._insertReleseFile('nmr-data-str', os.path.join(self._sessionPath, externalStrFile), externalStrFile, '', True)
        #
        if not self.__verifyGeneratingFile('nmr_data', internalNefFile, errMsg=errMsg):
            return
        #
        self._copyFileUtil(os.path.join(self._sessionPath, internalNefFile), os.path.join(self._sessionPath, externalNefFile))
        self._insertReleseFile('nmr-data-nef', os.path.join(self._sessionPath, externalNefFile), externalNefFile, '', True)

    def __checkReleaseFlag(self, contentType):
        if (contentType not in self._pickleData) or (not self._pickleData[contentType]) or \
           ('release' not in self._pickleData[contentType]) or (not self._pickleData[contentType]['release']) or \
           ('session_file' not in self._pickleData[contentType]) or (not self._pickleData[contentType]['session_file']):
            return False
        #
        return True

    def __verifyGeneratingFile(self, fileType, fileName, errMsg=""):
        filePath = os.path.join(self._sessionPath, fileName)
        if os.access(filePath, os.F_OK):
            return True
        #
        msg = 'Generating ' + fileName + ' failed.'
        if errMsg:
            msg = 'Generating ' + fileName + ' failed:\n' + errMsg
        #
        self._insertEntryMessage(errType=fileType, errMessage=msg, uniqueFlag=True)
        return False

    def __checkCIFFile(self, fileType, fileName, ext, warningOnlyFlag):
        """
        """
        reportFile = fileName + "-diag.log"
        _logFile = "checking_cif_" + fileType + ext + "_" + self._entryId + ".log"  # noqa: F841
        clogFile = "checking_cif_" + fileType + ext + "_command_" + self._entryId + ".log"
        outputList = []
        outputList.append((reportFile, True))
        outputList.append((clogFile, True))
        self._dpUtilityApi(operator="annot-check-cif", inputFileName=os.path.join(self._sessionPath, fileName), outputFileNameTupList=outputList)
        self._processLogError(fileType, "CifCheck", os.path.join(self._sessionPath, clogFile))
        #
        self.__processCheckReoprt(fileType, reportFile, False, warningOnlyFlag)

    def __checkXMLFile(self, xmlFile, version):
        """
        """
        reportFile = self.__pdbId + "." + version + ".xml.diag"
        outputList = []
        outputList.append((reportFile, True))
        #
        xmlPath = os.path.join(self._sessionPath, xmlFile)
        statinfo = os.stat(xmlPath)
        if statinfo.st_size < 100000000:
            self._dpUtilityApi(operator="annot-check-xml-xmllint", inputFileName=xmlPath, outputFileNameTupList=outputList)
            self.__processCheckReoprt("xml", reportFile, True, False)
        #
        self._dpUtilityApi(operator="annot-check-xml-stdinparse", inputFileName=xmlPath, outputFileNameTupList=outputList)
        self.__processCheckReoprt("xml", reportFile, True, False)

    def __checkPDBFile(self, pdbFile):
        """
        """
        reportFile = self.__pdbId + "_pdb.report"
        self._removeFile(os.path.join(self._sessionPath, reportFile))
        #
        tarFile = self.__pdbId + "-checking.tar.gz"
        logFile = "checking_pdb_" + self._entryId + ".log"
        clogFile = "checking_pdb_command_" + self._entryId + ".log"
        outputList = []
        outputList.append((tarFile, True))
        outputList.append((logFile, True))
        outputList.append((clogFile, True))
        #
        options = " -status " + self._entryDir["status_code"]
        if ("directory" in self._entryDir) and self._entryDir["directory"] == "modified":
            options += " -re_release "
        #
        self._dpUtilityApi(operator="annot-check-pdb-file", inputFileName=os.path.join(self._sessionPath, pdbFile),
                           outputFileNameTupList=outputList, option=options, id_value=self.__pdbId)
        #
        self._extractTarFile(tarFile)
        self._processLogError("pdb", "", os.path.join(self._sessionPath, logFile))
        self._processLogError("pdb", "CheckPDBFile", os.path.join(self._sessionPath, clogFile))
        #
        self.__processCheckReoprt("pdb", reportFile, True, False)

    def __checkingExperimentalDataFile(self, program, expType, expFile):
        """
        """
        dp_operator = "annot-check-" + expType + "-file"
        #
        reportFile = self.__pdbId + "_" + expType + ".report"
        clogFile = "checking_" + expType + "_" + self._entryId + ".log"
        outputList = []
        outputList.append((reportFile, True))
        outputList.append((clogFile, True))
        #
        options = ""
        if self._entryDir["status_code_" + expType] == "REL":
            options += " -rel_date " + self._rel_date
        #
        self._dpUtilityApi(operator=dp_operator, inputFileName=expFile, outputFileNameTupList=outputList, option=options, id_value=self.__pdbId)
        self._processLogError("pdb", program, os.path.join(self._sessionPath, clogFile))
        #
        self.__processCheckReoprt(expType, reportFile, True, False)

    def __processCheckReoprt(self, errType, reportFile, missingFlag, warningOnlyFlag):
        status, msg = self._getLogMessage("", os.path.join(self._sessionPath, reportFile))
        if status == "not found":
            if missingFlag:
                self._insertEntryMessage(errType=errType, errMessage="Checking releasing " + errType + " failed.", messageType="warning", uniqueFlag=True)
            #
            return
        #
        if not msg:
            return
        #
        msg_length = len(msg)
        msgList = msg.split("\n")
        msg = ""
        foudValue = False
        block_flag = False
        count = 0
        for line in msgList:
            if self.__containErrorKeyWords(line):
                block_flag = True
            #
            msg += line + "\n"
            count += 1
            if (count > 500) and (msg_length > 10000):
                break
            #
            strip_line = line.strip()
            if strip_line == "input_file_1 validates":
                continue
            elif strip_line == "":
                continue
            elif strip_line.startswith("stdin:"):
                continue
            else:
                foudValue = True
            #
        #
        if not foudValue:
            return
        #
        msgType = "warning"
        if block_flag:
            msgType = "error"
        #
        if warningOnlyFlag:
            msgType = "warning"
        #
        self._insertEntryMessage(errType=errType, errMessage=msg, messageType=msgType)

    def __containErrorKeyWords(self, line):
        for keyWordList in self.__errorKeyWordList:
            count = 0
            for keyWord in keyWordList:
                if line.find(keyWord) != -1:
                    count += 1
                #
            #
            if len(keyWordList) == count and line.find('The expected type is "symop"') == -1:
                return True
            #
        #
        return False
