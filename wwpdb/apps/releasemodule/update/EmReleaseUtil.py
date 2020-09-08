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
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import os
import sys
import traceback

from mmcif_utils.trans.InstanceMapper import InstanceMapper
from wwpdb.utils.config.ConfigInfoData import ConfigInfoData
# from wwpdb.utils.emdb.cifEMDBTranslator.cifEMDBTranslator import CifEMDBTranslator
from wwpdb.utils.emdb.cif_emdb_translator.cif_emdb_translator import CifEMDBTranslator

from wwpdb.apps.releasemodule.update.EntryUpdateBase import EntryUpdateBase


class EmReleaseUtil(EntryUpdateBase):
    """ Class responsible for release/pull off entries
    """
    def __init__(self, reqObj=None, entryDir=None, verbose=False, log=sys.stderr):
        super(EmReleaseUtil, self).__init__(reqObj=reqObj, entryDir=entryDir, statusDB=None, verbose=verbose, log=log)
        #
        self.__additionalTypeList = [ [ 'em-mask-volume',       '_msk',        'masks',            False, True,  True  ],
                                      [ 'em-additional-volume', '_additional', 'other',            True,  True,  True  ],
                                      [ 'em-half-volume',       '_half_map',   'other',            True,  True,  True  ],
                                      [ 'fsc',                  '_fsc',        'fsc',              False, False, True  ],
                                      [ 'img-emdb',             '',            'images',           False, False, True  ],
                                      [ 'layer-lines',          '_ll',         'layerLines',       True,  False, False ],
                                      [ 'structure-factors',    '_sf',         'structureFactors', True,  False, False ] ]
        #
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
            self.__generateEMapHeader()
        #
        if (not EmXmlHeaderOnly) and (not self._blockEmErrorFlag):
            self.__getFileContentDictionary(emMapTypeList)
            mapFile = self._findArchiveFileName('em-volume', 'map', 'latest', '1')
            if os.access(mapFile, os.F_OK):   
                self._insertReleseFile('em-volume', mapFile, self.__embdId + '.map', 'map', True)
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
        self.__generateEMapHeader(validateFlag=True)
        #
        self._dumpLocalPickle()

    def __getFileContentDictionary(self, emMapTypeList):
        ciD = ConfigInfoData(siteId=self._siteId, verbose=self._verbose, log=self._lfh).getConfigDictionary()
        for typeList in self.__additionalTypeList:
            if typeList[4]:
                if emMapTypeList and (typeList[0] not in emMapTypeList):
                    continue
                #
            #
            self.__contentD[typeList[0]] = ciD['CONTENT_TYPE_DICTIONARY'][typeList[0]]
        #
        self.__formatD = ciD['FILE_FORMAT_EXTENSION_DICTIONARY']
        for k,v in self.__contentD.items():
            for formatType in v[0]:
                self.__fileExtContentTypeD[v[1] + '_' + self.__formatD[formatType]] = k + '_' + formatType
            #
        #

    def __generateEMapHeader(self, validateFlag=False):
        modelfile = os.path.join(self._sessionPath, self._entryId + self._fileTypeList[0][0])
        if not os.access(modelfile, os.F_OK):
            return
            # per DAOTHER-2459's request, removed automtically generating xml header file. It is controlled by 'GenEmXmlHeaderFlag' now.
