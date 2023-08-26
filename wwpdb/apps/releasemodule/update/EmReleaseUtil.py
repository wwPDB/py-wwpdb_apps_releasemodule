##
# File:  EmReleaseUtil.py
# Date:  17-Oct-2016
# Updates:
##
"""
Class responsible for release/pull off entries

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
import traceback

from wwpdb.apps.releasemodule.update.EntryUpdateBase import EntryUpdateBase
from wwpdb.utils.config.ConfigInfoData import ConfigInfoData
from wwpdb.utils.emdb.cif_emdb_translator.cif_emdb_translator import CifEMDBTranslator


class EmReleaseUtil(EntryUpdateBase):
    """ Class responsible for release/pull off entries
    """
    def __init__(self, reqObj=None, entryDir=None, verbose=False, log=sys.stderr):
        super(EmReleaseUtil, self).__init__(reqObj=reqObj, entryDir=entryDir, statusDB=None, verbose=verbose, log=log)
        # fmt: off
        self.__additionalTypeList = [ [ 'em-mask-volume',       '_msk',        'masks',            False, True,  True  ],
                                      [ 'em-additional-volume', '_additional', 'other',            True,  True,  True  ],
                                      [ 'em-half-volume',       '_half_map',   'other',            True,  True,  True  ],
                                      [ 'fsc',                  '_fsc',        'fsc',              False, False, True  ],
                                      [ 'img-emdb',             '',            'images',           False, False, True  ],
                                      [ 'layer-lines',          '_ll',         'layerLines',       True,  False, False ],
                                      [ 'structure-factors',    '_sf',         'structureFactors', True,  False, False ] ]
        # fmt: on
        self.__embdId = self._entryDir['emdb_id'].replace('-', '_').lower()
        self.__contentD = {}
        self.__formatD = {}
        self.__fileExtContentTypeD = {}
        self.__partD = {}

    def run(self, emMapTypeList, GenEmXmlHeaderFlag, EmXmlHeaderOnly):
        self._loadLocalPickle()
        if self._blockErrorFlag or self._blockEmErrorFlag:
            return
        #
        if GenEmXmlHeaderFlag:
            self._generateEmCifHeader()
            self._generateEmXmlHeader()
        #
        if (not EmXmlHeaderOnly) and (not self._blockEmErrorFlag):
            emVolumeContentInfo = self.__getFileContentDictionary(emMapTypeList)
            # checking file matching with em_map category: DAOTHER-6570/DAOTHER-5842
            mapFile = ""
            fileType = ""
            if emMapTypeList:
                contentTypeInFileName = emVolumeContentInfo[1]
                if (contentTypeInFileName in emMapTypeList) and emMapTypeList[contentTypeInFileName]:
                    for part_type_info in emMapTypeList[contentTypeInFileName]:
                        part_type_split = part_type_info.split("_")
                        if len(part_type_split) != 2:
                            continue
                        #
                        for formatType in emVolumeContentInfo[0]:
                            if self.__formatD[formatType] == part_type_split[1]:  # file type match
                                tmpFile = self._findArchiveFileName("em-volume", formatType, "latest", part_type_split[0])
                                if os.access(tmpFile, os.F_OK):
                                    mapFile = tmpFile
                                    fileType = part_type_split[1]
                                    break
                                #
                            #
                        #
                        if mapFile:
                            break
                        #
                    #
                #
            else:
                mapFile = self._findArchiveFileName('em-volume', 'map', 'latest', '1')
                fileType = "map"
            #
            if mapFile and os.access(mapFile, os.F_OK):
                self._insertReleseFile('em-volume', mapFile, self.__embdId + '.' + fileType, 'map', True)
            #
            self.__getAdditionalFilePartNumber()
            self.__releaseAdditionalFiles()
        #
        self._dumpLocalPickle()

    def validateXml(self):
        self._loadLocalPickle()
        if self._blockErrorFlag or self._blockEmErrorFlag:
            return
        #
        self._generateEmXmlHeader(removeFlag=True)
        #
        self._dumpLocalPickle()

    def __getFileContentDictionary(self, emMapTypeList):
        """
        """
        em_map_selected_list = []
        ciD = ConfigInfoData(siteId=self._siteId, verbose=self._verbose, log=self._lfh).getConfigDictionary()
        self.__formatD = ciD['FILE_FORMAT_EXTENSION_DICTIONARY']
        for typeList in self.__additionalTypeList:
            # checking file matching with em_map category: DAOTHER-6570/DAOTHER-5842
            if typeList[4]:
                contentTypeInFileName = ciD['CONTENT_TYPE_DICTIONARY'][typeList[0]][1]
                if emMapTypeList and (contentTypeInFileName not in emMapTypeList):
                    continue
                #
                found = False
                for part_type_info in emMapTypeList[contentTypeInFileName]:
                    part_type_split = part_type_info.split("_")
                    if len(part_type_split) != 2:
                        continue
                    #
                    for formatType in ciD['CONTENT_TYPE_DICTIONARY'][typeList[0]][0]:
                        if self.__formatD[formatType] == part_type_split[1]:  # file type match
                            contentFormatType = typeList[0] + '_' + formatType
                            if contentFormatType in self.__partD:
                                if part_type_split[0] not in self.__partD[contentFormatType]:
                                    self.__partD[contentFormatType].append(part_type_split[0])
                                #
                            else:
                                self.__partD[contentFormatType] = [part_type_split[0]]
                            #
                            found = True
                            break
                        #
                    #
                #
                if found:
                    em_map_selected_list.append(typeList[0])
                #
            #
            self.__contentD[typeList[0]] = ciD['CONTENT_TYPE_DICTIONARY'][typeList[0]]
        #
        for k, v in self.__contentD.items():
            if k in em_map_selected_list:
                continue
            #
            for formatType in v[0]:
                self.__fileExtContentTypeD[v[1] + '_' + self.__formatD[formatType]] = k + '_' + formatType
            #
        #
        return ciD['CONTENT_TYPE_DICTIONARY']['em-volume']

    def _generateEmCifHeader(self):
        """
        """
        modelfile = os.path.join(self._sessionPath, self._entryId + self._fileTypeList[0][0])
        if not os.access(modelfile, os.F_OK):
            return
        #
        cifFile = self.__embdId.replace("_", "-") + ".cif"
        logFile = "generate_em_header_cif_" + self._entryId + ".log"
        clogFile = "generate_em_header_cif_command_" + self._entryId + ".log"
        outputList = []
        outputList.append((cifFile, True))
        outputList.append((logFile, True))
        outputList.append((clogFile, True))
        self._dpUtilityApi(operator="annot-cif-to-pdbx-em-header", inputFileName=modelfile, outputFileNameTupList=outputList)
        #
        cifFilePath = os.path.join(self._sessionPath, cifFile)
        if not os.access(cifFilePath, os.F_OK):
            self._insertEntryMessage(errType="em", errMessage="Generating " + cifFile + " failed.")
            return
        #
        self._insertReleseFile("em-volume", cifFilePath, cifFile, "metadata", True)

    def _generateEmXmlHeader(self, validateFlag=True, removeFlag=False):
        modelfile = os.path.join(self._sessionPath, self._entryId + self._fileTypeList[0][0])
        if not os.access(modelfile, os.F_OK):
            return
            # per DAOTHER-2459's request, removed automtically generating xml header file. It is controlled by 'GenEmXmlHeaderFlag' now.
            # modelfile = self._findArchiveFileName(self._fileTypeList[0][3], self._fileTypeList[0][4], 'latest', '1')
            # if not os.access(modelfile, os.F_OK):
            #    return
            #
        #
        xmlfile = os.path.join(self._sessionPath, self.__embdId + '_v3.xml')
        self._removeFile(xmlfile)
        #
        status, error = self.__cif2xmlTranslate(modelfile, xmlfile, validateFlag)
        if removeFlag:
            self._removeFile(xmlfile)
        #
        if status == 'failed':
            self._insertEntryMessage(errType='em', errMessage='emd -> xml translation failed:\n' + error)
        elif error.find('ERROR') != -1:
            self._insertEntryMessage(errType='em', errMessage=error)
        elif error.find('WARNING') != -1:
            self._insertReleseFile('em-volume', xmlfile, self.__embdId + '_v3.xml', 'header', False)
            self._insertEntryMessage(errType='em', errMessage=error, messageType='warning')
        else:
            self._insertReleseFile('em-volume', xmlfile, self.__embdId + '_v3.xml', 'header', False)
        #

    def __cif2xmlTranslate(self, ciffile, xmlfile, validateFlag):
        logFile = 'convert_em_xml_' + self._entryId + '.log'
        logFilePath = os.path.join(self._sessionPath, logFile)
        self._removeFile(logFilePath)
        #
        status = 'failed'
        error = ''
        try:
            translator = CifEMDBTranslator()
            translator.set_logger_logging(log_error=True, error_log_file_name=logFilePath)
            # translator.read_emd_map_v2_cif_file()
            if validateFlag:
                translator.translate_and_validate(in_cif=ciffile, out_xml=xmlfile)
            else:
                translator.translate(in_cif=ciffile, out_xml=xmlfile)
            #
            translator.write_logger_logs(write_error_log=True)
            # if translator.is_translation_log_empty and os.access(xmlfile, os.F_OK):
            if os.access(xmlfile, os.F_OK):
                status = 'ok'
            #
        except:  # noqa: E722 pylint: disable=bare-except
            error = traceback.format_exc()
        #
        if os.access(logFilePath, os.F_OK):
            ifh = open(logFilePath, 'r')
            msg = ifh.read()
            ifh.close()
            if msg:
                if error:
                    error += '\n'
                #
                error += msg
            #
        #
        if (not error) and status == 'failed':
            error = 'CifEMDBTranslator failed without error message'
        #
        return status, error

    def __getAdditionalFilePartNumber(self):
        storagePath = os.path.join(self._cI.get('SITE_ARCHIVE_STORAGE_PATH'), 'archive', self._entryId)
        for filename in os.listdir(storagePath):
            if not filename.startswith(self._entryId):
                continue
            #

            fFields = str(filename).strip().split('.')
            baseName = str(fFields[0]).strip()
            formatExt = str(fFields[1]).strip()
            nFields = baseName.split('_')
            fileExt = nFields[2] + '_' + formatExt
            if fileExt not in self.__fileExtContentTypeD:
                continue
            #
            ContentType = self.__fileExtContentTypeD[fileExt]
            PartNumber = str(nFields[3]).strip().replace('P', '')
            if ContentType in self.__partD:
                if PartNumber not in self.__partD[ContentType]:
                    self.__partD[ContentType].append(PartNumber)
                #
            else:
                self.__partD[ContentType] = [PartNumber]
            #
        #

    def __releaseAdditionalFiles(self):
        if not self.__partD:
            return
        #
        for typeList in self.__additionalTypeList:
            if typeList[0] not in self.__contentD:
                continue
            #
            for fType in self.__contentD[typeList[0]][0]:
                contentType = typeList[0] + '_' + fType
                if contentType not in self.__partD:
                    continue
                #
                formatExt = self.__formatD[fType]
                #
                for part in self.__partD[contentType]:
                    partExt = ''
                    if typeList[2] in ['fsc', 'images']:
                        # These files can be present with multiple but the first is considered the primary of it's type
                        # The first is of the format name.format
                        # All subsequent are of the format name_partnumber.format
                        if int(part) > 1:
                            partExt = '_' + part
                    elif len(self.__partD[contentType]) > 1 or typeList[2] in ['masks', 'other']:
                        partExt = '_' + part
                    #
                    sourcePath = self._findArchiveFileName(typeList[0], fType, 'latest', part)
                    if (not sourcePath) or (not os.access(sourcePath, os.F_OK)):
                        continue
                    #
                    self._insertReleseFile('em-volume', sourcePath, self.__embdId + typeList[1] + partExt + '.' + formatExt, typeList[2], typeList[3])
                #
            #
        #
