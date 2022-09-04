##
# File:  DepictCitation.py
# Date:  28-Jun-2013
# Updates:
##
"""
Create HTML depiction for citation finder result page.

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

try:
    import pickle as pickle
except ImportError:
    import pickle as pickle

import os
import sys

from wwpdb.apps.releasemodule.citation.StringUtil import calStringSimilarity
from wwpdb.apps.releasemodule.depict.DepictBase import DepictBase
from wwpdb.apps.releasemodule.utils.Utility import getFileName


class DepictCitation(DepictBase):
    """ Class responsible for generating citation finder result HTML depiction.

    """
    def __init__(self, reqObj=None, resultList=None, verbose=False, log=sys.stderr):
        super(DepictCitation, self).__init__(reqObj=reqObj, resultList=resultList, verbose=verbose, log=log)
        self.__high_count = 0
        self.__middle_count = 0
        self.__lower_count = 0

    def DoRender(self, finderFlag=True):
        myD = self._initialOverAllDict()
        pubmedInfoMap = {}
        pubmed_file = getFileName(self._sessionPath, myD['owner'] , 'db')
        #
        myD['pubmed_file'] = pubmed_file
        if finderFlag:
            pubmedInfoMap = self.__getFinderPubmedInfoMap()
            myD['entry_info'] = self.__getFinderEntryInfo()
            myD['finder_summary'] = self.__getFinderSummary()
        else:
            pubmedInfoMap = self.__getRequestPubmedInfoMap()
            myD['entry_info'] = self.__getRequestEntryInfo()
            myD['finder_summary'] = ''
        #
        myD['idlist'] = ' '.join(self._IdList)
        #
        self.__writePubmedInfo(pubmedInfoMap, pubmed_file)
        #
        return self._processTemplate('citation_finder/main_citation_form_tmplt.html', myD)

    def __getFinderPubmedInfoMap(self):
        pubmedInfoMap = {}
        for dataDict in self._resultList:
            if 'pubmed' not in dataDict:
                continue
            #
            for pdir in dataDict['pubmed']:
                pid = pdir['pdbx_database_id_PubMed']
                if pid in pubmedInfoMap:
                    continue
                #
                pubmedInfoMap[pid] = pdir
            #
        #
        return pubmedInfoMap

    def __getFinderEntryInfo(self):
        items = self._getItemList('citation_finder/entry_item_list')
        c_items = self._getItemList('citation_finder/author_citation_item_list')
        p_items = self._getItemList('citation_finder/pubmed_citation_item_list')
        text = ''
        count = 0
        flag = True
        for dataDict in self._resultList:
            if 'pubmed' not in dataDict:
                continue
            #
            myD, selectedData = self._initialEntryDict(dataDict, items, False, False, 'None')
            selectedData['JRNL'] = 'checked'
            selectedData['Citation'] = 'checked'
            myD['comment_start'] = ''
            myD['comment_end'] = ''
            if self._skipReleaseOptionFlag:
                myD['comment_start'] = '<!--'
                myD['comment_end'] = '-->'
            #
            p_dir = dataDict['pubmed'][0]
            myD['similarity_score'] = p_dir['similarity_score']
            myD['color'] = self.__getColorCode(p_dir['similarity_score'])
            fval = float(p_dir['similarity_score'])
            if fval > 0.9:
                self.__high_count += 1
            elif fval > 0.7:
                self.__middle_count += 1
            else:
                self.__lower_count += 1
            #
            if myD['check_option'] == 'checked':
                if (myD['pdb_id'] != 'None') and (myD['status_code'] != 'REL'):
                    myD['check_option'] = ''
                elif (myD['pdb_id'] == 'None') and (myD['comb_status_code'] != 'REL'):
                    myD['check_option'] = ''
                #
            #
            myD['pubmed_citation_info'], count = self.__getPubmedInfo(dataDict['pubmed'], dataDict['structure_id'], p_items, count, False)
            if flag:
                myD['bgclass'] = 'even'
                flag = False
            else:
                myD['bgclass'] = 'odd'
                flag = True
            #
            if 'citation_author' in dataDict:
                dataDict['author'] = ','.join(dataDict['citation_author'])
            #
            extraD = {}
            extraD['structure_id'] = dataDict['structure_id']
            extraD['keep_citation'] = self.__getKeepCitationValue(dataDict['pubmed'][0], dataDict)
            myD['auth_citation_info'] = self.__depictCitationInfo(dataDict, c_items, extraD, 'citation_finder/author_citation_tmplt.html', False)
            #
            if not self._skipReleaseOptionFlag:
                myD['release_option'] = self._getReleaseOption(dataDict, selectedData, True)
            #
            if (not self._newReleaseFlag) and ('pdb_id' in dataDict) and dataDict['pdb_id']:
                myD['revision'] = self._getRevisionInfo(dataDict['structure_id'], count, selectedData, '2', '', '', 'border-style:none;', 'none')
            else:
                myD['revision'] = ''
            text += self._processTemplate('citation_finder/entry_tmplt.html', myD)
            #
            self._IdList.append('entry_' + dataDict['structure_id'])
        #
        return text

    def __getKeepCitationValue(self, pubmed_Citation, curr_Citation):
        if ("pdbx_database_id_DOI" in pubmed_Citation) and pubmed_Citation["pdbx_database_id_DOI"] and \
           ("pdbx_database_id_DOI" in curr_Citation) and curr_Citation["pdbx_database_id_DOI"] and \
           (pubmed_Citation["pdbx_database_id_DOI"].upper() != curr_Citation["pdbx_database_id_DOI"].upper()):
            return 'checked'
        #
        return ''

    def __getFinderSummary(self):
        myD = {}
        myD['total'] = str(len(self._IdList))
        myD['high_count'] = str(self.__high_count)
        myD['middle_count'] = str(self.__middle_count)
        myD['lower_count'] = str(self.__lower_count)
        return self._processTemplate('citation_finder/citation_finder_summary_tmplt.html', myD)

    def __getRequestPubmedInfoMap(self):
        pubmedInfoMap = {}
        for dataDict in self._resultList:
            if 'pubmed' not in dataDict:
                continue
            #
            for _k, pdir in list(dataDict['pubmed'].items()):
                pid = pdir['pdbx_database_id_PubMed']
                if pid in pubmedInfoMap:
                    continue
                #
                pubmedInfoMap[pid] = pdir
            #
            break
        #
        return pubmedInfoMap

    def __getRequestEntryInfo(self):
        items = self._getItemList('citation_request/entry_item_list')
        c_items = self._getItemList('citation_request/citation_content_item_list')
        #
        text = ''
        count = 0
        flag = True
        for dataDict in self._resultList:
            if ('pubmed' not in dataDict) or ('citation_id' not in dataDict):
                continue
            #
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
            myD['citation_info'], count = self.__depictRequestCitationInfo(dataDict, c_items, count, myD['bgclass'])
            #
            text += self._processTemplate('citation_request/entry_tmplt.html', myD)
            #
            self._IdList.append('entry_' + dataDict['structure_id'])
        #
        return text

    def __writePubmedInfo(self, pubmedInfoMap, picklefile):
        fb = open(os.path.join(self._sessionPath, picklefile), 'wb')
        pickle.dump(pubmedInfoMap, fb)
        fb.close()

    def __depictRequestCitationInfo(self, entry, c_items, count, bgclass):
        text = ''
        flag = True
        for citation_id in entry['citation_id']:
            myD = {}
            myD['citation_id'] = citation_id
            myD['count'] = str(count)
            c_title = ''
            authFlag = False
            if ('auth_citation' in entry) and (citation_id in entry['auth_citation']):
                if 'title' in entry['auth_citation'][citation_id]:
                    c_title = entry['auth_citation'][citation_id]['title']
                #
                authFlag = True
                myD['auth_citation'] = '&nbsp;'
                #
                extraD = {}
                extraD['structure_id'] = entry['structure_id']
                extraD['citation_id'] = citation_id
                extraD['begin_keep_comment'] = ''
                extraD['end_keep_comment'] = ''
                if ('pubmed' in entry) and (citation_id in entry['pubmed']):
                    extraD['keep_citation'] = self.__getKeepCitationValue(entry['pubmed'][citation_id], entry['auth_citation'][citation_id])
                else:
                    extraD['keep_citation'] = ''
                #
                myD['auth_citation_info'] = self.__depictCitationInfo(entry['auth_citation'][citation_id], c_items, extraD,
                                                                      'citation_request/citation_content_tmplt.html', False)
            else:
                myD['auth_citation'] = 'None'
                myD['auth_citation_info'] = ''
            #
            p_title = ''
            pubFlag = False
            if ('pubmed' in entry) and (citation_id in entry['pubmed']):
                p_title = entry['pubmed'][citation_id]['title']
                pubFlag = True
                myD['checkbox'] = '<input type="checkbox" name="pubmed_' + entry['structure_id'] \
                    + '" value="' + str(entry['pubmed'][citation_id]['pdbx_database_id_PubMed']) \
                    + '_' + citation_id + '" checked />'
                myD['pubmed_citation'] = '&nbsp;'
                if citation_id == 'primary':
                    myD['pubmed_citation'] = self.__checkMarkedUnwantedPubMed(entry['structure_id'],
                                                                              str(entry['pubmed'][citation_id]['pdbx_database_id_PubMed']))
                #
                extraD = {}
                extraD['structure_id'] = entry['structure_id']
                extraD['citation_id'] = citation_id
                extraD['begin_keep_comment'] = '<!--'
                extraD['end_keep_comment'] = '-->'
                extraD['keep_citation'] = ''
                myD['pubmed_citation_info'] = self.__depictCitationInfo(entry['pubmed'][citation_id], c_items, extraD,
                                                                        'citation_request/citation_content_tmplt.html', True)
            else:
                myD['checkbox'] = '&nbsp; &nbsp; &nbsp;'
                myD['pubmed_citation'] = 'None'
                myD['pubmed_citation_info'] = ''
            #
            score = 'None'
            color = '#996600'
            if c_title and p_title:
                sim = calStringSimilarity(c_title, p_title)
                score = '%.3f' % sim
                color = self.__getColorCode(score)
            myD['similarity_score'] = score
            myD['color'] = color
            #
            myD['flag'] = ''
            if not authFlag and pubFlag:
                myD['flag'] = '<span style="color:#FF0000">[New]</span>'
            elif citation_id != 'primary':
                myD['flag'] = '&nbsp; &nbsp; &nbsp; &nbsp; &nbsp;'
            #
            if flag:
                myD['bgclass'] = 'green'
                flag = False
            else:
                myD['bgclass'] = bgclass
                flag = True
            #
            text += self._processTemplate('citation_request/citation_tmplt.html', myD)
            count += 1
        #
        return text, count

    def __checkMarkedUnwantedPubMed(self, structure_id, pubmed_id):
        archiveDirPath = self._pI.getDirPath(dataSetId=structure_id, wfInstanceId=None, contentType='model',
                                             formatType='pdbx',
                                             fileSource='archive', versionId='latest',
                                             partNumber=1)
        pickle_file = os.path.join(archiveDirPath, 'marked_pubmed_id.pic')
        if not os.access(pickle_file, os.F_OK):
            return '&nbsp;'
        #
        pubmed_id_list = []
        fb = open(pickle_file, 'rb')
        pubmed_id_list = pickle.load(fb)
        fb.close()
        if pubmed_id in pubmed_id_list:
            return '<span style="color:red">WARNING: ' + pubmed_id + ' marked as unwanted</span>'
        #
        return '&nbsp;'

    def __getColorCode(self, score):
        f_score = float(score)
        if f_score > 0.9:
            return '#00CC00'
        elif f_score > 0.7:
            return '#FFCC00'
        return '#996600'

    def __depictCitationInfo(self, dataDict, items, extraD, tmpltFile, textFlag):
        myD = {}
        for item in items:
            val = 'None'
            if item == 'page':
                val = self.__getPubmedPage(dataDict)
            elif item in dataDict:
                val = dataDict[item]
            #
            if item == 'author':
                val = val.replace(',', ', ')
                if textFlag:
                    if ('author_list' in dataDict) and dataDict['author_list']:
                        val = self.__depictCitationAuthor(extraD['structure_id'], dataDict['pdbx_database_id_PubMed'], dataDict['citation_id'], dataDict['author_list'])
                    else:
                        val = self.__getTextArea('author', extraD['structure_id'], dataDict['pdbx_database_id_PubMed'], dataDict['citation_id'], val)
                    #
                #
            elif item == 'title':
                if textFlag:
                    val = self.__getTextArea('title', extraD['structure_id'], dataDict['pdbx_database_id_PubMed'], dataDict['citation_id'], val)
                #
            elif item == 'pdbx_database_id_PubMed':
                myD['structure_id'] = extraD['structure_id']
                myD['pubmed_id'] = val
                val = self.__processPubmedURL(val)
            elif item == 'pdbx_database_id_DOI':
                val = self.__processDOIURL(val)
            elif item in extraD:
                val = extraD[item]
            #
            myD[item] = val
        #
        return self._processTemplate(tmpltFile, myD)

    def __getPubmedInfo(self, plist, structure_id, c_items, count, checkAll):
        text = ''
        first = True
        for dataDict in plist:
            checkFlag = False
            if checkAll or first:
                checkFlag = True
            #
            text += self.__depictPubmedInfo(dataDict, structure_id, c_items, count, checkFlag)
            count += 1
            first = False
        #
        return text, count

    def __depictPubmedInfo(self, dataDict, structure_id, c_items, count, checkFlag):
        items = ['pdbx_database_id_PubMed', 'similarity_score', 'type', 'citation_id']
        #
        myD = {}
        myD['count'] = str(count)
        myD['structure_id'] = structure_id
        myD['pubmed_citation_info'] = self.__depictCitationInfo(dataDict, c_items, myD, 'citation_finder/pubmed_citation_tmplt.html', True)
        if checkFlag:
            myD['check_option'] = 'checked'
        else:
            myD['check_option'] = ''
        #
        for item in items:
            val = 'None'
            if item == 'similarity_score':
                val = dataDict[item]
                myD['color'] = self.__getColorCode(val)
            elif item in dataDict:
                val = dataDict[item]
            #
            myD[item] = val
        #
        return self._processTemplate('citation_finder/pubmed_tmplt.html', myD)

    def __processPubmedURL(self, val):
        if not val or val == 'None':
            return 'None'
        #
        myD = {}
        myD['pdbx_database_id_PubMed'] = val
        return self._processTemplate('citation_finder/pubmed_url_tmplt.html', myD)

    def __processDOIURL(self, val):
        if not val or val == 'None':
            return 'None'
        #
        myD = {}
        myD['pdbx_database_id_DOI'] = val
        return self._processTemplate('citation_finder/doi_url_tmplt.html', myD)

    def __getTextArea(self, name_prefix, structure_id, pdbmed_id, citation_id, value):
        irow = len(value) / 120 + 1
        text = '<textarea name="' + name_prefix + '_' + structure_id + '_' \
            + pdbmed_id + '_' + citation_id + '" cols="120" rows="' + str(irow) \
            + '" wrap>' + value + '</textarea>'
        return text

    def __getPubmedPage(self, dataDict):
        first_page = ''
        if 'page_first' in dataDict:
            first_page = dataDict['page_first']
        last_page = ''
        if 'page_last' in dataDict:
            last_page = dataDict['page_last']
        if first_page and last_page:
            if first_page == last_page:
                return first_page
            else:
                return first_page + '-' + last_page
        elif first_page:
            return first_page
        elif last_page:
            return last_page
        return 'None'

    def __depictCitationAuthor(self, structure_id, pdbmed_id, citation_id, authorList):
        myD = {}
        myD['structure_id'] = structure_id
        myD['pdbmed_id'] = pdbmed_id
        myD['citation_id'] = citation_id
        myD['author_list_number'] = str(len(authorList) + 1)
        #
        count = 0
        author_data = ''
        for authorDict in authorList:
            authorDict['id'] = structure_id + '_' + pdbmed_id + '_' + citation_id + '_' + str(count)
            count += 1
            author_data += self._processTemplate('citation_finder/citation_author_row_tmplt.html', authorDict)
        #
        auD = {}
        auD['id'] = structure_id + '_' + pdbmed_id + '_' + citation_id + '_' + str(count)
        auD['name'] = ''
        auD['orcid'] = ''
        myD['author_data'] = author_data + self._processTemplate('citation_finder/citation_author_row_tmplt.html', auD)
        #
        return self._processTemplate('citation_finder/citation_author_table_tmplt.html', myD)
