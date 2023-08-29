##
# File:  Utility.py
# Date:  10-Jul-2013
# Updates:
##
"""
Various utility procedures.

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2013 wwPDB

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

from wwpdb.utils.config.ConfigInfoApp import ConfigInfoAppCommon
from wwpdb.apps.wf_engine.engine.dbAPI import dbAPI


def isDEPLocked(depid):
    ss = dbAPI(depid, verbose=True)
    ret = ss.runSelectNQ(table='deposition', select=['locking'], where={'dep_set_id': depid})
    if not ret:
        return False
    #
    for rlist in ret:
        for status in rlist:
            if status.find('DEP') != -1:
                return True
            #
        #
    #
    return False


def getCleanValue(dataDict, key):
    """
    """
    if key not in dataDict:
        return ''
    #
    if not dataDict[key]:
        return ''
    #
    return dataDict[key].strip().replace('None', '').replace('none', '').replace('?', '')


def getCombIDs(dataDict):
    comb_ids = ''
    for item in ('pdb_id', 'bmrb_id', 'emdb_id'):
        if comb_ids:
            comb_ids += '/'
        #
        if item in dataDict:
            comb_ids += dataDict[item]
        else:
            comb_ids += '-'
        #
    #
    return comb_ids


def getCombStatus(dataDict):
    statusCode = ''
    authorReleaseStatusCode = ''
    titleEM = ''
    authorListEM = ''
    if ('emdb_id' in dataDict) and dataDict['emdb_id']:
        if ('pdb_id' in dataDict) and dataDict['pdb_id']:
            if ('status_code' in dataDict) and dataDict['status_code'] and ('status_code_em' in dataDict) and dataDict['status_code_em']:
                statusCode = dataDict['status_code'] + '/' + dataDict['status_code_em']
            elif ('status_code' in dataDict) and dataDict['status_code']:
                statusCode = dataDict['status_code']
            #
            if ('author_release_status_code' in dataDict) and dataDict['author_release_status_code'] and \
               ('author_release_status_code_em' in dataDict) and dataDict['author_release_status_code_em']:
                authorReleaseStatusCode = dataDict['author_release_status_code'] + '/' + dataDict['author_release_status_code_em']
            elif ('author_release_status_code' in dataDict) and dataDict['author_release_status_code']:
                authorReleaseStatusCode = dataDict['author_release_status_code']
            #
        else:
            if ('status_code_em' in dataDict) and dataDict['status_code_em']:
                statusCode = dataDict['status_code_em']
            #
            if ('author_release_status_code_em' in dataDict) and dataDict['author_release_status_code_em']:
                authorReleaseStatusCode = dataDict['author_release_status_code_em']
            #
            if ('title_emdb' in dataDict) and dataDict['title_emdb']:
                titleEM = dataDict['title_emdb']
            #
            if ('author_list_emdb' in dataDict) and dataDict['author_list_emdb']:
                authorListEM = dataDict['author_list_emdb']
            #
        #
    else:
        if ('status_code' in dataDict) and dataDict['status_code']:
            statusCode = dataDict['status_code']
        #
        if ('author_release_status_code' in dataDict) and dataDict['author_release_status_code']:
            authorReleaseStatusCode = dataDict['author_release_status_code']
        #
    #
    return statusCode, authorReleaseStatusCode, titleEM, authorListEM


def getCombinationInfo(EntryList, infoMap):
    if not EntryList:
        return []
    #
    for entry in EntryList:
        merging_items = ('author_release_status_code', 'status_code_em', 'author_release_status_code_em', 'title', 'title_emdb', 'author_list', 'author_list_emdb')
        pdb_id = getCleanValue(entry, 'pdb_id')
        if pdb_id:
            merging_items = ('status_code', 'author_release_status_code', 'status_code_em', 'author_release_status_code_em', 'title', 'title_emdb', 'author_list', 'author_list_emdb')
        #
        if (not pdb_id) and ('pdb_id' in entry):
            del entry['pdb_id']
        #
        entryId = ''
        if ('entry' in entry) and entry['entry']:
            entryId = entry['entry']
        elif ('structure_id' in entry) and entry['structure_id']:
            entryId = entry['structure_id']
        #
        if entryId and (entryId in infoMap):
            for item in ('emdb_id', 'bmrb_id'):
                data = getCleanValue(infoMap[entryId], item)
                if data:
                    entry[item] = data
                #
            #
            for item in merging_items:
                if (item in entry) and entry[item]:
                    continue
                #
                data = getCleanValue(infoMap[entryId], item)
                if data:
                    entry[item] = data
                #
            #
        #
        entry['comb_ids'] = getCombIDs(entry)
        entry['comb_status_code'], entry['author_release_status_code'], titleEM, authorListEM = getCombStatus(entry)
        if titleEM:
            entry['title'] = titleEM
        #
        if authorListEM:
            entry['author_list'] = authorListEM
        #
    #
    return EntryList


def getFileName(path, root, ext):
    """Create unique file name.
    """
    count = 1
    while True:
        filename = root + '_' + str(count) + '.' + ext
        fullname = os.path.join(path, filename)
        if not os.access(fullname, os.F_OK):
            return filename
        #
        count += 1
    #
    return root + '_1.' + ext


def RunScript(path, script, log):
    """Run script command
    """
    cmd = 'cd ' + path + '; chmod 755 ' + script \
        + '; ./' + script + ' >& ' + log
    os.system(cmd)


def FindFiles(path):
    """ Find entry files
    """
    rlist = []
    for filename in os.listdir(path):
        # if filename.endswith('.cif') and filename[:4] == 'rcsb' and \
        #    (len(filename) == 14 or len(filename) == 17) or \
        #    filename.endswith('.mr') and filename[:4] == 'rcsb' and \
        #    len(filename) == 13:
        trueFlag = False
        if filename == 'all_files.tar.gz' or filename == 'all_files.tar':
            continue
        #
        if filename.endswith('.gz'):
            trueFlag = True
        elif filename.endswith('-valrpt.pdf') and len(filename) == 15:
            trueFlag = True
        elif filename.endswith('-valdata.xml') and len(filename) == 16:
            trueFlag = True
        elif filename.endswith('-sf.cif') or filename.endswith('-cs.cif'):
            if len(filename) == 17 or len(filename) == 11:
                trueFlag = True
        elif filename.endswith('.cif'):
            if filename.startswith('rcsb') and len(filename) == 14 or \
               len(filename) == 8:
                trueFlag = True
        elif filename.endswith('.mr'):
            if len(filename) == 13 or len(filename) == 7:
                trueFlag = True
        elif filename.endswith('-extatom.xml') or filename.endswith('-noatom.xml'):
            trueFlag = True
        elif filename.endswith('.xml') and len(filename) == 8:
            trueFlag = True
        elif filename.startswith('pdb') and filename.endswith('.ent') and len(filename) == 11:
            trueFlag = True
        elif filename.startswith('r') and filename.endswith('sf.ent') and len(filename) == 11:
            trueFlag = True
        elif filename.endswith('_cs.str') and len(filename) == 11:
            trueFlag = True
        elif len(filename) > 8 and filename[4:8] == '.pdb':
            trueFlag = True
        #
        if trueFlag:
            rlist.append(filename)
        #
    #
    return rlist


def FindLogFiles(path):
    """ Find log files
    """
    rlist = []
    for filename in os.listdir(path):
        trueFlag = False
        if filename.startswith('release') and filename.endswith('.log'):
            trueFlag = True
        elif filename.endswith('-validation.log'):
            trueFlag = True
        #
        if trueFlag:
            rlist.append(filename)
        #
    #
    return rlist


def FindRCSBFile(rcsbid, ext):
    rcsbTopPath = '/net/annotation'
    for subdir in ('prot', 'nmr', 'ndb'):
        filename = os.path.join(rcsbTopPath, subdir, rcsbid, rcsbid + ext)
        if os.access(filename, os.F_OK):
            return filename
        #
    #
    return ''


def GetUniqueLogMessage(program, logfile):
    if not os.access(logfile, os.F_OK):
        return ''
    #
    statinfo = os.stat(logfile)
    if statinfo.st_size == 0:
        return ''
    #
    f = open(logfile, 'r')
    data = f.read()
    f.close()
    #
    error = ''
    ldir = {}
    dlist = data.split('\n')
    for line in dlist:
        if not line:
            continue
        #
        if line in ldir:
            continue
        #
        ldir[line] = 'y'
        #
        if line == 'Finished!':
            continue
        #
        if error:
            error += '\n'
        #
        error += line
    #
    if program and error == 'Segmentation fault':
        return program + ': ' + error
    #
    return error


def FindReleaseFiles(siteId, entry_dir):
    returnMap = {}
    id_list = []
    if ('pdb_id' in entry_dir) and entry_dir['pdb_id']:
        id_list.append(entry_dir['pdb_id'].lower())
    #
    if ('emdb_id' in entry_dir) and entry_dir['emdb_id']:
        id_list.append(entry_dir['emdb_id'])
    #
    if not id_list:
        return returnMap
    #
    cIcommon = ConfigInfoAppCommon(siteId)
    opReleaseDir = cIcommon.get_for_release_path()

    fmap = {}
    for id in id_list:  # pylint: disable=redefined-builtin
        lower_id = id.lower()
        for subdir in ('added', 'modified', 'obsolete', 'reloaded', 'emd'):
            path = os.path.join(opReleaseDir, subdir, id)
            if not os.access(path, os.F_OK):
                continue
            #
            dlist = os.listdir(path)
            for filename in dlist:
                if filename in fmap:
                    continue
                #
                fmap[filename] = 'yes'
                if filename in ('header', 'metadata', 'map', 'masks', 'other', 'fsc', 'images', 'layerLines', 'structureFactors'):
                    path1 = os.path.join(opReleaseDir, subdir, id, filename)
                    list1 = os.listdir(path1)
                    for filename1 in list1:
                        if filename1 in fmap:
                            continue
                        #
                        fmap[filename1] = 'yes'
                        fullname = os.path.join(path1, filename1)
                        if 'releasedFiles' in returnMap:
                            returnMap['releasedFiles'].append(fullname)
                        else:
                            tlist = []
                            tlist.append(fullname)
                            returnMap['releasedFiles'] = tlist
                        #
                    #
                else:
                    fullname = os.path.join(path, filename)
                    if filename.endswith('.summary'):
                        returnMap['summary'] = fullname
                    else:
                        if 'releasedFiles' in returnMap:
                            returnMap['releasedFiles'].append(fullname)
                        else:
                            tlist = []
                            tlist.append(fullname)
                            returnMap['releasedFiles'] = tlist
                        #
                        if (filename.startswith('pdb') and filename.endswith('.ent')) or filename == lower_id + '.cif.gz' or \
                           filename == lower_id + '.cif' or filename == lower_id + '.xml':
                            returnMap['coor'] = True
                        elif filename.endswith('-sf.cif'):
                            returnMap['sf'] = True
                        elif filename.endswith('.mr'):
                            returnMap['mr'] = True
                        elif filename.endswith('-cs.cif') or filename.endswith('_cs.str'):
                            returnMap['cs'] = True
                        #
                    #
                #
            #
        #
    #
    return returnMap


if __name__ == "__main__":
    flist = FindFiles(sys.argv[1])
    print((len(flist)))
    print(flist)
