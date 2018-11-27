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
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import cPickle, os, sys, string, traceback

from wwpdb.apps.releasemodule.citation.StringUtil  import calStringSimilarity
from wwpdb.apps.releasemodule.depict.ReleaseOption import ReleaseOption
from wwpdb.apps.releasemodule.utils.TimeUtil       import TimeUtil
from wwpdb.apps.releasemodule.utils.Utility        import *
from wwpdb.utils.rcsb.PathInfo                    import PathInfo

class DepictCitation(object):
    """ Class responsible for generating citation finder result HTML depiction.

    """
    def __init__(self, reqObj=None, resultList=None, verbose=False, log=sys.stderr):
        self.__verbose=verbose
        self.__lfh=log
        self.__reqObj=reqObj
        self.__resultList=resultList
        self.__IdList = []
        self.__high_count = 0
        self.__middle_count = 0
        self.__lower_count = 0
        #
        self.__sessionId = str(self.__reqObj.getSessionId())
        self.__sessionPath = str(self.__reqObj.getValue('sessionPath'))
        self.__siteId  = str(self.__reqObj.getValue("WWPDB_SITE_ID"))
        #
        t =TimeUtil()
        self.__rel_date = t.NextWednesday()

    def DoRender(self,finderFlag=True):
        owner = str(self.__reqObj.getValue('owner'))
        pubmedInfoMap = {}
        pubmed_file = getFileName(self.__sessionPath, owner, 'db')
        #
        myD = {}
        myD['task'] = str(self.__reqObj.getValue('task'))
        myD['pubmed_file'] = pubmed_file
        myD['sessionid'] = self.__sessionId
        myD['owner'] = owner
        myD['annotator'] = str(self.__reqObj.getValue('annotator'))
        if finderFlag:
            pubmedInfoMap = self.__getFinderPubmedInfoMap()
            myD['entry_info'] = self.__getFinderEntryInfo()
            myD['finder_summary'] = self.__getFinderSummary()
        else:
            pubmedInfoMap = self.__getRequestPubmedInfoMap()
            myD['entry_info'] = self.__getRequestEntryInfo()
            myD['finder_summary'] = ''
        myD['idlist'] = ' '.join(self.__IdList)
        #
        self.__writePubmedInfo(pubmedInfoMap, pubmed_file)
        #
        return self.__processTemplate('citation_finder/main_citation_form_tmplt.html', myD)

    def __getFinderPubmedInfoMap(self):
        map = {}
        for dir in self.__resultList:
            if not dir.has_key('pubmed'):
                continue
            #
            for pdir in dir['pubmed']:
                id = pdir['pdbx_database_id_PubMed']
                if map.has_key(id):
                    continue
                #
                map[id] = pdir
            #
        #
        return map

    def __getRequestPubmedInfoMap(self):
        map = {}
        for entry in self.__resultList:
            if not entry.has_key('pubmed'):
                continue
            #
            for k,dir in entry['pubmed'].items():
                id = dir['pdbx_database_id_PubMed']
                if map.has_key(id):
                    continue
                #
                map[id] = dir
            #
            break
        #
        return map

    def __writePubmedInfo(self, map, picklefile):
        fb = open(os.path.join(self.__sessionPath, picklefile), 'wb')
        cPickle.dump(map, fb)
        fb.close()

    def __getFinderSummary(self):
        myD = {}
        myD['total'] = str(len(self.__IdList))
        myD['high_count'] = str(self.__high_count)
        myD['middle_count'] = str(self.__middle_count)
        myD['lower_count'] = str(self.__lower_count)
        return self.__processTemplate('citation_finder/citation_finder_summary_tmplt.html', myD)

    def __getFinderEntryInfo(self):
        items = [ 'structure_id', 'pdb_id', 'comb_ids', 'title', 'author_list', 'similarity_score', 'rcsb_annotator',
                  'status_code', 'comb_status_code', 'check_option' ] 
        c_items = [ 'c_title', 'author', 'journal_abbrev', 'journal_volume', 'page',
                    'year', 'pdbx_database_id_PubMed', 'pdbx_database_id_DOI' ]
        text = ''
        count = 0
        flag = True
        for dir in self.__resultList:
            if not dir.has_key('pubmed'):
                continue
            #
            newRelease = self.__getNewReleaseFlag(dir)
            p_dir = dir['pubmed'][0]
            myD = {}
            myD['status_color'] = '#000000'
            if dir.has_key('status_code') and (dir['status_code'] == 'PROC' or dir['status_code'] == 'WAIT' or \
               dir['status_code'] == 'AUCO' or dir['status_code'] == 'REPL' or dir['status_code'] == 'POLC'):
                myD['status_color'] = '#FF0000' 
            #
            for item in items:
                val = 'None'
                if item == 'similarity_score':
                    val = p_dir[item]
                    myD['color'] = self.__getColorCode(val)
                    fval = float(val)
                    if fval > 0.9:
                        self.__high_count += 1
                    elif fval > 0.7:
                        self.__middle_count += 1
                    else:
                        self.__lower_count += 1
                    #
                elif dir.has_key(item):
                    val = dir[item]
                #
                myD[item] = val
            #
            if myD['check_option'] == 'checked' and myD['status_code'] != 'REL':
                myD['check_option'] = ''
            #
            myD['pubmed_citation_info'],count = self.__getPubmedInfo(dir['pubmed'], dir['structure_id'], count, False)
            if flag:
                myD['bgclass'] = 'even'
                flag = False
            else:
                myD['bgclass'] = 'odd'
                flag = True
            #
            if dir.has_key('citation_author'):
                dir['author'] = ','.join(dir['citation_author'])
            #
            myD['auth_citation_info'] = self.__depictCitationInfo(dir, c_items, dir['structure_id'], \
                                       'citation_finder/auther_citation_tmplt.html', False)
            #
            myD['release_option'] = ReleaseOption(dir, True, newRelease)
            #
            if not newRelease:
                myD['revision'] = self.__getRevisionInfo(dir['structure_id'], count)
            else:
                myD['revision'] = ''
            text += self.__processTemplate('citation_finder/entry_tmplt.html', myD)
            #
            self.__IdList.append('entry_' + dir['structure_id'])
        #
        return text

    def __getRequestEntryInfo(self):
        items = [ 'structure_id', 'pdb_id', 'comb_ids', 'title', 'author_list', 'rcsb_annotator', 'status_code', 'comb_status_code' ]
        #
        text = ''
        count = 0
        flag = True
        for dir in self.__resultList:
            if not dir.has_key('pubmed') or not dir.has_key('citation_id'):
                continue
            #
            if (not dir.has_key('pdb_id')) or (not dir['pdb_id']):
                if dir.has_key('status_code'):
                    del dir['status_code']
                #
            #
            newRelease = self.__getNewReleaseFlag(dir)
            myD = {}
            myD['check_option'] = 'checked'
            myD['status_color'] = '#000000'
            """
            if dir.has_key('status_code') and (dir['status_code'] == 'PROC' or dir['status_code'] == 'WAIT' or \
               dir['status_code'] == 'AUCO' or dir['status_code'] == 'REPL' or dir['status_code'] == 'POLC'):
            """
            color_status_code = ''
            if dir.has_key('status_code') and dir['status_code']:
                color_status_code = dir['status_code']
            elif dir.has_key('status_code_em') and dir['status_code_em']:
                color_status_code = dir['status_code_em']
            #
            if color_status_code == 'PROC' or color_status_code == 'WAIT' or color_status_code == 'AUCO' or \
               color_status_code == 'REPL' or color_status_code == 'POLC':
                myD['status_color'] = '#FF0000' 
            #
            for item in items:
                val = 'None'
                if dir.has_key(item):
                    val = dir[item]
                #
                if item == 'status_code':
                    myD[item] = color_status_code
                else:
                    myD[item] = val
                #
            #
            if flag:
                myD['bgclass'] = 'even'
                flag = False
            else:
                myD['bgclass'] = 'odd'
                flag = True
            #
            myD['release_option'] = ReleaseOption(dir, True, newRelease)
            #
            if not newRelease and dir.has_key('pdb_id') and dir['pdb_id']:
                myD['revision'] = self.__getRevisionInfo(dir['structure_id'], count)
            else:
                myD['revision'] = ''
            #
            myD['citation_info'],count = self.__depictRequestCitationInfo(dir, count, myD['bgclass'])
            #
            text += self.__processTemplate('citation_request/entry_tmplt.html', myD)
            #
            self.__IdList.append('entry_' + dir['structure_id'])
        #
        return text

    def __getNewReleaseFlag(self, dir):
        newRelease = True
        if dir.has_key('status_code') and dir['status_code'] == 'REL':
            if dir.has_key('date_of_RCSB_release') and str(dir['date_of_RCSB_release']) < self.__rel_date:
                newRelease = False
            #
        elif dir.has_key('status_code_em') and dir['status_code_em'] == 'REL':
            if dir.has_key('date_of_EM_release') and str(dir['date_of_EM_release']).replace('00:00:00', '').strip() < self.__rel_date:
                newRelease = False
            #
        #
        return newRelease

    def __depictRequestCitationInfo(self, entry, count, bgclass):
        c_items = [ 'pdbx_database_id_PubMed', 'title', 'author', 'journal_abbrev',
                    'journal_volume', 'page', 'year', 'pdbx_database_id_DOI' ]
        text = ''
        flag = True
        for citation_id in entry['citation_id']:
            myD = {}
            myD['citation_id'] = citation_id
            myD['count'] = str(count)
            c_title = ''
            authFlag = False 
            if entry.has_key('auth_citation') and entry['auth_citation'].has_key(citation_id):
                c_title = entry['auth_citation'][citation_id]['title']
                authFlag = True
                myD['auth_citation'] = '&nbsp;'
                myD['auth_citation_info'] = self.__depictCitationInfo(entry['auth_citation'][citation_id], \
                         c_items, entry['structure_id'], 'citation_request/citation_content_tmplt.html', False)
            else:
                myD['auth_citation'] = 'None'
                myD['auth_citation_info'] = ''
            #
            p_title = ''
            pubFlag = False
            if entry.has_key('pubmed') and entry['pubmed'].has_key(citation_id):
                p_title = entry['pubmed'][citation_id]['title']
                pubFlag = True
                myD['checkbox'] = '<input type="checkbox" name="pubmed_' + entry['structure_id'] \
                                + '" value="' + str(entry['pubmed'][citation_id]['pdbx_database_id_PubMed']) \
                                + '_' + citation_id + '" checked />'
                myD['pubmed_citation'] = '&nbsp;'
                if citation_id == 'primary':
                    myD['pubmed_citation'] = self.__checkMarkedUnwantedPubMed(entry['structure_id'], \
                                              str(entry['pubmed'][citation_id]['pdbx_database_id_PubMed']))
                #
                myD['pubmed_citation_info'] = self.__depictCitationInfo(entry['pubmed'][citation_id], 
                         c_items, entry['structure_id'], 'citation_request/citation_content_tmplt.html', True)
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
            text += self.__processTemplate('citation_request/citation_tmplt.html', myD)
            count += 1
        #
        return text,count

    def __checkMarkedUnwantedPubMed(self, structure_id, pubmed_id):
        pI = PathInfo(siteId=self.__siteId, sessionPath=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        archiveDirPath = pI.getDirPath(dataSetId=structure_id, wfInstanceId=None, contentType='model', formatType='pdbx', \
                                       fileSource='archive', versionId='latest', partNumber=1)
        pickle_file = os.path.join(archiveDirPath, 'marked_pubmed_id.pic')
        if not os.access(pickle_file, os.F_OK):
            return '&nbsp;'
        #
        pubmed_id_list = []
        fb = open(pickle_file, 'rb')
        pubmed_id_list = cPickle.load(fb)
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

    def __depictCitationInfo(self, dir, items, structure_id, tmpltFile, textFlag):
        myD = {}
        for item in items:
            val = 'None'
            if item == 'page':
                val = self.__getPubmedPage(dir)
            elif dir.has_key(item):
                val = dir[item]
            #
            if item == 'author':
                val = val.replace(',', ', ')
                if textFlag:
                    val = self.__getTextArea('author', structure_id, \
                                     dir['pdbx_database_id_PubMed'], \
                                     dir['citation_id'], val)
                #
            elif item == 'title':
                if textFlag:
                    val = self.__getTextArea('title', structure_id, \
                                    dir['pdbx_database_id_PubMed'], \
                                    dir['citation_id'], val)
                #
            elif item == 'pdbx_database_id_PubMed':
                myD['structure_id'] = structure_id
                myD['pubmed_id'] = val
                val = self.__processPubmedURL(val)
            elif item == 'pdbx_database_id_DOI':
                val = self.__processDOIURL(val)
            #
            myD[item] = val
        #
        return self.__processTemplate(tmpltFile, myD)

    def __getPubmedInfo(self, plist, structure_id, count, checkAll):
        text = ''
        first = True
        for dir in plist:
            checkFlag = False
            if checkAll or first:
                checkFlag = True
            #
            text += self.__depictPubmedInfo(dir, structure_id, count, checkFlag)
            count += 1
            first = False
        #
        return text,count

    def __depictPubmedInfo(self, dir, structure_id, count, checkFlag):
        items = [ 'pdbx_database_id_PubMed', 'similarity_score', 'type', 'citation_id' ]
        c_items = [ 'pdbx_database_id_PubMed', 'title', 'author', 'journal_abbrev',
                    'journal_volume', 'page', 'year', 'pdbx_database_id_DOI' ]
        #
        myD = {}
        myD['count'] = str(count)
        myD['structure_id'] = structure_id
        myD['pubmed_citation_info'] = self.__depictCitationInfo(dir, c_items, \
                  structure_id, 'citation_finder/pubmed_citation_tmplt.html', True)
        if checkFlag:
            myD['check_option'] = 'checked'
        else:
            myD['check_option'] = ''
        #
        for item in items:
            val = 'None'
            if item == 'similarity_score':
                val = dir[item]
                myD['color'] = self.__getColorCode(val)
            elif dir.has_key(item):
                val = dir[item]
            #
            myD[item] = val
        #
        return self.__processTemplate('citation_finder/pubmed_tmplt.html', myD)

    def __processPubmedURL(self, val):
        if not val or val == 'None':
            return 'None'
        #
        myD = {}
        myD['pdbx_database_id_PubMed'] = val
        return self.__processTemplate('citation_finder/pubmed_url_tmplt.html', myD)

    def __processDOIURL(self, val):
        if not val or val == 'None':
            return 'None'
        #
        myD = {}
        myD['pdbx_database_id_DOI'] = val
        return self.__processTemplate('citation_finder/doi_url_tmplt.html', myD)

    def __getTextArea(self, name_prefix, structure_id, pdbmed_id, citation_id, value):
        irow = len(value) / 120 + 1
        text = '<textarea name="' + name_prefix + '_' + structure_id + '_' \
             + pdbmed_id + '_' + citation_id + '" cols="120" rows="' + str(irow) \
             + '" wrap>' + value + '</textarea>'
        return text

    def __getRevisionInfo(self, structure_id, count):
        myD = {}
        myD['structure_id'] = structure_id
        myD['count'] = str(count)
        myD['jrnl'] = 'checked'
        myD['cols'] = '2'
        myD['begin_comment'] = ''
        myD['end_comment'] = ''
        myD['class'] = ''
        myD['style'] = 'border-style:none;'
        myD['display'] = 'none'
        return self.__processTemplate('revision_tmplt.html', myD)

    def __getPubmedPage(self, dir):
        first_page = ''
        if dir.has_key('page_first'):
            first_page = dir['page_first']
        last_page = ''
        if dir.has_key('page_last'):
            last_page = dir['page_last']
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

    def __processTemplate(self,fn,parameterDict={}):
        """ Read the input HTML template data file and perform the key/value substitutions in the
            input parameter dictionary.
            
            :Params:
                ``parameterDict``: dictionary where
                key = name of subsitution placeholder in the template and
                value = data to be used to substitute information for the placeholder
                
            :Returns:
                string representing entirety of content with subsitution placeholders now replaced with data
        """
        tPath =self.__reqObj.getValue("TemplatePath")
        fPath=os.path.join(tPath,fn)
        ifh=open(fPath,'r')
        sIn=ifh.read()
        ifh.close()
        return (  sIn % parameterDict )
