##
# File:  UpdateUtil.py
# Date:  11-Oct-2016
# Updates:
##
"""
Class responsible for updating model, structure-factors, nmr-restraints, and nmr-chemical-shifts files

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

try:
    import cPickle as pickle
except ImportError:
    import pickle as pickle

import os
import sys

from mmcif.api.DataCategory import DataCategory
from mmcif.api.PdbxContainers import DataContainer
from mmcif.io.PdbxWriter import PdbxWriter
from wwpdb.apps.releasemodule.update.EntryUpdateBase import EntryUpdateBase
from wwpdb.io.file.mmCIFUtil import mmCIFUtil


class UpdateUtil(EntryUpdateBase):
    """ Class responsible for updating model, structure-factors, nmr-restraints, and nmr-chemical-shifts files
    """
    def __init__(self, reqObj=None, entryDir=None, verbose=False, log=sys.stderr):
        super(UpdateUtil, self).__init__(reqObj=reqObj, entryDir=entryDir, statusDB=None, verbose=verbose, log=log)
        #
        self.__citation_items = ['id', 'pdbx_database_id_PubMed', 'pdbx_database_id_DOI', 'title', 'journal_abbrev', 'journal_volume',
                                 'page_first', 'page_last', 'year', 'journal_id_ISSN', 'author', 'single_author', 'insert_flag']
        #
        self.__pubmedInfo = {}

    def run(self):
        emMapTypeList = {}
        self._loadLocalPickle()
        if self._blockErrorFlag:
            return emMapTypeList
        #
        self.__initializeFileName()
        self.__readPubmedInfo()
        self.__generateInputFile()
        self.__runContentUpdate()
        emMapTypeList = self.__readOutputFile()
        if self._blockErrorFlag:
            for typeList in self._fileTypeList:
                if (not ('status_code' + typeList[1]) in self._pickleData) or (not self._pickleData['status_code' + typeList[1]]):
                    continue
                #
                self._insertFileStatus(typeList[5], False)
            #
        #
        self._dumpLocalPickle()
        #
        return emMapTypeList

    def __initializeFileName(self):
        # pylint: disable=attribute-defined-outside-init
        self.__inputfile = 'inputfile_' + self._entryId + '.cif'
        self.__inputFilePath = os.path.join(self._sessionPath, self.__inputfile)
        self.__outputfile = 'outputfile_' + self._entryId + '.cif'
        self.__logfile = 'update_logfile_' + self._entryId + '.log'
        self.__clogfile = 'update_command_' + self._entryId + '.log'

    def __readPubmedInfo(self):
        pubmed_file = str(self._reqObj.getValue('pubmed_file'))
        if not pubmed_file:
            return
        #
        fb = open(os.path.join(self._sessionPath, pubmed_file), 'rb')
        self.__pubmedInfo = pickle.load(fb)
        fb.close()

    def __generateInputFile(self):
        items = ['entry', 'pdbid', 'emdb_id', 'annotator', 'option', 'input_file', 'output_file', 'status_code', 'input_file_sf', 'output_file_sf',
                 'status_code_sf', 'input_file_mr', 'output_file_mr', 'status_code_mr', 'input_file_cs', 'output_file_cs', 'status_code_cs',
                 'input_file_nmr_data', 'output_file_nmr_data', 'status_code_nmr_data', 'status_code_em', 'approval_type', 'revdat_tokens', 'obsolete_ids',
                 'supersede_ids', 'obspr_details', 'da_status_code', 'da_status_code_em', 'wf_status_code', 'wf_status_code_em']
        #
        checking_items = ['status_code', 'input_file_sf', 'output_file_sf', 'status_code_sf', 'input_file_mr', 'output_file_mr',
                          'status_code_mr', 'input_file_cs', 'output_file_cs', 'status_code_cs', 'input_file_nmr_data', 'output_file_nmr_data',
                          'status_code_nmr_data', 'status_code_em', 'approval_type', 'revdat_tokens', 'obsolete_ids', 'supersede_ids', 'obspr_details']
        #
        self._removeFile(self.__inputFilePath)
        #
        myDataList = []
        curContainer = DataContainer(self._entryId)
        curCat = DataCategory('update_info')
        for item in items:
            curCat.appendAttribute(item)
        #
        hasValueFlag = False
        for item in items:
            if self._blockEmErrorFlag and (item == 'status_code_em'):
                continue
            #
            if item == 'pdbid':
                item1 = 'pdb_id'
            else:
                item1 = item
            #
            if (item1 in self._entryDir) and self._entryDir[item1] and self._entryDir[item1] != 'CITATIONUpdate':
                # and self._entryDir[item1] != 'EMHEADERUpdate':
                if item1.startswith("input_file") and (self._processing_site == "PDBE"):
                    curCat.setValue(os.path.join(self._sessionPath, self._entryDir[item1]), item, 0)
                else:
                    curCat.setValue(self._entryDir[item1], item, 0)
                #
                if item1 in checking_items:
                    hasValueFlag = True
                #
            #
        #
        curContainer.append(curCat)
        #
        if 'revision' in self._entryDir:
            revCat = DataCategory('revision')
            revCat.appendAttribute('revision_type')
            revCat.appendAttribute('details')
            row = 0
            for dataDict in self._entryDir['revision']:
                for item1 in ('revision_type', 'details'):
                    if item1 in dataDict:
                        revCat.setValue(dataDict[item1], item1, row)
                    #
                #
                row += 1
            #
            curContainer.append(revCat)
            hasValueFlag = True
        #
        if 'pubmed' in self._entryDir:
            pubCat, authCat = self.__genPubmedCategory(self._entryDir['pubmed'])
            if pubCat:
                curContainer.append(pubCat)
                hasValueFlag = True
            #
            if authCat:
                curContainer.append(authCat)
                hasValueFlag = True
            #
        elif 'citation' in self._entryDir:
            pubCat, authCat = self.__genCitationCategory(self._entryDir['citation'])
            if pubCat:
                curContainer.append(pubCat)
                hasValueFlag = True
            #
            if authCat:
                curContainer.append(authCat)
                hasValueFlag = True
            #
        #
        myDataList.append(curContainer)
        #
        if not hasValueFlag:
            return
        #
        f = open(self.__inputFilePath, 'w')
        pdbxW = PdbxWriter(f)
        pdbxW.write(myDataList)
        f.close()

    def __runContentUpdate(self):
        if not os.access(self.__inputFilePath, os.F_OK):
            return
        #
        if self._processing_site == "PDBE":
            tarFile = self._entryId + "-release-updated.tar.gz"
            outputList = []
            outputList.append((tarFile, True))
            outputList.append((self.__logfile, True))
            outputList.append((self.__clogfile, True))
            self._dpUtilityApi(operator="annot-release-update", inputFileName=self.__inputFilePath, outputFileNameTupList=outputList,
                               option="-archivepath " + os.path.join(self._cI.get("SITE_ARCHIVE_STORAGE_PATH"), "archive"),
                               id_value=self._entryId, id_name="dep_id")
            #
            self._extractTarFile(tarFile)
            self._processLogError("", "", os.path.join(self._sessionPath, self.__logfile))
            self._processLogError("", "ReleaseUpdate", os.path.join(self._sessionPath, self.__clogfile))
        else:
            self._GetAndRunCmd('', '${BINPATH}', 'ReleaseUpdate', self.__inputfile, self.__outputfile, self.__logfile, self.__clogfile,
                               ' -archivepath ' + os.path.join(self._cI.get('SITE_ARCHIVE_STORAGE_PATH'), 'archive') + ' ')

    def __genPubmedCategory(self, pubmed_list):
        if not pubmed_list or not self.__pubmedInfo:
            return None, None
        #
        infoList = []
        authList = []
        for pubmedDir in pubmed_list:
            pubmed_id = pubmedDir['pdbx_database_id_PubMed']
            infoDir = {}
            for item in self.__citation_items:
                if item in pubmedDir:
                    infoDir[item] = pubmedDir[item]
                    continue
                #
                if (pubmed_id not in self.__pubmedInfo) or (item not in self.__pubmedInfo[pubmed_id]):
                    continue
                #
                infoDir[item] = self.__pubmedInfo[pubmed_id][item]
            #
            if not infoDir:
                continue
            #
            infoList.append(infoDir)
            if ('author_list' in pubmedDir) and pubmedDir['author_list']:
                authList.extend(pubmedDir['author_list'])
            #
        #
        return self.__genPubmedInfoCategory(infoList), self.__genPubmedAuthorCategory(authList)

    def __genCitationCategory(self, citDir):
        if not citDir:
            return None, None
        #
        authList = []
        if ('author_list' in citDir) and citDir['author_list']:
            authList = citDir['author_list']
        #
        return self.__genPubmedInfoCategory([citDir]), self.__genPubmedAuthorCategory(authList)

    def __genPubmedInfoCategory(self, infoList):
        if not infoList:
            return None
        #
        cat = DataCategory('pubmed_info')
        for item in self.__citation_items:
            cat.appendAttribute(item)
        #
        row = 0
        for pubmedDir in infoList:
            for item in self.__citation_items:
                if item in pubmedDir:
                    cat.setValue(pubmedDir[item], item, row)
                #
            #
            row += 1
        #
        return cat

    def __genPubmedAuthorCategory(self, authList):
        if not authList:
            return None
        #
        cat = DataCategory('pubmed_author_list')
        for item in ('id', 'name', 'orcid'):
            cat.appendAttribute(item)
        #
        row = 0
        for authDir in authList:
            for item in ('id', 'name', 'orcid'):
                if item in authDir:
                    cat.setValue(authDir[item], item, row)
                #
            #
            row += 1
        #
        return cat

    def __readOutputFile(self):
        emMapTypeList = {}
        outputfile = os.path.join(self._sessionPath, self.__outputfile)
        if not os.access(outputfile, os.F_OK):
            return emMapTypeList
        #
        cifObj = mmCIFUtil(filePath=outputfile)
        for typeList in (('error', 'error_message'), ('warning', 'warning_message')):
            msgList = cifObj.GetValue(typeList[1])
            if not msgList:
                continue
            #
            for msgDict in msgList:
                if msgDict['entry'] != self._entryId:
                    continue
                #
                self._insertEntryMessage(errType=msgDict['type'], errMessage=msgDict['message'], messageType=typeList[0])
            #
        #
        upList = cifObj.GetValue('update_list')
        if upList:
            for upDict in upList:
                if upDict['entry'] != self._entryId:
                    continue
                #
                self._insertArchivalFile(upDict['type'], upDict['format'], upDict['file'], True)
                if ('major_revision' in upDict) and upDict['major_revision'] and ('minor_revision' in upDict) and upDict['minor_revision']:
                    self._insertAuditRevisionInfo(upDict['type'], upDict['major_revision'], upDict['minor_revision'])
                #
            #
        #
        largeEntryList = cifObj.GetValue('large_entry_list')
        if largeEntryList:
            for largeDict in largeEntryList:
                if largeDict['entry'] == self._entryId:
                    self._pickleData['big_entry'] = 'yes'
                    break
                #
            #
        #
        emMapFileTypeList = cifObj.GetValue('em_map_file_type')
        if emMapFileTypeList:
            for typeDict in emMapFileTypeList:
                if ('type' not in typeDict) or (not typeDict['type']) or ('partNumber' not in typeDict) or (not typeDict['partNumber']):
                    continue
                #
                if typeDict['type'] in emMapTypeList:
                    emMapTypeList[typeDict['type']].append(typeDict['partNumber'])
                else:
                    emMapTypeList[typeDict['type']] = [typeDict['partNumber']]
                #
            #
        #
        return emMapTypeList
