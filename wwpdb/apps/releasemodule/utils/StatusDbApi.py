##
# File:  StatusDbApi.py
# Date:  30-Jun-2016
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
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"


import os,sys

from wwpdb.utils.config.ConfigInfo                import ConfigInfo
from wwpdb.apps.releasemodule.utils.DbApiUtil import DbApiUtil


class StatusDbApi(object):
    __schemaMap = {       "COUNT" : "select count(*) from %s",
              "CHECK_TABLE_EXIST" : "select distinct table_name from  information_schema.tables where table_schema = '%s' and table_name = '%s'",
              "GET_ANNO_INITIALS" : "select initials from da_users where active = 0 and da_group_id = '%s'",
              "GET_DA_GROUP_ID"   : "select da_group_id from da_group where code = '%s' and site = '%s'",
              "GET_ENTRY_LIST"    : "select dep_set_id,pdb_id,emdb_id,bmrb_id,status_code,author_release_status_code,status_code_emdb status_code_em," +
                                    "dep_author_release_status_code_emdb author_release_status_code_em,locking,title,title_emdb,author_list," +
                                    "author_list_emdb from deposition where %s",
      "GET_ENTRY_LIST_FROM_GROUP" : "select dep_set_id,group_id from group_deposition_information where group_id in ( '%s' ) order by dep_set_id"
                  }
    #
    """
    """
    def __init__(self, siteId=None, verbose=False, log=sys.stderr):
        """
        """
        self.__lfh       = log
        self.__verbose   = verbose
        self.__siteId    = siteId
        self.__cI        = ConfigInfo(self.__siteId)
        self.__dbServer  = self.__cI.get("SITE_DB_SERVER")
        self.__dbHost    = self.__cI.get("SITE_DB_HOST_NAME")
        self.__dbName    = self.__cI.get("SITE_DB_DATABASE_NAME")
        self.__dbUser    = self.__cI.get("SITE_DB_USER_NAME")
        self.__dbPw      = self.__cI.get("SITE_DB_PASSWORD")
        self.__dbSocket  = self.__cI.get("SITE_DB_SOCKET")
        self.__dbPort    = int(self.__cI.get("SITE_DB_PORT_NUMBER"))
        #
        self.__dbApi = DbApiUtil(dbServer=self.__dbServer, dbHost=self.__dbHost, dbName=self.__dbName, dbUser=self.__dbUser, dbPw=self.__dbPw, \
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
            if rdir and rdir.has_key('count(*)') and rdir['count(*)'] > 0:
                return True
            #
        #
        return False

#   def getEntryListForGroup(self, groupid=None):
#       if not groupid:
#           return None
#       #
#       return self.__dbApi.selectData(key="GET_ENTRY_LIST_FROM_GROUP", parameter=(groupid))

    def getEntryListFromIDs(self, entry_ids=None):
        if not entry_ids:
            return '',[],{}
        #
        id_map = {}
        group_ids = []
        all_id_list = []
        #
        message = ''
        input_ids = entry_ids.split(' ')
        for id in input_ids:
            if not id:
                continue
            #
            id_type = ''
            if id[:2] == 'D_':
                id_type = 'dep_set_id'
            elif id[:2] == 'G_':
                id_type = 'group_id'
            elif len(id) == 4:
                id_type = 'pdb_id'
            elif len(id) == 5:
                id_type = 'bmrb_id'
            elif ((len(id) == 8) or (len(id) == 9)) and str(id).upper().startswith("EMD"):
                id_type = 'emdb_id'
            #
            if not id_type:
                message += "'" + id + "' is not a valid ID.\n"
                continue
            #
            if id_type == 'group_id':
                group_ids.append(id.upper())
            else:
                all_id_list.append(id.upper())
                if id_map.has_key(id_type):
                    id_map[id_type].append(id.upper())
                else:
                    id_map[id_type] = [ id.upper() ]
                #
            #
        #
        if (not id_map) and (not group_ids):
            if not message:
                message += 'No input IDs\n'
            #
            return message,[],{}
        #
        if group_ids:
            group_ids = sorted(set(group_ids))
            err_message,dep_id_list = self.__getDepIDFromGroupID(group_ids)
            if err_message:
                message += err_message
            #
            if dep_id_list:
                if id_map.has_key('dep_set_id'):
                    id_map['dep_set_id'].extend(dep_id_list)
                else:
                    id_map['dep_set_id'] = dep_id_list
                #
            #
        #
        if (not id_map):
            return message,[],{}
        #
        return self.__getEntryList(message, id_map, all_id_list)

    def getEntryListFromIDList(self, entry_ids=None):
        if not entry_ids:
            return '',[],{}
        #
        message = ''
        id_map = {}
        id_map['dep_set_id'] = entry_ids
        all_id_list = entry_ids
        return self.__getEntryList(message, id_map, all_id_list)

    def getAnnoList(self, siteId=None):
        if not siteId:
            return []
        #
        da_group_id = '5'
        rdir = self.__getDataDir('GET_DA_GROUP_ID', ('ANN', siteId), 0)
        if rdir and rdir.has_key('da_group_id'):
            da_group_id = str(rdir['da_group_id'])
        #
        ann_list = []
        return_list = self.__dbApi.selectData(key='GET_ANNO_INITIALS', parameter=(da_group_id))
        if return_list:
            for rD in return_list:
                if rD.has_key('initials') and rD['initials']:
                    ann_list.append(rD['initials'].upper())
                #
            #
        #
        return ann_list
        
    def __getDataDir(self, key, parameter, idx):
        list = self.__dbApi.selectData(key=key, parameter=parameter)
        if list:
            return list[idx]
        #
        return None

    def __getDepIDFromGroupID(self, group_ids):
        return_list = self.__dbApi.selectData(key='GET_ENTRY_LIST_FROM_GROUP', parameter=("', '".join(group_ids)))
        return_id_list = []
        group_id_map = {}
        if return_list:
            for myD in return_list:
                if myD.has_key('dep_set_id') and myD['dep_set_id']:
                    return_id_list.append(myD['dep_set_id'])
                #
                if myD.has_key('group_id') and myD['group_id']:
                    group_id_map[myD['group_id'].upper()] = 'yes'
                #
            #
        #
        return self.__getNotValidIDMessage(group_ids, group_id_map),return_id_list

    def __getEntryList(self, message, id_map, all_id_list):
        parameter = ''
        for id_type in ( 'dep_set_id', 'pdb_id', 'bmrb_id', 'emdb_id' ):
            if not id_map.has_key(id_type):
                continue
            #
            id_map[id_type] = sorted(set(id_map[id_type]))
            if parameter:
                parameter += " or "
            #
            parameter += " " + id_type + " in ( '" + "', '".join(id_map[id_type]) + "' ) "
        #
        return_list = self.__dbApi.selectData(key='GET_ENTRY_LIST', parameter=(parameter))
        return_id_list = []
        return_id_map = {}
        all_id_map = {}
        if return_list:
            for myD in return_list:
                if (not myD.has_key('dep_set_id')) or (not myD['dep_set_id']):
                    continue
                #
                if myD['dep_set_id'] in return_id_list:
                    continue
                #
                return_id_list.append(myD['dep_set_id'])
                return_id_map[myD['dep_set_id']] = myD
                for id_type in ( 'dep_set_id', 'pdb_id', 'bmrb_id', 'emdb_id' ):
                    if myD.has_key(id_type) and myD[id_type]: 
                        all_id_map[myD[id_type].upper()] = 'yes'
                    #
                #
            #
        #
        not_valid_id_message = self.__getNotValidIDMessage(all_id_list, all_id_map)
        if not_valid_id_message:
            message += not_valid_id_message
        #
        return message,return_id_list,return_id_map

    def __getNotValidIDMessage(self, id_list, id_map):
        message = ''
        for id in id_list:
            if id_map.has_key(id):
                continue
            #
            message += "'" + id + "' is not a valid ID.\n"
        #
        return message

if __name__ == '__main__':
    db = StatusDbApi(siteId='WWPDB_DEPLOY_TEST_RU', verbose=True, log=sys.stderr)
    entry_ids = sys.argv[1]
    entry_ids = entry_ids.upper().replace(',', ' ')
    message,id_list,id_map = db.getEntryListFromIDs(entry_ids=entry_ids)
    print message
    print id_list
    print id_map
