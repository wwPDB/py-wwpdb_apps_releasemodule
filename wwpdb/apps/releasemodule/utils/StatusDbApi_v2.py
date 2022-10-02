##
# File:  StatusDbApi.py
# Date:  24-Sept-2016
# Updates:
##
"""
Providing addintaional APIs for WFE to get info from status database.

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


import sys

from wwpdb.utils.config.ConfigInfo import ConfigInfo
from wwpdb.apps.releasemodule.utils.DbApiUtil import DbApiUtil


class StatusDbApi(object):
    __schemaMap = {
        "COUNT" : "select count(*) from %s",
        "CHECK_TABLE_EXIST" : "select distinct table_name from  information_schema.tables where table_schema = '%s' and table_name = '%s'",
        "GET_ALL_ANNO_INITIALS" : "select initials from da_users where active = 0",
        "GET_SITE_ANNO_INITIALS" : "select initials from da_users where active = 0 and da_group_id = '%s'",
        "GET_DA_GROUP_ID"   : "select da_group_id from da_group where code = '%s' and site = '%s'",
        "GET_ENTRY_LIST"    : "select dep_set_id,pdb_id,emdb_id,bmrb_id,status_code,author_release_status_code,status_code_emdb status_code_em,"
                              + "dep_author_release_status_code_emdb author_release_status_code_em,locking,notify,title,title_emdb,author_list,"
                              + "author_list_emdb from deposition where %s",
        "GET_ENTRY_LIST_FROM_GROUP" : "select dep_set_id,group_id from group_deposition_information where group_id in ( '%s' ) order by dep_set_id",
        "GET_MAJOR_ISSUE_ENTRY_LIST" : "select dep_set_id from remind_message_track where major_issue != '' and dep_set_id in ( '%s' )"
    }
    #
    """
    """
    def __init__(self, siteId=None, verbose=False, log=sys.stderr):
        """
        """
        self.__lfh = log
        self.__verbose = verbose
        self.__siteId = siteId
        self.__cI = ConfigInfo(self.__siteId)
        self.__dbServer = self.__cI.get("SITE_DB_SERVER")
        self.__dbHost = self.__cI.get("SITE_DB_HOST_NAME")
        self.__dbName = self.__cI.get("SITE_DB_DATABASE_NAME")
        self.__dbUser = self.__cI.get("SITE_DB_USER_NAME")
        self.__dbPw = self.__cI.get("SITE_DB_PASSWORD")
        self.__dbSocket = self.__cI.get("SITE_DB_SOCKET")
        self.__dbPort = int(self.__cI.get("SITE_DB_PORT_NUMBER"))
        #
        self.__dbApi = DbApiUtil(dbServer=self.__dbServer, dbHost=self.__dbHost, dbName=self.__dbName, dbUser=self.__dbUser, dbPw=self.__dbPw,
                                 dbSocket=self.__dbSocket, dbPort=self.__dbPort, verbose=self.__verbose, log=self.__lfh)
        self.__dbApi.setSchemaMap(self.__schemaMap)

    def runUpdate(self, table=None, where=None, data=None):
        return self.__dbApi.runUpdate(table=table, where=where, data=data)

    def isTableExist(self, table=None):
        if not table:
            return False
        #
        ret_list = self.__dbApi.selectData(key="CHECK_TABLE_EXIST", parameter=(self.__dbName, table))
        if len(ret_list) > 0:
            return True
        #
        return False

    def isTableValid(self, table=None):
        if not table:
            return False
        #
        if self.isTableExist(table=table):
            rdir = self.__getDataDir("COUNT", (table), 0)
            if rdir and ('count(*)' in rdir) and rdir['count(*)'] > 0:
                return True
            #
        #
        return False

    def getAnnoList(self, siteId=None):
        ann_list = []
        if not siteId:
            return_list = self.__dbApi.selectData(key='GET_ALL_ANNO_INITIALS', parameter=())
        else:
            da_group_id = '5'
            rdir = self.__getDataDir('GET_DA_GROUP_ID', ('ANN', siteId), 0)
            if rdir and ('da_group_id' in rdir):
                da_group_id = str(rdir['da_group_id'])
            #
            return_list = self.__dbApi.selectData(key='GET_SITE_ANNO_INITIALS', parameter=(da_group_id))
        #
        if return_list:
            for rD in return_list:
                if ('initials' in rD) and rD['initials']:
                    ann_list.append(rD['initials'])
                #
            #
        #
        return ann_list

    def getEntryListFromDepIdList(self, id_list):
        if not id_list:
            return []
        #
        id_type_map = {}
        id_type_map['dep_set_id'] = id_list
        return self.getEntryListFromIdTypeMap(id_type_map)

    def getEntryListFromIdTypeMap(self, id_type_map):
        if not id_type_map:
            return []
        #
        parameter = ''
        for id_type in ('dep_set_id', 'pdb_id', 'bmrb_id', 'emdb_id'):
            if (id_type not in id_type_map) or (not id_type_map[id_type]):
                continue
            #
            id_type_map[id_type] = sorted(set(id_type_map[id_type]))
            if parameter:
                parameter += " or "
            #
            parameter += " " + id_type + " in ( '" + "', '".join(id_type_map[id_type]) + "' ) "
        #
        if not parameter:
            return []
        #
        return self.__dbApi.selectData(key='GET_ENTRY_LIST', parameter=(parameter))

    def getEntryListForGroup(self, groupid):
        if not groupid:
            return None
        #
        return self.__dbApi.selectData(key="GET_ENTRY_LIST_FROM_GROUP", parameter=(groupid))

    def getMajorIssueEntryList(self, id_list):
        if not id_list:
            return []
        #
        ret_list = self.__dbApi.selectData(key="GET_MAJOR_ISSUE_ENTRY_LIST", parameter=("', '".join(id_list)))
        major_id_list = []
        for Dict in ret_list:
            major_id_list.append(Dict['dep_set_id'])
        #
        return major_id_list

    def __getDataDir(self, key, parameter, idx):
        ret_list = self.__dbApi.selectData(key=key, parameter=parameter)
        if ret_list:
            return ret_list[idx]
        #
        return {}
