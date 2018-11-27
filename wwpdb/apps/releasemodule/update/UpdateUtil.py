##
# File:  UpdateUtil.py
# Date:  08-Aug-2013
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

import os, sys, string, traceback

from wwpdb.utils.config.ConfigInfo                      import ConfigInfo
from mmcif.io.PdbxWriter                           import PdbxWriter
from mmcif.api.PdbxContainers                       import *
from wwpdb.apps.entity_transform.utils.GetLogMessage  import GetLogMessage
from wwpdb.apps.entity_transform.utils.mmCIFUtil      import mmCIFUtil
from wwpdb.apps.releasemodule.utils.Utility           import *

class UpdateUtil(object):
    """ Class responsible for Update coordinate cif file.
    """
    def __init__(self, path='.', siteId=None, processLabel='', \
                 entryList=None, pubmedInfo=None, verbose=False, log=sys.stderr):
        """
        """
        self.__sessionPath  = path
        self.__siteId       = siteId
        self.__processLabel = processLabel
        self.__updateList   = entryList
        self.__pubmedInfo   = pubmedInfo
        self.__verbose      = verbose
        self.__lfh          = log
        #
        self.__cI = ConfigInfo(self.__siteId)
        self.__rcsbRoot = self.__cI.get('SITE_ANNOT_TOOLS_PATH')
        self.__compRoot = self.__cI.get('SITE_CC_CVS_PATH')
        #
        self.__entryErrorContent = {}
        self.__errorContent  = ''
        #

    def run(self):
        if len(self.__updateList) == 0:
            return
        #
        if self.__processLabel:
            inputfile  = 'inputfile_' + self.__processLabel + '.cif'
            outputfile  = 'outputfile_' + self.__processLabel + '.cif'
            scriptfile = 'update_' + self.__processLabel + '.csh'
            logfile    = 'update_' + self.__processLabel + '.log'
            clogfile   = 'update_command_' + self.__processLabel + '.log'
        else:
            inputfile  = getFileName(self.__sessionPath, 'inputfile', 'cif')
            outputfile  = getFileName(self.__sessionPath, 'outputfile', 'cif')
            scriptfile = getFileName(self.__sessionPath, 'update', 'csh')
            logfile    = getFileName(self.__sessionPath, 'update', 'log')
            clogfile   = getFileName(self.__sessionPath, 'update_command', 'log')
        #
        self.__genUpdateInputFile(inputfile)
        self.__genScriptFile(scriptfile, inputfile, outputfile, logfile)
        RunScript(self.__sessionPath, scriptfile, clogfile)
        #
        self.__errorContent += GetLogMessage(os.path.join(self.__sessionPath, logfile))
        self.__errorContent += GetUniqueLogMessage(self.__rcsbRoot + '/bin/RelModuleUpdate', \
                                             os.path.join(self.__sessionPath, clogfile))
        #if self.__errorContent:
        #    self.__deleteUpdateUtils()
        self.__readOutputFile(outputfile)
        self.__checkUpdateFile()

    def getEntryMessage(self):
        return self.__entryErrorContent

    def getErrorMessage(self):
        return self.__errorContent

    def __genUpdateInputFile(self, filename):
        items = [ 'entry', 'pdbid', 'annotator', 'option', 
                  'input_file',    'output_file',    'status_code',
                  'input_file_sf', 'output_file_sf', 'status_code_sf',
                  'input_file_mr', 'output_file_mr', 'status_code_mr',
                  'input_file_cs', 'output_file_cs', 'status_code_cs',
                  'status_code_em', 'approval_type', 'revdat_tokens',
                  'obsolete_ids',  'supersede_ids' ]
        #
        myDataList = []
        for dir in self.__updateList:
            curContainer = DataContainer(dir['entry'])
            curCat = DataCategory('update_info')
            for item in items:
                curCat.appendAttribute(item)
            #
            for item in items:
                if item == 'pdbid':
                    item1 = 'pdb_id'
                else:
                    item1 = item
                #
                if dir.has_key(item1) and dir[item1] != 'RELOAD' and dir[item1] != 'CITATIONUpdate':
                    curCat.setValue(dir[item1], item, 0)
                #
            #
            curContainer.append(curCat)
            #
            if dir.has_key('revision'):
                revCat = DataCategory('revision')
                revCat.appendAttribute('revision_type')
                revCat.appendAttribute('details')
                row = 0
                for dir1 in dir['revision']:
                    for item1 in ( 'revision_type', 'details' ):
                        if dir1.has_key(item1):
                            revCat.setValue(dir1[item1], item1, row)
                        #
                    #
                    row += 1
                #
                curContainer.append(revCat)
            #
            if dir.has_key('pubmed'):
                pubCat = self.__genPubmedCategory(dir['pubmed'])
                if pubCat:
                    curContainer.append(pubCat)
                #
            elif dir.has_key('citation'):
                pubCat = self.__genCitationCategory(dir['citation'])
                if pubCat:
                    curContainer.append(pubCat)
                #
            #
            myDataList.append(curContainer)
        #
        inputfile = os.path.join(self.__sessionPath, filename)
        f = file(inputfile, 'w')
        pdbxW = PdbxWriter(f)
        pdbxW.write(myDataList)
        f.close()

    def __genPubmedCategory(self, pubmed_list):
        if not pubmed_list or not self.__pubmedInfo:
            return None
        #
        items = [ 'id', 'pdbx_database_id_PubMed', 'pdbx_database_id_DOI',
                  'title', 'journal_abbrev', 'journal_volume', 'page_first',
                  'page_last', 'year', 'journal_id_ISSN', 'author' ]
        cat = DataCategory('pubmed_info')
        for item in items:
            cat.appendAttribute(item)
        #
        row = 0
        for dir in pubmed_list:
            pubmed_id = dir['pdbx_database_id_PubMed']
            for item in items:
                if dir.has_key(item):
                    cat.setValue(dir[item], item, row)
                    continue
                #
                if not self.__pubmedInfo.has_key(pubmed_id) or \
                   not self.__pubmedInfo[pubmed_id].has_key(item):
                    continue
                #
                cat.setValue(self.__pubmedInfo[pubmed_id][item], item, row);
            #
            row += 1
        #
        return cat

    def __genCitationCategory(self, dir):
        items = [ 'id', 'pdbx_database_id_PubMed', 'pdbx_database_id_DOI',
                  'title', 'journal_abbrev', 'journal_volume', 'page_first',
                  'page_last', 'year', 'journal_id_ISSN', 'author' ]
        cat = DataCategory('pubmed_info')
        for item in items:
            cat.appendAttribute(item)
        #
        for item in items:
            if dir.has_key(item):
                cat.setValue(dir[item], item, 0)
            #
        #
        return cat

    def __genScriptFile(self, scriptfile, inputfile, outputfile, logfile):
        script = os.path.join(self.__sessionPath, scriptfile)
        f = file(script, 'w')
        f.write('#!/bin/tcsh -f\n')
        f.write('#\n')
        f.write('setenv RCSBROOT ' + self.__rcsbRoot + '\n')
        f.write('setenv COMP_PATH ' + self.__compRoot + '\n')
        f.write('setenv BINPATH ${RCSBROOT}/bin\n')
        f.write('#\n')
        f.write('${BINPATH}/RelModuleUpdate -input ' + inputfile + \
                ' -output ' + outputfile + ' -log ' + logfile + '\n')
        f.write('#\n')
        f.close()

    def __deleteUpdateUtils(self):
        for dir in self.__updateList:
            rcsbid = dir['entry'].lower()
            filename = os.path.join(self.__sessionPath, rcsbid + '.cif')
            if os.access(filename, os.F_OK):
                os.remove(filename)
            #
        #

    def __readOutputFile(self, filename):
        outputfile = os.path.join(self.__sessionPath, filename)
        if not os.access(filename, os.F_OK):
            return
        #
        cifObj = mmCIFUtil(filePath=outputfile)
        rlist = cifObj.GetValue('error_message')
        for dir in rlist:
            if self.__entryErrorContent.has_key(dir['pdbid']):
                self.__entryErrorContent[dir['pdbid']][dir['type']] = dir['message']
            else:
                dir1 = {}
                dir1[dir['type']] = dir['message']
                self.__entryErrorContent[dir['pdbid']] = dir1
            #
        #

    def __checkUpdateFile(self):
        item_list = [ [ 'output_file',  'coor', 'coordinate'        ],
                      [ 'output_file_sf', 'sf', 'structural factor' ],
                      [ 'output_file_mr', 'mr', 'nmr constraints'   ],
                      [ 'output_file_cs', 'cs', 'chemical shifts'   ] ]
        #
        for dir in self.__updateList:
            key_id = dir['entry']
            if dir.has_key('pdb_id'):
                key_id = dir['pdb_id'].lower()
            #
            for list in item_list:
                if not dir.has_key(list[0]):
                    continue
                #
                filename = os.path.join(self.__sessionPath, dir[list[0]])
                if os.access(filename, os.F_OK):
                    continue
                #
                err = 'Missing updated ' + list[2] + ' file.'
                if self.__entryErrorContent.has_key(key_id):
                    if self.__entryErrorContent[key_id].has_key(list[1]):
                        self.__entryErrorContent[key_id][list[1]] += '\n' + err
                    else:
                        self.__entryErrorContent[key_id][list[1]] = err
                else:
                    dir1 = {}
                    dir1[list[1]] = err
                    self.__entryErrorContent[key_id] = dir1
                #
            #
        #
