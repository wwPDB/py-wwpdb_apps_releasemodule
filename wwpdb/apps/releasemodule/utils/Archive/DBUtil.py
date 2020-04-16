##
# File:  DBUtil.py
# Date:  27-Jun-2013
# Updates:
##
"""
Providing addintaional APIs for WFE to get info from local database.

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2013 wwPDB

This software is provided under a Creative Commons Attribution 3.0 Unported
License described at http://creativecommons.org/licenses/by/3.0/.

"""
__docformat__ = "restructuredtext en"
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import os,sys
import MySQLdb
#
from wwpdb.utils.wf.dbapi.DbConnection     import DbConnection    
from wwpdb.utils.config.ConfigInfo             import ConfigInfo
from wwpdb.apps.releasemodule.utils.TimeUtil import TimeUtil

class DBUtil(object):
    """
    """
    def __init__(self, siteId=None, verbose=False, log=sys.stderr):
        """
           connect to local database
        """
        self.__lfh       = log
        self.__verbose   = verbose
        self.__siteId    = siteId
        self.__cI        = ConfigInfo(self.__siteId)
        self.__dbServer  = self.__cI.get("SITE_DB_SERVER")
        self.__dbHost    = self.__cI.get("SITE_DB_HOST_NAME")
        self.__dbUser    = self.__cI.get("SITE_DB_USER_NAME")
        self.__dbPw      = self.__cI.get("SITE_DB_PASSWORD")
        self.__dbPort    = self.__cI.get("SITE_DB_PORT_NUMBER")
        self.__dbName    = "da_internal"

        t = TimeUtil()
        self.__cutoffday  = t.CutOffDay()
        self.__startDate = t.StartDay()
        self.__endDate = t.EndDay()
        self.__releaseDate = t.NextWednesday()
        
        self.__myDb  = DbConnection(dbServer=self.__dbServer,dbHost=\
                                    self.__dbHost,dbName=self.__dbName,\
                                    dbUser=self.__dbUser,dbPw=self.__dbPw,\
                                    dbPort=int(self.__dbPort))
        
        self.__dbcon = self.__myDb.connect()          

    def __getSelectedIDList(self, query):
        list = []
        rows = self.runSelectSQL(query)
        if rows:
            for row in rows:
                if 'structure_id' in row:
                    list.append(row['structure_id'])
                #
            #
        #
        return list
   
    def runSelectSQL(self, query):
        list = []
        try:
            self.__dbcon.commit()
            curs = self.__dbcon.cursor(MySQLdb.cursors.DictCursor)
            curs.execute(query)
            list = curs.fetchall()
            if list:
                for dir in list:
                    items = dir.keys()
                    for item in items:
                        if not dir[item]:
                            del dir[item]
                        #
                    #
                #
            #
        except MySQLdb.Error as e:
            self.__lfh.write("Database error %d: %s\n" % (e.args[0], e.args[1]))
        #
        return list

    def getEntriesWithStatusList(self, annotator, status_list):
        query = "select structure_id from rcsb_status where status_code in (" + status_list + ") " \
              + "and (rcsb_annotator = '" + annotator + "' or rcsb_annotator = 'UNASSIGN' or " \
              + "rcsb_annotator is null) order by structure_id"
        id_list = self.__getSelectedIDList(query)
        #
        query = "select r.structure_id from rcsb_status r, em_admin e where r.structure_id = e.structure_id and ( r.rcsb_annotator = '" \
              + annotator + "' or r.rcsb_annotator = 'UNASSIGN' or r.rcsb_annotator is null) and e.current_status in (" + status_list + ")"
        em_map_only_entry_list = self.__getSelectedIDList(query)
        if em_map_only_entry_list:
            id_list.extend(em_map_only_entry_list)
            id_list = sorted(set(id_list))
        #
        return id_list

    def getEntriesWithAuthorName(self, annotator, name):
        name1 = name.strip()
        query_string  = "a.name = '" + name1 + "'"
        if name1.find(',') != -1:
            list = name1.split(',')
            a1 = list[0].strip()
            a2 = list[1].strip()
            name1 = a1 + ',' + a2
            name2 = a1 + ', ' + a2
            query_string  = "(a.name = '" + name1 + "' or a.name = '" + name2 + "')"
        #
        query = "select r.structure_id from rcsb_status r, audit_author a where r.structure_id = a.structure_id " \
              + "and (rcsb_annotator = '" + annotator + "' or rcsb_annotator = 'UNASSIGN' or " \
              + "rcsb_annotator is null) and " + query_string + " order by structure_id"
        rows = self.runSelectSQL(query)
        #
        list = []
        if rows:
            map = {}
            for row in rows:
                if 'structure_id' in row:
                    if row['structure_id'] in map:
                        continue
                    #
                    map[row['structure_id']] = 'yes'
                    list.append(row['structure_id'])
                #
            #
        #
        return list

    def getHoldEntries(self, date_hold_item, annotator):
        query = "select structure_id from rcsb_status where status_code not in ('OBS','WDRN','REL') " \
              + "and (rcsb_annotator = '" + annotator + "' or rcsb_annotator = 'UNASSIGN' or " \
              + "rcsb_annotator is null) and " + date_hold_item + " != '0000-00-00' " \
              + "and " + date_hold_item + " <= DATE_ADD(curdate(), interval %d" % self.__cutoffday \
              + " day) order by structure_id"
        return self.__getSelectedIDList(query)

    def getRemindEntries(self, annotator):
        query = "select structure_id from rcsb_status where status_code in ('WAIT','PROC','REPL','AUTH','AUCO') " \
              + "and rcsb_annotator = '" + annotator + "' and initial_deposition_date <= " \
              + "DATE_SUB(curdate(), interval 14 day) order by structure_id"
        return self.__getSelectedIDList(query)

    def getThisWeekRelEntries(self, annotator):
        query = "select r.structure_id from rcsb_status r, PDB_status_information p " \
              + "where r.structure_id = p.structure_id and p.Revision_Date = '" \
              + self.__releaseDate + "' and (rcsb_annotator = '" + annotator \
              + "' or rcsb_annotator = 'UNASSIGN' or rcsb_annotator is null) order by structure_id"
        return self.__getSelectedIDList(query)

    def getThisForReleaseEntries(self, annotator):
        entry_list = []
        #
        pdbid_list = []
        for dir in ( 'added', 'modified', 'obsolete', 'reloaded' ):
            reloadDir = os.path.join(self.__cI.get('SITE_ARCHIVE_STORAGE_PATH'), 'for_release', dir)
            if not os.access(reloadDir, os.F_OK):
                continue
            #
            list = os.listdir(reloadDir)
            if not list:
                continue
            #
            for pdbid in list:
                if len(pdbid) == 4:
                    pdbid_list.append(pdbid)
                #
            #
        #
        if not pdbid_list:
            return entry_list
        #
        uniq_list = sorted(set(pdbid_list))
        id_string = ''
        for id in uniq_list:
            if id_string:
                id_string += ","
            id_string += "'" + id + "'"
        #
        query = "select structure_id, pdb_id, rcsb_annotator from rcsb_status where "
        if len(uniq_list) > 1:
            query += "pdb_id in (" + id_string + ") order by structure_id"
        else:
            query += "pdb_id = '" + id_string + "'"
        #
        rows = self.runSelectSQL(query)
        if rows:
            for row in rows:
                if 'structure_id' in row and (row['rcsb_annotator'] == None or \
                   str(row['rcsb_annotator']).upper() == annotator.upper() or \
                   str(row['rcsb_annotator']).upper() == 'UNASSIGN'):
                    entry_list.append(row['structure_id'])
                #
            #
        #
        return entry_list
        
    def getUnRelEntries(self, annotator):
        query = "select structure_id from rcsb_status where status_code not in ('OBS','WDRN','REL','PROC') " \
              + "and (rcsb_annotator = '" + annotator + "' or rcsb_annotator = 'UNASSIGN' or " \
              + "rcsb_annotator is null) and author_release_status_code = 'REL' order by structure_id"
        return self.__getSelectedIDList(query)

    def getAllHoldEntries(self, annotator):
        list = []
        for item in ('date_hold_coordinates', 'date_hold_struct_fact', \
                     'date_hold_nmr_constraints', 'date_hold_chemical_shifts'):
            list1 = self.getHoldEntries(item, annotator)
            if list1:
                list.extend(list1)
        #
        if not list:
            return list
        #
        uniq_list = sorted(set(list))
        return uniq_list

    def getRequestReleaseEntryList(self, annotator):
        query = "select structure_id from rcsb_status where (rcsb_annotator = '" + annotator \
              + "' or rcsb_annotator = 'UNASSIGN' or rcsb_annotator is null) and " \
              + "date_begin_release_preparation >= '" + self.__startDate \
              + "' and date_begin_release_preparation <= '" + self.__endDate + "' order by structure_id"
        return self.__getSelectedIDList(query)

    def getUnRelEntryInfo(self, annotator):
        id_list = []
        list = self.getAllHoldEntries(annotator)
        if list:
            id_list.extend(list)
        #
        list = self.getUnRelEntries(annotator)
        if list:
            id_list.extend(list)
        #
        return self.getEntryInfo(id_list)

    def getRequestReleaseEntryInfo(self, annotator):
        list = self.getRequestReleaseEntryList(annotator)
        return self.getEntryInfo(list)

    def getRelEntryId(self, annotator):
        id_list = self.getThisWeekRelEntries(annotator)
        reload_list = self.getThisForReleaseEntries(annotator)
        if reload_list:
            id_list.extend(reload_list)
            id_list = sorted(set(id_list))
        #
        return id_list

    def getRelEntryInfo(self, annotator):
        return self.getEntryInfo(self.getRelEntryId(annotator))

    def getAuthEntryInfo(self, annotator):
        id_list = self.getEntriesWithStatusList(annotator, "'AUTH'")
        return self.getEntryInfo(id_list)

    def getCitation(self, id):
        dir = {}
        query = "select title, publication journal_abbrev, volume_no journal_volume, year, " \
              + "first_page page_first, last_page page_last, pdbx_database_id_PubMed, " \
              + "pdbx_database_id_DOI " \
              + "from citation where structure_id = '" + id + "' and jrnl_serial_no = 1"

        try:
            self.__dbcon.commit()
            curs = self.__dbcon.cursor(MySQLdb.cursors.DictCursor)
            curs.execute(query)
            dir = curs.fetchone()
        except MySQLdb.Error as e:
            self.__lfh.write("Database error %d: %s\n" % (e.args[0], e.args[1]))
        return dir

    def getCitationInfo(self, id):
        query = "select title, publication journal_abbrev, volume_no journal_volume, year, " \
              + "first_page page_first, last_page page_last, pdbx_database_id_PubMed, " \
              + "pdbx_database_id_DOI, " \
              + "jrnl_serial_no from citation where structure_id = '" + id + "'"
        return self.runSelectSQL(query)

    def getCitationAuthorList(self, id, reformat):
        a_list = []
        query = "select citation_id, name, ordinal from citation_author " \
              + "where structure_id = '" + id + "' order by ordinal"
        rows = self.runSelectSQL(query)
        if rows:
            for row in rows:
                if 'name' not in row:
                    continue
                #
                if reformat:
                    list = row['name'].split(',')
                    if len(list) == 2:
                        s1 = list[0].strip()
                        if not s1:
                            continue
                        #
                        s2 = list[1].strip()
                        if not s2:
                            continue
                        #
                        if s2[-1] == '.':
                            row['name'] = s2 + s1
                        else:
                            row['name'] = s2 + "." + s1
                        # 
                    #
                #
                a_list.append(row)
            #
        #
        return a_list

    def getCitationAuthor(self, id):
        list1 = []
        list2 = []
        query = "select structure_id,name,ordinal from citation_author " \
              + "where structure_id = '" + id + "' and citation_id = 'primary' " \
              + "order by ordinal"
        rows = self.runSelectSQL(query)
        if rows:
            for row in rows:
                if 'name' not in row:
                    continue
                #
                list = row['name'].split(',')
                if len(list) == 2:
                    s1 = list[0].strip()
                    if not s1:
                        continue
                    #
                    s2 = list[1].strip()
                    if not s2:
                        continue
                    #
                    if s2[-1] == '.':
                        list1.append(s2 + s1)
                    else:
                        list1.append(s2 + "." + s1)
                    # 
                    # Construct Pubmed search format author
                    initial = ''
                    for c in s2:
                        if c == '.' or c == '-' or c == ' ':
                            continue
                        initial += c
                        if len(initial) == 2:
                            break
                        #
                    #
                    lst = s1.split(' ')
                    if len(lst) > 1:
                        suffix = lst[-1].upper()
                        if suffix == 'SR' or suffix == 'JR':
                            lst.pop()
                        #
                        if len(lst) > 1:
                            s1 = '+'.join(lst)
                        else:
                            s1 = lst[0]
                    #
                    list2.append(s1 + '+' + initial + '[au]')
                #else:
                #    list1.append(row['name'])
            #
        #
        return list1,list2

    def getPubmedSearchList(self):
        query = "select r.structure_id, r.rcsb_annotator, r.status_code, r.pdb_id, r.title, " \
              + "c.title c_title, c.publication journal_abbrev, c.volume_no journal_volume, " \
              + "c.first_page page_first, c.last_page page_last, c.year, " \
              + "c.pdbx_database_id_PubMed, c.pdbx_database_id_DOI, r.author_approval_type " \
              + "from rcsb_status r, citation c where c.structure_id = r.structure_id and " \
              + "r.exp_method != 'theoretical model' and c.jrnl_serial_no = 1 and " \
              + "r.initial_deposition_date >= DATE_SUB(curdate(), interval 730 day) and " \
              + "r.status_code in ('HOLD','HPUB','AUTH','POLC','REPL','REL','PROC','WAIT') and " \
              + "(c.publication = 'TO BE PUBLISHED' or c.publication = '' or c.publication is null or " \
              + "c.first_page = '' or c.first_page is null or c.volume_no = '' or c.volume_no is null) " \
              + "order by r.structure_id"
        #
        list = self.runSelectSQL(query)
        if list:
            for row in list:
                if 'structure_id' in row:
                    list1,list2 = self.getCitationAuthor(row['structure_id'])
                    if list1:
                        row['citation_author'] = list1
                        row['pubmed_author'] = list2
                    #
                #
            #
        #
        return list
  
    def getPreviousStatusCode(self, id_list):
        dir = {}
        if not id_list:
            return dir
        #
        uniq_list = sorted(set(id_list))

        id_string = ''
        for id in uniq_list:
            if id_string:
                id_string += ","
            id_string += "'" + id + "'"
        #

        query = "select structure_id,status_code from pdb_entry_tmp " \
              + "where structure_id in (" + id_string + ") order by structure_id"
        list = self.runSelectSQL(query)
        if list:
            for d in list:
                if 'structure_id' not in d or 'status_code' not in d:
                    continue
                #
                dir[d['structure_id']] = d['status_code']
            #
        #
        return dir

    def getPDBID(self, depid):
        pdbid = self.__getPDBID(depid)
        if pdbid:
            return pdbid
        #
        list = self.__getEntryInfo_from_pdbx_depui_entry_details("'" + depid + "'")
        if list:
            return 'EM_MAP ONLY'
        #
        return ''

    def __getPDBID(self, depid):
        pdbid = ''
        query = "select pdb_id from rcsb_status where structure_id = '" + depid + "'"
        list = self.runSelectSQL(query)
        if list and 'pdb_id' in list[0]:
            pdbid = list[0]['pdb_id']
        #
        return pdbid

    def getDepID(self, pdbid):
        depid = ''
        query = "select structure_id from rcsb_status where pdb_id = '" + pdbid + "'"
        list = self.runSelectSQL(query)
        if list and 'structure_id' in list[0]:
            depid = list[0]['structure_id']
        #
        return depid

    def getEntryInfo(self, id_list):
        list = []
        if not id_list:
            return list
        #
        uniq_list = sorted(set(id_list))

        id_string = ''
        for id in uniq_list:
            if id_string:
                id_string += ","
            id_string += "'" + id + "'"
        #

        obsprMap1 = self.getObsSprInfo(id_string)
        obsprMap2 = self.getObsSprInfo2(id_string)
        obsprMap = self.__mergeObsSprInfo(obsprMap1, obsprMap2)

        rcsb_list = self.__getEntryInfo_from_rcsb_status(id_string)
        em_list = self.__getEntryInfo_from_pdbx_depui_entry_details(id_string)
        list = self.__mergeEntryList(rcsb_list, em_list)

        for dir in list:
            if dir['structure_id'] not in obsprMap:
                continue
            #
            dir['obspr'] = obsprMap[dir['structure_id']]
        #
        return list

    def __getEntryInfo_from_rcsb_status(self, id_string):
        query = "select structure_id,pdb_id,author_release_status_code,status_code,rcsb_annotator," \
              + "date_hold_coordinates,date_hold_struct_fact,date_hold_nmr_constraints,title," \
              + "recvd_coordinates,recvd_struct_fact,recvd_nmr_constraints,recvd_chemical_shifts," \
              + "date_hold_chemical_shifts,status_code_sf,status_code_mr,status_code_cs," \
              + "author_approval_type,initial_deposition_date,exp_method,author_list,date_of_RCSB_release," \
              + "date_of_sf_release,date_of_mr_release,date_of_cs_release from " \
              + "rcsb_status where structure_id in (" + id_string + ") order by structure_id"
        return self.runSelectSQL(query)

    def __getEntryInfo_from_pdbx_depui_entry_details(self, id_string):
        list = []
        query = "select structure_id,requested_accession_types from pdbx_depui_entry_details where structure_id in (" \
              + id_string + ") order by structure_id"
        ret_list = self.runSelectSQL(query)
        if ret_list:
            for dir in ret_list:
                if 'requested_accession_types' in dir and dir['requested_accession_types'].upper().find('EMDB') != -1:
                    dir1 = {}
                    dir1['structure_id'] = dir['structure_id']
                    dir1['recvd_em_map'] = 'Y'
                    list.append(dir1)
                #
            #
        #
        return list

    def __mergeEntryList(self, rcsb_list, em_list):
        rcsb_id_list,rcsb_map = self.__getIDLIST_IDMAP(rcsb_list)
        em_id_list,em_map = self.__getIDLIST_IDMAP(em_list)
        all_id_list = []
        for id in rcsb_id_list:
            all_id_list.append(id)
        #
        for id in em_id_list:
            all_id_list.append(id)
        #
        list = []
        if not all_id_list:
            return list
        #
        em_status_code_map = self.__getEMStatusCodeInfo(em_id_list)
        #
        unique_id = sorted(set(all_id_list))
        for id in unique_id:
            if id in rcsb_map:
                dir = rcsb_map[id]
                if 'author_list' in dir:
                    dir['author_list'] = self.__processAuthorList(dir['author_list'])
                #
                if ('pdb_id' not in dir) or (not dir['pdb_id']):
                    if 'status_code' in dir:
                        del dir['status_code']
                    #
                #
                if id in em_map:
                    dir['recvd_em_map'] = em_map[id]['recvd_em_map']
                    if id in em_status_code_map:
                        for item in ( 'status_code_em', 'date_of_EM_release' ):
                            if item in em_status_code_map[id]:
                                dir[item] = em_status_code_map[id][item]
                            #
                        #
                        if ('pdb_id' not in dir) or (not dir['pdb_id']):
                            for item in ( 'title', 'author_list' ):
                                if item in em_status_code_map[id] and em_status_code_map[id][item]:
                                    dir[item] = em_status_code_map[id][item]
                                #
                            #
                        #
                    #
                #
                list.append(dir)
            elif id in em_map:
                if id in em_status_code_map:
                    for item in ( 'status_code_em', 'date_of_EM_release' ):
                        if item in em_status_code_map[id]:
                            em_map[id][item] = em_status_code_map[id][item]
                        #
                    #
                #
                list.append(em_map[id])
            #
        #
        return list

    def __getIDLIST_IDMAP(self, list):
        id_list = []
        id_map = {}
        for dir in list:
            id_list.append(dir['structure_id'])
            id_map[dir['structure_id']] = dir
        #
        return id_list,id_map

    def __getEMStatusCodeInfo(self, id_list):
        map = {}
        if not id_list:
            return map
        #
        id_string = ''
        for id in id_list:
            if id_string:
                id_string += ","
            id_string += "'" + id + "'"
        #

        query = "select structure_id, current_status status_code_em, map_release_date date_of_EM_release, title, author_list from em_admin " \
              + "where structure_id in (" + id_string + ") order by structure_id"
        list = self.runSelectSQL(query)
        if list:
            for d in list:
                if 'structure_id' not in d or 'status_code_em' not in d or not d['structure_id'] or not d['status_code_em']:
                    continue
                #
                if 'author_list' in d:
                    d['author_list'] = self.__processAuthorList(d['author_list'])
                #
                map[d['structure_id']] = d
            #
        #
        return map

    def __processAuthorList(self, author_list):
        org_authors = author_list
        authors = str(author_list).replace('?', '').replace(',', '').strip()
        if not authors:
            return ''
        #
        return org_authors

    def __mergeObsSprInfo(self, obsprMap1, obsprMap2):
        if (not obsprMap1) and (not obsprMap2):
            return {}
        elif obsprMap1 and (not obsprMap2):
            return obsprMap1
        elif (not obsprMap1) and obsprMap2:
            return obsprMap2
        #
        for k,list in obsprMap2.items():
            if k in obsprMap1:
                found = False
                for dir in obsprMap1[k]:
                    if dir['pdb_id'] == list[0]['pdb_id']:
                        found = True
                        replace_id = dir['relace_pdb_id'] + ' ' + list[0]['relace_pdb_id']
                        tmp_list = replace_id.replace(',', ' ').split(' ')
                        relace_id_list = []
                        for id in tmp_list:
                            if not id:
                                continue
                            #
                            relace_id_list.append(id)
                        #
                        uniq_list = sorted(set(relace_id_list))
                        dir['relace_pdb_id'] = ' '.join(uniq_list)
                    #
                #
                if not found:
                    obsprMap1[k].append(list[0])
                #
            else:
                obsprMap1[k] = list
            #
        #
        return obsprMap1

    def getObsSprInfo(self, id_string):
        map = {}
        #
        query = "select structure_id,id,pdb_id,relace_pdb_id from pdbx_database_PDB_obs_spr " \
              + "where structure_id in (" + id_string + ") order by structure_id"
        list = self.runSelectSQL(query)
        if list:
            for dir in list:
                if ('pdb_id' not in dir) or ('structure_id' not in dir) or \
                   ('relace_pdb_id' not in dir):
                    continue
                #
                pdb_id = str(dir['pdb_id'])
                if pdb_id.upper() == 'NONE':
                    pdb_id = ''
                relace_pdb_id = str(dir['relace_pdb_id'])
                if (not pdb_id) or (not relace_pdb_id):
                    continue
                #
                dir1 = {}
                dir1['pdb_id'] = pdb_id
                dir1['relace_pdb_id'] = relace_pdb_id
                if dir['structure_id'] in map:
                    map[dir['structure_id']].append(dir1)
                else:
                    list1 = []
                    list1.append(dir1)
                    map[dir['structure_id']] = list1
                #
            #
        #
        return map

    def getObsSprInfo2(self, id_string):
        map = {}
        #
        query = "select structure_id,replace_pdb_id from pdbx_depui_entry_details " \
              + "where structure_id in (" + id_string + ") order by structure_id"
        list = self.runSelectSQL(query)
        if list:
            for dir in list:
                if ('structure_id' not in dir) or ('replace_pdb_id' not in dir):
                    continue
                #
                pdb_id = self.getPDBID(str(dir['structure_id']))
                relace_pdb_id = str(dir['replace_pdb_id'])
                if (not pdb_id) or (pdb_id == 'EM_MAP ONLY') or (not relace_pdb_id) or (relace_pdb_id == 'None'):
                    continue
                #
                dir1 = {}
                dir1['pdb_id'] = pdb_id
                dir1['relace_pdb_id'] = relace_pdb_id
                list1 = []
                list1.append(dir1)
                map[dir['structure_id']] = list1
                #
            #
        #
        return map

if __name__ == '__main__':
    c=DBUtil(siteId='WWPDB_DEPLOY_TEST_RU', verbose=True, log=sys.stderr)
    query = "select structure_id, rcsb_annotator, pdb_id from rcsb_status where structure_id = 'D_8000200904'"
    list = c.runSelectSQL(query)
    #list = c.getEntryInfo('D_8000200904')
    #list = c.getPubmedSearchList()
    #list = c.getRequestReleaseEntryList('JY')
    #print str(len(list))
    #print list[0]
    #dir = c.getCitation('RCSB079557')
    #print dir
    #list = c.getThisWeekRelEntries('CS')
    #print list
    #dir = c.getPreviousStatusCode([ 'RCSB057158', 'RCSB079243', 'RCSB079395', 'RCSB079656' ])
    #print dir
    #list = c.getRelEntryInfo('CS')
    print(list)
    #dir = c.getRequestReleaseEntryInfo('JY')
    #print dir
    #print len(dir)
