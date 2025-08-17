##
# File:  ReleaseUtil.py
# Date:  13-Oct-2016
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


class ReleaseUtil(EntryUpdateBase):
    """ Class responsible for generating and checking release files
    """
    def __init__(self, reqObj=None, entryDir=None, verbose=False, log=sys.stderr):
        super(ReleaseUtil, self).__init__(reqObj=reqObj, entryDir=entryDir, statusDB=None, verbose=verbose, log=log)
        #
        self.__dictRoot = os.path.abspath(self._cICommon.get_mmcif_dict_path())
        self.__dictBase = self._cICommon.get_mmcif_archive_current_dict_filename()
        #
        self.__pdbId = ""
        self.__extendedPdbId = ""
        self.__major_revision = ""
        self.__minor_revision = ""
        self._errorKeyWordList = self._readErrorKeyWordList()

    def run(self):
        self._loadLocalPickle()
        if self._blockErrorFlag:
            return
        #
        self.__pdbId, self.__extendedPdbId, self._forReleaseDirPathMap, contentTypeList = self._getPdbReleaseInfo()
        self.__major_revision, self.__minor_revision = self._getAuditRevisionInfo('model')
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
            if ('status_code_em' in self._pickleData) and self._pickleData['status_code_em']:
                self._insertFileStatus('em', False)
            #
        #
        self._dumpLocalPickle()

    def __releasingModelFiles(self):
        if not self._checkReleaseFlag('model'):
            return
        #
        cifxmlInfo = ('v5', '.cif', self.__dictBase + '.sdb', self.__dictBase + '.sdb', self.__dictBase + '.odb', 'pdbx-v50', 'pdbx-v50.xsd',
                      (('.cif.xml', '.xml'), ('.cif.xml-noatom', '-noatom.xml'), ('.cif.xml-extatom', '-extatom.xml')))
        #
        self.__releasingCIFFile(cifxmlInfo, self._forReleaseDirPathMap["model"])
        self.__releasingXMLFiles(cifxmlInfo, self._forReleaseDirPathMap["model"])
        self.__runMiscChecking()
        #
        if self._entryDir['status_code'] == 'RELOAD':
            return
        #
        if ('big_entry' in self._pickleData) and self._pickleData['big_entry']:
            self.__releasingPdbBundleFile(self._forReleaseDirPathMap["model"])
            self.__releasingBioAssemblyFiles('GenBioCIFFile', 'cif', self._forReleaseDirPathMap["model"])
        else:
            self.__releasingPDBFile(self._forReleaseDirPathMap["model"])
            self.__releasingBioAssemblyFiles('GenBioCIFFile', 'cif', self._forReleaseDirPathMap["model"])
            self.__releasingBioAssemblyFiles('GenBioPDBFile', 'pdb', self._forReleaseDirPathMap["model"])
        #

    def __releasingCIFFile(self, cifxmlInfo, forRelDirPathTupl):
        cifFile = self.__pdbId + cifxmlInfo[1]
        if self.__generateCIFFile(cifxmlInfo, cifFile, '', '', False):
            self._insertFileStatus('cif', True)
            self._insertReleseFile("release_file", 'model', os.path.join(self._sessionPath, cifFile), cifFile, forRelDirPathTupl[1],
                                   self.__pdbId + ".release_file", True)
            self.__checkCIFFile('cif', cifFile, cifxmlInfo[3], '_' + cifxmlInfo[0], False)
            #
            if self.__extendedPdbId:
                betaCifFile = self.__extendedPdbId + cifxmlInfo[1]
                if self.__generateCIFFile(cifxmlInfo, betaCifFile, '_beta_', '-extendedids', True):
                    self._insertReleseFile("beta_release_file", 'model', os.path.join(self._sessionPath, betaCifFile), betaCifFile, forRelDirPathTupl[2],
                                           self.__extendedPdbId + ".beta_release_file", True)
                #
                versionFileInfoTupl = self._versionFileNameConversionMap[cifxmlInfo[1]]
                versionInfo = ""
                if self.__major_revision and self.__minor_revision:
                    versionInfo = "_v" + self.__major_revision + "-" + self.__minor_revision
                #
                versionCifFile = self.__extendedPdbId + "_" + versionFileInfoTupl[0] + versionInfo + versionFileInfoTupl[1]
                self._insertReleseFile("version_release_file", 'model', os.path.join(self._sessionPath, cifFile), versionCifFile, forRelDirPathTupl[3],
                                       self.__extendedPdbId + ".version_release_file", True)
            #
        #

    def __generateCIFFile(self, cifxmlInfo, cifFile, logExt, option, removeFlag):
        # self._removeFile(os.path.join(self._sessionPath, cifFile))
        logFile = 'generate_cif_' + cifxmlInfo[0] + '_' + self._entryId + logExt + '.log'
        # self._removeFile(os.path.join(self._sessionPath, logFile))
        clogFile = 'generate_cif_command_' + cifxmlInfo[0] + '_' + self._entryId + logExt + '.log'
        # self._removeFile(os.path.join(self._sessionPath, clogFile))
        if removeFlag:
            self._removeFile(os.path.join(self._sessionPath, cifFile))
            self._removeFile(os.path.join(self._sessionPath, logFile))
            self._removeFile(os.path.join(self._sessionPath, clogFile))
        #
        options = ' -dicSdb ' + os.path.join(self.__dictRoot, cifxmlInfo[2]) + ' -pdbxDicSdb ' \
            + os.path.join(self.__dictRoot, cifxmlInfo[3]) + ' -reorder -strip -op in -pdbids ' + option \
            + ' 2> ' + clogFile + ' 1> ' + logFile
        self._GetAndRunCmd('cif', '${DICTBINPATH}', 'cifexch2', self._pickleData['model']['session_file'], cifFile, '', '', options)
        # self._processLogError('cif', 'cifexch2', os.path.join(self._sessionPath, clogFile))
        return self._verifyGeneratingFile('cif', cifFile)

    def __releasingXMLFiles(self, cifxmlInfo, forRelDirPathTupl):
        if not self.__generateXMLFiles(cifxmlInfo, self.__pdbId, '', True):
            return
        #
        self._insertFileStatus('xml', True)
        #
        if self.__extendedPdbId:
            self.__generateXMLFiles(cifxmlInfo, self.__extendedPdbId, '_beta_', False)
        #
        for xmlType in cifxmlInfo[7]:
            if self._verifyGeneratingFile('xml', self.__pdbId + xmlType[0]):
                self._insertReleseFile("release_file", 'model', os.path.join(self._sessionPath, self.__pdbId + xmlType[0]), self.__pdbId + xmlType[1],
                                       forRelDirPathTupl[1], self.__pdbId + ".release_file", True)
                #
                if xmlType[0].endswith('.xml-noatom'):
                    self.__checkXMLFile(self.__pdbId + xmlType[0], cifxmlInfo[6], cifxmlInfo[0])
                #
                if self.__extendedPdbId:
                    versionFileInfoTupl = self._versionFileNameConversionMap[xmlType[0]]
                    versionInfo = ""
                    if self.__major_revision and self.__minor_revision:
                        versionInfo = "_v" + self.__major_revision + "-" + self.__minor_revision
                    #
                    versionXmlFile = self.__extendedPdbId + "_" + versionFileInfoTupl[0] + versionInfo + versionFileInfoTupl[1]
                    self._insertReleseFile("version_release_file", 'model', os.path.join(self._sessionPath, self.__pdbId + xmlType[0]), versionXmlFile,
                                           forRelDirPathTupl[3], self.__extendedPdbId + ".version_release_file", True)
                #
            #
            if self.__extendedPdbId and self._verifyGeneratingFile('xml', self.__extendedPdbId + xmlType[0]):
                self._insertReleseFile("beta_release_file", 'model', os.path.join(self._sessionPath, self.__extendedPdbId + xmlType[0]),
                                       self.__extendedPdbId + xmlType[1], forRelDirPathTupl[2], self.__extendedPdbId + ".beta_release_file", True)
            #
        #

    def __generateXMLFiles(self, cifxmlInfo, pdbId, logExt, processFlag):
        cifFile = pdbId + cifxmlInfo[1]
        if not os.access(os.path.join(self._sessionPath, cifFile), os.F_OK):
            return False
        #
        for xmlType in cifxmlInfo[7]:
            self._removeFile(os.path.join(self._sessionPath, pdbId + xmlType[0]))
        #
        logFile = 'generate_xml_' + cifxmlInfo[0] + '_' + self._entryId + logExt + '.log'
        self._removeFile(os.path.join(self._sessionPath, logFile))
        clogFile = 'generate_xml_command_' + cifxmlInfo[0] + '_' + self._entryId + logExt + '.log'
        self._removeFile(os.path.join(self._sessionPath, clogFile))
        options = ' -dictName mmcif_pdbx.dic -df ' + os.path.join(self.__dictRoot, cifxmlInfo[4]) \
            + ' -prefix ' + cifxmlInfo[5] + ' -ns PDBx -funct mmcif2xmlall -f ' + cifFile + ' 2> ' + clogFile + ' 1> ' + logFile
        self._GetAndRunCmd('xml', '${DICTBINPATH}', 'mmcif2XML', '', '', '', '', options)
        if processFlag:
            self._processLogError('xml', '', os.path.join(self._sessionPath, logFile))
            self._processLogError('xml', '', os.path.join(self._sessionPath, clogFile))
        #
        return True

    def __runMiscChecking(self):
        outputFile = self._entryId + '_MiscChecking.txt'
        logFile = self._entryId + '_MiscChecking.log'
        clogFile = self._entryId + '_MiscChecking_command.log'
        self._GetAndRunCmd('', '${BINPATH}', 'MiscChecking', self._pickleData['model']['session_file'], outputFile, logFile, clogFile, ' -released ')
        #
        if not os.access(os.path.join(self._sessionPath, outputFile), os.F_OK):
            return
        #
        data = self._readFile(os.path.join(self._sessionPath, outputFile))
        if data:
            self._insertEntryMessage(errType="MiscChecking", errMessage=data, messageType='warning', uniqueFlag=True)
        #

    def __releasingPDBFile(self, forRelDirPathTupl):
        pdbFile = self._entryId + '_model_P1.pdb'
        # self._removeFile(os.path.join(self._sessionPath, pdbFile))
        logFile = 'generate_pdb_' + self._entryId + '.log'
        clogFile = 'generate_pdb_command_' + self._entryId + '.log'
        self._GetAndRunCmd('pdb', '${BINPATH}', 'maxit', self._pickleData['model']['session_file'], pdbFile, logFile, clogFile, ' -o 2 ')
        if not self._verifyGeneratingFile('pdb', pdbFile):
            return
        #
        self._insertFileStatus('pdb', True)
        self._insertArchivalFile('model', 'pdb', pdbFile, False)
        self._insertReleseFile("release_file", 'model', os.path.join(self._sessionPath, pdbFile), 'pdb' + self.__pdbId + '.ent',
                               forRelDirPathTupl[1], self.__pdbId + ".release_file", False)
        #
        if self.__extendedPdbId:
            self._insertReleseFile("beta_release_file", 'model', os.path.join(self._sessionPath, pdbFile), self.__extendedPdbId + ".pdb",
                                   forRelDirPathTupl[2], self.__extendedPdbId + ".beta_release_file", True)
        #
        self.__checkPDBFile(pdbFile)

    def __releasingPdbBundleFile(self, forRelDirPathTupl):
        logFile = 'generate_bundle_' + self._entryId + '.log'
        clogFile = 'generate_bundle_command_' + self._entryId + '.log'
        outputFile = 'bundle_file_' + self._entryId + '.index'
        mappingFile = self.__pdbId + '-chain-id-mapping.txt'
        self._removeFile(os.path.join(self._sessionPath, outputFile))
        self._removeFile(os.path.join(self._sessionPath, mappingFile))
        self._GetAndRunCmd('pdb', '${BINPATH}', 'GetPdbBundle', self._pickleData['model']['session_file'], outputFile, logFile, clogFile,
                           ' -output_mapping ' + mappingFile, messageType='warning')
        #
        if (not os.access(os.path.join(self._sessionPath, outputFile), os.F_OK)) or \
           (not os.access(os.path.join(self._sessionPath, mappingFile), os.F_OK)):
            self._insertEntryMessage(errType='pdb', errMessage='PDB bundle file(s) will not be generated.', messageType='warning', uniqueFlag=True)
            return
        #
        data = self._readFile(os.path.join(self._sessionPath, outputFile))
        #
        tarFileName = os.path.join(self._sessionPath, self.__pdbId + '-pdb-bundle.tar.gz')
        tar = tarfile.open(tarFileName, 'w:gz')
        for fileName in data.split('\n'):
            if not fileName:
                continue
            #
            tar.add(os.path.join(self._sessionPath, fileName), arcname=fileName)
        #
        tar.add(os.path.join(self._sessionPath, mappingFile), arcname=mappingFile)
        tar.close()
        self._insertReleseFile("release_file", 'model', tarFileName, self.__pdbId + '-pdb-bundle.tar.gz', forRelDirPathTupl[1],
                               self.__pdbId + ".release_file", False)

    def __releasingBioAssemblyFiles(self, program, fileType, forRelDirPathTupl):
        logFile = 'generate_biol_' + self._entryId + '_' + program + '.log'
        clogFile = 'generate_biol_command_' + self._entryId + '_' + program + '.log'
        indexFile = 'biol_file_' + self._entryId + '_' + program + '.index'
        self._removeFile(os.path.join(self._sessionPath, indexFile))
        option = ' -index ' + indexFile
        if fileType == 'cif':
            option += ' -public '
        #
        self._GetAndRunCmd(fileType, '${BINPATH}', program, self._pickleData['model']['session_file'], self.__pdbId, logFile, clogFile, option)
        if not os.access(os.path.join(self._sessionPath, indexFile), os.F_OK):
            self._insertEntryMessage(errType=fileType, errMessage='Generating bio-assembly file(s) failed.', uniqueFlag=True)
            return
        #
        data = self._readFile(os.path.join(self._sessionPath, indexFile))
        #
        for fileName in data.split('\n'):
            if not fileName:
                continue
            #
            self._insertReleseFile("release_file", 'model', os.path.join(self._sessionPath, fileName), fileName,
                                   forRelDirPathTupl[1], self.__pdbId + ".release_file", True)
            #
            if (fileType == 'cif') and self.__extendedPdbId:
                betaFileName = fileName.replace(self.__pdbId, self.__extendedPdbId)
                self._insertReleseFile("beta_release_file", 'model', os.path.join(self._sessionPath, fileName), betaFileName,
                                       forRelDirPathTupl[2], self.__extendedPdbId + ".beta_release_file", True)
            #
        #

    def __releasingSfFile(self):
        if not self._checkReleaseFlag('structure-factors'):
            return
        #
        self._insertReleseFile("release_file", 'structure-factors', self._pickleData['structure-factors']['session_file'], self.__pdbId + '-sf.cif',
                               self._forReleaseDirPathMap["structure-factors"][1], self.__pdbId + ".release_file", False)
        self.__checkingExperimentalDataFile('CheckSFFile', 'sf', self._pickleData['structure-factors']['session_file'])
        if self._entryDir['status_code_sf'] == 'REL':
            dList = self._pickleData['structure-factors']['session_file'].split('/')
            self.__checkCIFFile('sf', dList[-1], self.__dictBase + '.sdb', '', True)
            #
            if self.__extendedPdbId:
                generatedBetaSfFile = os.path.join(self._sessionPath, self._entryId + "-" + self.__extendedPdbId + "-sf.cif")
                if os.access(generatedBetaSfFile, os.F_OK):
                    self._insertReleseFile("beta_release_file", 'structure-factors', generatedBetaSfFile, self.__extendedPdbId + "-sf.cif",
                                           self._forReleaseDirPathMap["structure-factors"][2], self.__extendedPdbId + ".beta_release_file", True)
                else:
                    self._insertEntryMessage(errType='sf', errMessage='Generating ' + self.__extendedPdbId + '-sf.cif failed.', uniqueFlag=True)
                #
            #
        #

    def __releasingMrFile(self):
        if not self._checkReleaseFlag('nmr-restraints'):
            return
        #
        self._insertReleseFile("release_file", 'nmr-restraints', self._pickleData['nmr-restraints']['session_file'], self.__pdbId + '.mr',
                               self._forReleaseDirPathMap["nmr-restraints"][1], self.__pdbId + ".release_file", False)
        self.__checkingExperimentalDataFile('CheckMRFile', 'mr', self._pickleData['nmr-restraints']['session_file'])
        #
        if self.__extendedPdbId:
            self._insertReleseFile("beta_release_file", 'nmr-restraints', self._pickleData['nmr-restraints']['session_file'], self.__extendedPdbId + '.mr',
                                   self._forReleaseDirPathMap["nmr-restraints"][2], self.__extendedPdbId + ".beta_release_file", True)
        #

    def __releasingCsFile(self):
        if not self._checkReleaseFlag('nmr-chemical-shifts'):
            return
        #
        strFile = self.__pdbId + '_cs.str'
        logFile = 'str_logfile_' + self._entryId + '.log'
        self._GetAndRunCmd('cs', '${BINPATH}', 'GenNMRStarCSFile', self._pickleData['nmr-chemical-shifts']['session_file'],
                           strFile, '', logFile, ' -pdbid ' + self.__pdbId)
        #
        if not self._verifyGeneratingFile('cs', strFile):
            return
        #
        self._insertReleseFile("release_file", 'nmr-chemical-shifts', os.path.join(self._sessionPath, strFile), strFile,
                               self._forReleaseDirPathMap["nmr-chemical-shifts"][1], self.__pdbId + ".release_file",
                               False)
        self.__checkingExperimentalDataFile('CheckCSFile', 'cs', self._pickleData['nmr-chemical-shifts']['session_file'])
        #
        if not self.__extendedPdbId:
            return
        #
        strFile = self.__extendedPdbId + '_cs.str'
        logFile = 'str_logfile_' + self._entryId + '_beta.log'
        self._GetAndRunCmd('cs', '${BINPATH}', 'GenNMRStarCSFile', self._pickleData['nmr-chemical-shifts']['session_file'],
                           strFile, '', logFile, ' -pdbid ' + self.__extendedPdbId)
        #
        if self._verifyGeneratingFile('cs', strFile):
            self._insertReleseFile("beta_release_file", 'nmr-chemical-shifts',
                                   os.path.join(self._sessionPath, strFile), strFile,
                                   self._forReleaseDirPathMap["nmr-chemical-shifts"][2], self.__extendedPdbId + ".beta_release_file", True)
        #

    def __checkCIFFile(self, fileType, fileName, dictionary, ext, warningOnlyFlag):
        reportFile = fileName + '-diag.log'
        self._removeFile(os.path.join(self._sessionPath, reportFile))
        logFile = 'checking_cif_' + fileType + ext + '_' + self._entryId + '.log'
        self._removeFile(os.path.join(self._sessionPath, logFile))
        clogFile = 'checking_cif_' + fileType + ext + '_command_' + self._entryId + '.log'
        self._removeFile(os.path.join(self._sessionPath, clogFile))
        options = ' -dictSdb ' + os.path.join(self.__dictRoot, dictionary) + ' -f ' + fileName + ' 2> ' + clogFile + ' 1> ' + logFile
        self._GetAndRunCmd(fileType, '${DICTBINPATH}', 'CifCheck', '', '', '', '', options)
        self._processLogError(fileType, 'CifCheck', os.path.join(self._sessionPath, clogFile))
        self._processCheckReoprt(fileType, reportFile, fileName, False, warningOnlyFlag)

    def __checkXMLFile(self, xmlFile, xmlschema, version):
        reportFile = self.__pdbId + '.' + version + '.xml.diag'
        self._removeFile(os.path.join(self._sessionPath, reportFile))
        #
        cmd = "cd " + self._sessionPath + " ; " + self._bashSetting()
        #
        if not os.access(os.path.join(self._sessionPath, xmlschema), os.F_OK):
            cmd += " cp -f " + os.path.join(self.__dictRoot, xmlschema) + " . ; "
        #
        xmlPath = os.path.join(self._sessionPath, xmlFile)
        statinfo = os.stat(xmlPath)
        if statinfo.st_size < 100000000:
            cmd += " ${LOCALBINPATH}/xmllint --noout --schema " + os.path.join(self.__dictRoot, xmlschema) \
                + " " + xmlFile + " > " + reportFile + " 2>&1; "
        #
        cmd += " ${LOCALBINPATH}/StdInParse -s -f -n -v=always < " + xmlFile + " >> " + reportFile + " 2>&1; "
        self._insertAction(cmd)
        self._runCmd(cmd)
        self._processCheckReoprt('xml', reportFile, xmlFile, True, False)

    def __checkPDBFile(self, pdbFile):
        reportFile = self.__pdbId + '_pdb.report'
        logFile = 'checking_pdb_' + self._entryId + '.log'
        clogFile = 'checking_pdb_command_' + self._entryId + '.log'
        self._removeFile(os.path.join(self._sessionPath, reportFile))
        options = ' -status ' + self._entryDir['status_code'] + ' -obslte ' + self.__pdbId + '.obslte' \
            + ' -sprsde ' + self.__pdbId + '.sprsde' + ' -pdbid ' + self.__pdbId
        if ('directory' in self._entryDir) and self._entryDir['directory'] == 'modified':
            options += ' -re_release '
        #
        self.__runCheckingProcess('${BINPATH}', 'CheckPDBFile', pdbFile, reportFile, logFile, clogFile, options, 'pdb', True)

    def __checkingExperimentalDataFile(self, program, expType, expFile):
        reportFile = self.__pdbId + '_' + expType + '.report'
        logFile = 'checking_' + expType + '_' + self._entryId + '.log'
        self._removeFile(os.path.join(self._sessionPath, reportFile))
        #
        options = ' -pdbid ' + self.__pdbId
        if self._entryDir['status_code_' + expType] == 'REL':
            options += ' -rel_date ' + self._rel_date
        #
        self.__runCheckingProcess('${BINPATH}', program, expFile, reportFile, '', logFile, options, expType, True)

    def __runCheckingProcess(self, programPath, programName, inputFile, outputFile, logFile, clogFile, extraOptions, errType, missingFlag):
        self._GetAndRunCmd(errType, programPath, programName, inputFile, outputFile, logFile, clogFile, extraOptions)
        self._processCheckReoprt(errType, outputFile, inputFile, missingFlag, False)
