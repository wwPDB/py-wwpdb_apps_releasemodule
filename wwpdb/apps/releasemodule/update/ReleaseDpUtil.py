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

class ReleaseDpUtil(EntryUpdateBase):
    """ Class responsible for generating and checking release files
    """
    def __init__(self, reqObj=None, entryDir=None, verbose=False, log=sys.stderr):
        """
        """
        super(ReleaseDpUtil, self).__init__(reqObj=reqObj, entryDir=entryDir, statusDB=None, verbose=verbose, log=log)
        #
        self.__pdbId = ""
        self.__extendedPdbId = ""
        self.__major_revision = ""
        self.__minor_revision = ""
        self._errorKeyWordList = self._readErrorKeyWordList()

    def run(self):
        """
        """
        self._loadLocalPickle()
        if self._blockErrorFlag:
            return
        #
        self.__pdbId, self.__extendedPdbId, self._forReleaseDirPathMap, contentTypeList = self._getPdbReleaseInfo()
        self.__major_revision, self.__minor_revision = self._getAuditRevisionInfo("model")
        #
        if self.__pdbId:
            self.__releasingModelFiles()
            self.__releasingSfFile()
            self.__releasingMrFile()
            self.__releasingCsFile()
            self._releasingNefFile(self.__pdbId, self.__extendedPdbId)
        elif len(contentTypeList) > 0:
            self._insertEntryMessage(errType=contentTypeList[0], errMessage="Can not find the PDB ID.", uniqueFlag=True)
        #
        if self._blockErrorFlag:
            if ("status_code_em" in self._pickleData) and self._pickleData["status_code_em"]:
                self._insertFileStatus("em", False)
            #
        #
        self._dumpLocalPickle()

    def __releasingModelFiles(self):
        """
        """
        if not self._checkReleaseFlag("model"):
            return
        #
        self.__releasingCIFFile(self._forReleaseDirPathMap["model"])
        self.__releasingXMLFiles(self._forReleaseDirPathMap["model"])
        self.__runMiscChecking()
        #
        if self._entryDir["status_code"] == "RELOAD":
            return
        #
        if ("big_entry" in self._pickleData) and self._pickleData["big_entry"]:
            self.__releasingPdbBundleFile(self._forReleaseDirPathMap["model"])
            self.__releasingBioAssemblyFiles("GenBioCIFFile", "cif", self._forReleaseDirPathMap["model"])
        else:
            self.__releasingPDBFile(self._forReleaseDirPathMap["model"])
            self.__releasingBioAssemblyFiles("GenBioCIFFile", "cif", self._forReleaseDirPathMap["model"])
            self.__releasingBioAssemblyFiles("GenBioPDBFile", "pdb", self._forReleaseDirPathMap["model"])
        #

    def __releasingCIFFile(self, forRelDirPathTupl):
        """
        """
        cifFile = self.__pdbId + ".cif"
        if self.__generateCIFFile(cifFile, "", ""):
            self._insertFileStatus("cif", True)
            self._insertReleseFile("release_file", "model", os.path.join(self._sessionPath, cifFile), cifFile, forRelDirPathTupl[1], \
                                   self.__pdbId + ".release_file", True)
            self.__checkCIFFile("cif", cifFile, "_v5", False)
            #
            if self.__extendedPdbId:
                betaCifFile = self.__extendedPdbId + ".cif"
                if self.__generateCIFFile(betaCifFile, "_beta_", "-extendedids"):
                    self._insertReleseFile("beta_release_file", "model", os.path.join(self._sessionPath, betaCifFile), betaCifFile, \
                                           forRelDirPathTupl[2], self.__extendedPdbId + ".beta_release_file", True)
                #
                versionFileInfoTupl = self._versionFileNameConversionMap[".cif"]
                versionInfo = ""
                if self.__major_revision and self.__minor_revision:
                    versionInfo = "_v" + self.__major_revision + "-" + self.__minor_revision
                #
                versionCifFile = self.__extendedPdbId + "_" + versionFileInfoTupl[0] + versionInfo + versionFileInfoTupl[1]
                self._insertReleseFile("version_release_file", "model", os.path.join(self._sessionPath, cifFile), versionCifFile, forRelDirPathTupl[3], \
                                       self.__extendedPdbId + ".version_release_file", True)
            #
        #

    def __generateCIFFile(self, cifFile, logExt, options):
        """
        """
        logFile = "generate_cif_v5_" + self._entryId + logExt + ".log"
        clogFile = "generate_cif_command_v5_" + self._entryId + logExt + ".log"
        #
        outputList = []
        outputList.append((cifFile, True))
        outputList.append((logFile, True))
        outputList.append((clogFile, True))
        self._dpUtilityApi(operator="annot-cif-to-public-pdbx", inputFileName=self._pickleData["model"]["session_file"],
                           outputFileNameTupList=outputList, option=options)
        #
        return self._verifyGeneratingFile("cif", cifFile)

    def __releasingXMLFiles(self, forRelDirPathTupl):
        """
        """
        if not self.__generateXMLFiles(self.__pdbId, "", True):
            return
        #
        self._insertFileStatus("xml", True)
        #
        if self.__extendedPdbId:
            self.__generateXMLFiles(self.__extendedPdbId, "_beta_",  False)
        #
        for xmlType in ((".cif.xml", ".xml"), (".cif.xml-noatom", "-noatom.xml"), (".cif.xml-extatom", "-extatom.xml")):
            if self._verifyGeneratingFile("xml", self.__pdbId + xmlType[0]):
                self._insertReleseFile("release_file", "model", os.path.join(self._sessionPath, self.__pdbId + xmlType[0]), self.__pdbId + xmlType[1], \
                                       forRelDirPathTupl[1], self.__pdbId + ".release_file", True)
                #
                if xmlType[0].endswith(".xml-noatom"):
                    self.__checkXMLFile(self.__pdbId + xmlType[0], "v5")
                #
                if self.__extendedPdbId:
                    versionFileInfoTupl = self._versionFileNameConversionMap[xmlType[0]]
                    versionInfo = ""
                    if self.__major_revision and self.__minor_revision:
                        versionInfo = "_v" + self.__major_revision + "-" + self.__minor_revision
                    #
                    versionXmlFile = self.__extendedPdbId + "_" + versionFileInfoTupl[0] + versionInfo + versionFileInfoTupl[1]
                    self._insertReleseFile("version_release_file", "model", os.path.join(self._sessionPath, self.__pdbId + xmlType[0]), versionXmlFile, \
                                           forRelDirPathTupl[3], self.__extendedPdbId + ".version_release_file", True)
                #
            #
            if self.__extendedPdbId and self._verifyGeneratingFile("xml", self.__extendedPdbId + xmlType[0]):
                self._insertReleseFile("beta_release_file", "model", os.path.join(self._sessionPath, self.__extendedPdbId + xmlType[0]), \
                                       self.__extendedPdbId + xmlType[1], forRelDirPathTupl[2], self.__extendedPdbId + ".beta_release_file", True)
            #
        #

    def __generateXMLFiles(self, pdbId, logExt, processFlag):
        """
        """
        cifFile = pdbId + ".cif"
        if not os.access(os.path.join(self._sessionPath, cifFile), os.F_OK):
            return False
        #
        outputList = []
        for xmlType in ((".cif.xml", ".xml"), (".cif.xml-noatom", "-noatom.xml"), (".cif.xml-extatom", "-extatom.xml")):
            outputList.append((pdbId + xmlType[0], True))
        #
        logFile = "generate_xml_v5_" + self._entryId + logExt + ".log"
        clogFile = "generate_xml_command_v5_" + self._entryId + logExt + ".log"
        outputList.append((logFile, True))
        outputList.append((clogFile, True))
        #
        self._dpUtilityApi(operator="annot-public-pdbx-to-xml", inputFileName=os.path.join(self._sessionPath, cifFile), outputFileNameTupList=outputList)
        #
        if processFlag:
            self._processLogError("xml", "", os.path.join(self._sessionPath, logFile))
            self._processLogError("xml", "mmcif2XML", os.path.join(self._sessionPath, clogFile))
        #
        return True

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
        data = self._readFile(os.path.join(self._sessionPath, outputFile))
        if data:
            self._insertEntryMessage(errType="MiscChecking", errMessage=data, messageType="warning", uniqueFlag=True)
        #

    def __releasingPDBFile(self, forRelDirPathTupl):
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
        if not self._verifyGeneratingFile("pdb", pdbFile):
            return
        #
        self._insertFileStatus("pdb", True)
        self._insertArchivalFile("model", "pdb", pdbFile, False)
        self._insertReleseFile("release_file", "model", os.path.join(self._sessionPath, pdbFile), "pdb" + self.__pdbId + ".ent", \
                               forRelDirPathTupl[1], self.__pdbId + ".release_file", False)
        #
        if self.__extendedPdbId:
            self._insertReleseFile("beta_release_file", "model", os.path.join(self._sessionPath, pdbFile), self.__extendedPdbId + ".pdb", \
                                   forRelDirPathTupl[2], self.__extendedPdbId + ".beta_release_file", True)
        #
        self.__checkPDBFile(pdbFile)

    def __releasingPdbBundleFile(self, forRelDirPathTupl):
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
        self._insertReleseFile("release_file", "model", os.path.join(self._sessionPath, tarFile), tarFile, forRelDirPathTupl[1], \
                               self.__pdbId + ".release_file", False)

    def __releasingBioAssemblyFiles(self, program, fileType, forRelDirPathTupl):
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
        data = self._readFile(os.path.join(self._sessionPath, indexFile))
        #
        for fileName in data.split("\n"):
            if not fileName:
                continue
            #
            self._insertReleseFile("release_file", "model", os.path.join(self._sessionPath, fileName), fileName, \
                                   forRelDirPathTupl[1], self.__pdbId + ".release_file", True)
            #
            if (fileType == "cif") and self.__extendedPdbId:
                betaFileName = fileName.replace(self.__pdbId, self.__extendedPdbId)
                self._insertReleseFile("beta_release_file", "model", os.path.join(self._sessionPath, fileName), betaFileName, \
                                       forRelDirPathTupl[2], self.__extendedPdbId + ".beta_release_file", True)
            #
        #

    def __releasingSfFile(self):
        if not self._checkReleaseFlag("structure-factors"):
            return
        #
        self._insertReleseFile("release_file", "structure-factors", self._pickleData["structure-factors"]["session_file"], self.__pdbId + "-sf.cif", \
                               self._forReleaseDirPathMap["structure-factors"][1], self.__pdbId + ".release_file", False)
        self.__checkingExperimentalDataFile("CheckSFFile", "sf", self._pickleData["structure-factors"]["session_file"])
        if self._entryDir["status_code_sf"] == "REL":
            dList = self._pickleData["structure-factors"]["session_file"].split("/")
            self.__checkCIFFile("sf", dList[-1], "", True)
            #
            if self.__extendedPdbId:
                generatedBetaSfFile = os.path.join(self._sessionPath, self._entryId + "-" + self.__extendedPdbId + "-sf.cif")
                if os.access(generatedBetaSfFile, os.F_OK):
                    self._insertReleseFile("beta_release_file", "structure-factors", generatedBetaSfFile, self.__extendedPdbId + "-sf.cif", \
                               self._forReleaseDirPathMap["structure-factors"][2], self.__extendedPdbId + ".beta_release_file", True)
                else:
                    self._insertEntryMessage(errType="sf", errMessage="Generating " + self.__extendedPdbId + "-sf.cif failed.", uniqueFlag=True)
                #
            #
        #

    def __releasingMrFile(self):
        if not self._checkReleaseFlag("nmr-restraints"):
            return
        #
        self._insertReleseFile("release_file", "nmr-restraints", self._pickleData["nmr-restraints"]["session_file"], self.__pdbId + ".mr", \
                               self._forReleaseDirPathMap["nmr-restraints"][1], self.__pdbId + ".release_file", False)
        self.__checkingExperimentalDataFile("CheckMRFile", "mr", self._pickleData["nmr-restraints"]["session_file"])
        #
        if self.__extendedPdbId:
            self._insertReleseFile("beta_release_file", "nmr-restraints", self._pickleData["nmr-restraints"]["session_file"], self.__extendedPdbId + ".mr", \
                                   self._forReleaseDirPathMap["nmr-restraints"][2], self.__extendedPdbId + ".beta_release_file", True)
        #

    def __releasingCsFile(self):
        if not self._checkReleaseFlag("nmr-chemical-shifts"):
            return
        #
        for tupL in ( ( self.__pdbId, ".log", True, "release_file", 1, self.__pdbId + ".release_file", False ), \
                      ( self.__extendedPdbId, "_beta.log", False, "beta_release_file", 2, self.__extendedPdbId + ".beta_release_file", True ) ):
            if not tupL[0]:
                continue
            #
            strFile = tupL[0] + "_cs.str"
            clogFile = "str_logfile_" + self._entryId + tupL[1]
            outputList = []
            outputList.append((strFile, True))
            outputList.append((clogFile, True))
            self._dpUtilityApi(operator="annot-pdbx2nmrstar", inputFileName=self._pickleData["nmr-chemical-shifts"]["session_file"],
                               outputFileNameTupList=outputList, id_value=tupL[0])
            #
            if tupL[2]:
                self._processLogError("cs", "GenNMRStarCSFile" , os.path.join(self._sessionPath, clogFile))
            #
            if not self._verifyGeneratingFile("cs", strFile):
                return
            #
            self._insertReleseFile(tupL[3], "nmr-chemical-shifts", os.path.join(self._sessionPath, strFile), strFile, \
                                   self._forReleaseDirPathMap["nmr-chemical-shifts"][tupL[4]], tupL[5], tupL[6])
            if tupL[2]:
                self.__checkingExperimentalDataFile("CheckCSFile", "cs", self._pickleData["nmr-chemical-shifts"]["session_file"])
            #
        #

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
        self._processCheckReoprt(fileType, reportFile, "input_file_1", False, warningOnlyFlag)

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
            self._processCheckReoprt("xml", reportFile, "input_file_1", True, False)
        #
        self._dpUtilityApi(operator="annot-check-xml-stdinparse", inputFileName=xmlPath, outputFileNameTupList=outputList)
        self._processCheckReoprt("xml", reportFile, "input_file_1", True, False)

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
        self._processCheckReoprt("pdb", reportFile, "input_file_1", True, False)

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
        self._processCheckReoprt(expType, reportFile, "input_file_1", True, False)
