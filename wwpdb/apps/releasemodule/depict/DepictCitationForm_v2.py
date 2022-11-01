##
# File:  DepictCitationForm.py
# Date:  24-Jun-2014
# Updates:
##
"""
Create HTML depiction for citation input form

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

from wwpdb.apps.releasemodule.citation.RisCitationParser import RisCitationParser
from wwpdb.apps.releasemodule.depict.DepictBase import DepictBase
from wwpdb.apps.releasemodule.utils.JournalAbbrev import JournalAbbrev
from wwpdb.utils.session.WebUploadUtils import WebUploadUtils


class DepictCitationForm(DepictBase):
    """ Class responsible for generating citation input form depiction.
    """
    def __init__(self, reqObj=None, resultList=None, verbose=False, log=sys.stderr):
        super(DepictCitationForm, self).__init__(reqObj=reqObj, resultList=resultList, verbose=verbose, log=log)
        #
        self.__ja = JournalAbbrev(reqObj=self._reqObj, verbose=self._verbose, log=self._reqObj)
        self.__risCitation = {}
        #
        self.__getUploadRISCitation()

    def DoRender(self):
        myD = self._initialOverAllDict()
        myD['pubmed_file'] = ''
        if self.__risCitation:
            myD['citation_info'] = self.__depictCitationInfo(self.__risCitation)
        elif self._resultList:
            myD['citation_info'] = self.__depictCitationInfo(self._resultList[0]['citation'])
        else:
            myD['citation_info'] = ''
        myD['entry_info'] = self.__getRequestEntryInfo()
        myD['finder_summary'] = ''
        myD['idlist'] = ' '.join(self._IdList)
        myD['abbrev_info'] = self.__ja.GetJoinQuoterList(',\n')
        #
        return self._processTemplate('citation_request/main_citation_input_form_tmplt.html', myD)

    def __getUploadRISCitation(self):
        """
        """
        wuu = WebUploadUtils(reqObj=self._reqObj, verbose=self._verbose, log=self._lfh)
        if not wuu.isFileUpload():
            return
        #
        uploadFileName = wuu.copyToSession(uncompress=False)
        if not uploadFileName:
            return
        #
        uploadFilePath = os.path.join(self._sessionPath, uploadFileName)
        if not os.access(uploadFilePath, os.F_OK):
            return
        #
        risParser = RisCitationParser(uploadFilePath)
        self.__risCitation = risParser.getCitationData()
        if self.__risCitation:
            self.__risCitation["citation_id"] = str(self._reqObj.getValue("citation_id"))
            self.__risCitation["citation_id_text"] = str(self._reqObj.getValue("citation_id"))
            abbrev = ""
            if ("journal_abbrev" in self.__risCitation) and self.__risCitation["journal_abbrev"]:
                abbrev = self.__ja.FindJournalAbbrev(self.__risCitation["journal_abbrev"])
            if (not abbrev) and ("journal_issn" in self.__risCitation) and self.__risCitation["journal_issn"]:
                abbrev = self.__ja.FindJournalAbbrevWithISSN(self.__risCitation["journal_issn"])
            #
            if abbrev:
                self.__risCitation["journal_abbrev"] = abbrev
            else:
                self.__risCitation["citation_id_text"] = str(self._reqObj.getValue("citation_id")) + ' &nbsp; &nbsp; &nbsp; &nbsp; <span style="color:red">' + \
                    'Please select the proper "Journal Abbrev." for journal "' + self.__risCitation["journal_abbrev"] + '" using auto suggestion.</span>'
            #
        #

    def __getRequestEntryInfo(self):
        items = self._getItemList('citation_request/entry_item_list')
        #
        text = ''
        count = 0
        flag = True
        for dataDict in self._resultList:
            myD, selectedData = self._initialEntryDict(dataDict, items, True, False, 'None')
            selectedData['JRNL'] = 'checked'
            selectedData['Citation'] = 'checked'
            myD['comment_start'] = ''
            myD['comment_end'] = ''
            if self._skipReleaseOptionFlag:
                myD['comment_start'] = '<!--'
                myD['comment_end'] = '-->'
            #
            myD['check_option'] = 'checked'
            if flag:
                myD['bgclass'] = 'even'
                flag = False
            else:
                myD['bgclass'] = 'odd'
                flag = True
            #
            if not self._skipReleaseOptionFlag:
                myD['release_option'] = self._getReleaseOption(dataDict, selectedData, True)
            #
            if (not self._newReleaseFlag) and ('pdb_id' in dataDict) and dataDict['pdb_id']:
                myD['revision'] = self._getRevisionInfo(dataDict['structure_id'], count, selectedData, '2', '', '', 'border-style:none;', 'none')
            else:
                myD['revision'] = ''
            #
            myD['citation_info'] = ''
            #
            text += self._processTemplate('citation_request/entry_tmplt.html', myD)
            #
            self._IdList.append('entry_' + dataDict['structure_id'])
            count += 1
        #
        return text

    def __depictCitationInfo(self, dataDict):
        authorlist = []
        if 'author' in dataDict:
            authorlist = dataDict['author']
        #
        max_author_num = len(authorlist) + 5
        if max_author_num < 10:
            max_author_num = 10
        #
        items = self._getItemList('citation_request/citation_form_item_list')
        #
        myD = {}
        for item in items:
            val = ''
            if (item in dataDict) and dataDict[item]:
                val = str(dataDict[item])
            #
            if (item != 'citation_id') and (item != 'citation_id_text'):
                val = self.__getTextArea(item, val)
            #
            if (val == '') and (item == 'citation_id_text') and ('citation_id' in dataDict):
                val = dataDict['citation_id']
            #
            myD[item] = val
        #
        myD['max_author_num'] = str(max_author_num)
        myD['previous_doi_value'] = ''
        if ('pdbx_database_id_DOI' in dataDict) and dataDict['pdbx_database_id_DOI']:
            myD['previous_doi_value'] = dataDict['pdbx_database_id_DOI']
        #
        text = self._processTemplate('citation_request/citation_form_tmplt.html', myD)
        #
        text += self.__depictCitationAuthor(authorlist, max_author_num)
        return text

    def __depictCitationAuthor(self, authorlist, max_num):
        max_num = len(authorlist) + 5
        if max_num < 10:
            max_num = 10
        #
        diff_num = max_num - len(authorlist)
        count = 0
        text = ''
        if authorlist:
            for myD in authorlist:
                count += 1
                myD['count'] = str(count)
                text += self._processTemplate('citation_request/author_form_tmplt.html', myD)
            #
        #
        for _i in range(0, diff_num):
            count += 1
            myD = {}
            myD['count'] = str(count)
            myD['name'] = ''
            myD['orcid'] = ''
            text += self._processTemplate('citation_request/author_form_tmplt.html', myD)
        #
        return text

    def __getTextArea(self, name, value):
        irow = int(len(value) / 120) + 1
        text = '<textarea name="' + name + '" id="' + name + '" cols="120" rows="' + str(irow) + '" wrap>' + value + '</textarea>'
        return text
