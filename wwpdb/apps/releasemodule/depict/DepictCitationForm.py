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
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import cPickle, os, sys, string, traceback

from wwpdb.apps.releasemodule.citation.StringUtil  import calStringSimilarity
from wwpdb.apps.releasemodule.depict.ReleaseOption import ReleaseOption
from wwpdb.apps.releasemodule.utils.JournalAbbrev  import JournalAbbrev
from wwpdb.apps.releasemodule.utils.TimeUtil       import TimeUtil
from wwpdb.apps.releasemodule.utils.Utility        import *

class DepictCitationForm(object):
    """ Class responsible for generating citation input form depiction.
    """
    def __init__(self, reqObj=None, resultList=None, verbose=False, log=sys.stderr):
        self.__verbose=verbose
        self.__lfh=log
        self.__reqObj=reqObj
        self.__resultList=resultList
        self.__IdList = []
        #
        self.__sessionId = str(self.__reqObj.getSessionId())
        self.__sessionPath = str(self.__reqObj.getValue('sessionPath'))
        #
        t =TimeUtil()
        self.__rel_date = t.NextWednesday()

    def DoRender(self):
        owner = str(self.__reqObj.getValue('owner'))
        #
        myD = {}
        myD['task'] = str(self.__reqObj.getValue('task'))
        myD['pubmed_file'] = ''
        myD['sessionid'] = self.__sessionId
        myD['owner'] = owner
        myD['annotator'] = str(self.__reqObj.getValue('annotator'))
        if self.__resultList:
            myD['citation_info'] = self.__depictCitationInfo(self.__resultList[0]['citation'])
        else:
            myD['citation_info'] = ''
        myD['entry_info'] = self.__getRequestEntryInfo()
        myD['finder_summary'] = ''
        myD['idlist'] = ' '.join(self.__IdList)
        ja = JournalAbbrev(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        myD['abbrev_info'] = ja.GetJoinQuoterList(',\n')
        #
        return self.__processTemplate('citation_request/main_citation_input_form_tmplt.html', myD)

    def __getRequestEntryInfo(self):
        items = [ 'structure_id', 'pdb_id', 'comb_ids', 'title', 'author_list', 'rcsb_annotator', 'status_code', 'comb_status_code' ]
        #
        text = ''
        count = 0
        flag = True
        for dir in self.__resultList:
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
            myD['citation_info'] = ''
            #
            text += self.__processTemplate('citation_request/entry_tmplt.html', myD)
            #
            self.__IdList.append('entry_' + dir['structure_id'])
            count += 1
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

    def __depictCitationInfo(self, dir):
        authorlist = []
        if dir.has_key('author'):
            authorlist = dir['author']
        #
        max_author_num = len(authorlist) + 5
        if max_author_num < 10:
            max_author_num = 10
        #
        items = [ 'citation_id', 'title', 'journal_abbrev', 'journal_volume', 'year', 'page_first',
                  'page_last', 'pdbx_database_id_PubMed', 'pdbx_database_id_DOI' ]
        #
        myD = {}
        for item in items:
            val = ''
            if dir.has_key(item) and dir[item]:
                val = str(dir[item])
            #
            if item != 'citation_id':
                val = self.__getTextArea(item, val)
            #
            myD[item] = val
        #
        myD['max_author_num'] = str(max_author_num)
        text = self.__processTemplate('citation_request/citation_form_tmplt.html', myD)
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
            for author in authorlist:
                count += 1
                myD = {}
                myD['count'] = str(count)
                myD['name'] = self.__getTextArea('name_' + str(count), author)
                text += self.__processTemplate('citation_request/author_form_tmplt.html', myD)
            #
        #
        for i in xrange (0, diff_num):
            count += 1
            myD = {}
            myD['count'] = str(count)
            myD['name'] = self.__getTextArea('name_' + str(count), '')
            text += self.__processTemplate('citation_request/author_form_tmplt.html', myD)
        #
        return text

    def __getTextArea(self, name, value):
        irow = len(value) / 120 + 1
        text = '<textarea name="' + name + '" id="' + name + '" cols="120" rows="' + str(irow) + '" wrap>' + value + '</textarea>'
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
