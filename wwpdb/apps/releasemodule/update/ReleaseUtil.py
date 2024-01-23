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
from wwpdb.apps.releasemodule.update.NmrDataGenerator import NmrDataGenerator


class ReleaseUtil(EntryUpdateBase):
    """ Class responsible for generating and checking release files
    """
    def __init__(self, reqObj=None, entryDir=None, verbose=False, log=sys.stderr):
        super(ReleaseUtil, self).__init__(reqObj=reqObj, entryDir=entryDir, statusDB=None, verbose=verbose, log=log)
        #
        self.__pdbId = self._entryDir['pdb_id'].lower()
        self.__dictRoot = os.path.abspath(self._cICommon.get_mmcif_dict_path())
        self.__dictBase = self._cICommon.get_mmcif_archive_current_dict_filename()
        # 0        1              2                            3                         4                         5           6           7
        # version, cif_extension, current_internal_dictionary, target_public_dictionary, xml_convertor_dictionary, xml_prefix, xml_schema, xml_extension
        self.__CifXmlInfo = self.__readDictionaryInfo()
        if not self.__CifXmlInfo:
            # """
            # self.__CifXmlInfo = [ \
            #   [ 'v4', '.cif', self._cI.get('SITE_PDBX_DICT_NAME') + '.sdb', self._cI.get('SITE_PDBX_V4_DICT_NAME') + '.sdb', 'mmcif_pdbx_v42.odb', \
            #     'pdbx-v42', 'pdbx-v42.xsd', [ [ '.cif.xml', '.xml' ], [ '.cif.xml-noatom', '-noatom.xml' ], [ '.cif.xml-extatom', '-extatom.xml' ] ] ],
            #   [ 'v5', '.v5.cif', 'mmcif_pdbx_v50.sdb', 'mmcif_pdbx_v50.sdb', 'mmcif_pdbx_v50.odb', 'pdbx-v50', 'pdbx-v50.xsd', \
            #     [ [ '.v5.cif.xml', '.v5.xml' ], [ '.v5.cif.xml-noatom', '-noatom.v5.xml' ], [ '.v5.cif.xml-extatom', '-extatom.v5.xml' ] ] ]
            # ]
            # """
            self.__CifXmlInfo = [
                ['v5', '.cif', 'mmcif_pdbx_v50.sdb', 'mmcif_pdbx_v50.sdb', 'mmcif_pdbx_v50.odb', 'pdbx-v50', 'pdbx-v50.xsd',
                 [['.cif.xml', '.xml'], ['.cif.xml-noatom', '-noatom.xml'], ['.cif.xml-extatom', '-extatom.xml']]]
            ]
        #
        self.__errorKeyWordList = []
        self.__readErrorKeyWordList()

    def run(self):
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
            if ('status_code_em' in self._pickleData) and self._pickleData['status_code_em']:
                self._insertFileStatus('em', False)
            #
        #
        self._dumpLocalPickle()

    def __readErrorKeyWordList(self):
        fPath = os.path.join(self._reqObj.getValue('TemplatePath'), 'cif_xml_error_list')
        sIn = self.__readFile(fPath)
        #
        lineList = sIn.split('\n')
        for line in lineList:
            if not line:
                continue
            #
            if line[0] == '#':
                continue
            #
            keylist = line.split(';')
            self.__errorKeyWordList.append(keylist)
        #

    def __readFile(self, filePath):
        """
        """
        ifh = open(filePath, 'r')
        data = ifh.read()
        ifh.close()
        #
        return data

    def __readDictionaryInfo(self):
        """ Read dictionary information for converting public mmCIF and XML files
        """
        fPath = os.path.join(self._reqObj.getValue("TemplatePath"), 'dictionary_info_list')
        if not os.access(fPath, os.F_OK):
            self._lfh.write("+ReleaseUtil.__readDictionaryInfo - Can not find dictionary information file %s\n" % fPath)
            return []
        #
        sIn = self.__readFile(fPath)
        #
        cifXmlInfoList = []
        lineList = sIn.split('\n')
        for line in lineList:
            line = line.strip().replace(' ', '')
            if not line:
                continue
            #
            if line[0] == '#':
                continue
            #
            elementList = line.split(',')
            infoList = []
            xmlTypes = []
            for element in elementList:
                sList = element.split(':')
                if len(sList) == 1:
                    infoList.append(element)
                elif len(sList) == 2:
                    xmlTypes.append(sList)
                else:
                    self._lfh.write("+ReleaseUtil.__readDictionaryInfo - Incorrect value %s in line %s\n" % (element, line))
                #
            #
            infoList.append(xmlTypes)
            cifXmlInfoList.append(infoList)
        #
        return cifXmlInfoList

    def __releasingModelFiles(self):
        if not self.__checkReleaseFlag('model'):
            return
        #
