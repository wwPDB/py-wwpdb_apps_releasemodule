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

import gzip,json,os,sys,time,traceback

from wwpdb.apps.releasemodule.update.EntryUpdateBase import EntryUpdateBase
from wwpdb.io.file.mmCIFUtil import mmCIFUtil
from wwpdb.utils.config.ConfigInfoData import ConfigInfoData
from wwpdb.utils.emdb.cif_emdb_translator.cif_emdb_translator import CifEMDBTranslator


class EmReleaseUtil(EntryUpdateBase):
    """ Class responsible for release/pull off entries
    """
    def __init__(self, reqObj=None, entryDir=None, verbose=False, log=sys.stderr):
        super(EmReleaseUtil, self).__init__(reqObj=reqObj, entryDir=entryDir, statusDB=None, verbose=verbose, log=log)
#       self._lfh.write("Metadata type: %s\n" % self.__emInfoList[-1][0])
        #
        self.__additionalStart = 4
        #
        # tuple[0]: audit revision data content type
        # tuple[1]: file content type
        # tuple[2]: file content type naming
        # tuple[3]: file format extension
        # tuple[4]: public file content type naming
        # tuple[5]: release sub directory
        # tuple[6]: has audit revision record or not
        # tuple[7]: compress public released file or not
        #
        # fmt: off
        self.__emInfoList = [[ "Primary map",       "em-volume",            "em-volume",            "map", "",            "map",              True,  True  ],
                             [ "Half map",          "em-half-volume",       "em-half-volume",       "map", "_half_map",   "other",            True,  True  ],
                             [ "Mask",              "em-mask-volume",       "em-mask-volume",       "map", "_msk",        "masks",            True,  False ],
                             [ "Additional map",    "em-additional-volume", "em-additional-volume", "map", "_additional", "other",            True,  True  ],
                             [ "FSC",               "fsc",                  "fsc-xml",              "xml", "_fsc",        "fsc",              True,  False ],
                             [ "Image",             "img-emdb",             "img-emdb",             "",    "",            "images",           True,  False ],
                             [ "Structure factors", "structure-factors",    "sf",                   "cif", "_sf",         "structureFactors", False, True  ],
                             [ "Layer lines",       "layer-lines",          "layer-lines",          "txt", "_ll",         "layerLines",       False, True  ],
                             [ "EM metadata",       "model",                "model",                "cif", "",            "",                 True,  False ]
                             ]
        # fmt: on
        self.__newReleaseFlag = False
        self.__map_release_date = ""
        #
        self.__storagePath = os.path.join(self._cI.get("SITE_ARCHIVE_STORAGE_PATH"), "archive", self._entryId)
        self.__embdId = self._entryDir["emdb_id"].replace("-", "_").lower()
        #
        self.__contentTypeFileExtD = self.__getContentTypeFileExtension()
        self.__archivalFilePathList = []
        self.__releaseFileList = []
        self.__mapDataContentTypeList = []
        self.__currentMapPartListMap = {}
        #
        self.__neededInitialReleaseTypeList = []
        self.__lastReleaseInfoMap = {}

    def getEmReleaseInfo(self, EmXmlHeaderOnly):
        """ Get EM experimental data release information
        """
        self._loadLocalPickle()
        #
        jsonFile = self._entryId + "_em_info.json"
        logFile = "generate_em_info_" + self._entryId + ".log"
        clogFile = "generate_em_info_command_" + self._entryId + ".log"
        outputList = []
        outputList.append((jsonFile, True))
        outputList.append((logFile, True))
        outputList.append((clogFile, True))
        self._dpUtilityApi(operator="annot-get-em-exp-info", inputFileName=self._pickleData["model"]["session_file"], outputFileNameTupList=outputList)
        #
        jsonFilePath = os.path.join(self._sessionPath, jsonFile)
        if os.access(jsonFilePath, os.F_OK):
            with open(jsonFilePath) as DATA:
                emInfoObj = json.load(DATA)
            #
            self.__newReleaseFlag = True
            #
            if "map_release_date" in emInfoObj:
                self.__map_release_date = emInfoObj["map_release_date"]
                if (self.__map_release_date != "") and (self.__map_release_date != self._rel_date):
                    self.__newReleaseFlag = False
                #
            #
            self.__getEmMapFileList(emInfoObj, EmXmlHeaderOnly)
            self.__getPreviousReleaseInfo(emInfoObj)
        #
        if not EmXmlHeaderOnly:
            self.__getAdditionalEmFileList()
        #
        self._dumpLocalPickle()

    def validateXml(self):
        self._loadLocalPickle()
        if self._blockErrorFlag or self._blockEmErrorFlag:
            return
        #
        self.__generateEmXmlHeader(removeFlag=True)
        #
        self._dumpLocalPickle()

    def getEmUpdatedInfoList(self):
        """ Generate EM experimental file releaseing information
        """
        updatedList,fileNameList = self.__getMissingInitialInfoList()
        if len(self.__releaseFileList) > 0:
            revision_type = "Data updated"
            if self.__newReleaseFlag:
                revision_type = "Initial release"
            #
            for releaseTuple in self.__releaseFileList:
                emInfo = releaseTuple[0]
                if emInfo[0] == "EM metadata":
                    continue
                #
                for fileTuple in releaseTuple[1]:
                    fFields = str(fileTuple[0]).strip().split("/")
                    #
                    if fFields[-1] in fileNameList:
                        continue
                    #
                    myD = {}
                    myD["data_content_type"] = emInfo[0]
                    myD["revision_type"] = revision_type
                    myD["file_name"] = fFields[-1]
                    if len(fileTuple[3]) > 0:
                        myD["part_number"] = fileTuple[3]
                    else:
                        myD["part_number"] = "?"
                    #
                    updatedList.append(myD)
                #
            #
        #
        return updatedList

    def run(self, GenEmXmlHeaderFlag, EmXmlHeaderOnly):
        """ Run EM experimental data release process
        """
        self._loadLocalPickle()
        if self._blockErrorFlag or self._blockEmErrorFlag:
            return
        #
        if GenEmXmlHeaderFlag:
            self.__generateEmCifHeader()
            self.__generateEmXmlHeader()
        #
        if EmXmlHeaderOnly or self._blockEmErrorFlag or (len(self.__releaseFileList) == 0):
            self._dumpLocalPickle()
            return
        #
        for releaseTuple in self.__releaseFileList:
            emInfo = releaseTuple[0]
            for fileTuple in releaseTuple[1]:
                fFields = str(fileTuple[0]).strip().split(".")
                formatExt = fFields[-2]
                #
                partNumber = ""
                if len(fileTuple[3]) > 0:
                    partNumber = "_" + fileTuple[3]
                #
                self._insertReleseFile("em-volume", fileTuple[0], self.__embdId + emInfo[4] + partNumber + "." + formatExt, emInfo[5], emInfo[7])
            #
        #
        self._dumpLocalPickle()

    def __getContentTypeFileExtension(self):
        """ Get file extension list map
        """
        contentTypeFileExtD = {}
        #
        ciD = ConfigInfoData(siteId=self._siteId, verbose=self._verbose, log=self._lfh).getConfigDictionary()
        #
        formatD = ciD["FILE_FORMAT_EXTENSION_DICTIONARY"]
        #
        for emInfo in self.__emInfoList:
            if emInfo[3] != "":
                contentTypeFileExtD[emInfo[1]] = [ emInfo[3] ]
            else:
                extList = []
                for formatType in ciD["CONTENT_TYPE_DICTIONARY"][emInfo[1]][0]:
                    if formatType in formatD:
                        extList.append(formatD[formatType])
                    #
                #
                if len(extList) > 0:
                    contentTypeFileExtD[emInfo[1]] = extList
                #
            #
        #
        return contentTypeFileExtD

    def __getEmMapFileList(self, emInfoObj, EmXmlHeaderOnly):
        """ Get EM map file names from "em_map" category.
        """
        #
        if "em_map" not in emInfoObj:
            return
        #
        for emInfo in self.__emInfoList[:self.__additionalStart]:
            self.__mapDataContentTypeList.append(emInfo[0])
            #
            if emInfo[0] not in emInfoObj["em_map"]:
                continue
            #
            # checking file matching with em_map category using self.__releaseFileList: DAOTHER-6570/DAOTHER-5842
            #
            # fileInfo[0]: file_name
            # fileInfo[1]: part_number
            # fileInfo[2]: version_number
            #
            fileList = []
            partNumList = []
            for fileInfo in emInfoObj["em_map"][emInfo[0]]:
                filePath = os.path.join(self.__storagePath, fileInfo[0])
                if not EmXmlHeaderOnly:
                    if not os.access(filePath, os.F_OK):
                        self._insertEntryMessage(errType="em", errMessage="File '" + fileInfo[0]
                                                 + "' defined in 'em_map' category can not be found in archive directory.")
                        continue
                    #
                    fileList.append( [ filePath, fileInfo[1], fileInfo[2], "" ] )
                #
                partNumList.append(fileInfo[1])
            #
            if len(fileList) > 0:
                # list[0]: full path archive file name
                # list[1]: archive file part number
                # list[2]: archive file verion number
                # list[3]: public part number
                #
                if len(fileList) > 1:
                    fileList.sort(key=lambda tup: int(tup[1]))
                    for idx, fileTup in enumerate(fileList, start=1):
                        #fileTup[3] = str(idx)
                        fileTup[3] = fileTup[1]
                    #
                #
                self.__releaseFileList.append( [ emInfo, fileList ] )
            #
            if len(partNumList) > 0:
                self.__currentMapPartListMap[emInfo[0]] = partNumList
            #
        #

    def __getPreviousReleaseInfo(self, emInfoObj):
        """ Get self.__neededInitialReleaseTypeList and self.__lastReleaseInfoMap information from model coordinate file.
        """
        if self.__newReleaseFlag:
            return
        #
        initial_release_type_list = []
        if "initial_release_type" in emInfoObj:
            initial_release_type_list = emInfoObj["initial_release_type"]
        #
        release_info_map = {}
        if "release_info" in emInfoObj:
            release_info_map = emInfoObj["release_info"]
        #
        for emInfo in self.__emInfoList:
            if emInfo[0] not in initial_release_type_list:
                self.__neededInitialReleaseTypeList.append(emInfo)
            #
            if emInfo[0] in release_info_map:
                infoMap = {}
                for infoList in release_info_map[emInfo[0]]:
                    infoMap[int(infoList[0])] = infoList
                #
                self.__lastReleaseInfoMap[emInfo[0]] = infoMap
            #
        #

    def __getAdditionalEmFileList(self):
        """ Get additional EM file names
        """
        if len(self.__archivalFilePathList) == 0:
            self.__getAarchivalFilePathList()
        #
        for emInfo in self.__emInfoList[self.__additionalStart:-1]:
            if emInfo[1] not in self.__contentTypeFileExtD:
                continue
            #
            fileMap = {}
            for fileNameTuple in self.__archivalFilePathList:
                if fileNameTuple[0].endswith(".gz"):
                    continue
                #
                fFields = str(fileNameTuple[0]).strip().split(".")
                if len(fFields) != 3:
                    continue
                #
                baseName = str(fFields[0]).strip()
                formatExt = str(fFields[1]).strip()
                versionTxt = str(fFields[2]).strip()
                if (versionTxt[:1] != "V") or (not versionTxt[1:].isdigit()):
                    continue
                #
                if formatExt not in self.__contentTypeFileExtD[emInfo[1]]:
                    continue
                #
                nFields = baseName.split("_")
                if nFields[2] != emInfo[2]:
                    continue
                #
                partNumber = int(nFields[3][1:])
                if partNumber in fileMap:
                    fileMap[partNumber].append( [ fileNameTuple[1], nFields[3][1:], versionTxt[1:], "" ] )
                else:
                    fileMap[partNumber] = [ [ fileNameTuple[1], nFields[3][1:], versionTxt[1:], "" ] ]
                #
            #
            if len(fileMap) == 0:
                continue
            #
            fileList = []
            for partNumber, myL in fileMap.items():
                if len(myL) > 1:
                    myL.sort(key=lambda tup: int(tup[2]))
                #
                fileList.append(myL[-1])
                #
            #
            if len(fileList) > 0:
                # list[0]: full path archive file name
                # list[1]: archive file part number
                # list[2]: archive file verion number
                # list[3]: public part number
                #
                if len(fileList) > 1:
                    fileList.sort(key=lambda tup: int(tup[1]))
                    for idx, fileTup in enumerate(fileList, start=1):
                        #fileTup[3] = str(idx)
                        fileTup[3] = fileTup[1]
                    #
                #
                self.__releaseFileList.append(( emInfo, fileList ))
            #
        #

    def __generateEmXmlHeader(self, validateFlag=True, removeFlag=False):
        modelfile = os.path.join(self._sessionPath, self._entryId + self._fileTypeList[0][0])
        if not os.access(modelfile, os.F_OK):
            return
            # per DAOTHER-2459's request, removed automtically generating xml header file. It is controlled by 'GenEmXmlHeaderFlag' now.
        #
        xmlfile = os.path.join(self._sessionPath, self.__embdId + "_v3.xml")
        self._removeFile(xmlfile)
        #
        status, error = self.__cif2xmlTranslate(modelfile, xmlfile, validateFlag)
        if removeFlag:
            self._removeFile(xmlfile)
        #
        if status == "failed":
            self._insertEntryMessage(errType="em", errMessage="emd -> xml translation failed:\n" + error)
        elif error.find("ERROR") != -1:
            self._insertEntryMessage(errType="em", errMessage=error)
        elif error.find("WARNING") != -1:
            self._insertReleseFile("em-volume", xmlfile, self.__embdId + "_v3.xml", "header", False)
            self._insertEntryMessage(errType="em", errMessage=error, messageType="warning")
        else:
            self._insertReleseFile("em-volume", xmlfile, self.__embdId + "_v3.xml", "header", False)
        #

    def __getMissingInitialInfoList(self):
        """ Generate missing initial releaseing information
        """
        if len(self.__neededInitialReleaseTypeList) == 0:
            return [],[]
        #
        if len(self.__archivalFilePathList) == 0:
            self.__getAarchivalFilePathList()
        #
        updatedList = []
        fileNameList = []
        for emInfo in self.__neededInitialReleaseTypeList:
            # For map files, only creates initial release information for map file defined in "em_map" category
            #
            if (emInfo[0] in self.__mapDataContentTypeList) and (emInfo[0] not in self.__currentMapPartListMap):
                continue
            #
            foundFileListMap = {}
            fileNamePattern = self._entryId + "_" + emInfo[2] + "_P"
            for fileNameTuple in self.__archivalFilePathList:
                if not fileNameTuple[0].startswith(fileNamePattern):
                    continue
                #
                fFields = str(fileNameTuple[0]).strip().split(".")
                if len(fFields) < 3:
                    continue
                #
                baseName = str(fFields[0]).strip()
                formatExt = str(fFields[1]).strip()
                versionTxt = str(fFields[2]).strip()
                if (versionTxt[:1] != "V") or (not versionTxt[1:].isdigit()):
                    continue
                #
                if (emInfo[3] != "") and (formatExt != emInfo[3]):
                    continue
                #
                versionNumver = versionTxt[1:]
                #
                nFields = baseName.split("_")
                partNumber = int(nFields[3][1:])
                #
                # For map files, only creates initial release information for map file defined in "em_map" category
                # 
                if (emInfo[0] in self.__currentMapPartListMap) and (nFields[3][1:] not in self.__currentMapPartListMap[emInfo[0]]):
                    continue
                #
                date = time.strftime("%Y-%m-%d", time.localtime(os.stat(fileNameTuple[1]).st_mtime))
                #
                if partNumber in foundFileListMap:
                    foundFileListMap[partNumber].append( [ fileNameTuple[0], fileNameTuple[1], versionNumver, date ] )
                else:
                    foundFileListMap[partNumber] = [ [ fileNameTuple[0], fileNameTuple[1], versionNumver, date ] ]
                #
            #
            if len(foundFileListMap) == 0:
                continue
            #
            fileList = []
            for partNumber,foundFileList in sorted(foundFileListMap.items()):
                if emInfo[0] == "EM metadata":
                    if partNumber != 1:
                        continue
                    #
                    if len(foundFileList) > 1:
                        foundFileList.sort(key=lambda tup: int(tup[2]))
                    #
                    for fileNameTuple in foundFileList:
                        if fileNameTuple[0].endswith(".gz") and self.__checkModelFile(fileNameTuple[1], True):
                            fileList.append( [ fileNameTuple[0][:-3], str(partNumber) ] )
                            fileNameList.append(fileNameTuple[0][:-3])
                            break
                        elif fileNameTuple[0].endswith(".V" + fileNameTuple[2]) and self.__checkModelFile(fileNameTuple[1], False):
                            fileList.append( [ fileNameTuple[0], str(partNumber) ] )
                            fileNameList.append(fileNameTuple[0])
                            break
                        #
                    #
                else:
                    if len(foundFileList) > 1:
                        foundFileList.sort(reverse=True, key=lambda tup: int(tup[2]))
                    #
                    for fileNameTuple in foundFileList:
                        if fileNameTuple[3] < self.__map_release_date:
                            if fileNameTuple[0].endswith(".gz"):
                                fileList.append( [ fileNameTuple[0][:-3], str(partNumber) ] )
                                fileNameList.append(fileNameTuple[0][:-3])
                                break
                            elif fileNameTuple[0].endswith(".V" + fileNameTuple[2]):
                                fileList.append( [ fileNameTuple[0], str(partNumber) ] )
                                fileNameList.append(fileNameTuple[0])
                                break
                            #
                        #
                    #
                #
            #
            if len(fileList) == 0:
                continue
            #
            for fileTuple in fileList:
                myD = {}
                myD["data_content_type"] = emInfo[0]
                myD["revision_type"] = "Initial release"
                myD["file_name"] = fileTuple[0]
                if len(fileList) > 1:
                    myD["part_number"] = fileTuple[1]
                else:
                    myD["part_number"] = "?"
                #
                updatedList.append(myD)
            #
        #
        return updatedList,fileNameList

    def __generateEmCifHeader(self):
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

    def __getAarchivalFilePathList(self):
        """ Get all archival file name list
        """
        for filename in os.listdir(self.__storagePath):
            if not filename.startswith(self._entryId):
                continue
            #
            self.__archivalFilePathList.append( ( filename, os.path.join(self.__storagePath, filename) ) )
        #

    def __cif2xmlTranslate(self, ciffile, xmlfile, validateFlag):
        logFile = "convert_em_xml_" + self._entryId + ".log"
        logFilePath = os.path.join(self._sessionPath, logFile)
        self._removeFile(logFilePath)
        #
        status = "failed"
        error = ""
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
                status = "ok"
            #
        except:  # noqa: E722 pylint: disable=bare-except
            error = traceback.format_exc()
        #
        if os.access(logFilePath, os.F_OK):
            ifh = open(logFilePath, "r")
            msg = ifh.read()
            ifh.close()
            if msg:
                if error:
                    error += "\n"
                #
                error += msg
            #
        #
        if (not error) and status == "failed":
            error = "CifEMDBTranslator failed without error message"
        #
        return status, error

    def __checkModelFile(self, fileNamePath, gzipFlag):
        """ Check em_admin category in model file for Map-only entry
        """
        try:
            modelFilePath = fileNamePath
            if gzipFlag:
                modelFilePath = os.path.join(self._sessionPath, self._entryId + "-tmp-model.cif")
                with gzip.open(fileNamePath, "rb") as f_in:
                    with open(modelFilePath, "wb") as f_out:
                        f_out.write(f_in.read())
                    #
                #
            #
            cifObj = mmCIFUtil(filePath=modelFilePath)
            status = cifObj.GetSingleValue("em_admin", "current_status")
            map_release_date = cifObj.GetSingleValue("em_admin", "map_release_date")
            header_release_date = cifObj.GetSingleValue("em_admin", "header_release_date")
            if (status == "REL") and ((map_release_date == self.__map_release_date) or (header_release_date == self.__map_release_date)):
                return True
            #
            return False
        except:  # noqa: E722 pylint: disable=bare-except
            return False
        #
