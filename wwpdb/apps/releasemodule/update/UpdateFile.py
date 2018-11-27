##
# File:  UpdateFile.py
# Date:  01-Jul-2013
# Updates:
##
"""
Update coordinate cif file.

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

import cPickle, logging, os, shutil, sys, string, traceback

from pdbx_v2.trans.InstanceMapper                    import InstanceMapper
from wwpdb.api.facade.ConfigInfo                     import ConfigInfo
from wwpdb.api.facade.ConfigInfoData                 import ConfigInfoData
from wwpdb.api.status.dbapi.WfDbApi                  import WfDbApi
from wwpdb.apps.ann_tasks_v2.status.StatusHistoryUtils import StatusHistoryUtils
from wwpdb.apps.entity_transform.utils.GetLogMessage import GetLogMessage
from wwpdb.apps.entity_transform.utils.mmCIFUtil     import mmCIFUtil
from wwpdb.apps.msgmodule.io.MessagingIo             import MessagingIo
from wwpdb.apps.releasemodule.update.ArchiveFileUtil import ArchiveFileUtil
from wwpdb.apps.releasemodule.update.CheckMP         import CheckMP
from wwpdb.apps.releasemodule.update.GenerateMP      import GenerateMP
from wwpdb.apps.releasemodule.update.GenerateUtil    import GenerateUtil
from wwpdb.apps.releasemodule.update.GzipMP          import GzipMP
from wwpdb.apps.releasemodule.update.UpdateCifMP     import UpdateCifMP
from wwpdb.apps.releasemodule.update.UpdateMP        import UpdateMP
from wwpdb.apps.releasemodule.update.UpdateUtil      import UpdateUtil
from wwpdb.apps.releasemodule.utils.DBLoadUtil       import DBLoadUtil
from wwpdb.apps.releasemodule.utils.Utility          import *
from wwpdb.apps.wf_engine.engine.WFEapplications     import killAllWF
from wwpdb.utils.emdb.cifEMDBTranslator.cifEMDBTranslator import CifEMDBTranslator
from wwpdb.utils.rcsb.DataExchange                   import DataExchange
from wwpdb.utils.rcsb.PathInfo                       import PathInfo

class UpdateFile(object):
    """ Class responsible for Update coordinate cif file.
    """
    def __init__(self, reqObj=None, updateList=None, verbose=False, log=sys.stderr):
        self.__verbose=verbose
        self.__lfh=log
        self.__reqObj=reqObj
        self.__inputList=updateList
        self.__sObj=None
        self.__sessionId=None
        self.__sessionPath=None
        self.__siteId  = str(self.__reqObj.getValue("WWPDB_SITE_ID"))
        self.__cI=ConfigInfo(self.__siteId)
        self.__topReleaseDir = os.path.join(self.__cI.get('SITE_ARCHIVE_STORAGE_PATH'), 'for_release')
        ##
        self.__fileTypeList = [ [ '_model_P1.cif',     '',    'Coordinate',        'model',               'pdbx',     'coor' ],
                                [ '_sf_P1.cif',        '_sf', 'Structural Factor', 'structure-factors',   'pdbx',     'sf'   ],
                                [ '_em-volume_P1.map', '_em', 'EM Map',            'em-volume',           'map',      'em'   ],
                                [ '_mr_P1.mr',         '_mr', 'NMR Constraints',   'nmr-restraints',      'pdb-mr',   'mr'   ],
                                [ '_cs_P1.cif',        '_cs', 'Chemical Shifts',   'nmr-chemical-shifts', 'pdbx',     'cs'   ] ]
        #
        self.__em_additional_type = [ 'em-mask-volume', 'em-additional-volume', 'em-half-volume', 'fsc', 'img-emdb', 'layer-lines', 'structure-factors' ]
        self.__em_additional_list = [ [ 'em-mask-volume',       '_msk',        'masks',            'no'  ],
                                      [ 'em-additional-volume', '_additional', 'other',            'yes' ],
                                      [ 'em-half-volume',       '_half_map',   'other',            'yes' ],
                                      [ 'fsc',                  '_fsc',        'fsc',              'no'  ],
                                      [ 'img-emdb',             '',            'images',           'no'  ],
                                      [ 'layer-lines',          '_ll',         'layerLines',       'yes' ],
                                      [ 'structure-factors',    '_sf',         'structureFactors', 'yes' ] ]
        self.__contentD = {}
        self.__formatD = {}
        self.__fileExtContentTypeD = {}
        # entry list involved in both file update and release process
        self.__updateList = []
        # entry list involved EM map release process
        self.__releaseEMList = []
        # entry list only involved in file update
        self.__updateFileList = []
        # entry list only involved in release process
        self.__releaseList = []
        self.__modelCifList = []
        self.__messageListMap = {} 
        self.__errorContent = ''
        self.__returnContent = ''
        self.__wfDBUpdateStatus = {}
        self.__entryErrorContent = {}
        self.__sysErrorContent = []
        #
        self.__getSession()
        #
        self.__annotator = str(self.__reqObj.getValue('annotator'))
        self.__option = str(self.__reqObj.getValue('option'))
        self.__pubmedInfo = {}
        self.__readPubmedInfo() 
        self.__pI = PathInfo(siteId=self.__siteId, sessionPath=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)

    def DoUpdate(self):
        self.__findSourceFile()
        if self.__errorContent:
            return
        #
        self.__runUpdateMP()
        self.__runGenerateMP()
        self.__runCheckMP()
        self.__updateDatabase()
        self.__updateStatusHistory()
        self.__generateEMapHeader()
        self.__generateReturnContent()
        self.__runGzipMP()
        self.__copyEMaps()
        #
        self.__updateArchive(False)
        self.__sendMessage()

    def PullRelease(self):
        self.__findBeforeReleaseFiles()
        if self.__errorContent:
            return
        #
        self.__updateDatabase()
        self.__updateArchive(True)
        #
        for dir in self.__updateFileList:
            entryId = dir['entry']
            if dir.has_key('pdb_id'):
                self.__returnContent += 'Entry ' + entryId + '(' + dir['pdb_id'] + ') is pulled off from release.'
            else:
                self.__returnContent += 'Entry ' + entryId + ' is pulled off from release.'
            #
            if self.__wfDBUpdateStatus.has_key(entryId):
                self.__returnContent += ' ' + self.__wfDBUpdateStatus[entryId]
            self.__returnContent += '\n'
        #

    def getErrorContent(self):
        return self.__errorContent

    def getReturnContent(self):
        return self.__returnContent
 
    def __readPubmedInfo(self):
        pubmed_file = str(self.__reqObj.getValue('pubmed_file'))
        if not pubmed_file:
            return
        #
        fb = open(os.path.join(self.__sessionPath, pubmed_file), 'rb')
        self.__pubmedInfo = cPickle.load(fb)
        fb.close() 

    def __findSourceFile(self):
        if not self.__inputList:
            self.__errorContent += 'No update list defined\n'
            return
        #
        entry_index = {}
        anno_indexfile = os.path.join(self.__topReleaseDir, 'index', self.__annotator + '.index')
        if os.access(anno_indexfile, os.F_OK):
            fbr = open(anno_indexfile, 'rb')
            entry_index = cPickle.load(fbr)
            fbr.close()
        #
        errMsg = ''
        for dir in self.__inputList:
            dir['annotator'] = self.__annotator
            dir['option'] = self.__option
            #
            entryId = dir['entry']
            key_id = entryId
            pdbid = ''
            if dir.has_key('pdb_id'):
                pdbid = dir['pdb_id'].lower()
                key_id = pdbid
            #
            index_id = entryId.lower()
            if pdbid:
                index_id = pdbid
            #
            index = {}
            indexfile = os.path.join(self.__topReleaseDir, 'index', index_id + '.index')
            if os.access(indexfile, os.F_OK):
                fbr = open(indexfile, 'rb')
                index = cPickle.load(fbr)
                fbr.close() 
            #
            copyModelFile = False
            foundFile = False
            foundEMFile = False
            foundRelFlag = False
            foundReloadFlag = False
            foundCitationUpdateFlag = False
            for list in self.__fileTypeList:
                if not dir.has_key('status_code' + list[1]):
                    continue
                #
                if dir['status_code' + list[1]] == 'RELOAD':
                    foundReloadFlag = True
                elif dir['status_code' + list[1]] == 'CITATIONUpdate':
                    foundCitationUpdateFlag = True
                elif list[1] != '_em':
                    foundRelFlag = True
                #
                sourcePath,err = self.__copyArchiveFile(entryId, key_id, list)
                if not sourcePath:
                    if err:
                        errMsg += err + '\n'
                    #
                    continue
                #
                if list[3] == 'model':
                    copyModelFile = True
                #
                if index.has_key(list[5]):
                    if not sourcePath in index[list[5]]:
                        index[list[5]].append(sourcePath)
                    #
                else:
                    filelist = []
                    filelist.append(sourcePath)
                    index[list[5]] = filelist
                #
                dir['input_file' + list[1]] = entryId + list[0]
                dir['output_file'+ list[1]] = entryId + list[0]
                if not list[1]:
                    self.__modelCifList.append(entryId + list[0])
                #
                if list[5] == 'coor':
                    if self.__isBigEntry(entryId + list[0], pdbid):
                        dir['big_entry'] = 'yes'
                    #
                #
                foundFile = True
                if list[1] == '_em':
                    foundEMFile = True
                #
            #
            if foundFile:
                release_dir = {}
                self.__updateList.append(dir)
                if foundRelFlag or foundReloadFlag:
                    self.__releaseList.append(dir)
                    release_dir['pdb'] = pdbid
                    if dir.has_key('status_code') and dir['status_code'] == 'REL' and \
                       dir.has_key('directory') and dir['directory'] == 'added':
                        checkFile = os.path.join(self.__topReleaseDir, dir['directory'], pdbid, pdbid + '.cif.gz')
                        if not os.access(checkFile, os.F_OK):
                            self.__messageListMap[entryId] = { 'pdb' : checkFile }
                        #
                    #
                #
                if foundEMFile:
                    fn = os.path.join(self.__sessionPath, entryId + self.__fileTypeList[0][0])
                    if not copyModelFile:
                        sourcePath,err = self.__copyArchiveFile(entryId, key_id, self.__fileTypeList[0])
                        if sourcePath:
                            if index.has_key(self.__fileTypeList[0][5]):
                                if not sourcePath in index[self.__fileTypeList[0][5]]:
                                    index[self.__fileTypeList[0][5]].append(sourcePath)
                                #
                            else:
                                filelist = []
                                filelist.append(sourcePath)
                                index[self.__fileTypeList[0][5]] = filelist
                            #
                        else:
                            if err:
                                errMsg += err + '\n'
                            #
                        #
                    #
                    if os.access(fn, os.F_OK):
                        if not dir.has_key('input_file' + self.__fileTypeList[0][1]):
                            dir['input_file' + self.__fileTypeList[0][1]] = entryId + self.__fileTypeList[0][0]
                            self.__modelCifList.append(entryId + self.__fileTypeList[0][0])
                        #
                        if not dir.has_key('output_file' + self.__fileTypeList[0][1]):
                            dir['output_file' + self.__fileTypeList[0][1]] = entryId + self.__fileTypeList[0][0]
                        #
                        if dir.has_key('emdb_id') and dir['emdb_id']:
                            release_dir['emd'] = dir['emdb_id']
                            index['emdb_id'] = dir['emdb_id']
                            emdb_id = dir['emdb_id']
                            checkFile = os.path.join(self.__topReleaseDir, 'emd', emdb_id, 'map', emdb_id.replace('-', '_').lower() + '.map.gz')
                            is_new_release = False
                            if dir.has_key('status_code_em') and dir['status_code_em'] == 'REL':
                                is_new_release = True
                            #
                            if is_new_release and (not os.access(checkFile, os.F_OK)):
                                if self.__messageListMap.has_key(entryId):
                                    self.__messageListMap[entryId]['emd'] = checkFile
                                else:
                                    self.__messageListMap[entryId] = { 'emd' : checkFile }
                                #
                            #
                        #
                    #
                    self.__updateFileList.append(dir)
                    self.__releaseEMList.append(dir)
                elif foundRelFlag or foundCitationUpdateFlag:
                    self.__updateFileList.append(dir)
                elif foundReloadFlag and dir.has_key('revision'):
                    self.__updateFileList.append(dir)
                #
                if release_dir:
                    entry_index[entryId] = release_dir
                #
            #
            fbw = open(indexfile, 'wb')
            cPickle.dump(index, fbw)
            fbw.close()
        #
        fbw = open(anno_indexfile, 'wb')
        cPickle.dump(entry_index, fbw)
        fbw.close()
        #
        if not self.__updateList:
            if errMsg:
                self.__errorContent += errMsg
            #
        #

    def __copyArchiveFile(self, entryId, key_id, list):
        sourcePath = self.__pI.getFilePath(dataSetId=entryId, wfInstanceId=None, contentType=list[3], formatType=list[4], \
                           fileSource='archive', versionId='latest', partNumber='1')
        if (not sourcePath) or not os.access(sourcePath, os.F_OK):
            err = "Can't find " + list[2].lower() + ' file for entry ' + entryId
            #errMsg += err + '\n'
            self.__insertEntryError(key_id, list[5], err)
            return '',err
        #
        fn = os.path.join(self.__sessionPath, entryId + list[0])
        shutil.copyfile(sourcePath, fn)
        if not os.access(fn, os.F_OK):
            err = 'Copy ' + list[2].lower() + ' file for entry ' + entryId + ' failed.'
            #errMsg += err + '\n'
            self.__insertEntryError(key_id, list[5], err)
            return '',err
        #
        return sourcePath,''

    def __findBeforeReleaseFiles(self):
        if not self.__inputList:
            self.__errorContent += 'No update list defined\n'
            return
        #
        errMsg = ''
        id_list = []
        for dir in self.__inputList:
            entryId = dir['entry']
            key_id = entryId
            if dir.has_key('pdb_id'):
                key_id = dir['pdb_id'].lower()
                id_list.append(key_id)
            #
            foundIndex = False
            index = {}
            file_index = {}
            indexfile = os.path.join(self.__topReleaseDir, 'index', key_id.lower() + '.index')
            if os.access(indexfile, os.F_OK):
                fbr = open(indexfile, 'rb')
                index = cPickle.load(fbr)
                fbr.close() 
                foundIndex = True
                if index.has_key('emdb_id') and index['emdb_id']:
                    id_list.append(index['emdb_id'])
                #
            else:
                file_index = FindReleaseFiles(self.__siteId, dir)
            #
            arObj = ArchiveFileUtil(reqObj=self.__reqObj, entryId=entryId, verbose=self.__verbose, log=self.__lfh)
            if not foundIndex:
                arObj.GetFileList()
            #
            for list in self.__fileTypeList:
                if foundIndex:
                    if not index.has_key(list[5]):
                        continue
                    #
                    arObj.GetBeforeReleaseFileWithList(filenameList=index[list[5]], baseExt=list[0])
                else:
                    if not file_index.has_key(list[5]):
                        continue
                    #
                    arObj.GetBeforeReleaseFile(baseExt=list[0])
                #
                fn = os.path.join(self.__sessionPath, entryId + list[0])
                if not os.access(fn, os.F_OK):
                    err = "Can't find " + list[2] + ' file for entry ' + entryId
                    errMsg += err + '\n'
                    self.__insertEntryError(key_id, list[5], err)
                elif list[0] == '_model_P1.cif':
                    cifObj = mmCIFUtil(filePath=fn)
                    statusCode = cifObj.GetSingleValue('pdbx_database_status', 'status_code')
                    statusCodeEM = cifObj.GetSingleValue('em_admin', 'current_status')
                    if statusCode:
                        dir['status_code'] = statusCode
                    #
                    if statusCodeEM:
                        dir['status_code_em'] = statusCodeEM
                    #
                #
            #
            self.__updateFileList.append(dir)
        #
        if errMsg:
            self.__errorContent += errMsg
            return
        #
        if not self.__updateFileList:
            self.__errorContent += 'No update list defined\n'
        #
        self.__removeDirectory(id_list)

    def __removeDirectory(self, id_list):
        if not id_list:
            return
        #
        scriptfile = getFileName(self.__sessionPath, 'remove', 'csh')
        logfile    = getFileName(self.__sessionPath, 'remove', 'log')
        script = os.path.join(self.__sessionPath, scriptfile)
        f = file(script, 'w')
        f.write('#!/bin/tcsh -f\n')
        f.write('#\n')
        #
        for id in id_list:
            for dir in ( 'added', 'modified', 'obsolete', 'reloaded', 'emd' ):
                f.write('if ( ( -e ' + self.__topReleaseDir + '/' + dir + '/' + id + ' ) ) then\n')
                f.write('    /bin/rm -rf ' + self.__topReleaseDir + '/' + dir + '/' + id + '\n')
                f.write('endif\n')
                f.write('#\n')
            #
        #
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, logfile)

    def __updateArchive(self, pull_flag):
        if not self.__updateFileList:
            return
        #
        for dir in self.__updateFileList:
            entryId = dir['entry']
            de=DataExchange(reqObj=self.__reqObj, depDataSetId=entryId, fileSource='archive', \
                            verbose=self.__verbose,log=self.__lfh)
            for list in self.__fileTypeList:
                fn = os.path.join(self.__sessionPath, entryId + list[0])
                if not os.access(fn, os.F_OK):
                    continue
                #
                if pull_flag and list[5] == 'em':
                    continue
                #
                de.export(fn,contentType=list[3], formatType=list[4], version="next")
                #
                if dir.has_key('status_code' + list[1]) and (dir['status_code' + list[1]] == 'REL' or \
                   dir['status_code'+ list[1]] == 'OBS' or dir['status_code'+ list[1]] == 'REREL' or \
                   dir['status_code' + list[1]] == 'RELOAD'):
                    de.export(fn, contentType=list[3]+'-release', formatType=list[4], version='next')
                #
            #
            fn = os.path.join(self.__sessionPath, entryId + "_model_P1.pdb")
            if not pull_flag and os.access(fn, os.F_OK):
                de.export(fn, contentType='model-release', formatType='pdb', version='next')
                de.export(fn, contentType='model', formatType='pdb', version='next')
            #
        #

    def __sendMessage(self):
        if not self.__messageListMap:
            return
        #
        emdList = []
        pdbList = []
        for entry,dir in self.__messageListMap.items():
            if dir.has_key('emd') and dir.has_key('pdb'):
                if os.access(dir['emd'], os.F_OK) and os.access(dir['pdb'], os.F_OK):
                    emdList.append(entry)
                #
            elif dir.has_key('emd'):
                if os.access(dir['emd'], os.F_OK):
                    emdList.append(entry)
                #
            elif dir.has_key('pdb'):
                if os.access(dir['pdb'], os.F_OK):
                    pdbList.append(entry)
                #
            #
        #
        msgOption = 'release-nopubl'
        if self.__option == 'citation_update':
            msgOption = 'release-publ'
        #
        self.__sendMessageProcess(emdList, msgOption, True)
        self.__sendMessageProcess(pdbList, msgOption, False)

    def __sendMessageProcess(self, entryList, type, em_flag):
        if not entryList:
            return
        #
        msgIo = MessagingIo(self.__reqObj, self.__verbose, self.__lfh)
        if em_flag:
            rtrnStatus = msgIo.autoMsg(entryList, type, p_isEmdbEntry=True)
        else:
            rtrnStatus = msgIo.autoMsg(entryList, type)

    def __runUpdateMP(self):
        if not self.__updateFileList:
            return
        #
        if self.__modelCifList:
            updateCif = UpdateCifMP(path=self.__sessionPath, siteId=self.__siteId, entryList=self.__modelCifList, \
                                    log=self.__lfh, verbose=self.__verbose)
            updateCif.run()
        #
        update = UpdateMP(path=self.__sessionPath, siteId=self.__siteId, entryList=self.__updateFileList, \
                          pubmedInfo=self.__pubmedInfo,log=self.__lfh, verbose=self.__verbose)
        update.run()
        self.__mergeEntryErrors(update.getEntryMessage())
        self.__sysErrorContent = update.getErrorMessage()

    def __runGenerateMP(self):
        if not self.__releaseList:
            return
        #
        generate = GenerateMP(path=self.__sessionPath, siteId=self.__siteId, entryList=self.__releaseList, \
                              log=self.__lfh, verbose=self.__verbose)
        generate.run()
        self.__mergeEntryErrors(generate.getEntryMessage())
        self.__mergeSysErrors(generate.getErrorMessage())

    def __runCheckMP(self):
        if self.__errorContent:
            return
        #
        check = CheckMP(path=self.__sessionPath, siteId=self.__siteId, entryList=self.__releaseList, \
                        log=self.__lfh, verbose=self.__verbose)
        check.run()
        self.__mergeEntryErrors(check.getEntryMessage())
        self.__mergeSysErrors(check.getErrorMessage())

    def __generateEMapHeader(self):
        if not self.__releaseEMList:
            return
        #
        for dir in self.__releaseEMList:
            if not dir.has_key('emdb_id'):
                continue
            #
            emdb_id = dir['emdb_id']
            entryId = dir['entry']
            key_id = entryId
            if dir.has_key('pdb_id'):
                key_id = dir['pdb_id'].lower()
            #
            modelfile = os.path.join(self.__sessionPath, entryId + self.__fileTypeList[0][0])
            if not os.access(modelfile, os.F_OK):
                continue
            #
            emdfile = os.path.join(self.__sessionPath, emdb_id.replace('-', '_').lower() + '.cif')
            if os.access(emdfile, os.F_OK):
                os.remove(emdfile)
            #
            im = InstanceMapper(verbose=self.__verbose, log=self.__lfh)
            im.setMappingFilePath(self.__cI.get('SITE_EXT_DICT_MAP_EMD_FILE_PATH'))
            ok = im.translate(modelfile, emdfile, mode="src-dst")
            if ok:
                xmlfile = os.path.join(self.__sessionPath, emdb_id.replace('-', '_').lower() + '_v2.xml')
                if os.access(xmlfile, os.F_OK):
                    os.remove(xmlfile)
                #
                ret = self.__cif2xmlTranslate(emdfile, xmlfile)
                if ret:
                    self.__insertEntryError(key_id, 'em', 'emd -> xml translation failed:\n' + ret)
                #
            else:
                self.__insertEntryError(key_id, 'em', 'em -> emd translation failed.')
            #
        #

    def __generateReturnContent(self):
        type_list = [ [ 'cif', 'PDBx CIF' ], [ 'pdb', 'PDB' ], [ 'xml', 'XML' ] ]
        #
        self.__returnContent = str(self.__reqObj.getValue('task'))
        if self.__sysErrorContent:
            self.__returnContent += '\n\nSystem related error:\n' \
                           + '\n'.join(self.__sysErrorContent)
        #
        for dir in self.__updateList:
            self.__returnContent += '\n\nEntry ' + dir['entry']
            if dir.has_key('comb_ids'):
                self.__returnContent += ' ' + dir['comb_ids']
            elif dir.has_key('pdb_id'):
                self.__returnContent += ' ' + dir['pdb_id']
            #
            self.__returnContent += ': '
            Content_by_entry = ''
            key_id = dir['entry']
            if dir.has_key('pdb_id'):
                key_id = dir['pdb_id'].lower()
            #
            if self.__wfDBUpdateStatus.has_key(key_id):
                Content_by_entry += '\n\n' + self.__wfDBUpdateStatus[key_id]
            for list in self.__fileTypeList:
                status_key = 'status_code' + list[1]
                type_key = list[5]
                name_key = list[2]
                if not dir.has_key(status_key) or dir[status_key] == 'CITATIONUpdate':
                    continue
                #
                if type_key == 'coor':
                    Content_by_entry += '\n\n' + name_key + ':'
                    foundError = False
                    if self.__entryErrorContent.has_key(key_id):
                        if self.__entryErrorContent[key_id].has_key(type_key):
                            Content_by_entry += '\n' + self.__entryErrorContent[key_id][type_key]
                            foundError = True
                        #
                    #
                    if not foundError:
                        if dir.has_key(status_key) and (dir[status_key] == 'REL' or dir[status_key] == 'OBS' \
                           or dir[status_key] == 'RELOAD'):
                            for list1 in type_list:
                                if list1[1] == 'PDB' and dir[status_key] == 'RELOAD':
                                    continue
                                #
                                Content_by_entry += '\n' + list1[1] + ':'
                                if self.__entryErrorContent.has_key(key_id):
                                    if self.__entryErrorContent[key_id].has_key(list1[0]):
                                        Content_by_entry += '\n' + self.__entryErrorContent[key_id][list1[0]]
                                    else:
                                        Content_by_entry += ' OK'
                                    #
                                else:
                                    Content_by_entry += ' OK'
                                #
                            #
                        else:
                            Content_by_entry += ' OK'
                        #
                    #
                else:
                    Content_by_entry += '\n\n' + name_key + ':'
                    if self.__entryErrorContent.has_key(key_id):
                        if self.__entryErrorContent[key_id].has_key(type_key):
                            Content_by_entry += '\n' + self.__entryErrorContent[key_id][type_key]
                        else:
                            Content_by_entry += ' OK'
                    else:
                        Content_by_entry += ' OK'
                    #
                #
            #
            self.__returnContent += Content_by_entry
            #
            summaryfile = open(os.path.join(self.__sessionPath, key_id + '.summary'), 'w')
            summaryfile.write(Content_by_entry + '\n')
            summaryfile.close()
        #

    def __runGzipMP(self):
        if self.__errorContent:
            return
        #
        gzipOp = GzipMP(path=self.__sessionPath, siteId=self.__siteId, entryList=self.__releaseList, \
                        log=self.__lfh, verbose=self.__verbose)
        gzipOp.run()

    def __copyEMaps(self):
        if not self.__releaseEMList:
            return
        #
        self.__getFileContentDictionary()
        #
        scriptfile = getFileName(self.__sessionPath, 'copy_em', 'csh')
        logfile    = getFileName(self.__sessionPath, 'copy_em', 'log')
        #
        script = os.path.join(self.__sessionPath, scriptfile)
        f = file(script, 'w')
        f.write('#!/bin/tcsh -f\n')
        f.write('#\n')
        for dir in self.__releaseEMList:
            if not dir.has_key('emdb_id'):
                continue
            #
            emdb_id = dir['emdb_id']
            entryId = dir['entry']
            key_id = entryId
            if dir.has_key('pdb_id'):
                key_id = dir['pdb_id'].lower()
            #
            modelfile = os.path.join(self.__sessionPath, emdb_id.replace('-', '_').lower() + '_v2.xml')
            if not os.access(modelfile, os.F_OK):
                modelfile = ''
            #   modelfile = os.path.join(self.__sessionPath, emdb_id.replace('-', '_').lower() + '.cif')
            #   if not os.access(modelfile, os.F_OK):
            #       modelfile = os.path.join(self.__sessionPath, entryId + self.__fileTypeList[0][0])
            #       if not os.access(modelfile, os.F_OK):
            #           modelfile = ''
            #       #
            #   #
            #
            mapfile = os.path.join(self.__sessionPath, entryId + self.__fileTypeList[2][0])
            if not os.access(mapfile, os.F_OK):
                mapfile = ''
            #
            #if (not modelfile) and (not mapfile):
            #    continue
            #
            f.write('if ( ( -e ' + self.__topReleaseDir + '/emd/' + emdb_id + ' ) ) then\n')
            f.write('    /bin/rm -rf ' + self.__topReleaseDir + '/emd/' + emdb_id + '\n')
            f.write('endif\n')
            f.write('#\n')
            #
            f.write('/bin/mkdir ' + self.__topReleaseDir + '/emd/' + emdb_id + '\n')
            if modelfile:
                f.write('/bin/mkdir ' + self.__topReleaseDir + '/emd/' + emdb_id + '/header\n')
                f.write('/bin/cp -f ' + modelfile + ' ' + self.__topReleaseDir + '/emd/' + emdb_id + '/header\n')
                f.write('#\n')
                #
            #
            if mapfile:
                f.write('/bin/mkdir ' + self.__topReleaseDir + '/emd/' + emdb_id + '/map\n')
                f.write('/bin/cp -f ' + mapfile + ' ' + self.__topReleaseDir + '/emd/' + emdb_id + '/map/' + emdb_id.replace('-', '_').lower() + '.map\n')
                f.write('/bin/gzip -f ' + self.__topReleaseDir + '/emd/' + emdb_id + '/map/' + emdb_id.replace('-', '_').lower() + '.map\n')
                f.write('#\n')
            #
            summaryfile = os.path.join(self.__sessionPath, key_id + '.summary')
            if os.access(summaryfile, os.F_OK):
                f.write('/bin/cp -f ' + summaryfile + ' ' + self.__topReleaseDir + '/emd/' + emdb_id + '/' + key_id + '.summary\n')
                f.write('#\n')
            #
            partMap = self.__getAdditionalFilePartNumber(entryId)
            if not partMap:
                continue
            #
            for list in self.__em_additional_list:
                if not self.__contentD.has_key(list[0]):
                    continue
                #
                for fType in self.__contentD[list[0]][0]:
                    contentType = list[0]+ '_' + fType
                    if not partMap.has_key(contentType):
                        continue
                    #
                    formatExt = self.__formatD[fType]
                    #
                    for part in partMap[contentType]:
                        partExt = ''
                        if len(partMap[contentType]) > 1 or list[2] == 'masks':
                            partExt = '_' + part
                        #
                        sourcePath = self.__pI.getFilePath(dataSetId=entryId, wfInstanceId=None, contentType=list[0], formatType=fType, \
                                       fileSource='archive', versionId='latest', partNumber=part)
                        if (not sourcePath) or not os.access(sourcePath, os.F_OK):
                            continue
                        #
                        f.write('if ( ! ( -e ' + self.__topReleaseDir + '/emd/' + emdb_id + '/' + list[2] + ' ) ) then\n')
                        f.write('    /bin/mkdir ' + self.__topReleaseDir + '/emd/' + emdb_id + '/' + list[2] + '\n')
                        f.write('endif\n')
              
                        f.write('/bin/cp -f ' + sourcePath + ' ' + self.__topReleaseDir + '/emd/' + emdb_id + '/' + list[2] + \
                                '/' + emdb_id.replace('-', '_').lower() + list[1] + partExt + '.' + formatExt + '\n')
                        if list[3] == 'yes':
                            f.write('/bin/gzip -f ' + self.__topReleaseDir + '/emd/' + emdb_id + '/' + list[2] + \
                                    '/'  + emdb_id.replace('-', '_').lower() + list[1] + partExt + '.' + formatExt + '\n')
                        #
                    #
                #
            #
        #
        f.close()
        RunScript(self.__sessionPath, scriptfile, logfile)

    def __insertEntryError(self, id, type, err):
        if self.__entryErrorContent.has_key(id):
            if self.__entryErrorContent[id].has_key(type):
                self.__entryErrorContent[id][type] += '\n' + err
            else:
                self.__entryErrorContent[id][type] = err
        else:
            dir = {}
            dir[type] = err
            self.__entryErrorContent[id] = dir
        #

    def __isBigEntry(self, inputfile, pdbid):
        scriptfile = getFileName(self.__sessionPath, 'check_bigentry', 'csh')
        logfile    = getFileName(self.__sessionPath, 'check_bigentry', 'log')
        clogfile   = getFileName(self.__sessionPath, 'check_bigentry_command', 'log')
        #
        script = os.path.join(self.__sessionPath, scriptfile)
        f = file(script, 'w')
        f.write('#!/bin/tcsh -f\n')
        f.write('#\n')
        f.write('setenv RCSBROOT ' + self.__cI.get('SITE_ANNOT_TOOLS_PATH') + '\n')
        f.write('setenv COMP_PATH ' + self.__cI.get('SITE_CC_CVS_PATH') + '\n')
        f.write('setenv BINPATH ${RCSBROOT}/bin\n')
        f.write('#\n')
        f.write('${BINPATH}/CheckBigEntry -input ' + inputfile + ' -output ' + pdbid + \
                '.bigentry -log ' + logfile + '\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        #
        filename = os.path.join(self.__sessionPath, pdbid + '.bigentry')
        if os.access(filename, os.F_OK):
            f = file(filename, 'r')
            data = f.read()
            f.close()
            #
            if data.startswith('large entry'):
                return True
            #
        #
        return False

    def __mergeEntryErrors(self, e_error):
        if not e_error:
            return
        #
        for k,dir in e_error.items():
            if not self.__entryErrorContent.has_key(k):
                self.__entryErrorContent[k] = dir
            else:
                for k1,v in dir.items():
                    if not self.__entryErrorContent[k].has_key(k1):
                        self.__entryErrorContent[k][k1] = v
                    else:
                        self.__entryErrorContent[k][k1] += '\n' + v
                    #
                #
            #
        #

    def __mergeSysErrors(self, s_error):
        if not s_error:
            return
        #
        for err in s_error:
            if self.__sysErrorContent and (err in self.__sysErrorContent):
                continue
            #
            self.__sysErrorContent.append(err)
        #

    def __updateDatabase(self):
        """ Update content & workflow database
        """
        if not self.__updateFileList:
            return
        #
        file_list = []
        for dir in self.__updateFileList:
            entryId = dir['entry']
            key_id = entryId
            if dir.has_key('pdb_id'):
                key_id = dir['pdb_id'].lower()
            #
            fn = os.path.join(self.__sessionPath, entryId + '_model_P1.cif')
            if not os.access(fn, os.F_OK):
                continue
            #
            message = ''
            file_list.append(fn)
            #
            status_map = {}
            if dir.has_key('status_code') and dir['status_code']:
                status  = dir['status_code']
                if status != '' and status != 'RELOAD' and status != 'CITATIONUpdate':
                    status_map['status_code'] = status
                    #returnCode = self.__updateWfDb(entryId, 'STATUS_CODE', status)
                    #message = "Update workflow DB status to '" + status + "' " + returnCode
                #
            #
            if dir.has_key('status_code_em') and dir['status_code_em']:
                status_map['status_code_emdb'] = dir['status_code_em']
            #
            if status_map:
                returnCode = self.__updateWfDb(entryId, status_map)
                message = "Update workflow DB status to " + ",".join([ "'%s' = '%s'" % (k, v) for k, v in status_map.iteritems()]) + " " + returnCode
            #
            code = 'failed.'
            returnStatus = killAllWF(entryId, 'RelMod') 
            if returnStatus.strip().upper() == 'OK':
                code = 'successful.'
            #
            if message:
                message += '\n'
            #
            message += 'Killing WF ' + code
            self.__wfDBUpdateStatus[key_id] = message
        #
        dbLoader = DBLoadUtil(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        dbLoader.doLoading(file_list)

    def __updateWfDb(self, idCode, statusCodeMap):
        """ Update workflow database
        """
        returnCode = 'failed.'
        try:
            c = WfDbApi(self.__lfh, self.__verbose)
            """
            rd = c.getObject(idCode)
            #rd['STATUS_CODE'] = statusCode
            for k,v in statusCodeMap.items():
                rd[k] = v
            #
            constDict = {}
            constDict['DEP_SET_ID'] = idCode
            dBreturnCode = c.saveObject(rd, 'update', constDict)
            if dBreturnCode and dBreturnCode == 'ok':
            """
            sql = "update deposition set " + ",".join([ "%s = '%s'" % (k, v) for k, v in statusCodeMap.iteritems()]) \
                + " where dep_set_id = '" + idCode + "'"
            ret = c.runUpdateSQL(sql)
            if ret != None:
                returnCode = 'successful.'
            #
        except:
            if (self.__verbose):
                self.__lfh.write("+UpdateFile.__updateWfDb() wfload failed  %s\n" % idCode)
                traceback.print_exc(file=self.__lfh)
            #
        #
        return returnCode

    def __updateStatusHistory(self):
        """
        """
        if not self.__releaseList:
            return
        #
        for dir in self.__releaseList:
            entryId = dir['entry']
            if (not dir.has_key('entry')) or (not dir.has_key('status_code')):
                continue
            #
            try:
                okShLoad = False
                shu = StatusHistoryUtils(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
                okShUpdate = shu.updateEntryStatusHistory(entryIdList=[dir['entry']], \
                         statusCode=dir['status_code'], annotatorInitials=dir['annotator'], \
                         details="Update by release module")
                if okShUpdate:
                    okShLoad = shu.loadEntryStatusHistory(entryIdList=[dir['entry']])
                if (self.__verbose):
                    self.__lfh.write("+UpdateFile.__updateStatusHistory() %s status history database load status %r\n" % (dir['entry'], okShLoad))
            except:
                if (self.__verbose):
                    self.__lfh.write("+UpdateFile.__updateStatusHistory() %s status history update and database load failed with exception\n")
                    traceback.print_exc(file=self._lfh)
                #
            #
        #

    def __cif2xmlTranslate(self, ciffile, xmlfile):
        #scriptfile = getFileName(self.__sessionPath, 'convert_xml', 'csh')
        logfile    = getFileName(self.__sessionPath, 'convert_xml', 'log')
        """
        #
        script = os.path.join(self.__sessionPath, scriptfile)
        f = file(script, 'w')
        f.write('#!/bin/tcsh -f\n')
        f.write('#\n')
        f.write('setenv DEPLOY_DIR ' + self.__cI.get('SITE_DEPLOY_PATH') + '\n')
        f.write('source ${DEPLOY_DIR}/scripts/env/runtime-environment.csh\n')
        f.write('setenv PYTHONPATH ' + self.__cI.get('SITE_TOOLS_PATH') + '/cifEMDBTranslator:${PYTHONPATH}\n')
        f.write('#\n')
        f.write('python ' + self.__cI.get('SITE_PYTHON_SOURCE_PATH') + '/wwpdb/apps/releasemodule/update/Emd2XmlTranslator.py ' + \
                ciffile + ' ' + xmlfile + '\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, logfile)
        #
        """
        logger = logging.getLogger()
        logging.captureWarnings(True)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(message)s")
        handler = logging.FileHandler(os.path.join(self.__sessionPath, logfile))
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
            self.__lfh.write("+UpdateFile.__cif2xmlTranslate failing for %s\n" % ciffile)
            se = traceback.format_exc()
            self.__lfh.write("+UpdateFile.__cif2xmlTranslate %s\n" % se)
        #
        if os.access(xmlfile, os.F_OK):
            return ""
        #
        error = GetLogMessage(os.path.join(self.__sessionPath, logfile))
        if not error:
            error = 'CifEMDBTranslator failed without error message'
        #
        return error

    def __getFileContentDictionary(self):
        ciD = ConfigInfoData(siteId=self.__siteId, verbose=self.__verbose, log=self.__lfh).getConfigDictionary()
        for k,v in ciD['CONTENT_TYPE_DICTIONARY'].items():
            if k not in self.__em_additional_type:
                continue
            #
            self.__contentD[k] = v
        #
        self.__formatD = ciD['FILE_FORMAT_EXTENSION_DICTIONARY']
        for k,v in self.__contentD.items():
            for ext_type in v[0]:
                self.__fileExtContentTypeD[v[1] + '_' + self.__formatD[ext_type]] = k + '_' + ext_type
            #
        #

    def __getAdditionalFilePartNumber(self, depID):
        storagePath = os.path.join(self.__cI.get('SITE_ARCHIVE_STORAGE_PATH'), 'archive', depID)
        os.chdir(storagePath)
        p_map = {}
        for filename in os.listdir('.'):
            if not filename.startswith(depID):
                continue
            #

            fFields = str(filename).strip().split('.')
            baseName = str(fFields[0]).strip()
            formatExt = str(fFields[1]).strip()
            nFields = baseName.split('_')
            fileExt = nFields[2] + '_' + formatExt
            if not self.__fileExtContentTypeD.has_key(fileExt):
                continue
            #
            ContentType = self.__fileExtContentTypeD[fileExt]
            PartNumber = str(nFields[3]).strip().replace('P', '')
            if p_map.has_key(ContentType):
                if PartNumber not in p_map[ContentType]:
                    p_map[ContentType].append(PartNumber)
                #
            else:
                p_list = []
                p_list.append(PartNumber)
                p_map[ContentType] = p_list
            #
        #
        return p_map

    def __getSession(self):
        """ Join existing session or create new session as required.
        """
        #
        self.__sObj=self.__reqObj.newSessionObj()
        self.__sessionId=self.__sObj.getId()
        self.__sessionPath=self.__sObj.getPath()
        if (self.__verbose):
            self.__lfh.write("------------------------------------------------------\n")                    
            self.__lfh.write("+UpdateFile.__getSession() - creating/joining session %s\n" % self.__sessionId)
            self.__lfh.write("+UpdateFile.__getSession() - session path %s\n" % self.__sessionPath)            
