##
# File:  RisCitationParser.py
# Date:  21-Oct-2020
# Updates:
##
"""
Parse citation information from ris file.

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2020 wwPDB

This software is provided under a Creative Commons Attribution 3.0 Unported
License described at http://creativecommons.org/licenses/by/3.0/.

"""
__docformat__ = "restructuredtext en"
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import sys, os
from xml.dom import minidom
from wwpdb.apps.releasemodule.citation.FetchResultParser import UniCodeHandler

class RisCitationParser(object):
    """ Parse citation information from ris file.
    """
    def __init__(self, risfile=None):
        """
        """
        self.__risfile = risfile
        self.__convertedCitationData = {}
        #
        self.__codeHandler = UniCodeHandler()
        self.__parseRisFile()

    def getCitationData(self):
        """
        """
        return self.__convertedCitationData

    def __parseRisFile(self):
        """
        """
        if (not self.__risfile) or (not os.access(self.__risfile, os.F_OK)):
            return
        #
        tmpCitationData = {}
        #
        with open(self.__risfile, encoding="utf-8") as fin:
            for line in fin:
                if not line:
                    continue
                #
                line = line.replace("    ", " ").replace("   ", " ").replace("  ", " ")
                if (not line) or (len(line) < 6) or (line[2:5] != " - "):
                    continue
                #
                if line[0:2] not in ( "AU", "A1", "A2", "A3", "A4", "TI", "T1", "JO", "JA", "JF", "PY", "Y1", "VL", "SP", "EP", "SN", "DO" ):
                    continue
                #
                angstromFlag = False
                if line[0:2] in ( "TI", "T1" ):
                    angstromFlag = True
                #
                value = self.__processValue(line[5:].strip(), angstromFlag)
                if not value:
                    continue
                #
                if line[0:2] in ( "AU", "A1", "A2", "A3", "A4" ): # Author
                    self.__processAuthorName(value)
                elif line[0:2] in ( "TI", "T1" ): # Title
                    tmpCitationData[line[0:2]] = value
                elif line[0:2] in ( "JO", "JA", "JF" ): # Journal
                    tmpCitationData[line[0:2]] = value
                elif line[0:2] in ( "PY", "Y1" ): # Year
                    tList = value.split("/")
                    if (len(tList) > 0) and (len(tList[0]) == 4) and tList[0].isdigit():
                        tmpCitationData[line[0:2]] = tList[0]
                    #
                elif line[0:2] == "VL": # Volume number
                    self.__convertedCitationData["journal_volume"] = value
                elif line[0:2] == "SP": # Start Page
                    if value.isdigit():
                        self.__convertedCitationData["page_first"] = value
                    #
                elif line[0:2] == "EP": # End Page
                    if value.isdigit():
                        self.__convertedCitationData["page_last"] = value
                    #
                #elif line[0:2] == "SN": # ISBN/ISSN
                elif line[0:2] == "DO": # DOI
                    self.__convertedCitationData["pdbx_database_id_DOI"] = value.replace('http://doi.org/', '').replace('https://doi.org/', '')
                #
            #
        #
        # Get title, journal_abbrev, year
        cif_ris_token_map = { "title": ( "TI", "T1" ), "journal_abbrev": ( "JA", "JF", "JO" ), "year": ( "PY", "Y1" ) }
        #
        for cif_token,ris_tokens in cif_ris_token_map.items():
            for token in ris_tokens:
                if token in tmpCitationData:
                    self.__convertedCitationData[cif_token] = tmpCitationData[token]
                    break
                #
            #
        #

    def __processValue(self, ris_value, angstromFlag):
        """
        """
        if not ris_value:
            return ""
        #
        major = sys.version_info[0]
        if major > 2:
            minor = sys.version_info[1]
            if minor > 3:
                import html as parser
            else:
                import html.parser
                parser = html.parser.HTMLParser()
            #
        else:
            import HTMLParser
            parser = HTMLParser.HTMLParser()
        #
        doc = minidom.parseString("<RisStringTag>" + parser.unescape(ris_value) + "</RisStringTag>")
        return self.__processNodes(doc.getElementsByTagName("RisStringTag")[0].childNodes, angstromFlag)

    def __processNodes(self, childNodes, angstromFlag):
        text = ""
        for node in childNodes:
            if node.nodeType == node.ELEMENT_NODE:
                if text:
                    text += " "
                #
                text += self.__processNodes(node.childNodes, angstromFlag)
            else:
                if text:
                    text += " "
                #
                text += self.__processData(node, angstromFlag)
            #
        #
        return text

    def __processData(self, node, angstromFlag):
        if not node:
            return ""
        #
        return self.__codeHandler.process(node.data, angstromFlag)

    def __processAuthorName(self, ris_author):
        """
        """
        aList = ris_author.split(" ")
        if aList[0][-1] != ",":
            return
        #
        found = False
        cif_author = aList[0] + " "
        for val in aList[1:]:
            if not val:
                continue
            #
            found = True
            initList = val.split("-")
            for init in initList:
                cif_author += init[0:1].upper() + "."
            #
        #
        if not found:
            return
        #
        if "author" in self.__convertedCitationData:
            self.__convertedCitationData["author"].append( { "name" : cif_author, "orcid" : "" } )
        else:
            self.__convertedCitationData["author"] = [ { "name" : cif_author, "orcid" : "" } ]
        #

if __name__ == "__main__":
    parser = RisCitationParser(sys.argv[1])
    citDict = parser.getCitationData()
    for key,val in citDict.items():
        sys.stderr.write("%r=%r\n" % (key,val))
    #
