##
# File:  ArchiveFileUtil.py
# Date:  24-Mar-2014
# Updates:
##
"""
Find archival files

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

import os, shutil, sys, string, traceback

from wwpdb.utils.config.ConfigInfo                  import ConfigInfo
from wwpdb.apps.entity_transform.utils.mmCIFUtil  import mmCIFUtil
from wwpdb.apps.releasemodule.utils.TimeUtil      import TimeUtil

class ArchiveFileUtil(object):
    """ Class responsible for finding archival files.
    """
    def __init__(self, reqObj=None, entryId=None, verbose=False, log=sys.stderr):
        """
        """
        self.__reqObj      = reqObj
        self.__entryId     = entryId
        self.__verbose     = verbose
        self.__lfh         = log
        #
        self.__sObj        = None
        self.__sessionId   = None
        self.__sessionPath = None
        self.__getSession()
        #
        self.__siteId      = str(self.__reqObj.getValue("WWPDB_SITE_ID"))
        self.__cI          = ConfigInfo(self.__siteId)
        self.__archPath    = os.path.join(self.__cI.get('SITE_ARCHIVE_STORAGE_PATH'),'archive', self.__entryId)
        #
        self.__fileList = []
        #
        self.__releaseDate = ''
        self.__releaseDatePDBFormat = ''
        self.__getReleaseDate()

    def __getSession(self):
        """ Join existing session or create new session as required.
        """
        #
        self.__sObj=self.__reqObj.newSessionObj()
        self.__sessionId=self.__sObj.getId()
        self.__sessionPath=self.__sObj.getPath()
        if (self.__verbose):
            self.__lfh.write("------------------------------------------------------\n")
            self.__lfh.write("+ArchiveFileUtil.__getSession() - creating/joining session %s\n" % self.__sessionId)
            self.__lfh.write("+ArchiveFileUtil.__getSession() - session path %s\n" % self.__sessionPath)

    def GetFileList(self):
        """
        """
        if not os.access(self.__archPath, os.F_OK):
            return
        #
        self.__fileList = os.listdir(self.__archPath)

    def __getReleaseDate(self):
        """
        """
        t = TimeUtil()
        self.__releaseDate = t.NextWednesday()
        self.__releaseDatePDBFormat = t.PDBFormatReleaseDate()
 
    def GetBeforeReleaseFile(self, baseExt='_model_P1.cif'):
        """
        """
        if not self.__fileList:
            return
        #
        baseName = self.__entryId + baseExt
        vList=[]
        for fN in self.__fileList:
            if fN.startswith(baseName):
                fSp=fN.split('.V')
                vList.append(int(fSp[1]))
            #
        #
        if len(vList) == 0:
            return
        #
        vList.sort()
        filenameList = []
        for v in vList:
            filenameList.append(os.path.join(self.__archPath, baseName + '.V' + str(v)))
        #
        filename = self.__findBeforeReleaseFile(baseExt, filenameList)
        if filename:
            shutil.copyfile(filename, os.path.join(self.__sessionPath, baseName))
        #

    def GetBeforeReleaseFileWithList(self, filenameList=[], baseExt='_model_P1.cif'):
        """
        """
        if not filenameList:
            return
        #
        filename = self.__findBeforeReleaseFile(baseExt, filenameList)
        if not filename:
            filename = filenameList[0]
        #
        shutil.copyfile(filename, os.path.join(self.__sessionPath, self.__entryId + baseExt))

    def __findBeforeReleaseFile(self, baseExt, vList):
        """
        """
        for i in xrange(len(vList) - 1, 0, -1):
            if baseExt == '_model_P1.cif':
                 if (self.__findReleaseDateCIF(vList[i])) and (not self.__findReleaseDateCIF(vList[i-1])):
                     return vList[i-1]
            elif baseExt == '_sf_P1.cif':
                 if (self.__findReleaseDateSF(vList[i])) and (not self.__findReleaseDateSF(vList[i-1])):
                     return vList[i-1]
            elif baseExt == '_mr_P1.mr':
                 if (self.__findReleaseDateMR(vList[i])) and (not self.__findReleaseDateMR(vList[i-1])):
                     return vList[i-1]
            elif baseExt == '_cs_P1.cif':
                 if (self.__findReleaseDateCS(vList[i])) and (not self.__findReleaseDateCS(vList[i-1])):
                     return vList[i-1]
            else:
                return ''
            #
        #
        return ''

    def __findReleaseDateCIF(self, filename):
        """
        """
        cifObj = mmCIFUtil(filePath=filename)
        rlist = cifObj.GetValue('database_PDB_rev')
        found = False
        for dir in rlist:
            if dir.has_key('date') and dir['date'] == self.__releaseDate:
                found = True
            #
        #
        if not found:
            rlist = cifObj.GetValue('pdbx_version')
            for dir in rlist:
                if dir.has_key('revision_date') and dir['revision_date'] == self.__releaseDate:
                    found = True
                #
            #
        #
        return found

    def __findReleaseDateSF(self, filename):
        """
        """
        cifObj = mmCIFUtil(filePath=filename)
        rlist = cifObj.GetValue('audit')
        found = False
        for dir in rlist:
            if dir.has_key('creation_date') and dir['creation_date'] == self.__releaseDate: # and \
                #dir.has_key('update_record') and dir['update_record'].lower() == 'initial release':
                found = True
            #
        #
        return found

    def __findReleaseDateMR(self, filename):
        """
        """
        f = file(filename, 'r')
        data = f.read()
        f.close()
        #
        found = False
        list = data.split('\n')
        for line in list:
            if not line:
                continue
            #
            if line.startswith('*REVDAT') and line.find(self.__releaseDatePDBFormat) != -1:
                found = True
                break
            #
        #
        return found

    def __findReleaseDateCS(self, filename):
        """
        """
        cifObj = mmCIFUtil(filePath=filename)
        rlist = cifObj.GetValue('Audit')
        found = False
        for dir in rlist:
            if dir.has_key('Creation_date') and dir['Creation_date'] == self.__releaseDate: # and \
                #dir.has_key('Update_record') and dir['Update_record'].lower() == 'initial release':
                found = True
            #
        #
        return found
