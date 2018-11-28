##
# File:  CheckUtil.py
# Date:  28-Aug-2013
# Updates:
##
"""
Check all release public files.

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

from wwpdb.utils.config.ConfigInfo                    import ConfigInfo
from wwpdb.apps.releasemodule.utils.GetLogMessage     import GetLogMessage
from wwpdb.apps.releasemodule.utils.TimeUtil          import TimeUtil
from wwpdb.apps.releasemodule.utils.Utility           import *

class CheckUtil(object):
    """ Class responsible for checking release public files
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
        self.__localBinRoot =  os.path.join(self.__cI.get('SITE_LOCAL_APPS_PATH'), 'bin')
        self.__dictBinRoot = os.path.join(self.__cI.get('SITE_PACKAGES_PATH'), 'dict', 'bin')
        self.__dictRoot = self.__cI.get('SITE_PDBX_DICT_PATH')
        self.__dictionary = self.__cI.get('SITE_PDBX_V4_DICT_NAME') + '.sdb'
        self.__xmlschema = 'pdbx-v42.xsd'
        #
        self.__checkResult = {}
        self.__sysError = []
        #

    def run(self):
        file_items = [ [ 'status_code',  'coor' ],
                       [ 'status_code_sf', 'sf' ],
                       [ 'status_code_mr', 'mr' ],
                       [ 'status_code_cs', 'cs' ] ]
        #
        if len(self.__updateList) == 0:
            return
        #
        # Assume all files are new release
        #
        t =TimeUtil()
        rel_date = t.NextWednesday()
        #
        for dir in self.__updateList:
            pdbid = dir['pdb_id'].lower()
            for list in file_items:
                if not dir.has_key(list[0]):
                    continue
                #
                if list[1] == 'coor':
                    re_release_flag = ''
                    if dir.has_key('directory') and dir['directory'] == 'modified':
                        re_release_flag = ' -re_release '
                    #
                    self.__checkPDBFile(dir[list[0]], pdbid, re_release_flag)
                    self.__checkCIFFile(pdbid, 'cif')
                    self.__checkXMLFile(pdbid)
                elif list[1] == 'sf':
                    #rel_date = ''
                    #if dir.has_key('date_of_sf_release') and \
                    #   dir['date_of_sf_release']:
                    #    rel_date = dir['date_of_sf_release']
                    #
                    self.__checkSFFile(rel_date, dir[list[0]], pdbid)
                    self.__checkCIFFile(pdbid, 'sf')
                elif list[1] == 'mr':
                    #rel_date = ''
                    #if dir.has_key('date_of_mr_release') and \
                    #   dir['date_of_mr_release']:
                    #    rel_date = dir['date_of_mr_release']
                    #
                    self.__checkMRFile(rel_date, dir[list[0]], pdbid)
                elif list[1] == 'cs':
                    #rel_date = ''
                    #if dir.has_key('date_of_cs_release') and \
                    #   dir['date_of_cs_release']:
                    #    rel_date = dir['date_of_cs_release']
                    #
                    self.__checkCSFile(rel_date, dir[list[0]], pdbid)
                #
            #
        #

    def getEntryMessage(self):
        return self.__checkResult

    def getErrorMessage(self):
        return self.__sysError

    def __checkPDBFile(self, status_code, pdbid, re_release_flag):
        filename = 'pdb' + pdbid + '.ent'
        fullname = os.path.join(self.__sessionPath, filename)
        if not os.access(fullname, os.F_OK):
            return
        #
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('check_pdb')
        #
        f = self.__openScriptFile(scriptfile)
        f.write('if ( -e ' + logfile + ' ) then\n')
        f.write('    rm -f ' + logfile + '\n')
        f.write('endif\n')
        f.write('#\n')
        f.write('if ( -e ' + pdbid + '_pdb.report ) then\n')
        f.write('    rm -f ' + pdbid + '_pdb.report\n')
        f.write('endif\n')
        f.write('#\n')
        f.write('${BINPATH}/CheckPDBFile -input ' + filename + \
                ' -output ' + pdbid + '_pdb.report' + \
                ' -status ' + status_code + ' -pdbid ' + pdbid + \
                ' -obslte ' + pdbid + '.obslte' + \
                ' -sprsde ' + pdbid + '.sprsde' + re_release_flag + \
                ' -log ' + logfile + '\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        #
        self.__readCheckResult('pdb', pdbid, pdbid + '_pdb.report', True)
        self.__readSYSError('pdb', pdbid, '', logfile)
        self.__readSYSError('pdb', pdbid, self.__rcsbRoot + '/bin/CheckPDBFile', clogfile)

    def __checkCIFFile(self, pdbid, type):
        filename = pdbid + '.cif'
        if type == 'sf':
            filename = 'r' + pdbid + 'sf.ent'
        #
        fullname = os.path.join(self.__sessionPath, filename)
        if not os.access(fullname, os.F_OK):
            return
        #
        filehead = 'check_cif'
        if type == 'sf':
            filehead = 'check_cif_sf'
        #
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames(filehead)
        #
        f = self.__openScriptFile(scriptfile)
        f.write('if ( -e ' + filename + '-diag.log ) then\n')
        f.write('    rm -f ' + filename + '-diag.log\n')
        f.write('endif\n')
        f.write('#\n')
        f.write('${DICTBINPATH}/CifCheck -dictSdb ' + os.path.join(self.__dictRoot, self.__dictionary) + \
                ' -f ' + filename + ' > ' + logfile + '\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        #
        self.__readCheckResult(type, pdbid, filename + '-diag.log', False)
        self.__readSYSError(type, pdbid, self.__dictBinRoot + '/CifCheck', clogfile)

    def __checkXMLFile(self, pdbid):
        filename = pdbid + '-noatom.xml'
        fullname = os.path.join(self.__sessionPath, filename)
        if not os.access(fullname, os.F_OK):
            return
        #
        statinfo = os.stat(fullname)
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('check_xml')
        #
        f = self.__openScriptFile(scriptfile)
        f.write('if ( -e ' + pdbid + '.xml.diag ) then\n')
        f.write('    rm -f ' + pdbid + '.xml.diag\n')
        f.write('endif\n')
        f.write('#\n')
        f.write('if ( ! ( -e ' + self.__xmlschema + ' ) ) then\n')
        f.write('    cp -f ' + os.path.join(self.__dictRoot, self.__xmlschema) + ' .\n')
        f.write('endif\n')
        f.write('#\n')
        if statinfo.st_size < 100000000:
            f.write('${LOCALBINPATH}/xmllint --noout --schema ' + os.path.join(self.__dictRoot, self.__xmlschema) + \
                    ' ' + filename + ' >& ' + pdbid + '.xml.diag\n')
        #
        f.write('${LOCALBINPATH}/StdInParse -s -f -n -v=always < ' + filename + ' >>& ' + pdbid + '.xml.diag\n')
        #
        #fullname = os.path.join(self.__sessionPath, pdbid + '-extatom.xml')
        #if os.access(fullname, os.F_OK):
        #    f.write('${LOCALBINPATH}/xmllint --noout --schema ' + os.path.join(self.__dictRoot, \
        #            self.__xmlschema) + ' ' + pdbid + '-extatom.xml' + ' >>& ' + pdbid + '.xml.diag\n')
        #
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        #
        #if self.__readSYSError(self.__localBinRoot + '/xmllint', clogfile):
        #    fullname = os.path.join(self.__sessionPath, pdbid + '.xml.diag')
        #    if os.access(fullname, os.F_OK):
        #        os.remove(fullname)
        #    #
        #
        self.__readCheckResult('xml', pdbid, pdbid + '.xml.diag', True)

    def __checkSFFile(self, rel_date, status_code, pdbid):
        filename = 'r' + pdbid + 'sf.ent'
        fullname = os.path.join(self.__sessionPath, filename)
        if not os.access(fullname, os.F_OK):
            return
        #
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('check_sf')
        f = self.__openScriptFile(scriptfile)
        f.write('if ( -e ' + pdbid + '_sf.report ) then\n')
        f.write('    rm -f ' + pdbid + '_sf.report\n')
        f.write('endif\n')
        f.write('#\n')
        f.write('${BINPATH}/CheckSFFile -input ' + filename + \
                ' -output ' + pdbid + '_sf.report' + ' -pdbid ' + pdbid)
        if rel_date and status_code == 'REL':
            f.write(' -rel_date ' + rel_date + '\n')
        else:
            f.write('\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        #
        self.__readCheckResult('sf', pdbid, pdbid + '_sf.report', True)
        self.__readSYSError('sf', pdbid, self.__rcsbRoot + '/bin/CheckSFFile', clogfile)

    def __checkMRFile(self, rel_date, status_code, pdbid):
        filename = pdbid + '.mr'
        fullname = os.path.join(self.__sessionPath, filename)
        if not os.access(fullname, os.F_OK):
            return
        #
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('check_mr')
        f = self.__openScriptFile(scriptfile)
        f.write('if ( -e ' + pdbid + '_mr.report ) then\n')
        f.write('    rm -f ' + pdbid + '_mr.report\n')
        f.write('endif\n')
        f.write('#\n')
        f.write('${BINPATH}/CheckMRFile -input ' + filename + \
                ' -output ' + pdbid + '_mr.report' + ' -pdbid ' + pdbid)
        if rel_date and status_code == 'REL':
            f.write(' -rel_date ' + rel_date + '\n')
        else:
            f.write('\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        #
        self.__readCheckResult('mr', pdbid, pdbid + '_mr.report', True)
        self.__readSYSError('mr', pdbid, self.__rcsbRoot + '/bin/CheckMRFile', clogfile)

    def __checkCSFile(self, rel_date, status_code, pdbid):
        filename = pdbid + '-cs.cif'
        fullname = os.path.join(self.__sessionPath, filename)
        if not os.access(fullname, os.F_OK):
            return
        #
        scriptfile,logfile,clogfile = self.__getAuxiliaryFileNames('check_cs')
        f = self.__openScriptFile(scriptfile)
        f.write('if ( -e ' + pdbid + '_cs.report ) then\n')
        f.write('    rm -f ' + pdbid + '_cs.report\n')
        f.write('endif\n')
        f.write('#\n')
        f.write('${BINPATH}/CheckCSFile -input ' + filename + \
                ' -output ' + pdbid + '_cs.report' + ' -pdbid ' + pdbid)
        if rel_date and status_code == 'REL':
            f.write(' -rel_date ' + rel_date + '\n')
        else:
            f.write('\n')
        f.write('#\n')
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, clogfile)
        #
        self.__readCheckResult('cs', pdbid, pdbid + '_cs.report', True)
        self.__readSYSError('cs', pdbid, self.__rcsbRoot + '/bin/CheckCSFile', clogfile)

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
        f.write('setenv LOCALBINPATH ' + self.__localBinRoot + '\n')
        f.write('setenv DICTBINPATH ' + self.__dictBinRoot + '\n')
        f.write('#\n')
        return f

    def __readCheckResult(self, type, pdbid, reportfile, flag):
        msg = ''
        filename = os.path.join(self.__sessionPath, reportfile)
        if not os.access(filename, os.F_OK):
            if flag:
                msg = 'Checking releasing ' + type + ' failed.' 
            #
        else:
            msg = GetLogMessage(os.path.join(self.__sessionPath, reportfile))
            if len(msg) > 10000:
                list = msg.split('\n')
                msg = ''
                count = 0
                for line in list:
                    msg += line + '\n'
                    count += 1
                    if count > 500:
                        break
                    #
                #
            #
        #
        if not msg:
            return
        #
        msg1 = msg.strip() 
        list = msg1.split('\n')
        found = False
        for line in list:
            if line == pdbid + '-noatom.xml validates':
                continue
            elif line == '':
                continue
            elif line.startswith('stdin:'):
                continue
            else:
                found = True
        #if msg1 == pdbid + '-noatom.xml validates':
        if not found:
            return
        #
        self.__addCheckResult(type, pdbid, msg)

    def __addCheckResult(self, type, pdbid, msg):
        if self.__checkResult.has_key(pdbid):
            if self.__checkResult[pdbid].has_key(type):
                self.__checkResult[pdbid][type] += '\n' + msg
            else: 
                self.__checkResult[pdbid][type] = msg
            #
        else:
            dir = {}
            dir[type] = msg
            self.__checkResult[pdbid] = dir
        #

    def __readSYSError(self, type, pdbid, program, logfile):
        flag = False
        error = GetUniqueLogMessage(program, os.path.join(self.__sessionPath, logfile))
        if error.find('Segmentation fault') != -1:
            flag = True
        #
        if not error:
            return flag
        #
        self.__addCheckResult(type, pdbid, error)
        #
        if self.__sysError and (error in self.__sysError):
            return flag
        #
        self.__sysError.append(error)
        return flag
