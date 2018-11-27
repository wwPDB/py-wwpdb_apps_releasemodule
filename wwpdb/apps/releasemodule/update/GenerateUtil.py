##
# File:  GenerateUtil.py
# Date:  20-Aug-2013
# Updates:
##
"""
Generate all release public files.

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

import os, shutil, string, sys, traceback

from wwpdb.api.facade.ConfigInfo                      import ConfigInfo
from wwpdb.apps.entity_transform.utils.GetLogMessage  import GetLogMessage
from wwpdb.apps.releasemodule.utils.Utility           import *

class GenerateUtil(object):
    """ Class responsible for generating release public files
    """
    def __init__(self, path='.', siteId=None, processLabel='', entryList=None, verbose=False, log=sys.stderr):
        """
        """
        self.__sessionPath  = path
        self.__siteId       = siteId
        self.__processLabel = processLabel
        self.__updateList   = entryList
        self.__verbose      = verbose
        self.__lfh          = log
        #
        self.__cI = ConfigInfo(self.__siteId)
        self.__rcsbRoot = self.__cI.get('SITE_ANNOT_TOOLS_PATH')
        self.__compRoot = self.__cI.get('SITE_CC_CVS_PATH')
        self.__dictBinRoot = os.path.join(self.__cI.get('SITE_PACKAGES_PATH'), 'dict', 'bin')
        self.__dictRoot = self.__cI.get('SITE_PDBX_DICT_PATH')
        self.__dictionary_v40 = self.__cI.get('SITE_PDBX_V4_DICT_NAME') + '.sdb'
        self.__dictionary_v42 = 'mmcif_pdbx_v42.odb'
        self.__prefix = 'pdbx-v42'
        self.__dictionary_v5 = self.__cI.get('SITE_PDBX_DICT_NAME') + '.sdb'
        #
        self.__entryErrorContent = {}
        self.__errorContent  = []
        #

    def run(self):
        file_items = [ [ 'output_file',    'status_code',  'coor' ],
                       [ 'output_file_sf', 'status_code_sf', 'sf' ],
                       [ 'output_file_mr', 'status_code_mr', 'mr' ],
                       [ 'output_file_cs', 'status_code_cs', 'cs' ] ]
        #
        if len(self.__updateList) == 0:
            return
        #
        for dir in self.__updateList:
            pdbid = dir['pdb_id'].lower()
            entryId = dir['entry']
            for list in file_items:
                if not dir.has_key(list[0]) or not dir.has_key(list[1]):
                    continue
                #
                if dir[list[1]] != 'REL' and dir[list[1]] != 'REREL' and dir[list[1]] != 'OBS' and dir[list[1]] != 'RELOAD':
                    continue
                #
                filename = os.path.join(self.__sessionPath, dir[list[0]])
                if not os.access(filename, os.F_OK):
                    continue
                #
                if list[2] == 'coor':
                    skipFlag = False
                    if dir[list[1]] == 'RELOAD':
                        skipFlag = True
                    #
                    bigEntryFlag = False
                    if dir.has_key('big_entry'):
                        bigEntryFlag = True
                        skipFlag = False
                    #
                    self.__generateAllCoordFiles(bigEntryFlag, dir[list[0]], entryId, pdbid, skipFlag)
                elif list[2] == 'sf':
                    self.__generateSFFile(dir[list[0]], pdbid)
                elif list[2] == 'mr':
                    self.__generateMRFile(dir[list[0]], pdbid)
                elif list[2] == 'cs':
                    self.__generateCSFile(dir[list[0]], pdbid)
                #
            #
        #

    def getEntryMessage(self):
        return self.__entryErrorContent

    def getErrorMessage(self):
        return self.__errorContent

    def __generateAllCoordFiles(self, bigEntryFlag, inputfile, entryId, pdbid, skipFlag):
        if not skipFlag:
            #if not self.__isBigEntry(inputfile, pdbid):
            if not bigEntryFlag:
                self.__generatePDBFile(inputfile, entryId, pdbid)
                self.__generateBioPDBFiles(inputfile, pdbid)
            else:
                self.__generatePdbBundleFile(inputfile, pdbid)
                self.__generateBioCIFFiles(inputfile, pdbid)
            #
        #
        self.__generateCIFFile(inputfile, pdbid)
        self.__generateXMLFiles(pdbid)

    def __generateSFFile(self, inputfile, pdbid):
        #self.__copyFile(inputfile, pdbid, '-sf.cif')
        shutil.copy(os.path.join(self.__sessionPath, inputfile), \
                    os.path.join(self.__sessionPath, 'r' + pdbid + 'sf.ent'))
        self.__checkReleaseFile(pdbid, 'sf', 'Coping', 'r' + pdbid + 'sf.ent')

    def __generateMRFile(self, inputfile, pdbid):
        self.__copyFile(inputfile, pdbid, '.mr')
        self.__checkReleaseFile(pdbid, 'mr', 'Coping', pdbid + '.mr')

    def __generateCSFile(self, inputfile, pdbid):
        self.__copyFile(inputfile, pdbid, '-cs.cif')
        self.__generateCSStarFile(pdbid, '-cs.cif')
        self.__checkReleaseFile(pdbid, 'cs', 'Coping', pdbid + '-cs.cif')
        self.__checkReleaseFile(pdbid, 'cs', 'Generating', pdbid + '_cs.str')

#   def __isBigEntry(self, inputfile, pdbid):
#       scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('check_bigentry')
#       #
#       f = self.__openScriptFile(scriptfile)
#       f.write('${BINPATH}/CheckBigEntry -input ' + inputfile + ' -output ' + pdbid + \
#               '.bigentry -log ' + logfile + '\n')
#       f.write('#\n')
#       f.close()
#       #
#       RunScript(self.__sessionPath, scriptfile, clogfile)
#       #
#       filename = os.path.join(self.__sessionPath, pdbid + '.bigentry')
#       if os.access(filename, os.F_OK):
#           f = file(filename, 'r')
#           data = f.read()
#           f.close()
#           #
#           if data.startswith('large entry'):
#               return True
#           #
#       #
#
#       return False

    def __generatePDBFile(self, inputfile, entryId, pdbid):
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('generate_pdb')
        #
        f = self.__openScriptFile(scriptfile)
        f.write('${BINPATH}/maxit -i ' + inputfile + ' -o 2 -output pdb' + pdbid + \
                '.ent -log ' + logfile + '\n')
        f.write('if ( -e pdb' + pdbid + '.ent ) then\n')
        f.write('    cp -f pdb' + pdbid + '.ent ' + entryId + '_model_P1.pdb\n')
        f.write('endif\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        self.__readSYSError(self.__rcsbRoot + '/bin/maxit', clogfile)
        #
        self.__checkReleaseFile(pdbid, 'pdb', 'Generating', 'pdb' + pdbid + '.ent')

    def __generatePdbBundleFile(self, inputfile, pdbid):
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('generate_pdbbundle')
        #
        f = self.__openScriptFile(scriptfile)
        f.write('${BINPATH}/GetPdbBundle -input ' + inputfile + ' -log ' + logfile + '\n')
        f.write('tar cvf ' + pdbid + '-pdb-bundle.tar ' + pdbid + '-pdb-bundle*.pdb ' + pdbid + '-chain-id-mapping.txt >& tar_log\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        self.__readSYSError(self.__rcsbRoot + '/bin/maxit', clogfile)

    def __generateBioPDBFiles(self, inputfile, pdbid):
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('generate_biolpdb')
        #
        f = self.__openScriptFile(scriptfile)
        f.write('${BINPATH}/GenBioPDBFile -input ' + inputfile + ' -output ' + pdbid + \
                ' -log ' + logfile + '\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        self.__readSYSError(self.__rcsbRoot + '/bin/GenBioPDBFile', clogfile)

    def __generateBioCIFFiles(self, inputfile, pdbid):
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('generate_biolcif')
        #
        f = self.__openScriptFile(scriptfile)
        f.write('${BINPATH}/GenBioCIFFile -input ' + inputfile + ' -depid ' + pdbid + \
                ' -index ' + pdbid + '.biolcif_index -public -log ' + logfile + '\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        self.__readSYSError(self.__rcsbRoot + '/bin/GenBioCIFFile', clogfile)

    def __generateCIFFile(self, inputfile, pdbid):
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('generate_cif')
        #
        f = self.__openScriptFile(scriptfile)
        f.write('${DICTBINPATH}/cifexch2 -dicSdb ' + os.path.join(self.__dictRoot, self.__dictionary_v5) + \
                ' -pdbxDicSdb ' + os.path.join(self.__dictRoot, self.__dictionary_v40) + \
                ' -reorder -strip -op in -pdbids -input ' + inputfile + ' -output ' + pdbid + '.cif\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        #self.__readSYSError(self.__dictBinRoot + '/cifexch2', clogfile)
        #
        self.__checkReleaseFile(pdbid, 'cif', 'Generating', pdbid + '.cif')

    def __generateXMLFiles(self, pdbid):
        filename = os.path.join(self.__sessionPath, pdbid + '.cif')
        if not os.access(filename, os.F_OK):
            return
        #
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('generate_xml')
        #
        f = self.__openScriptFile(scriptfile)
        f.write('${DICTBINPATH}/mmcif2XML -dictName mmcif_pdbx.dic -df ' + os.path.join(self.__dictRoot, \
                self.__dictionary_v42) + ' -prefix ' + self.__prefix + ' -ns PDBx -funct mmcif2xmlall -f ' + pdbid + '.cif\n') 
        f.write('#\n')
        f.write('if ( -e ' + pdbid + '.cif.xml ) then\n')
        f.write('    mv -f ' + pdbid + '.cif.xml ' + pdbid + '.xml\n')
        f.write('endif\n')
        f.write('#\n')
        f.write('if ( -e ' + pdbid + '.cif.xml-noatom ) then\n')
        f.write('    mv -f ' + pdbid + '.cif.xml-noatom ' + pdbid + '-noatom.xml\n')
        f.write('endif\n')
        f.write('#\n')
        f.write('if ( -e ' + pdbid + '.cif.xml-extatom ) then\n')
        f.write('    mv -f ' + pdbid + '.cif.xml-extatom ' + pdbid + '-extatom.xml\n')
        f.write('endif\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        #self.__readSYSError(self.__dictBinRoot + 'mmcif2XML', clogfile)
        self.__checkSYSError(pdbid, 'xml', self.__dictBinRoot + 'mmcif2XML', clogfile)
        #
        self.__checkReleaseFile(pdbid, 'xml', 'Generating', pdbid + '.xml')
        self.__checkReleaseFile(pdbid, 'xml', 'Generating', pdbid + '-noatom.xml')
        self.__checkReleaseFile(pdbid, 'xml', 'Generating', pdbid + '-extatom.xml')

    def __checkSYSError(self, pdbid, type, program, logfile):
        error = GetUniqueLogMessage(program, os.path.join(self.__sessionPath, logfile))
        if error:
            self._insertEntryErrorContent(pdbid, type, error)
        #

    def __checkReleaseFile(self, pdbid, type, action, filename):
        fullname = os.path.join(self.__sessionPath, filename)
        if os.access(fullname, os.F_OK):
            return
        #
        err = action + ' ' + filename + ' failed.'
        self._insertEntryErrorContent(pdbid, type, err)

    def _insertEntryErrorContent(self, pdbid, type, err):
        if self.__entryErrorContent.has_key(pdbid):
            if self.__entryErrorContent[pdbid].has_key(type):
                self.__entryErrorContent[pdbid][type] += '\n' + err
            else:
                self.__entryErrorContent[pdbid][type] = err
        else:
            dir = {}
            dir[type] = err
            self.__entryErrorContent[pdbid] = dir
        #

    def __copyFile(self, inputfile, pdbid, ext):
        shutil.copy(os.path.join(self.__sessionPath, inputfile), \
                    os.path.join(self.__sessionPath, pdbid + ext))

    def __generateCSStarFile(self, pdbid, ext):
        filename = os.path.join(self.__sessionPath, pdbid + ext)
        if not os.access(filename, os.F_OK):
            return
        #
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('generate_star')
        #
        f = self.__openScriptFile(scriptfile)
        f.write('${BINPATH}/GenNMRStarCSFile -i ' + pdbid  + ext + ' -pdbid ' + pdbid + \
                ' -o ' + pdbid + '_cs.str\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        self.__readSYSError(self.__rcsbRoot + '/bin/GenNMRStarCSFile', clogfile)
        #

    def __getAuxiliaryFileNames(self, prefix):
        if self.__processLabel:
            scriptfile = prefix + '_' + self.__processLabel + '.csh'
            logfile    = prefix + '_' + self.__processLabel + '.log'
            clogfile   = prefix + '_command_' + self.__processLabel + '.log'
        else:
            scriptfile = getFileName(self.__sessionPath, prefix, 'csh')
            logfile    = getFileName(self.__sessionPath, prefix, 'log')
            clogfile   = getFileName(self.__sessionPath, prefix + '_command', 'log')
        #
        return scriptfile,logfile,clogfile

    def __openScriptFile(self, scriptfile):
        script = os.path.join(self.__sessionPath, scriptfile)
        f = file(script, 'w')
        f.write('#!/bin/tcsh -f\n')
        f.write('#\n')
        f.write('setenv RCSBROOT ' + self.__rcsbRoot + '\n')
        f.write('setenv COMP_PATH ' + self.__compRoot + '\n')
        f.write('setenv BINPATH ${RCSBROOT}/bin\n')
        f.write('setenv DICTBINPATH ' + self.__dictBinRoot + '\n')
        f.write('#\n')
        return f

    def __readSYSError(self, program, logfile):
        error = GetUniqueLogMessage(program, os.path.join(self.__sessionPath, logfile))
        if not error:
            return
        #
        if self.__errorContent and (error in self.__errorContent):
            return
        #
        self.__errorContent.append(error)
