##
# File:  Depict.py
# Date:  28-Jun-2013
# Updates:
##
"""
Create HTML depiction for release module.

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

import os, sys, string, traceback

from wwpdb.apps.releasemodule.depict.ReleaseOption import ReleaseOption
from wwpdb.apps.releasemodule.utils.TimeUtil       import TimeUtil
from wwpdb.apps.releasemodule.utils.Utility        import FindReleaseFiles

class Depict(object):
    """ Class responsible for generating HTML depiction.

    """
    def __init__(self, reqObj=None, resultList=None, itemList=None, verbose=False, log=sys.stderr):
        self.__verbose=verbose
        self.__lfh=log
        self.__reqObj=reqObj
        self.__resultList=resultList
        self.__items = itemList
        self.__atList = []
        #
        self.__sessionId = str(self.__reqObj.getSessionId())
        self.__formTemplate = str(self.__reqObj.getValue('FormTemplate'))
        self.__rowTemplate = str(self.__reqObj.getValue('RowTemplate'))
        self.__option = str(self.__reqObj.getValue('option'))
        self.__cols = str(len(self.__items) - 1)
        #
        t =TimeUtil()
        self.__rel_date = t.NextWednesday()

    def DoRender(self):
        myD = {}
        myD['task'] = str(self.__reqObj.getValue('task'))
        myD['sessionid'] = self.__sessionId
        myD['owner'] = str(self.__reqObj.getValue('owner'))
        myD['annotator'] = str(self.__reqObj.getValue('annotator'))
        myD['table_rows'] = self.__getRows()
        myD['atlist'] = ' '.join(self.__atList)
        return self.__processTemplate(self.__formTemplate, myD)

    def __getRows(self):
        text = ''
        count = 0
        for dir in self.__resultList:
            if ('pdb_id' not in dir) or (not dir['pdb_id']):
                if 'status_code' in dir:
                    del dir['status_code']
                #
            #
            newRelease = self.__getNewReleaseFlag(dir)
            if self.__option == 'status_update':
                dir['new_status_code'] = dir['author_release_status_code']
            elif self.__option == 'pull_release':
                if 'p_status' in dir:
                    dir['new_status_code'] = dir['p_status']
                elif 'author_release_status_code' in dir and dir['author_release_status_code'] == 'HPUB':
                    dir['new_status_code'] = dir['author_release_status_code']
                else:
                    dir['new_status_code'] = 'HOLD'
            #
            release_date = ''
            if 'date_of_RCSB_release' in dir and dir['date_of_RCSB_release']:
                release_date = str(dir['date_of_RCSB_release']).replace('00:00:00', '').strip()
            elif 'date_of_EM_release' in dir and dir['date_of_EM_release']:
                release_date = str(dir['date_of_EM_release']).replace('00:00:00', '').strip()
            #
            myD = {}
            myD['status_color'] = '#000000'
            skip_release_option = False
            myD['comment_start'] = ''
            myD['comment_end'] = ''
            """
            if dir.has_key('status_code') and (dir['status_code'] == 'PROC' or dir['status_code'] == 'WAIT' or \
               dir['status_code'] == 'AUCO' or dir['status_code'] == 'REPL' or dir['status_code'] == 'POLC'):
            """
            color_status_code = ''
            if 'status_code' in dir and dir['status_code']:
                color_status_code = dir['status_code']
            elif 'status_code_em' in dir and dir['status_code_em']:
                color_status_code = dir['status_code_em']
            #
            if color_status_code == 'PROC' or color_status_code == 'WAIT' or color_status_code == 'AUCO' or \
               color_status_code == 'REPL' or color_status_code == 'POLC':
                skip_release_option = True
                myD['status_color'] = '#FF0000'
                myD['comment_start'] = '<!--'
                myD['comment_end'] = '-->'
            #
            for item in self.__items:
                val = ''
                if item in dir:
                    val = dir[item]
                #
                if item == 'exp_data': 
                    myD[item] = self.__getExpStatus(dir)
                elif item == 'date_of_RCSB_release':
                   myD[item] = release_date
                elif val or item == 'new_status_code':
                    myD[item] = val
                else:
                    myD[item] = '&nbsp;'
            #
            text += self.__processTemplate(self.__rowTemplate, myD)
            if (self.__option != 'pull_release') and (not skip_release_option):
                text += self.__getReleaseOption(dir, newRelease)
            text += self.__processAuthorTitle(dir, count)
            if self.__option == 'pull_release':
                text += self.__getReleaseInfo(dir, count)
            elif not newRelease and 'pdb_id' in dir and dir['pdb_id']:
                text += self.__getRevisionInfo(dir['structure_id'], count)
            #
            # Add empty line
            #
            text += '<tr><td style="border-style:none" colspan="' + self.__cols + '">&nbsp; &nbsp; </td></tr>'
            #
            self.__atList.append('author_' + str(count))
            count += 1
        #
        return text

    def __getNewReleaseFlag(self, dir):
        newRelease = True
        if 'status_code' in dir and dir['status_code'] == 'REL':
            if 'date_of_RCSB_release' in dir and str(dir['date_of_RCSB_release']) < self.__rel_date:
                newRelease = False
            #
        elif 'status_code_em' in dir and dir['status_code_em'] == 'REL':
            if 'date_of_EM_release' in dir and str(dir['date_of_EM_release']).replace('00:00:00', '').strip() < self.__rel_date:
                newRelease = False
            #
        #
        return newRelease

    def __getExpStatus(self, dir):
        exp_list = [ [ 'recvd_struct_fact',     'status_code_sf', 'SF' ],
                     [ 'recvd_em_map',          'status_code_em', 'EM' ],
                     [ 'recvd_nmr_constraints', 'status_code_mr', 'MR' ],
                     [ 'recvd_chemical_shifts', 'status_code_cs', 'CS' ] ]
        #
        text = ''
        for list in exp_list:
            if list[0] not in dir:
                continue
            #
            if dir[list[0]] != 'Y' and dir[list[0]] != 'y':
                continue
            #
            if text:
                text += ' <br /> '
            #
            status = ''
            if list[1] in dir:
                status = dir[list[1]]
            #
            text += list[2] + ': ' + status
            #
        #
        if not text:
            text = '&nbsp;'
        #
        return text

    def __getReleaseOption(self, dir, newRelease):
        text = '<tr><td style="text-align:left;" colspan="' + self.__cols + '">Release Option: &nbsp; &nbsp; '
        text += ReleaseOption(dir, False, newRelease)
        text += '</td></tr>\n'
        return text

    def __processAuthorTitle(self, dir, count):
        myD = {}
        myD['id'] = str(count)
        myD['cols'] = self.__cols
        for item in ( 'author_list', 'title'):
            val = ''
            if item in dir:
                val = dir[item]
            #
            if val:
                myD[item] = val
            else:
                myD[item] = '&nbsp;'
        #
        return self.__processTemplate('author_title_tmplt.html', myD)

    def __getRevisionInfo(self, structure_id, count):
        myD = {}
        myD['structure_id'] = structure_id
        myD['count'] = str(count)
        myD['jrnl'] = ''
        myD['cols'] = self.__cols
        myD['begin_comment'] = '<!--'
        myD['end_comment'] = '-->'
        myD['class'] = '' # 'class="odd"'
        myD['style'] = ''
        myD['display'] = 'block'
        return self.__processTemplate('revision_tmplt.html', myD)

    def __getReleaseInfo(self, dir, count):
        siteId  = str(self.__reqObj.getValue('WWPDB_SITE_ID'))
        FileInfo = FindReleaseFiles(siteId, dir)
        #
        myD = {}
        myD['id'] = str(count)
        myD['cols'] = self.__cols
        myD['summary'] = self.__getSummaryInfo(FileInfo)
        myD['rows'] = self.__getReleasedFilesLink(FileInfo)
        return self.__processTemplate('request/release_info_tmplt.html', myD)

    def __getSummaryInfo(self, FileInfo):
        summary = ''
        if 'summary' in FileInfo:
            f = open(FileInfo['summary'], 'r')
            data = f.read()
            f.close()
            summary = data.strip()
            #
        #
        return summary

    def __getReleasedFilesLink(self, FileInfo):
        rows = ''
        if 'releasedFiles' not in FileInfo:
            return rows
        #
        num = len(FileInfo['releasedFiles'])
        num_per_line = 5
        l = int(num / num_per_line)
        x = num % num_per_line
        m = l
        if x == 0:
            m = l - 1
        #
        for i in range(m + 1):
            n = num_per_line
            if i == l:
                n = x
            #
            rows += '<tr>\n'
            for j in range(n):
                filepath = FileInfo['releasedFiles'][i * num_per_line + j]
                (path,filename) = os.path.split(filepath)
                rows += '<td style="text-align:left;border-style:none">' \
                      + '<a href="/service/entity/download_file?filepath=' \
                      + filepath + '" target="_blank"> ' + filename + ' </a></td>\n'
            #
            rows += '</tr>\n'
        #
        return rows

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
