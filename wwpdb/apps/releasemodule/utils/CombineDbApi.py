##
# File:  CombineDbApi.py
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
# import traceback
#
from wwpdb.apps.releasemodule.utils.ContentDbApi import ContentDbApi
from wwpdb.apps.releasemodule.utils.StatusDbApi_v2 import StatusDbApi
from wwpdb.apps.releasemodule.utils.TimeUtil import TimeUtil
from wwpdb.apps.releasemodule.utils.Utility import getCleanValue, getCombIDs, getCombStatus
from wwpdb.io.locator.PathInfo import PathInfo


class CombineDbApi(object):
    """
    """
    def __init__(self, siteId=None, path="/var/tmp", verbose=False, log=sys.stderr):
        """
           connect to local database
        """
        self.__lfh = log
        self.__verbose = verbose
        self.__siteId = siteId
        self.__sessionPath = path
        self.__ContentDB = None
        self.__StatusDB = None

    def __connectContentDB(self):
        """
        """
        if self.__ContentDB:
            return
        #
        self.__ContentDB = ContentDbApi(siteId=self.__siteId, verbose=self.__verbose, log=self.__lfh)

    def __connectStatusDB(self):
        """
        """
        if self.__StatusDB:
            return
        #
        self.__StatusDB = StatusDbApi(siteId=self.__siteId, verbose=self.__verbose, log=self.__lfh)

    def __connectAllDB(self):
        """
        """
        self.__connectContentDB()
        self.__connectStatusDB()

    def getFunctionCall(self, statusFlag, funcName, args):
        try:
            if statusFlag:
                self.__connectStatusDB()
                if args:
                    return getattr(self.__StatusDB, '%s' % funcName)(*args)
                else:
                    return getattr(self.__StatusDB, '%s' % funcName)()
                #
            else:
                self.__connectContentDB()
                if args:
                    return getattr(self.__ContentDB, '%s' % funcName)(*args)
                else:
                    return getattr(self.__ContentDB, '%s' % funcName)()
                #
            #
        except:  # noqa: E722 pylint: disable=bare-except
            # traceback.print_exc(file=self.__lfh)
            return None
        #

    def getRequestReleaseEntryInfo(self, annotator):
        self.__connectAllDB()
        return self.getEntryInfo(self.__ContentDB.getRequestReleaseEntryList(annotator))

    def getExpiredEntryInfo(self, annotator):
        self.__connectAllDB()
        entryList = []
        return_list = self.getEntryInfo(self.__ContentDB.getExpiredEntryList(annotator))
        for entry in return_list:
            if ('locking' in entry) and entry['locking']:
                locking = entry['locking'].upper()
                if locking.find('DEP') != -1:
                    entryList.append(entry)
                #
            #
        #
        return entryList

    def getEntriesWithStatusList(self, annotator, status_list):
        self.__connectAllDB()
        return self.getEntryInfo(self.__ContentDB.getEntriesWithStatusList(annotator, "', '".join(status_list)))

    def getEntriesWithAuthorName(self, annotator, name):
        self.__connectAllDB()
        return self.getEntryInfo(self.__ContentDB.getEntriesWithAuthorName(annotator, name))

    def getCitationAuthorList(self, entry_id, reformat):
        a_list = []
        self.__connectContentDB()
        rows = self.__ContentDB.getCitationAuthorList(entry_id)
        if rows:
            for row in rows:
                if 'name' not in row:
                    continue
                #
                if reformat:
                    nlist = row['name'].split(',')
                    if len(nlist) == 2:
                        s1 = nlist[0].strip()
                        if not s1:
                            continue
                        #
                        s2 = nlist[1].strip()
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

    def getEntryInfoFromInputIDs(self, entry_ids):
        if not entry_ids:
            return '', []
        #
        self.__connectAllDB()
        #
        id_type_map = {}
        group_ids = []
        all_id_list = []
        #
        message = ''
        input_ids = entry_ids.split(' ')
        for id in input_ids:  # pylint: disable=redefined-builtin
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
                if id_type in id_type_map:
                    id_type_map[id_type].append(id.upper())
                else:
                    id_type_map[id_type] = [id.upper()]
                #
            #
        #
        if (not id_type_map) and (not group_ids):
            if not message:
                message += 'No input IDs\n'
            #
            return message, []
        #
        if group_ids:
            group_ids = sorted(set(group_ids))
            group_err_message, dep_id_list = self.__getDepIDFromGroupID(group_ids)
            if group_err_message:
                message += group_err_message
            #
            if dep_id_list:
                if 'dep_set_id' in id_type_map:
                    id_type_map['dep_set_id'].extend(dep_id_list)
                else:
                    id_type_map['dep_set_id'] = dep_id_list
                #
            #
        #
        if (not id_type_map):
            return message, []
        #
        ret_id_list, ret_map = self.__processDepInfo(self.__StatusDB.getEntryListFromIdTypeMap(id_type_map))
        #
        all_id_map = {}
        if ret_map:
            for _k, myD in ret_map.items():
                for id_type in ('dep_set_id', 'pdb_id', 'bmrb_id', 'emdb_id'):
                    if (id_type in myD) and myD[id_type]:
                        all_id_map[myD[id_type].upper()] = 'yes'
                    #
                #
            #
        #
        not_valid_id_message = self.__getNotValidIDMessage(all_id_list, all_id_map)
        if not_valid_id_message:
            message += not_valid_id_message
        #
        if (not ret_id_list):
            return message, []
        #
        return message, self.__getEntryInfo(ret_id_list, ret_map)

    def getEntryInfo(self, id_list):
        if not id_list:
            return []
        #
        self.__connectAllDB()
        #
        uniq_list = sorted(set(id_list))
        _ret_id_list, ret_map = self.__processDepInfo(self.__StatusDB.getEntryListFromDepIdList(uniq_list))
        return self.__getEntryInfo(uniq_list, ret_map)

    def getEntryInfoMap(self, id_list):
        return_list = self.getEntryInfo(id_list)
        if not return_list:
            return {}
        #
        return_map = {}
        for dataDict in return_list:
            return_map[dataDict['structure_id']] = dataDict
        #
        return return_map

    def getEntryCitationInfoMap(self, id_list):
        if not id_list:
            return {}
        #
        self.__connectContentDB()
        #
        return_map = {}
        for entry_id in id_list:
            cInfo = self.__ContentDB.getPrimaryCitation(entry_id)
            if not cInfo:
                continue
            #
            authorList = self.__ContentDB.getPrimaryCitationAuthorList(entry_id)
            if authorList:
                cInfo['author'] = ', '.join(authorList)
            #
            return_map[entry_id] = cInfo
        #
        return return_map

    def __getDepIDFromGroupID(self, group_ids):
        return_list = self.__StatusDB.getEntryListForGroup("', '".join(group_ids))
        return_id_list = []
        group_id_map = {}
        if return_list:
            for myD in return_list:
                if ('dep_set_id' in myD) and myD['dep_set_id']:
                    return_id_list.append(myD['dep_set_id'])
                #
                if ('group_id' in myD) and myD['group_id']:
                    group_id_map[myD['group_id'].upper()] = 'yes'
                #
            #
        #
        return self.__getNotValidIDMessage(group_ids, group_id_map), return_id_list

    def __processDepInfo(self, dep_info_list):
        if not dep_info_list:
            return [], {}
        #
        return_id_list = []
        return_map = {}
        for myD in dep_info_list:
            if ('dep_set_id' not in myD) or (not myD['dep_set_id']):
                continue
            #
            if myD['dep_set_id'] in return_id_list:
                continue
            #
            return_id_list.append(myD['dep_set_id'])
            return_map[myD['dep_set_id']] = myD
        #
        return return_id_list, return_map

    def __getNotValidIDMessage(self, id_list, id_map):
        message = ''
        for did in id_list:
            if did in id_map:
                continue
            #
            message += "'" + did + "' is not a valid ID.\n"
        #
        return message

    def __getEntryInfo(self, id_list, dep_info_map):
        id_string = "', '".join(id_list)
        #
        majorIssueEntryList = self.__StatusDB.getMajorIssueEntryList(id_list)
        selectedEntryList = self.__ContentDB.getEntryInfo(id_string)
        em_info_map = self.__getEMInfo(id_string)
        #
        pdbIdMap = self.__getPdbIdMap(selectedEntryList)
        obsprMap = self.__getObsSprMap(id_string, pdbIdMap)
        #
        pI = PathInfo(siteId=self.__siteId, sessionPath=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        #
        for myD in selectedEntryList:
            if myD['structure_id'] in majorIssueEntryList:
                myD['major_issue'] = 'YES'
            #
            pdb_id = getCleanValue(myD, 'pdb_id')
            if not pdb_id:
                for item in ('pdb_id', 'status_code'):
                    if item in myD:
                        del myD[item]
                    #
                #
            elif ('exp_method' in myD) and ((myD['exp_method'].upper().find("ELECTRON CRYSTALLOGRAPHY") != -1)
                                            or (myD['exp_method'].upper().find("ELECTRON MICROSCOPY") != -1)
                                            or (myD['exp_method'].upper().find("ELECTRON TOMOGRAPHY") != -1)):
                emVolumeFile = pI.getFilePath(dataSetId=myD['structure_id'], wfInstanceId=None, contentType='em-volume', formatType='map',
                                              fileSource='archive', versionId='latest', partNumber=1)
                if (not emVolumeFile) or (not os.access(emVolumeFile, os.F_OK)):
                    assoicatedEmdIdList = self.__ContentDB.getNotReleasedAssoicatedEmdId(myD['structure_id'])
                    if len(assoicatedEmdIdList) > 0:
                        warning_message = 'The entry does not have the associated map. The associated EMDB ID'
                        if len(assoicatedEmdIdList) > 1:
                            warning_message += 's = [ ' + ', '.join(assoicatedEmdIdList) + ' ].'
                        else:
                            warning_message += ' = [ ' + assoicatedEmdIdList[0] + ' ].'
                        #
                        myD['warning_message'] = warning_message
                    #
                #
            #
            if (myD['structure_id'] in dep_info_map) and dep_info_map[myD['structure_id']]:
                merging_items = ('emdb_id', 'bmrb_id', 'author_release_status_code', 'status_code_em', 'author_release_status_code_em',
                                 'locking', 'notify', 'title', 'title_emdb', 'author_list', 'author_list_emdb')
                if pdb_id:
                    merging_items = ('emdb_id', 'bmrb_id', 'status_code', 'author_release_status_code', 'status_code_em', 'locking',
                                     'notify', 'author_release_status_code_em', 'title', 'title_emdb', 'author_list', 'author_list_emdb')
                #
                for item in merging_items:
                    data = getCleanValue(dep_info_map[myD['structure_id']], item)
                    if not data:
                        continue
                    #
                    if item == 'status_code' or item == 'status_code_em':
                        myD['wf_' + item] = data
                    #
                    if (item in myD) and myD[item]:
                        continue
                    #
                    myD[item] = data
                #
                if ('emdb_id' in myD) and myD['emdb_id'] and (myD['structure_id'] in em_info_map) and em_info_map[myD['structure_id']] and \
                   ('emdb_release' in em_info_map[myD['structure_id']]) and em_info_map[myD['structure_id']]['emdb_release']:
                    myD['recvd_em_map'] = 'Y'
                    for item in ('emdb_release', 'status_code_em', 'date_of_EM_release'):
                        if (item in em_info_map[myD['structure_id']]) and em_info_map[myD['structure_id']][item]:
                            myD[item] = em_info_map[myD['structure_id']][item]
                        #
                    #
                    if ('pdb_id' not in myD) or (not myD['pdb_id']):
                        for item in ('title_emdb', 'author_list_emdb'):
                            if (item in em_info_map[myD['structure_id']]) and em_info_map[myD['structure_id']][item]:
                                myD[item] = em_info_map[myD['structure_id']][item]
                            #
                        #
                    #
                #
            #
            for item in ('author_list', 'author_list_emdb'):
                if item in myD:
                    myD[item] = self.__processAuthorList(myD[item])
                #
            #
            if (myD['structure_id'] in obsprMap) and obsprMap[myD['structure_id']]:
                myD['obspr'] = obsprMap[myD['structure_id']]
            #
            myD['comb_ids'] = getCombIDs(myD)
            myD['comb_status_code'], myD['author_release_status_code'], titleEM, authorListEM = getCombStatus(myD)
            if titleEM:
                myD['title'] = titleEM
            #
            if authorListEM:
                myD['author_list'] = authorListEM
            #
        #
        return selectedEntryList

    def __getEMInfo(self, id_string):
        em_info_map = {}
        emInfoList = self.__ContentDB.getEMInfo(id_string)
        requestedInfoList = self.__ContentDB.getRequestedInfo(id_string)
        if emInfoList:
            for myD in emInfoList:
                if ('structure_id' not in myD) or (not myD['structure_id']):
                    continue
                #
                em_info_map[myD['structure_id']] = myD
            #
        #
        if requestedInfoList:
            for myD in requestedInfoList:
                if ('structure_id' not in myD) or (not myD['structure_id']) or ('requested_accession_types' not in myD) or \
                   (myD['requested_accession_types'].upper().find("EMDB") == -1):
                    continue
                #
                if myD['structure_id'] in em_info_map:
                    em_info_map[myD['structure_id']]['emdb_release'] = True
                else:
                    em_info_map[myD['structure_id']] = {'structure_id': myD['structure_id'], 'emdb_release': True}
                #
            #
        #
        return em_info_map

    def __getPdbIdMap(self, entryList):
        t = TimeUtil()
        rel_date = t.NextWednesday()
        #
        pdbIdMap = {}
        for entry in entryList:
            if ('structure_id' in entry) and entry['structure_id'] and ('pdb_id' in entry) and entry['pdb_id']:
                status = ""
                if ('status_code' in entry) and (entry['status_code'] == 'REL') and ('last_release_date' in entry) and \
                   entry['last_release_date'] and (entry['last_release_date'] < rel_date):
                    status = 'REL'
                #
                pdbIdMap[entry['structure_id']] = (entry['pdb_id'].upper(), status)
            #
        #
        return pdbIdMap

    def __getObsSprMap(self, id_string, pdbIdMap):
        pdbxObsSprMap = self.__getPdbxObsSprMap(id_string, pdbIdMap)
        depuiObsSprMap = self.__getDepuiObsSprMap(id_string, pdbIdMap)
        #
        if (not pdbxObsSprMap) and (not depuiObsSprMap):
            return {}
        elif pdbxObsSprMap and (not depuiObsSprMap):
            return pdbxObsSprMap
        elif (not pdbxObsSprMap) and depuiObsSprMap:
            return depuiObsSprMap
        #
        for entry_key, obsSprList in depuiObsSprMap.items():
            if entry_key in pdbxObsSprMap:
                found = False
                for obsSprDict in pdbxObsSprMap[entry_key]:
                    # """
                    # if obsSprDict['pdb_id'] == obsSprList[0]['pdb_id']:
                    #     found = True
                    #     replace_id = obsSprDict['replace_pdb_id'] + ' ' + obsSprList[0]['replace_pdb_id']
                    #     tmp_list = replace_id.replace(',', ' ').split(' ')
                    #     relace_id_list = []
                    #     for pdb_id in tmp_list:
                    #         if not pdb_id:
                    #             continue
                    #         #
                    #         relace_id_list.append(pdb_id)
                    #     #
                    #     uniq_list = sorted(set(relace_id_list))
                    #     obsSprDict['replace_pdb_id'] = ' '.join(uniq_list)
                    # #
                    # """
                    if (obsSprDict['pdb_id'] == obsSprList[0]['pdb_id']) and (obsSprDict['id'] == obsSprList[0]['id']):
                        # pdbxReplaceIdList = self.__getReplaceIdList(obsSprDict)
                        depuiReplaceIdList = self.__getReplaceIdList(obsSprList[0])
                        if depuiReplaceIdList:
                            foundList = []
                            for replace_pdb_id in depuiReplaceIdList:
                                foundList.append(replace_pdb_id)
                            #
                            if len(foundList) == len(depuiReplaceIdList):
                                found = True
                            #
                        #
                    #
                #
                if not found:
                    pdbxObsSprMap[entry_key].append(obsSprList[0])
                #
            else:
                pdbxObsSprMap[entry_key] = obsSprList
            #
        #
        return pdbxObsSprMap

    def __getPdbxObsSprMap(self, id_string, pdbIdMap):
        obsprList = self.__ContentDB.getPdbxObsSprInfo(id_string)
        if not obsprList:
            return {}
        #
        retMap = {}
        for obsD in obsprList:
            # if ('pdb_id' not in obsD) or (not obsD['pdb_id']) or ('structure_id' not in obsD) or (not obsD['structure_id']) or \
            #  ('replace_pdb_id' not in obsD) or (not obsD['replace_pdb_id']):
            #   continue
            #
            if ('structure_id' not in obsD) or (not obsD['structure_id']) or (obsD['structure_id'] not in pdbIdMap):
                continue
            #
            pdb_id = ''
            if ('pdb_id' in obsD) and obsD['pdb_id']:
                pdb_id = str(obsD['pdb_id']).strip().upper()
                if pdb_id.upper() == 'NONE':
                    pdb_id = ''
                #
            #
            replace_pdb_id = ''
            if ('replace_pdb_id' in obsD) and obsD['replace_pdb_id']:
                replace_pdb_id = str(obsD['replace_pdb_id']).strip().upper()
            #
            details = ''
            if ('details' in obsD) and obsD['details']:
                details = str(obsD['details']).strip()
            #
            if ((not pdb_id) or (not replace_pdb_id)) and (not details):
                continue
            #
            if pdb_id != pdbIdMap[obsD['structure_id']][0] and replace_pdb_id != pdbIdMap[obsD['structure_id']][0]:
                continue
            #
            myD = {}
            if pdb_id:
                myD['pdb_id'] = pdb_id
            #
            if replace_pdb_id:
                myD['replace_pdb_id'] = replace_pdb_id
            #
            for item in ('id', 'date', 'details'):
                if (item not in obsD) or (not obsD[item]):
                    continue
                #
                if item == 'details':
                    myD[item] = str(obsD[item]).strip()
                else:
                    myD[item] = str(obsD[item]).replace('00:00:00', '').strip().upper()
                #
            #
            if obsD['structure_id'] in retMap:
                retMap[obsD['structure_id']].append(myD)
            else:
                retMap[obsD['structure_id']] = [myD]
            #
        #
        return retMap

    def __getDepuiObsSprMap(self, id_string, pdbIdMap):
        obsprList = self.__ContentDB.getDepuiObsSprInfo(id_string)
        if not obsprList:
            return {}
        #
        retMap = {}
        for obsD in obsprList:
            if ('structure_id' not in obsD) or (not obsD['structure_id']) or ('replace_pdb_id' not in obsD) or (not obsD['replace_pdb_id']):
                continue
            #
            if (obsD['structure_id'] not in pdbIdMap) or (pdbIdMap[obsD['structure_id']][1] == 'REL'):
                continue
            #
            pdb_id = pdbIdMap[obsD['structure_id']][0]
            replace_pdb_id = str(obsD['replace_pdb_id']).upper()
            #
            myD = {}
            myD['id'] = 'SPRSDE'
            myD['pdb_id'] = pdb_id
            myD['replace_pdb_id'] = replace_pdb_id
            retMap[obsD['structure_id']] = [myD]
        #
        return retMap

    def __getReplaceIdList(self, dictObj):
        if (not dictObj) or ('replace_pdb_id' not in dictObj):
            return []
        #
        relace_id_list = []
        for pdb_id in dictObj['replace_pdb_id'].upper().replace(',', ' ').split(' '):
            if not pdb_id:
                continue
            #
            relace_id_list.append(pdb_id)
        #
        return relace_id_list

    def __processAuthorList(self, author_list):
        org_authors = author_list
        authors = str(author_list).replace('?', '').replace(',', '').strip()
        if not authors:
            return ''
        #
        return org_authors


def test_main():
    siteId = os.getenv('WWPDB_SITE_ID')
    c = CombineDbApi(siteId=siteId, verbose=True, log=sys.stderr)
    print((c.getFunctionCall(True, 'getAnnoList', [])))


if __name__ == '__main__':
    test_main()