#           modelfile = self._findArchiveFileName(self._fileTypeList[0][3], self._fileTypeList[0][4], 'latest', '1')
#           if not os.access(modelfile, os.F_OK):
#               return
#           #
        #
        emdfile = os.path.join(self._sessionPath, self.__embdId + '.cif')
        self._removeFile(emdfile)
        #
        im = InstanceMapper(verbose=self._verbose, log=self._lfh)
        im.setMappingFilePath(self._cI.get('SITE_EXT_DICT_MAP_EMD_FILE_PATH'))
        ok = im.translate(modelfile, emdfile, mode="src-dst")
        if ok:
            xmlfile = os.path.join(self._sessionPath, self.__embdId + '_v3.xml')
            #xmlfile = os.path.join(self._sessionPath, self.__embdId + '_v2.xml')
            self._removeFile(xmlfile)
            #
            status,error = self.__cif2xmlTranslate(emdfile, xmlfile, validateFlag)
            if validateFlag:
                self._removeFile(xmlfile)
            #
            if status == 'failed':
                self._insertEntryMessage(errType='em', errMessage='emd -> xml translation failed:\n' + error)
                #self._insertEntryMessage(errType='em', errMessage='emd -> xml translation failed:\n' + error, messageType='warning')
            elif error.find('ERROR') != -1:
                self._insertEntryMessage(errType='em', errMessage=error)
            elif error.find('WARNING') != -1:
                self._insertReleseFile('em-volume', xmlfile, self.__embdId + '_v3.xml', 'header', False)
                self._insertEntryMessage(errType='em', errMessage=error, messageType='warning')
            else:
                self._insertReleseFile('em-volume', xmlfile, self.__embdId + '_v3.xml', 'header', False)
                #self._insertReleseFile('em-volume', xmlfile, self.__embdId + '_v2.xml', 'header', False)
                #if (error.find('- WARNING -') != -1) or (error.find('- ERROR -') != -1):
                #    self._insertEntryMessage(errType='em', errMessage=error, messageType='warning')
                #
            #
        else:
            self._insertEntryMessage(errType='em', errMessage='em -> emd translation failed.')
            #self._insertEntryMessage(errType='em', errMessage='em -> emd translation failed.', messageType='warning')
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
            translator.read_emd_map_v2_cif_file()
            schema = os.path.join(self._cI.get('SITE_EM_DICT_PATH'), 'emdb-v3.xsd')
            if validateFlag:
                translator.translate_and_validate(in_cif=ciffile, out_xml=xmlfile, in_schema=schema)
            else:
                translator.translate(in_cif=ciffile, out_xml=xmlfile)
            #
            translator.write_logger_logs(write_error_log=True)
            #if translator.is_translation_log_empty and os.access(xmlfile, os.F_OK):
            if os.access(xmlfile, os.F_OK):
                status = 'ok'
            #
        except:
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
        return status,error

    """
    def __cif2xmlTranslate(self, ciffile, xmlfile):
        logFile = 'convert_em_xml_' + self._entryId + '.log'
        self._removeFile(os.path.join(self._sessionPath, logFile))
        logger = logging.getLogger()
        logging.captureWarnings(True)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(message)s")
        handler = logging.FileHandler(os.path.join(self._sessionPath, logFile))
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logging.info("Starting conversion for %s " % ciffile)
        #
        try:
            translator = CifEMDBTranslator()
            translator.readCifFile(ciffile)
            translator.translateCif2Xml()
            translator.writeXmlFile(xmlfile)
        except:
            logging.info("Map header translation failed for %s" % ciffile)
            self._lfh.write("+EmReleaseUtil.__cif2xmlTranslate failing for %s\n" % ciffile)
            se = traceback.format_exc()
            self._lfh.write("+EmReleaseUtil.__cif2xmlTranslate %s\n" % se)
        #
        status = 'failed'
        if os.access(xmlfile, os.F_OK):
            status = 'ok'
        #
        error = ''
        if os.access(os.path.join(self._sessionPath, logFile), os.F_OK):
            ifh = open(os.path.join(self._sessionPath, logFile), 'r')
            error = ifh.read()
            ifh.close()
        #
        if (not error) and status == 'failed':
            error = 'CifEMDBTranslator failed without error message'
        #
        return status,error
    """

    def __getAdditionalFilePartNumber(self):
        storagePath = os.path.join(self._cI.get('SITE_ARCHIVE_STORAGE_PATH'), 'archive', self._entryId)
        os.chdir(storagePath)
        for filename in os.listdir('.'):
            if not filename.startswith(self._entryId):
                continue
            #

            fFields = str(filename).strip().split('.')
            baseName = str(fFields[0]).strip()
            formatExt = str(fFields[1]).strip()
            nFields = baseName.split('_')
            fileExt = nFields[2] + '_' + formatExt
            if not fileExt in self.__fileExtContentTypeD:
                continue
            #
            ContentType = self.__fileExtContentTypeD[fileExt]
            PartNumber = str(nFields[3]).strip().replace('P', '')
            if ContentType in self.__partD:
                if PartNumber not in self.__partD[ContentType]:
                    self.__partD[ContentType].append(PartNumber)
                #
            else:
                self.__partD[ContentType] = [ PartNumber ]
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
                contentType = typeList[0]+ '_' + fType
                if not contentType in self.__partD:
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
