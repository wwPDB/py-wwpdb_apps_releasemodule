##
# File:  UpdateBase.py
# Date:  06-Oct-2016
# Updates:
##
"""
Base class for handle all release-related activities

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

from wwpdb.apps.releasemodule.utils.MessageBaseClass import MessageBaseClass
from wwpdb.apps.releasemodule.utils.Utility import getFileName


class UpdateBase(MessageBaseClass):
    """ Base Class responsible for all release-related activities
    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        super(UpdateBase, self).__init__(reqObj=reqObj, verbose=verbose, log=log)
        #
        self._fileTypeMap = {}
        for typeList in self._fileTypeList:
            self._fileTypeMap[typeList[3]] = [typeList[2], typeList[5]]
        #

    def _getAuxiliaryFileNames(self, prefix):
        return getFileName(self._sessionPath, prefix, 'csh'), getFileName(self._sessionPath, prefix, 'log'), \
            getFileName(self._sessionPath, prefix + '_command', 'log')

    def _openScriptFile(self, scriptfile):
        """
        """
        script = os.path.join(self._sessionPath, scriptfile)
        f = open(script, 'w')
        f.write('#!/bin/tcsh -f\n')
        f.write('#\n')
        f.write('setenv RCSBROOT ' + self._cICommon.get_site_annot_tools_path() + '\n')
        f.write('setenv COMP_PATH ' + self._cIAppCc.get_site_cc_cvs_path() + '\n')
        f.write('setenv BINPATH ${RCSBROOT}/bin\n')
        f.write('setenv LOCALBINPATH ' + os.path.join(self._cICommon.get_site_local_apps_path(), 'bin') + '\n')
        f.write('setenv DICTBINPATH ' + os.path.join(self._cICommon.get_site_packages_path(), 'dict', 'bin') + '\n')
        f.write('#\n')
        return f

    def _bashSetting(self):
        setting = " RCSBROOT=" + self._cICommon.get_site_annot_tools_path() + "; export RCSBROOT; " \
            + " COMP_PATH=" + self._cIAppCc.get_site_cc_cvs_path() + "; export COMP_PATH; " \
            + " BINPATH=${RCSBROOT}/bin; export BINPATH; " \
            + " LOCALBINPATH=" + os.path.join(self._cICommon.get_site_local_apps_path(), 'bin') + "; export LOCALBINPATH; " \
            + " DICTBINPATH=" + os.path.join(self._cICommon.get_site_packages_path(), 'dict', 'bin') + "; export DICTBINPATH; "
        return setting

    def _getCmd(self, command, inputFile, outputFile, logFile, clogFile, extraOptions):
        cmd = "cd " + self._sessionPath + " ; " + self._bashSetting() + " " + command
        if inputFile:
            cmd += " -input " + inputFile
        #
        if outputFile:
            if outputFile != inputFile:
                self._removeFile(os.path.join(self._sessionPath, outputFile))
            #
            cmd += " -output " + outputFile
        #
        if extraOptions:
            cmd += " " + extraOptions
        #
        if logFile:
            self._removeFile(os.path.join(self._sessionPath, logFile))
            cmd += " -log " + logFile
        #
        if clogFile:
            self._removeFile(os.path.join(self._sessionPath, clogFile))
            cmd += " > " + clogFile + " 2>&1"
        #
        cmd += " ; "
        return cmd

    def _runCmd(self, cmd):
        # self._lfh.write('running cmd=%s\n' % cmd)
        os.system(cmd)

    def _removeFile(self, filePath):
        if os.access(filePath, os.F_OK):
            os.remove(filePath)
        #
