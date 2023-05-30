##
# File:  CheckResult.py
# Date:  24-Jul-2013
# Updates:
##
"""
Citation finder.

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

try:
    import cPickle as pickle
except ImportError:
    import pickle

from wwpdb.apps.releasemodule.citation.StringUtil import calStringSimilarity


class CheckResult(object):
    """
    """

    def __init__(self, path='.', input='result.db', log=sys.stderr, verbose=False):  # pylint: disable=unused-argument,redefined-builtin
        """ Initial CheckResult class
        """
        self.__sessionPath = path
        self.__picklefile = input
        # self.__lfh = log
        # self.__verbose = verbose
        self.__annotEntryMap = {}
        #
        self._deserialize()
        #

    def _deserialize(self):
        filename = os.path.join(self.__sessionPath, self.__picklefile)
        fb = open(filename, 'rb')
        self.__annotEntryMap = pickle.load(fb)
        fb.close()

    def Check(self):
        aemap = self.__annotEntryMap
        self.__annotEntryMap = {}
        for k, list in aemap.items():  # pylint: disable=redefined-builtin
            elist = []
            for dir in list:  # pylint: disable=redefined-builtin
                print(dir['structure_id'] + ': ' + dir['c_title'])
                plist = []
                for pdir in dir['pubmed']:
                    sim = calStringSimilarity(dir['c_title'], pdir['title'])
                    if sim < 0.5:
                        continue
                    #
                    print(pdir['pdbx_database_id_PubMed'] + ': '
                          + pdir['similarity_score'] + ' <--> '
                          + '%.3f' % sim + ' ' + pdir['title'])
                    plist.append(pdir)
                #
                if not plist:
                    continue
                #
                dir['pubmed'] = plist
                elist.append(dir)
            #
            if elist:
                self.__annotEntryMap[k] = elist
        #
        fb = open('new_citation_finder.db', 'wb')
        pickle.dump(self.__annotEntryMap, fb)
        fb.close()


if __name__ == '__main__':
    cf = CheckResult(input=sys.argv[1], log=sys.stderr, verbose=False)
    cf.Check()
