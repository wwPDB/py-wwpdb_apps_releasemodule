##
# File:  MatchUtil.py
# Date:  25-Jul-2013
# Updates:
##
"""

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

import operator
import sys

from wwpdb.apps.releasemodule.citation.StringUtil import calStringSimilarity


class MatchUtil(object):
    """
    """

    def __init__(self, entry=None, termMap=None, pubmedInfo=None, log=sys.stderr, verbose=False):  # pylint: disable=unused-argument
        """ Initial MatchUtil class
        """
        self.__entry = entry
        self.__termMap = termMap
        self.__pubmedInfo = pubmedInfo
        # self.__lfh = log
        # self.__verbose = verbose
        self.__pubmedMatchList = []

    def run(self):
        if 'rcsb_annotator' not in self.__entry or \
                'c_title' not in self.__entry or \
                'pubmed_author' not in self.__entry or \
                'structure_id' not in self.__entry:
            return
        #
        idlist = self._getUniquePubmedIdList()
        if not idlist:
            return
        #
        self._findMatchList(idlist)

    def getMatchList(self):
        return self.__pubmedMatchList

    def _getUniquePubmedIdList(self):
        idlist = []
        t_map = {}
        for term in self.__entry['pubmed_author']:
            if term not in self.__termMap:
                continue
            #
            for t_id in self.__termMap[term]:
                if t_id in t_map:
                    continue
                #
                t_map[t_id] = 'y'
                idlist.append(t_id)
            #
        return idlist

    def _findMatchList(self, idlist):
        for p_id in idlist:
            if p_id not in self.__pubmedInfo:
                continue
            sim = calStringSimilarity(self.__entry['c_title'],
                                      self.__pubmedInfo[p_id]['title'])
            if sim < 0.5:
                continue
            #
            self.__pubmedMatchList.append([p_id, '%.3f' % sim])
        #
        if len(self.__pubmedMatchList) < 2:
            return
        #
        self.__pubmedMatchList.sort(key=operator.itemgetter(1))
        self.__pubmedMatchList.reverse()
