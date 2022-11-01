##
# File:  ReleaseOption.py
# Date:  20-Mar-2014
# Updates:
##
"""

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


def getReleaseManu(name, value, val_list, js_class, include_empty_selection):
    display_list = []
    if include_empty_selection:
        display_list = [['', '']]
    #
    for tup_list in val_list:
        display_list.append(tup_list)
    #
    text = '<select name="' + name + '" id="' + name + '" ' + js_class + '>\n'
    label = ''
    for tup_list in display_list:
        text += '<option value="' + tup_list[0] + '" '
        if value == tup_list[0]:
            text += 'selected'
            label = tup_list[1]
        #
        text += '>' + tup_list[1] + '</option>\n'
    text += '</select> &nbsp; &nbsp; &nbsp;\n'
    return text, label


def getCheckBox(name, value, label):
    text = '<input type="checkbox" id="' + name + '" name="' + name + '" value="' \
        + value + '" checked /> ' + label + ' &nbsp; &nbsp; &nbsp; \n'
    return text


def processAuthorApprovalType(existing_value, structure_id):
    val_list = ['', 'implicit', 'explicit']
    val = ''
    if existing_value:
        val = existing_value.lower()
    #
    text = 'Approval Type: &nbsp; <select name="approval_type_' + structure_id + \
           '" id="approval_type_' + structure_id + '">\n'
    for v in val_list:
        text += '<option value="' + v + '" '
        if v == val:
            text += 'selected'
        text += '>' + v + '</option>\n'
    text += '</select> &nbsp; &nbsp; &nbsp;\n'
    return text


def getTextBox(name_prefix, structure_id, value, size="20"):
    text = '<input type="text" name="' + name_prefix + '_' + structure_id \
        + '" id="' + name_prefix + '_' + structure_id + '" value="' + value + '" size="' + size + '" /> '
    return text


def getSupersedeIDBox(structure_id, spr_entry, obs_details, display):
    text = '<span id="span_supersede_' + structure_id + '" style="display:' + display + '">Supersede PDB ID: &nbsp; ' \
        + getTextBox('supersede', structure_id, spr_entry, size="20") + ' <br/> &nbsp; Obsolete Details: &nbsp; ' \
        + getTextBox('obspr_details', structure_id, obs_details, size="160") + ' </span> &nbsp; &nbsp; &nbsp; \n'
    return text


def getObsoleteIDBox(structure_id, obs_entry, display):
    text = '<span id="span_obsolete_' + structure_id + '" style="display:' + display + '">Obsolete PDB IDs: &nbsp; ' \
        + getTextBox('obsolete', structure_id, obs_entry) + '</span> &nbsp; &nbsp; &nbsp; \n'
    return text


def getObsSprInfo(pdb_id, obspr_list):
    text = ''
    for dataDict in obspr_list:
        if dataDict['pdb_id'].upper() == pdb_id:
            text += 'Entry ' + dataDict['pdb_id'] + ' is to supersede entry ' + dataDict['replace_pdb_id'] + '. '
        else:
            text += 'Entry ' + dataDict['replace_pdb_id'] + ' is obsoleted by entry ' + dataDict['pdb_id'] + '. '
        #
    #
    if not text:
        return text
    #
    return '<br /><span style="color:red;">Warning: ' + text + '</span>\n'


def addHiddenInput(name, value):
    text = '<input type="hidden" name="' + name + '" id="' + name + '" value="' + value + '" />\n'
    return text


def ModelReleaseOption(dataDict, selectedOptions, citationFlag, newReleaseFlag, reObsoleteFlag):
    model_list = [ [ 'REL_added',       'Release Coord.'              ],
                   [ 'EMHEADERUpdate',  'EM XML header'               ],
                   [ 'REREL_modified',  'Re-release Coord.'           ],
                   # [ 'RELOAD_reloaded', 'Re-release CIF w/o PDB'     ],
                   [ 'OBS_obsolete',    'Obsolete Coord.'             ],
                   [ 'CITATIONUpdate',  'Update citation w/o release' ] ]
    #
    isWdrnEntry = False
    if ('status_code' in dataDict) and (dataDict['status_code'].upper() == 'WDRN'):
        isWdrnEntry = True
    #
    value = ''
    val_list = []
    if ('pdb_id' in dataDict) and dataDict['pdb_id'] and (not isWdrnEntry):
        value = 'REREL_modified'
        val_list = model_list[2:4]
        if citationFlag:
            val_list.insert(2, model_list[4])
        #
        if ('emdb_release' in dataDict) and dataDict['emdb_release']:
            val_list.insert(2, model_list[1])
        #
        if reObsoleteFlag:
            value = 'OBS_obsolete'
            val_list = model_list[3:4]
            if ('emdb_release' in dataDict) and dataDict['emdb_release']:
                val_list.insert(0, model_list[1])
            #
        elif newReleaseFlag:
            value = 'REL_added'
            val_list = model_list[0:1]
            if ('emdb_release' in dataDict) and dataDict['emdb_release']:
                val_list = model_list[0:2]
            #
            if citationFlag:
                val_list.append(model_list[4])
            #
        #
    elif ('emdb_release' in dataDict) and dataDict['emdb_release']:
        value = 'EMHEADERUpdate'
        if isWdrnEntry:
            val_list.append(model_list[1])
        else:
            val_list = model_list[1:2]
            if citationFlag:
                val_list.append(model_list[4])
            #
        #
    #
    if not val_list:
        '', False, ''  # pylint: disable=pointless-statement
    #
    if selectedOptions:
        value = ''
        if ('status_' in selectedOptions) and selectedOptions['status_']:
            value = selectedOptions['status_']
        #
    #
    include_empty_selection = True
    if ('emdb_release' in dataDict) and dataDict['emdb_release']:
        include_empty_selection = False
    #
    text, label = getReleaseManu('status_' + dataDict['structure_id'], value, val_list, 'class="release_status"', include_empty_selection)
    pre_select_flag = False
    if newReleaseFlag or (selectedOptions and value and label):
        text += addHiddenInput('pre_select_status_' + dataDict['structure_id'], value + ':' + label)
        pre_select_flag = True
    #
    return text, pre_select_flag, value


def ExpReleaseOption(dataDict, selectedOptions, newReleaseFlag, reObsoleteFlag, newReleaseEmFlag, reObsoleteEmFlag):
    exp_list = [ [ 'recvd_struct_fact',     'status_sf_', 'SF', 'status_code_sf',
                   [ [ 'REL_added',         'Release SF'    ],
                     [ 'REREL_modified',    'Re-release SF' ],
                     [ 'OBS_obsolete',      'Obsolete SF'   ] ] ],
                 [ 'recvd_em_map',          'status_em_', 'EM', 'status_code_em',
                   [ [ 'REL_added',         'Release EM'    ],
                     [ 'REREL_modified',    'Re-release EM' ],
                     [ 'OBS_obsolete',      'Obsolete EM'   ] ] ],
                 [ 'recvd_nmr_constraints', 'status_mr_', 'MR', 'status_code_mr',
                   [ [ 'REL_added',         'Release MR'    ],
                     [ 'REREL_modified',    'Re-release MR' ],
                     [ 'OBS_obsolete',      'Obsolete MR'   ] ] ],
                 [ 'recvd_chemical_shifts', 'status_cs_', 'CS', 'status_code_cs',
                   [ [ 'REL_added',         'Release CS'    ],
                     [ 'REREL_modified',    'Re-release CS' ],
                     [ 'OBS_obsolete',      'Obsolete CS'   ] ] ],
                 [ 'recvd_nmr_data', 'status_nmr_data_', 'NMR DATA', 'status_code_nmr_data',
                   [ [ 'REL_added',      'Release NMR DATA'    ],
                     [ 'REREL_modified', 'Re-release NMR DATA' ],
                     [ 'OBS_obsolete',   'Obsolete NMR DATA'   ] ] ] ]
    #
    text = ''
    pre_select_flag = False
    for t_list in exp_list:
        if t_list[0] not in dataDict:
            continue
        #
        if dataDict[t_list[0]] != 'Y' and dataDict[t_list[0]] != 'y':
            continue
        #
        releaseFlag = newReleaseFlag
        obsoleteFlag = reObsoleteFlag
        if t_list[0] == 'recvd_em_map':
            releaseFlag = newReleaseEmFlag
            obsoleteFlag = reObsoleteEmFlag
        #
        isWdrnEntry = False
        if (t_list[3] in dataDict) and (dataDict[t_list[3]].upper() == 'WDRN'):
            isWdrnEntry = True
        #
        value = ''
        display_list = t_list[4][1:]
        if obsoleteFlag:
            display_list = t_list[4][2:]
        elif isWdrnEntry:
            value = ''
            display_list = []
        elif releaseFlag:
            value = t_list[4][0][0]
            display_list = t_list[4][0:1]
        elif selectedOptions:
            if (t_list[1] in selectedOptions) and selectedOptions[t_list[1]]:
                value = selectedOptions[t_list[1]]
            #
        elif ('pdb_id' not in dataDict) or (not dataDict['pdb_id']):
            value = t_list[4][1][0]
        #
        select_text, label = getReleaseManu(t_list[1] + dataDict['structure_id'], value, display_list, '', True)
        text += t_list[2] + ': &nbsp; ' + select_text
        if newReleaseFlag or (selectedOptions and value and label):
            text += addHiddenInput('pre_select_' + t_list[1] + dataDict['structure_id'], value + ':' + label)
            pre_select_flag = True
        #
    #
    return text, pre_select_flag


def ReleaseOption(dataDict, selectedData, citationFlag, newReleaseFlag, reObsoleteFlag, newReleaseEmFlag, reObsoleteEmFlag, releaseDate):
    selectedOptions = {}
    if (not newReleaseFlag) and ('pre_select' in selectedData) and selectedData['pre_select']:
        selectedOptions = selectedData['pre_select']
    #
    model_text, model_pre_select_flag, value = ModelReleaseOption(dataDict, selectedOptions, citationFlag, newReleaseFlag, reObsoleteFlag)
    exp_text, exp_pre_select_flag = ExpReleaseOption(dataDict, selectedOptions, newReleaseFlag, reObsoleteFlag, newReleaseEmFlag, reObsoleteEmFlag)
    if selectedOptions and (not model_pre_select_flag) and (not exp_pre_select_flag):
        model_text, model_pre_select_flag, value = ModelReleaseOption(dataDict, {}, citationFlag, newReleaseFlag, reObsoleteFlag)
        exp_text, exp_pre_select_flag = ExpReleaseOption(dataDict, {}, newReleaseFlag, reObsoleteFlag, newReleaseEmFlag, reObsoleteEmFlag)
    #
    text = ''
    if newReleaseFlag:
        text += addHiddenInput('new_release_flag_' + dataDict['structure_id'], 'yes')
        text += addHiddenInput('pre_select_flag_' + dataDict['structure_id'], 'yes')
    elif selectedOptions and (model_pre_select_flag or exp_pre_select_flag):
        text += addHiddenInput('pre_select_flag_' + dataDict['structure_id'], 'yes')
    #
    text += model_text
    #
    author_approval_type = ''
    if ('author_approval_type' in dataDict) and dataDict['author_approval_type']:
        author_approval_type = dataDict['author_approval_type']
    #
    if (not author_approval_type) and ('approval_type' in selectedData) and selectedData['approval_type']:
        author_approval_type = selectedData['approval_type']
    #
    text += processAuthorApprovalType(author_approval_type, dataDict['structure_id'])
    #
    text += exp_text
    #
    obspr_text = ''
    if ('pdb_id' in dataDict) and dataDict['pdb_id']:
        spr_entry = ''
        obs_entry = ''
        obs_details = ''
        if 'obspr' in dataDict:
            for obsprDict in dataDict['obspr']:
                # if ('date' not in obsprDict) or (obsprDict['date'] != releaseDate) or ('id' not in obsprDict):
                if ('id' not in obsprDict) or (('date' in obsprDict) and (obsprDict['date'] != releaseDate)):
                    continue
                #
                if obsprDict['id'].upper() == 'OBSLTE':
                    if ('replace_pdb_id' in obsprDict) and (obsprDict['replace_pdb_id'].upper() == dataDict['pdb_id'].upper()) and \
                       ('pdb_id' in obsprDict) and (obsprDict['pdb_id'].upper() != 'NONE'):
                        spr_entry = obsprDict['pdb_id'].upper()
                        obspr_text += 'Entry ' + dataDict['pdb_id'].upper() + ' is obsoleted by entry ' + spr_entry + '. '
                    #
                    if ('details' in obsprDict) and obsprDict['details']:
                        obs_details = obsprDict['details']
                    #
                elif obsprDict['id'].upper() == 'SPRSDE':
                    if ('pdb_id' in obsprDict) and (obsprDict['pdb_id'].upper() == dataDict['pdb_id'].upper()) and \
                       ('replace_pdb_id' in obsprDict) and obsprDict['replace_pdb_id']:
                        obs_entry = obsprDict['replace_pdb_id'].upper()
                        obspr_text += 'Entry ' + dataDict['pdb_id'].upper() + ' is to supersede entry ' + obs_entry + '. '
                    #
                #
            #
        #
        spr_display = 'none'
        obs_display = 'inline'
        if ('status_code' in dataDict) and (dataDict['status_code'] == 'OBS'):
            spr_display = 'inline'
            obs_display = 'none'
        #
        if value:
            if (value == 'REL_added') or (value == 'REREL_modified'):
                spr_display = 'none'
                obs_display = 'inline'
            elif value == 'OBS_obsolete':
                spr_display = 'inline'
                obs_display = 'none'
            else:
                spr_display = 'none'
                obs_display = 'none'
            #
        #
        text += getSupersedeIDBox(dataDict['structure_id'], spr_entry, obs_details, spr_display)
        text += getObsoleteIDBox(dataDict['structure_id'], obs_entry, obs_display)
        if spr_entry:
            text += addHiddenInput('author_supersede_' + dataDict['structure_id'], spr_entry)
        #
        if obs_details:
            text += addHiddenInput('author_obspr_details_' + dataDict['structure_id'], obs_details)
        #
        if obs_entry:
            text += addHiddenInput('author_obsolete_' + dataDict['structure_id'], obs_entry)
        #
    #
#   if ('obspr' in dataDict) and (not reObsoleteFlag):
#       text += getObsSprInfo(str(dataDict['pdb_id']).upper(), dataDict['obspr'])
    if obspr_text and (not reObsoleteFlag):
        text += '<br /><span style="color:red;">Warning: ' + obspr_text + '</span>\n'
    #
    if reObsoleteFlag:
        text += addHiddenInput('reobsolete_' + dataDict['structure_id'], 'yes')
    #
    return text