#       for cifxmlInfo in self.__CifXmlInfo:
#           if (cifxmlInfo[0] == 'v5') and (not self._EMEntryFlag):
#               continue
#           #
#           self.__releasingCIFFile(cifxmlInfo)
#           self.__releasingXMLFiles(cifxmlInfo)
#       #
        cifxmlInfo = ('v5', '.cif', self.__dictBase + '.sdb', self.__dictBase + '.sdb', self.__dictBase + '.odb', 'pdbx-v50', 'pdbx-v50.xsd',
                      (('.cif.xml', '.xml'), ('.cif.xml-noatom', '-noatom.xml'), ('.cif.xml-extatom', '-extatom.xml')))
        #
        self.__releasingCIFFile(cifxmlInfo)
        self.__releasingXMLFiles(cifxmlInfo)
        self.__runMiscChecking()
        #
        if self._entryDir['status_code'] == 'RELOAD':
            return
        #
        if ('big_entry' in self._pickleData) and self._pickleData['big_entry']:
            self.__releasingPdbBundleFile()
            self.__releasingBioAssemblyFiles('GenBioCIFFile', 'cif')
        else:
            self.__releasingPDBFile()
            self.__releasingBioAssemblyFiles('GenBioCIFFile', 'cif')
            self.__releasingBioAssemblyFiles('GenBioPDBFile', 'pdb')
        #

    def __releasingCIFFile(self, cifxmlInfo):
        cifFile = self.__pdbId + cifxmlInfo[1]
        # self._removeFile(os.path.join(self._sessionPath, cifFile))
        logFile = 'generate_cif_' + cifxmlInfo[0] + '_' + self._entryId + '.log'
        # self._removeFile(os.path.join(self._sessionPath, logFile))
        clogFile = 'generate_cif_command_' + cifxmlInfo[0] + '_' + self._entryId + '.log'
        # self._removeFile(os.path.join(self._sessionPath, clogFile))
        options = ' -dicSdb ' + os.path.join(self.__dictRoot, cifxmlInfo[2]) + ' -pdbxDicSdb ' \
            + os.path.join(self.__dictRoot, cifxmlInfo[3]) + ' -reorder -strip -op in -pdbids 2> ' \
            + clogFile + ' 1> ' + logFile
        self._GetAndRunCmd('cif', '${DICTBINPATH}', 'cifexch2', self._pickleData['model']['session_file'], cifFile, '', '', options)
        # self._processLogError('cif', 'cifexch2', os.path.join(self._sessionPath, clogFile))
        if not self.__verifyGeneratingFile('cif', cifFile):
            return
        #
        self._insertFileStatus('cif', True)
        self._insertReleseFile('model', os.path.join(self._sessionPath, cifFile), cifFile, '', True)
        self.__checkCIFFile('cif', cifFile, cifxmlInfo[3], '_' + cifxmlInfo[0], False)

    def __releasingXMLFiles(self, cifxmlInfo):
        cifFile = self.__pdbId + cifxmlInfo[1]
        if not os.access(os.path.join(self._sessionPath, cifFile), os.F_OK):
            return
        #
        for xmlType in cifxmlInfo[7]:
            self._removeFile(os.path.join(self._sessionPath, self.__pdbId + xmlType[0]))
        #
        logFile = 'generate_xml_' + cifxmlInfo[0] + '_' + self._entryId + '.log'
        self._removeFile(os.path.join(self._sessionPath, logFile))
        clogFile = 'generate_xml_command_' + cifxmlInfo[0] + '_' + self._entryId + '.log'
        self._removeFile(os.path.join(self._sessionPath, clogFile))
        options = ' -dictName mmcif_pdbx.dic -df ' + os.path.join(self.__dictRoot, cifxmlInfo[4]) \
            + ' -prefix ' + cifxmlInfo[5] + ' -ns PDBx -funct mmcif2xmlall -f ' + cifFile + ' 2> ' + clogFile + ' 1> ' + logFile
        self._GetAndRunCmd('xml', '${DICTBINPATH}', 'mmcif2XML', '', '', '', '', options)
        self._processLogError('xml', '', os.path.join(self._sessionPath, logFile))
        self._processLogError('xml', '', os.path.join(self._sessionPath, clogFile))

        self._insertFileStatus('xml', True)
        for xmlType in cifxmlInfo[7]:
            if not self.__verifyGeneratingFile('xml', self.__pdbId + xmlType[0]):
                continue
            #
            self._insertReleseFile('model', os.path.join(self._sessionPath, self.__pdbId + xmlType[0]), self.__pdbId + xmlType[1], '', True)
            #
            if xmlType[0].endswith('.xml-noatom'):
                self.__checkXMLFile(self.__pdbId + xmlType[0], cifxmlInfo[6], cifxmlInfo[0])
            #
        #

    def __runMiscChecking(self):
        outputFile = self._entryId + '_MiscChecking.txt'
        logFile = self._entryId + '_MiscChecking.log'
        clogFile = self._entryId + '_MiscChecking_command.log'
        self._GetAndRunCmd('', '${BINPATH}', 'MiscChecking', self._pickleData['model']['session_file'], outputFile, logFile, clogFile, ' -released ')
        #
        if not os.access(os.path.join(self._sessionPath, outputFile), os.F_OK):
            return
        #
        data = self.__readFile(os.path.join(self._sessionPath, outputFile))
        if data:
            self._insertEntryMessage(errType="MiscChecking", errMessage=data, messageType='warning', uniqueFlag=True)
        #

    def __releasingPDBFile(self):
        pdbFile = self._entryId + '_model_P1.pdb'
        # self._removeFile(os.path.join(self._sessionPath, pdbFile))
        logFile = 'generate_pdb_' + self._entryId + '.log'
        clogFile = 'generate_pdb_command_' + self._entryId + '.log'
        self._GetAndRunCmd('pdb', '${BINPATH}', 'maxit', self._pickleData['model']['session_file'], pdbFile, logFile, clogFile, ' -o 2 ')
        if not self.__verifyGeneratingFile('pdb', pdbFile):
            return
        #
        self._insertFileStatus('pdb', True)
        self._insertArchivalFile('model', 'pdb', pdbFile, False)
        self._insertReleseFile('model', os.path.join(self._sessionPath, pdbFile), 'pdb' + self.__pdbId + '.ent', '', False)
        self.__checkPDBFile(pdbFile)

    def __releasingPdbBundleFile(self):
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
        data = self.__readFile(os.path.join(self._sessionPath, outputFile))
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
        self._insertReleseFile('model', tarFileName, self.__pdbId + '-pdb-bundle.tar.gz', '', False)

    def __releasingBioAssemblyFiles(self, program, fileType):
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
        data = self.__readFile(os.path.join(self._sessionPath, indexFile))
        #
        for fileName in data.split('\n'):
            if not fileName:
                continue
            #
            self._insertReleseFile('model', os.path.join(self._sessionPath, fileName), fileName, '', True)
        #

    def __releasingSfFile(self):
        if not self.__checkReleaseFlag('structure-factors'):
            return
        #
        self._insertReleseFile('structure-factors', self._pickleData['structure-factors']['session_file'], self.__pdbId + '-sf.cif', '', False)
        self.__checkingExperimentalDataFile('CheckSFFile', 'sf', self._pickleData['structure-factors']['session_file'])
        if self._entryDir['status_code_sf'] == 'REL':
            dList = self._pickleData['structure-factors']['session_file'].split('/')
            self.__checkCIFFile('sf', dList[-1], self.__dictBase + '.sdb', '', True)
        #

    def __releasingMrFile(self):
        if not self.__checkReleaseFlag('nmr-restraints'):
            return
        #
        self._insertReleseFile('nmr-restraints', self._pickleData['nmr-restraints']['session_file'], self.__pdbId + '.mr', '', False)
        self.__checkingExperimentalDataFile('CheckMRFile', 'mr', self._pickleData['nmr-restraints']['session_file'])

    def __releasingCsFile(self):
        if not self.__checkReleaseFlag('nmr-chemical-shifts'):
            return
        #
        strFile = self.__pdbId + '_cs.str'
        logFile = 'str_logfile_' + self._entryId + '.log'
        self._GetAndRunCmd('cs', '${BINPATH}', 'GenNMRStarCSFile', self._pickleData['nmr-chemical-shifts']['session_file'],
                           strFile, '', logFile, ' -pdbid ' + self.__pdbId)
        #
        if not self.__verifyGeneratingFile('cs', strFile):
            return
        #
        self._insertReleseFile('nmr-chemical-shifts', os.path.join(self._sessionPath, strFile), strFile, '', False)
        self.__checkingExperimentalDataFile('CheckCSFile', 'cs', self._pickleData['nmr-chemical-shifts']['session_file'])

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
        self.__processCheckReoprt(fileType, reportFile, fileName, False, warningOnlyFlag)

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
        self.__processCheckReoprt('xml', reportFile, xmlFile, True, False)

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
        self.__processCheckReoprt(errType, outputFile, inputFile, missingFlag, False)

    def __processCheckReoprt(self, errType, reportFile, sourceFile, missingFlag, warningOnlyFlag):
        status, msg = self._getLogMessage('', os.path.join(self._sessionPath, reportFile))
        if status == 'not found':
            if missingFlag:
                self._insertEntryMessage(errType=errType, errMessage='Checking releasing ' + errType + ' failed.', messageType='warning', uniqueFlag=True)
            #
            return
        #
        if not msg:
            return
        #
        msg_length = len(msg)
        msgList = msg.split('\n')
        msg = ''
        foudValue = False
        block_flag = False
        count = 0
        for line in msgList:
            if self.__containErrorKeyWords(line):
                block_flag = True
            #
            msg += line + '\n'
            count += 1
            if (count > 500) and (msg_length > 10000):
                break
            #
            strip_line = line.strip()
            if strip_line == sourceFile + ' validates':
                continue
            elif strip_line == '':
                continue
            elif strip_line.startswith('stdin:'):
                continue
            else:
                foudValue = True
            #
        #
        if not foudValue:
            return
        #
        msgType = 'warning'
        if block_flag:
            msgType = 'error'
        #
        if warningOnlyFlag:
            msgType = 'warning'
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
