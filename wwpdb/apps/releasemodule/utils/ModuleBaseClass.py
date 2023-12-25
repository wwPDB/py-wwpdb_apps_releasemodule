##
# File:  ModuleBaseClass.py
# Date:  18-Nov-2016
# Updates:
##
"""
Base class for handle all release module activities

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2016 wwPDB

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

from wwpdb.utils.config.ConfigInfo import ConfigInfo
from wwpdb.utils.config.ConfigInfoApp import ConfigInfoAppCommon, ConfigInfoAppCc
from wwpdb.apps.releasemodule.utils.TimeUtil import TimeUtil


class ModuleBaseClass(object):
    """ Base Class responsible for all release module activities
    """
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        self._verbose = verbose
        self._lfh = log
        self._reqObj = reqObj
        self._sObj = None
        self._sessionId = None
        self._sessionPath = None
        self._siteId = str(self._reqObj.getValue("WWPDB_SITE_ID"))
        self._cI = ConfigInfo(self._siteId)
        self._cICommon = ConfigInfoAppCommon(self._siteId)
        self._cIAppCc = ConfigInfoAppCc(self._siteId)
        self._topReleaseDir = os.path.join(self._cICommon.get_for_release_path())
        self._topReleaseBetaDir = os.path.join(self._cICommon.get_for_release_beta_path())
        self._topReleaseVersionDir = os.path.join(self._cICommon.get_for_release_version_path())
        #
        self._fileTypeList = [ [ '_model_P1.cif',     '',    'Coordinate',        'model',               'pdbx',     'coor' ],
                               [ '_sf_P1.cif',        '_sf', 'Structural Factor', 'structure-factors',   'pdbx',     'sf'   ],
                               [ '_em-volume_P1.map', '_em', 'EM Header/Map',     'em-volume',           'map',      'em'   ],
                               [ '_mr_P1.mr',         '_mr', 'NMR restraints',    'nmr-restraints',      'pdb-mr',   'mr'   ],
                               [ '_cs_P1.cif',        '_cs', 'Chemical Shifts',   'nmr-chemical-shifts', 'pdbx',     'cs'   ],
                               [ '_nmr-data-str_P1.cif', '_nmr_data', 'NMR DATA', 'nmr-data-str',        'pdbx', 'nmr_data' ] ]
        #
        t = TimeUtil()
        self._rel_date = t.NextWednesday()
        #
        self.__getSession()
        #
        self.__selectOptionMap = {}
        self.__getselectOptionMap()

    def _loadPickle(self, pickleFile):
        if not os.access(pickleFile, os.F_OK):
            return None
        #
        fb = open(pickleFile, 'rb')
        pickleData = pickle.load(fb)
        fb.close()
        return pickleData

    def _dumpPickle(self, pickleFile, pickleData):
        fb = open(pickleFile, 'wb')
        pickle.dump(pickleData, fb)
        fb.close()

    def __getIndexPath(self):
        index_path = os.path.join(self._topReleaseDir, 'index')
        if not os.path.exists(index_path):
            os.makedirs(index_path)
        return index_path

    def _getEntryPickleFileName(self, entryId):
        return os.path.join(self.__getIndexPath(), entryId.lower() + '.index')

    def _loadEntryPickle(self, entryId):
        if not entryId:
            return None
        #
        pickleFile = self._getEntryPickleFileName(entryId)
        return self._loadPickle(pickleFile)

    def _dumpEntryPickle(self, entryId, pickleData):
        pickleFile = self._getEntryPickleFileName(entryId)
        self._dumpPickle(pickleFile, pickleData)

    def _getLocalEntryPickleFileName(self, entryId):
        return os.path.join(self._sessionPath, entryId.lower() + '.pickle')

    def _loadLocalEntryPickle(self, entryId):
        if not entryId:
            return None
        #
        pickleFile = self._getLocalEntryPickleFileName(entryId)
        return self._loadPickle(pickleFile)

    def _dumpLocalEntryPickle(self, entryId, pickleData):
        pickleFile = self._getLocalEntryPickleFileName(entryId)
        self._dumpPickle(pickleFile, pickleData)

    def _getLoginAnnotator(self):
        return str(self._reqObj.getValue('annotator'))

    def _getSelectedAnnotator(self):
        selected_annotator = str(self._reqObj.getValue('owner'))
        if not selected_annotator:
            selected_annotator = str(self._reqObj.getValue('annotator'))
        #
        return selected_annotator

    def __getAnnotatorPickleFileName(self, ann):
        return os.path.join(self.__getIndexPath(), ann + '.index')

    def _loadAnnotatorPickle(self, ann):
        pickleFile = self.__getAnnotatorPickleFileName(ann)
        pickleData = self._loadPickle(pickleFile)
        if not pickleData:
            return {}
        #
        return pickleData

    def _dumpAnnotatorPickle(self, pickleData):
        pickleFile = self.__getAnnotatorPickleFileName(self._getLoginAnnotator())
        self._dumpPickle(pickleFile, pickleData)

    def _processTemplate(self, fn, parameterDict=None):
        """ Read the input HTML template data file and perform the key/value substitutions in the
            input parameter dictionary.

            :Params:
                ``parameterDict``: dictionary where
                key = name of subsitution placeholder in the template and
                value = data to be used to substitute information for the placeholder

            :Returns:
                string representing entirety of content with subsitution placeholders now replaced with data
        """
        if parameterDict is None:
            parameterDict = {}

        tPath = self._reqObj.getValue("TemplatePath")
        fPath = os.path.join(tPath, fn)
        ifh = open(fPath, 'r')
        sIn = ifh.read()
        ifh.close()
        return (  sIn % parameterDict )

    def _getReleaseOptionFromPickle(self, pickleData):
        selectedOptionText = ''
        selectedOptionMap = {}
        for typeList in self._fileTypeList:
            if (not ('status_code' + typeList[1]) in pickleData) or (not pickleData['status_code' + typeList[1]]):
                continue
            #
            option_value = pickleData['status_code' + typeList[1]]
            if (('directory' + typeList[1]) in pickleData) and pickleData['directory' + typeList[1]]:
                option_value += '_' + pickleData['directory' + typeList[1]]
            #
            selectedOptionMap['status' + typeList[1] + '_'] = option_value
            if (option_value + typeList[1]) in self.__selectOptionMap:
                if selectedOptionText:
                    selectedOptionText += ', '
                #
                selectedOptionText += self.__selectOptionMap[option_value + typeList[1]]
            #
        #
        return selectedOptionText, selectedOptionMap

    def __getSession(self):
        """ Join existing session or create new session as required.
        """
        #
        self._sObj = self._reqObj.newSessionObj()
        self._sessionId = self._sObj.getId()
        self._sessionPath = self._sObj.getPath()
        if (self._verbose):
            self._lfh.write("------------------------------------------------------\n")
            self._lfh.write("+ModuleBaseClass._getSession() - creating/joining session %s\n" % self._sessionId)
            self._lfh.write("+ModuleBaseClass._getSession() - session path %s\n" % self._sessionPath)
        #

    def __getselectOptionMap(self):
        optionList = [ [ '',    'REL_added',       'Release Coord.'              ],
                       [ '',    'EMHEADERUpdate',  'EM XML header'               ],
                       [ '',    'CITATIONUpdate',  'Update citation w/o release' ],
                       [ '',    'REREL_modified',  'Re-release Coord.'           ],
                       [ '',    'RELOAD_reloaded', 'Re-release CIF w/o PDB'      ],
                       [ '',    'OBS_obsolete',    'Obsolete Coord.'             ],
                       [ '_sf', 'REL_added',       'Release SF'                  ],
                       [ '_sf', 'REREL_modified',  'Re-release SF'               ],
                       [ '_sf', 'OBS_obsolete',    'Obsolete SF'                 ],
                       [ '_em', 'REL_added',       'Release EM'                  ],
                       [ '_em', 'REREL_modified',  'Re-release EM'               ],
                       [ '_em', 'OBS_obsolete',    'Obsolete EM'                 ],
                       [ '_mr', 'REL_added',       'Release MR'                  ],
                       [ '_mr', 'REREL_modified',  'Re-release MR'               ],
                       [ '_mr', 'OBS_obsolete',    'Obsolete MR'                 ],
                       [ '_cs', 'REL_added',       'Release CS'                  ],
                       [ '_cs', 'REREL_modified',  'Re-release CS'               ],
                       [ '_cs', 'OBS_obsolete',    'Obsolete CS'                 ],
                       [ '_nmr_data', 'REL_added',      'Release NMR DATA'       ],
                       [ '_nmr_data', 'REREL_modified', 'Re-release NMR DATA'    ],
                       [ '_nmr_data', 'OBS_obsolete',   'Obsolete NMR DATA'      ] ]
        #
        for olist in optionList:
            self.__selectOptionMap[olist[1] + olist[0]] = olist[2]
        #
