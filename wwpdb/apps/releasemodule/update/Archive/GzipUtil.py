##
# File:  GzipUtil.py
# Date:  27-Aug-2013
# Updates:
##
"""
Gzip all release public files.

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

import gzip, os, shutil, string, sys, traceback

from wwpdb.utils.config.ConfigInfo                    import ConfigInfo
from wwpdb.apps.releasemodule.utils.GetLogMessage     import GetLogMessage
from wwpdb.apps.releasemodule.utils.DBUtil            import DBUtil
from wwpdb.apps.releasemodule.utils.TimeUtil          import TimeUtil
from wwpdb.apps.releasemodule.utils.Utility           import *

class GzipUtil(object):
    """ Class responsible for gzipping release public files
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
        self.__prevStatus = {}
        #
        self.__cI = ConfigInfo(self.__siteId)
        self.__topReleaseDir = os.path.join(self.__cI.get('SITE_ARCHIVE_STORAGE_PATH'), 'for_release')
        #
        self.__getPrevStatus()

    def run(self):
        if len(self.__updateList) == 0:
            return
        #
        if self.__processLabel:
            scriptfile = 'gzip_' + self.__processLabel + '.csh'
            logfile    = 'gzip_' + self.__processLabel + '.log'
        else:
            scriptfile = getFileName(self.__sessionPath, 'gzip', 'csh')
            logfile    = getFileName(self.__sessionPath, 'gzip', 'log')
        #
        script = os.path.join(self.__sessionPath, scriptfile)
        f = open(script, 'w')
        f.write('#!/bin/tcsh -f\n')
        f.write('#\n')
        #
        for dir in self.__updateList:
            pdbid = dir['pdb_id'].lower()
            self.__removeDirectory(f, pdbid)
            self.__gzipCoorFiles(f, pdbid, dir)
            self.__gzipExpFiles(f, pdbid, dir)
        #
        f.close()
        #
        RunScript(self.__sessionPath, scriptfile, logfile)

    def __getPrevStatus(self):
        entryList = []
        for dir in self.__updateList:
            entryList.append(dir['entry'])
        #
        db = DBUtil(siteId=self.__siteId,verbose=self.__verbose,log=self.__lfh)
        list = db.getEntryInfo(entryList)
        if not list:
            return
        #
        t = TimeUtil()
        releaseDate = t.NextWednesday()
        #
        map = {}
        map['status_code'] = 'date_of_RCSB_release'
        map['status_code_sf'] = 'date_of_sf_release'
        map['status_code_mr'] = 'date_of_mr_release'
        map['status_code_cs'] = 'date_of_cs_release'
        #
        for dir in list:
            if 'pdb_id' not in dir:
                continue
            #
            # Change 'REL' status to 'NEWREL' for this week's release
            #
            for k,v in map.items():
                if not dir.has_key(k):
                    continue
                #
                if dir[k] != 'REL':
                    continue
                #
                if v not in dir:
                    dir[k] = 'NEWREL'
                elif not dir[v]:
                    dir[k] = 'NEWREL'
                elif str(dir[v]) == releaseDate:
                    dir[k] = 'NEWREL'
                #
            #
            pdbid = dir['pdb_id'].lower()
            self.__prevStatus[pdbid] = dir
        #

    def __removeDirectory(self, f, pdbid):
        for subdirectory in ( 'added', 'modified', 'obsolete', 'reloaded' ):
            f.write('if ( ( -e ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + ' ) ) then\n')
            f.write('    /bin/rm -rf ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n') 
            f.write('endif\n')
            f.write('#\n')
        #

    def __createDirectory(self, f, pdbid, dir, dir_key, checklist):
        found = False
        for filename in checklist:
            fullname = os.path.join(self.__sessionPath, filename)
            if os.access(fullname, os.F_OK):
                found = True
                break
            #
        #
        if not found:
            return ''
        #
        subdirectory = ''
        if dir_key in dir:
            subdirectory = dir[dir_key]
            if 'big_entry' in dir and subdirectory == 'reloaded':
                subdirectory = 'modified'
            #
        #
        if not subdirectory:
            return ''
        #
        f.write('if ( ! ( -e ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + ' ) ) then\n')
        f.write('    /bin/mkdir ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n') 
        f.write('endif\n')
        f.write('#\n')
        #
        return subdirectory

    def __gzipCoorFiles(self, f, pdbid, dir):
        checklist = []
        checklist.append('pdb' + pdbid + '.ent')
        checklist.append(pdbid + '.cif')
        checklist.append(pdbid + '.xml')
        checklist.append(pdbid + '-noatom.xml')
        checklist.append(pdbid + '-extatom.xml')
        checklist.append(pdbid + '.pdb1')
        #
        subdirectory = self.__createDirectory(f, pdbid, dir, 'directory', checklist)
        if not subdirectory:
            return
        #
        # Summary file
        f.write('if ( -e ' + pdbid + '.summary ) then\n')
        f.write('    /bin/cp -f ' + pdbid + '.summary ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
        f.write('endif\n')
        f.write('#\n')
        #
        # Validation pdf
        f.write('if ( -e ' + pdbid + '-valrpt.pdf ) then\n')
        f.write('    /bin/cp -f ' + pdbid + '-valrpt.pdf ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
        f.write('endif\n')
        f.write('#\n')
        #
        # Validation xml
        f.write('if ( -e ' + pdbid + '-valdata.xml ) then\n')
        f.write('    /bin/cp -f ' + pdbid + '-valdata.xml ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
        f.write('endif\n')
        f.write('#\n')
        #
        # PDB file
        f.write('if ( -e pdb' + pdbid + '.ent ) then\n') 
        f.write('    /bin/cp -f pdb' + pdbid + '.ent ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n') 
        f.write('    /bin/gzip -f pdb' + pdbid + '.ent\n')
        f.write('endif\n')
        f.write('#\n')
        # PDB bundle file
        f.write('if ( -e ' + pdbid + '-pdb-bundle.tar ) then\n') 
        f.write('    /bin/gzip -f ' + pdbid + '-pdb-bundle.tar\n')
        f.write('    /bin/cp -f ' + pdbid + '-pdb-bundle.tar.gz ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n') 
        f.write('endif\n')
        f.write('#\n')
        # cif file
        f.write('if ( -e ' + pdbid + '.cif ) then\n')
        f.write('    /bin/gzip -f ' + pdbid + '.cif\n')
        f.write('    /bin/cp -f ' + pdbid + '.cif.gz ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
        f.write('endif\n')
        f.write('#\n')
        # xml file
        f.write('if ( -e ' + pdbid + '.xml ) then\n')
        f.write('    /bin/gzip -f ' + pdbid + '.xml\n')
        f.write('    /bin/cp -f ' + pdbid + '.xml.gz ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
        f.write('endif\n')
        f.write('#\n')
        # noatom xml file
        f.write('if ( -e ' + pdbid + '-noatom.xml ) then\n')
        f.write('    /bin/gzip -f ' + pdbid + '-noatom.xml\n')
        f.write('    /bin/cp -f ' + pdbid + '-noatom.xml.gz ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
        f.write('endif\n')
        f.write('#\n')
        # extatom xml file
        f.write('if ( -e ' + pdbid + '-extatom.xml ) then\n')
        f.write('    /bin/gzip -f ' + pdbid + '-extatom.xml\n')
        f.write('    /bin/cp -f ' + pdbid + '-extatom.xml.gz ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
        f.write('endif\n')
        f.write('#\n')
        # biogical unit files
        filename = os.path.join(self.__sessionPath, pdbid + '.pdb1')
        if os.access(filename, os.F_OK):
            f.write('foreach file (' + pdbid + '.pdb? ' + pdbid + '.pdb??)\n')
            f.write('    /bin/gzip -f ${file}\n')
            f.write('    /bin/cp -f ${file}.gz ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
            f.write('end\n')
            f.write('#\n')
        #
        filename = os.path.join(self.__sessionPath, pdbid + '-assembly1.cif')
        if os.access(filename, os.F_OK):
            f.write('foreach file (' + pdbid + '-assembly*.cif)\n')
            f.write('    /bin/gzip -f ${file}\n')
            f.write('    /bin/cp -f ${file}.gz ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
            f.write('end\n')
            f.write('#\n')
        #

    def __gzipExpFiles(self, f, pdbid, dir):
        # sf file
        sflist = []
        sflist.append('r' + pdbid + 'sf.ent')
        subdirectory = self.__createDirectory(f, pdbid, dir, 'directory_sf', sflist)
        if subdirectory:
            #
            # Summary file
            f.write('if ( -e ' + pdbid + '.summary ) then\n')
            f.write('    /bin/cp -f ' + pdbid + '.summary ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
            f.write('endif\n')
            f.write('#\n')
            #
            # Validation pdf
            f.write('if ( -e ' + pdbid + '-valrpt.pdf ) then\n')
            f.write('    /bin/cp -f ' + pdbid + '-valrpt.pdf ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
            f.write('endif\n')
            f.write('#\n')
            #
            # Validation xml
            f.write('if ( -e ' + pdbid + '-valdata.xml ) then\n')
            f.write('    /bin/cp -f ' + pdbid + '-valdata.xml ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
            f.write('endif\n')
            f.write('#\n')
            #
            f.write('if ( -e r' + pdbid + 'sf.ent ) then\n')
            f.write('    /bin/cp -f r' + pdbid + 'sf.ent ' + self.__topReleaseDir + '/' + subdirectory  + '/' + pdbid + '/' + pdbid + '-sf.cif\n')
            f.write('    /bin/gzip -f r' + pdbid + 'sf.ent\n')
            f.write('endif\n')
            f.write('#\n')
        #
        # mr file
        mrlist = []
        mrlist.append(pdbid + '.mr')
        subdirectory = self.__createDirectory(f, pdbid, dir, 'directory_mr', mrlist)
        if subdirectory:
            #
            # Summary file
            f.write('if ( -e ' + pdbid + '.summary ) then\n')
            f.write('    /bin/cp -f ' + pdbid + '.summary ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
            f.write('endif\n')
            f.write('#\n')
            #
            f.write('if ( -e ' + pdbid + '.mr ) then\n')
            f.write('    /bin/cp -f ' + pdbid + '.mr ' + self.__topReleaseDir + '/' + subdirectory  + '/' + pdbid + '\n')
            f.write('    /bin/gzip -f ' + pdbid + '.mr\n')
            f.write('endif\n')
            f.write('#\n')
        #
        # cs file
        cslist = []
        cslist.append(pdbid + '-cs.cif')
        subdirectory = self.__createDirectory(f, pdbid, dir, 'directory_cs', cslist)
        if subdirectory:
            #
            # Summary file
            f.write('if ( -e ' + pdbid + '.summary ) then\n')
            f.write('    /bin/cp -f ' + pdbid + '.summary ' + self.__topReleaseDir + '/' + subdirectory + '/' + pdbid + '\n')
            f.write('endif\n')
            f.write('#\n')
            #
            #f.write('if ( -e ' + pdbid + '-cs.cif ) then\n')
            #f.write('    /bin/cp -f ' + pdbid + '-cs.cif ' + self.__topReleaseDir + '/' + subdirectory  + '/' + pdbid + '\n')
            #f.write('    /bin/gzip -f ' + pdbid + '-cs.cif\n')
            #f.write('endif\n')
            #f.write('#\n')
            # cs str file
            f.write('if ( -e ' + pdbid + '_cs.str ) then\n')
            f.write('    /bin/cp -f ' + pdbid + '_cs.str ' + self.__topReleaseDir + '/' + subdirectory  + '/' + pdbid + '\n')
            f.write('    /bin/gzip -f ' + pdbid + '_cs.str\n')
            f.write('endif\n')
            f.write('#\n')
        #
