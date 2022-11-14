##
# File:  SearchResultParser.py
# Date:  18-Jun-2013
# Updates:
##
"""
Parse Pubmed search result xml file.

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

from xml.dom import minidom

import sys


class SearchResultParser(object):
    """Parse Pubmed search result xml file, return pubmed id list
    """

    def __init__(self, xmlfile=None):
        self.__xmlfile = xmlfile
        self.__pubmedIdList = []
        self._parseXml()

    def getIdList(self):
        return self.__pubmedIdList

    def _parseXml(self):
        try:
            __doc = minidom.parse(self.__xmlfile)
            self.__pubmedIdList = self._parseDoc(__doc)
        except:  # noqa: E722 pylint: disable=bare-except
            pass

    def _parseDoc(self, doc):
        idlist = []
        entryList = doc.getElementsByTagName('Id')
        if len(entryList) > 0:
            for entry in entryList:
                if entry.firstChild:
                    d_id = str(entry.firstChild.data)
                    idlist.append(d_id)
                #
            #
        #
        return idlist


if __name__ == "__main__":
    parser = SearchResultParser(sys.argv[1])
    clist = parser.getIdList()
    print(clist)
