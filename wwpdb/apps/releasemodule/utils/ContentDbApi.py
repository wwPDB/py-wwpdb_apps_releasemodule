##
# File:  ContentDbApi.py
# Date:  23-Sept-2016
# Updates:
##
"""
Providing addintaional APIs for WFE to get info from local database.

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2016 wwPDB

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
#
from wwpdb.utils.config.ConfigInfo import ConfigInfo
from wwpdb.apps.releasemodule.utils.DbApiUtil import DbApiUtil
from wwpdb.apps.releasemodule.utils.TimeUtil import TimeUtil


class ContentDbApi(object):
    """
    """
    __schemaMap = {
        "SELECT_PDB_ENTRY_BY_STATUS" : "select structure_id from rcsb_status where (rcsb_annotator = '%s' or rcsb_annotator = 'UNASSIGN' or "
                                     + "rcsb_annotator is null) and status_code in ( '%s' ) and pdb_id is not null order by structure_id",
        "SELECT_EM_ONLY_ENTRY_BY_STATUS" : "select r.structure_id from rcsb_status r, em_admin e where r.structure_id = e.structure_id and "
                                         + "( r.rcsb_annotator = '%s' or r.rcsb_annotator = 'UNASSIGN' or r.rcsb_annotator is null) and "
                                         + "e.current_status in ( '%s' )",
        "SELECT_ALL_EM_ONLY_ENTRY_BY_STATUS" : "select r.structure_id from rcsb_status r, em_admin e where r.structure_id = e.structure_id and "
                                             + "e.current_status in ( '%s' )",
        "SELECT_ENTRY_BY_AUDIT_AUTHOR" : "select r.structure_id from rcsb_status r, audit_author a where r.structure_id = a.structure_id "
                                       + "and (r.rcsb_annotator = '%s' or r.rcsb_annotator = 'UNASSIGN' or r.rcsb_annotator is null) and "
                                       + "%s order by structure_id",
        "SELECT_THIS_WEEK_RELEASE" : "select r.structure_id from rcsb_status r, PDB_status_information p where r.structure_id = p.structure_id and "
                                   + "p.Revision_Date = '%s' and (r.rcsb_annotator = '%s' or r.rcsb_annotator = 'UNASSIGN' or r.rcsb_annotator is "
                                   + "null) order by structure_id",
        "SELECT_REQUEST_RELEASE" : "select structure_id from rcsb_status where (rcsb_annotator = '%s' or rcsb_annotator = 'UNASSIGN' or "
                                 + "rcsb_annotator is null) and date_begin_release_preparation >= '%s' and date_begin_release_preparation "
                                 + "<= '%s' order by structure_id",
        "SELECT_ALL_CITATION" : "select title, publication journal_abbrev, volume_no journal_volume, year, first_page page_first, "
                              + "last_page page_last, pdbx_database_id_PubMed, pdbx_database_id_DOI, jrnl_serial_no from citation where structure_id = '%s'",
        "SELECT_PRIMARY_CITATION" : "select title, publication journal_abbrev, volume_no journal_volume, year, first_page page_first, "
                                  + "last_page page_last, pdbx_database_id_PubMed, pdbx_database_id_DOI from citation where "
                                  + "structure_id = '%s' and jrnl_serial_no = 1",
        "SELECT_ALL_CITATION_AUTHOR" : "select citation_id, name, identifier_ORCID orcid, ordinal from citation_author where structure_id = '%s' order by ordinal",
        "SELECT_PRIMARY_CITATION_AUTHOR" : "select name, ordinal from citation_author where structure_id = '%s' and citation_id = 'primary' order by ordinal",
        "SELECT_PUBMED_SEARCH_LIST" : "select r.structure_id, r.rcsb_annotator, r.status_code, r.post_rel_status, r.post_rel_recvd_coord, r.post_rel_recvd_coord_date, r.pdb_id, r.title, c.title c_title, "
                                    + "c.publication journal_abbrev, c.volume_no journal_volume, c.first_page page_first, c.last_page page_last, "
                                    + "c.year, c.pdbx_database_id_PubMed, c.pdbx_database_id_DOI, r.author_approval_type from rcsb_status r, "
                                    + "citation c where c.structure_id = r.structure_id and r.exp_method != 'theoretical model' and "
                                    + "c.jrnl_serial_no = 1 and r.initial_deposition_date >= DATE_SUB(curdate(), interval %d day) and "
                                    + "r.status_code in ('HOLD','HPUB','AUTH','POLC','REPL','REL','PROC','WAIT') and (c.publication = "
                                    + "'TO BE PUBLISHED' or c.publication = '' or c.publication is null or c.first_page = '' or c.first_page "
                                    + "is null or c.volume_no = '' or c.volume_no is null or c.pdbx_database_id_PubMed = '' or "
                                    + "c.pdbx_database_id_PubMed is null) order by r.structure_id",
        "SELECT_ENTRY_INFO" : "select structure_id,pdb_id,author_release_status_code,status_code,post_rel_status,post_rel_recvd_coord,post_rel_recvd_coord_date,rcsb_annotator,date_hold_coordinates,"
                            + "date_hold_struct_fact,date_hold_nmr_constraints,title,recvd_coordinates,recvd_struct_fact,recvd_nmr_constraints,"
                            + "recvd_chemical_shifts,date_hold_chemical_shifts,status_code_sf,status_code_mr,status_code_cs,author_approval_type,"
                            + "initial_deposition_date,exp_method,author_list,date_of_RCSB_release,date_of_sf_release,date_of_mr_release,"
                            + "status_code_nmr_data,recvd_nmr_data,date_nmr_data,date_hold_nmr_data,dep_release_code_nmr_data,date_of_nmr_data_release,"
                            + "date_of_cs_release from rcsb_status where structure_id in ( '%s' ) order by structure_id",
        "SELECT_EM_INFO" : "select structure_id, current_status status_code_em, map_release_date date_of_EM_release, last_update last_EM_release_date, "
                         + "title title_emdb, author_list author_list_emdb from em_admin where structure_id in ( '%s' ) order by structure_id",
        "SELECT_REQUESTED_ACCESSION_TYPES" : "select structure_id, requested_accession_types from pdbx_depui_entry_details "
                         + "where structure_id in ( '%s' ) order by structure_id",
        "SELECT_PDBX_OBS_SPR_INFO" : "select structure_id,id,pdb_id,date,details,relace_pdb_id replace_pdb_id from pdbx_database_PDB_obs_spr where structure_id "
                                   + "in ( '%s' ) order by structure_id",
        "SELECT_DEPUI_OBS_SPR_INFO" : "select structure_id,replace_pdb_id from pdbx_depui_entry_details "
                                    + "where structure_id in ( '%s' ) order by structure_id",
        "SELECT_LAST_PDBX_AUDIT_REVISION_HISTORY" : "select structure_id, ordinal, revision_date from pdbx_audit_revision_history where "
                                                  + "structure_id = '%s' order by ordinal desc limit 1",
        "SELECT_ALL_EXPIRED_PDB_ENTRY" : "select structure_id from rcsb_status where ( initial_deposition_date <= DATE_SUB( curdate(), interval 365 day ) ) and (pdb_id != '') "
                                       + "and (pdb_id is not null) and ( status_code in ( 'AUTH', 'HPUB', 'HOLD' ) ) and ( ( date_hold_coordinates is null ) or "
                                       + " ( date_hold_coordinates < curdate() ) ) order by structure_id",
        "SELECT_ALL_EXPIRED_EM_ENTRY" : "select r.structure_id from rcsb_status r, em_admin e where (r.structure_id = e.structure_id) and "
                                      + "((r.pdb_id is null) or (r.pdb_id = '')) and (e.deposition_date <= DATE_SUB( curdate(), interval 365 day ) ) and "
                                      + "(e.current_status in ( 'AUTH', 'HPUB', 'HOLD' ) ) and ( ( e.map_hold_date is null ) or "
                                      + " ( e.map_hold_date < curdate() ) ) order by r.structure_id",
        "SELECT_EXPIRED_PDB_ENTRY_BY_ANNOTATOR" : "select structure_id from rcsb_status where ( rcsb_annotator = '%s' ) and (pdb_id is not null) and (pdb_id != '') and "
                                                + "( initial_deposition_date <= DATE_SUB( curdate(), interval 365 day ) ) and "
                                                + "( status_code in ( 'AUTH', 'HPUB', 'HOLD' ) ) and ( ( date_hold_coordinates is null ) or "
                                                + "( date_hold_coordinates < curdate() ) ) order by structure_id",
        "SELECT_EXPIRED_EM_ENTRY_BY_ANNOTATOR" : "select r.structure_id from rcsb_status r, em_admin e where (r.structure_id = e.structure_id) and "
                                               + "(r.rcsb_annotator = '%s' ) and ((r.pdb_id is null) or (r.pdb_id = '')) and "
                                               + "(e.deposition_date <= DATE_SUB( curdate(), interval 365 day ) ) and "
                                               + "(e.current_status in ( 'AUTH', 'HPUB', 'HOLD' ) ) and ( ( e.map_hold_date is null ) or "
                                               + " ( e.map_hold_date < curdate() ) ) order by r.structure_id",
        "SELECT_EMDB_ID_FROM_DATABASE_2" : "select database_code from database_2 where Structure_ID = '%s' and database_id = 'EMDB'",
        "SELECT_ENTRY_ID_FROM_DATABASE_2" : "select Structure_ID from database_2 where database_code = '%s' and database_id = 'EMDB'",
        "SELECT_EMDB_ID_FROM_DATABASE_RELATED" : "select db_id from pdbx_database_related where Structure_ID = '%s' and db_name = 'EMDB' and content_type = 'associated EM volume'",
    }
    #

    def __init__(self, siteId=None, verbose=False, log=sys.stderr):
        """
           connect to local database
        """
        self.__lfh = log
        self.__verbose = verbose
        self.__siteId = siteId
        self.__cI = ConfigInfo(self.__siteId)
        self.__dbServer = self.__cI.get("SITE_DB_SERVER")
        self.__dbHost = self.__cI.get("SITE_DB_HOST_NAME")
        self.__dbName = "da_internal"
        self.__dbUser = self.__cI.get("SITE_DB_USER_NAME")
        self.__dbPw = self.__cI.get("SITE_DB_PASSWORD")
        self.__dbSocket = self.__cI.get("SITE_DB_SOCKET")
        self.__dbPort = int(self.__cI.get("SITE_DB_PORT_NUMBER"))
        #
        self.__dbApi = DbApiUtil(dbServer=self.__dbServer, dbHost=self.__dbHost, dbName=self.__dbName, dbUser=self.__dbUser, dbPw=self.__dbPw,
                                 dbSocket=self.__dbSocket, dbPort=self.__dbPort, verbose=self.__verbose, log=self.__lfh)
        self.__dbApi.setSchemaMap(self.__schemaMap)
        #
        t = TimeUtil()
        self.__startDate = t.StartDay()
        self.__endDate = t.EndDay()
        self.__releaseDate = t.NextWednesday()

    def getEntriesWithStatusList(self, annotator, status_list):
        pdb_entries = self.__getSelectedIDList('SELECT_PDB_ENTRY_BY_STATUS', (annotator, status_list))
        em_map_only_entries = self.__getSelectedIDList('SELECT_EM_ONLY_ENTRY_BY_STATUS', (annotator, status_list))
        if em_map_only_entries:
            pdb_entries.extend(em_map_only_entries)
            pdb_entries = sorted(set(pdb_entries))
        #
        return pdb_entries

    def getEntriesWithAuthorName(self, annotator, name):
        name1 = name.strip()
        query_string = "a.name = '" + name1 + "'"
        if name1.find(',') != -1:
            nlist = name1.split(',')
            a1 = nlist[0].strip()
            a2 = nlist[1].strip()
            name1 = a1 + ',' + a2
            name2 = a1 + ', ' + a2
            query_string = "(a.name = '" + name1 + "' or a.name = '" + name2 + "')"
        #
        entries = self.__getSelectedIDList('SELECT_ENTRY_BY_AUDIT_AUTHOR', (annotator, query_string))
        if entries:
            entries = sorted(set(entries))
        #
        return entries

    def getThisWeekRelEntries(self, annotator):
        return self.__getSelectedIDList('SELECT_THIS_WEEK_RELEASE', (self.__releaseDate, annotator))

    def getRequestReleaseEntryList(self, annotator):
        return self.__getSelectedIDList('SELECT_REQUEST_RELEASE', (annotator, self.__startDate, self.__endDate))

    def getExpiredEntryList(self, annotator):
        if annotator.strip().upper() == "ALL":
            pdbList = self.__getSelectedIDList('SELECT_ALL_EXPIRED_PDB_ENTRY', ())
            emList = self.__getSelectedIDList('SELECT_ALL_EXPIRED_EM_ENTRY', ())
            pdbList.extend(emList)
            return sorted(set(pdbList))
        else:
            pdbList = self.__getSelectedIDList('SELECT_EXPIRED_PDB_ENTRY_BY_ANNOTATOR', (annotator))
            emList = self.__getSelectedIDList('SELECT_EXPIRED_EM_ENTRY_BY_ANNOTATOR', (annotator))
            pdbList.extend(emList)
            return sorted(set(pdbList))

    def getCitation(self, entry_id):
        rows = self.__dbApi.selectData(key='SELECT_PRIMARY_CITATION', parameter=(entry_id))
        if rows:
            return rows[0]
        #
        return {}

    def getPrimaryCitation(self, entry_id):
        return self.getCitation(entry_id)

    def getPrimaryCitationAuthorList(self, entry_id):
        list1, _list2 = self.__getCitationAuthor(entry_id)
        return list1

    def getCitationInfo(self, entry_id):
        return self.__dbApi.selectData(key='SELECT_ALL_CITATION', parameter=(entry_id))

    def getCitationAuthorList(self, entry_id):
        return self.__dbApi.selectData(key='SELECT_ALL_CITATION_AUTHOR', parameter=(entry_id))

    def getPubmedSearchList(self, year=2):
        em_map_only_entries = self.__getSelectedIDList('SELECT_ALL_EM_ONLY_ENTRY_BY_STATUS', ('OBS'))
        rows = self.__dbApi.selectData(key='SELECT_PUBMED_SEARCH_LIST', parameter=(year * 365))
        retList = []
        if rows:
            for row in rows:
                if ('structure_id' in row) and row['structure_id']:
                    if (('pdb_id' not in row) or (not row['pdb_id'])) and (row['structure_id'] in em_map_only_entries):
                        continue
                    #
                    list1, list2 = self.__getCitationAuthor(row['structure_id'])
                    if list1:
                        row['citation_author'] = list1
                        row['pubmed_author'] = list2
                    #
                #
                retList.append(row)
            #
        #
        return retList

    def getEntryInfo(self, id_string):
        rows = self.__dbApi.selectData(key='SELECT_ENTRY_INFO', parameter=(id_string))
        if rows:
            emReleaseDateMap = {}
            em_rows = self.__dbApi.selectData(key='SELECT_EM_INFO', parameter=(id_string))
            if em_rows:
                for row in em_rows:
                    if ('structure_id' not in row) or (not row['structure_id']) or ('date_of_EM_release' not in row) or (not row['date_of_EM_release']):
                        continue
                    #
                    myD = {}
                    lastReleasedate = 'n.a.'
                    if ('last_EM_release_date' in row) and row['last_EM_release_date']:
                        lastReleasedate = str(row['last_EM_release_date']).replace(' 00:00:00', '')
                        myD['last_release_date'] = lastReleasedate
                    #
                    myD['release_dates'] = str(row['date_of_EM_release']).replace(' 00:00:00', '') + ' / ' + lastReleasedate
                    emReleaseDateMap[row['structure_id']] = myD
                #
            #
            for row in rows:
                if ('structure_id' not in row) or (not row['structure_id']):
                    continue
                #
                if ('pdb_id' in row) and row['pdb_id']:
                    lastReleasedate = self.getLastReleaseDate(row['structure_id'])
                    if ('date_of_RCSB_release' in row) and row['date_of_RCSB_release'] and lastReleasedate:
                        row['release_dates'] = str(row['date_of_RCSB_release']) + ' / ' + lastReleasedate
                        row['last_release_date'] = lastReleasedate
                    elif ('date_of_RCSB_release' in row) and row['date_of_RCSB_release']:
                        row['release_dates'] = str(row['date_of_RCSB_release']) + ' / n.a.'
                    elif lastReleasedate:
                        row['release_dates'] = 'n.a. / ' + lastReleasedate
                        row['last_release_date'] = lastReleasedate
                    #
                elif row['structure_id'] in emReleaseDateMap:
                    for item in ('release_dates', 'last_release_date'):
                        if (item in emReleaseDateMap[row['structure_id']]) and emReleaseDateMap[row['structure_id']][item]:
                            row[item] = emReleaseDateMap[row['structure_id']][item]
                        #
                    #
                #
            #
        #
        return rows

    def getEMInfo(self, id_string):
        return self.__dbApi.selectData(key='SELECT_EM_INFO', parameter=(id_string))

    def getRequestedInfo(self, id_string):
        return self.__dbApi.selectData(key='SELECT_REQUESTED_ACCESSION_TYPES', parameter=(id_string))

    def getPdbxObsSprInfo(self, id_string):
        return self.__dbApi.selectData(key='SELECT_PDBX_OBS_SPR_INFO', parameter=(id_string))

    def getDepuiObsSprInfo(self, id_string):
        return self.__dbApi.selectData(key='SELECT_DEPUI_OBS_SPR_INFO', parameter=(id_string))

    def getLastPdbxAuditRevisionHistory(self, entryid):
        return self.__dbApi.selectData(key='SELECT_LAST_PDBX_AUDIT_REVISION_HISTORY', parameter=(entryid))

    def getLastReleaseDate(self, entryid):
        release_date = ''
        rows = self.__dbApi.selectData(key='SELECT_LAST_PDBX_AUDIT_REVISION_HISTORY', parameter=(entryid))
        if rows and ('revision_date' in rows[0]) and rows[0]['revision_date']:
            release_date = str(rows[0]['revision_date'])
        #
        return release_date

    def getAssoicatedEmdId(self, entryid):
        emdIdList = self.__getSelectedIDList('SELECT_EMDB_ID_FROM_DATABASE_2', (entryid), item='database_code')
        emdIdList1 = self.__getSelectedIDList('SELECT_EMDB_ID_FROM_DATABASE_RELATED', (entryid), item='db_id')
        for emdId in emdIdList1:
            if emdId not in emdIdList:
                emdIdList.append(emdId)
            #
        #
        return emdIdList

    def getNotReleasedAssoicatedEmdId(self, entryid):
        emdIdList = []
        possibleEmdIdList = self.getAssoicatedEmdId(entryid)
        if not possibleEmdIdList:
            return emdIdList
        #
        for emdId in possibleEmdIdList:
            isReleased = False
            structureIdList = self.__getSelectedIDList('SELECT_ENTRY_ID_FROM_DATABASE_2', (emdId), item='Structure_ID')
            for structureId in structureIdList:
                if structureId == entryid:
                    continue
                #
                em_rows = self.getEMInfo(structureId)
                if (len(em_rows) == 1) and ('structure_id' in em_rows[0]) and (em_rows[0]['structure_id'] == structureId) and \
                   ('status_code_em' in em_rows[0]) and (em_rows[0]['status_code_em'] == 'REL'):
                    isReleased = True
                    break
                #
            #
            if isReleased:
                continue
            #
            emdIdList.append(emdId)
        #
        return emdIdList

    def __getSelectedIDList(self, key, parameter, item='structure_id'):
        idlist = []
        rows = self.__dbApi.selectData(key=key, parameter=parameter)
        if rows:
            for row in rows:
                if (item in row) and row[item]:
                    idlist.append(row[item])
                #
            #
        #
        return idlist

    def __getCitationAuthor(self, entry_id):
        list1 = []
        list2 = []
        rows = self.__dbApi.selectData(key='SELECT_PRIMARY_CITATION_AUTHOR', parameter=(entry_id))
        if rows:
            for row in rows:
                if 'name' not in row:
                    continue
                #
                t_list = row['name'].split(',')
                if len(t_list) == 2:
                    s1 = t_list[0].strip()
                    if not s1:
                        continue
                    #
                    s2 = t_list[1].strip()
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
                #
            #
        #
        return list1, list2


def test_main():
    siteId = os.getenv('WWPDB_SITE_ID')
    c = ContentDbApi(siteId=siteId, verbose=True, log=sys.stderr)
    # print c.getEntriesWithStatusList(sys.argv[1], sys.argv[2])
    # print c.getPubmedSearchList()
    # """
    # print c.getThisWeekRelEntries(sys.argv[1])
    # print c.getRequestReleaseEntryList(sys.argv[1])
    # print c.getCitation(sys.argv[2])
    # print c.getCitationInfo(sys.argv[2])
    # print c.getCitationAuthorList(sys.argv[2])
    # print((c.getLastPdbxAuditRevisionHistory(sys.argv[1])))
    # print((c.getLastReleaseDate(sys.argv[1])))
    # """
    print(c.getNotReleasedAssoicatedEmdId(sys.argv[1]))


if __name__ == '__main__':
    test_main()
