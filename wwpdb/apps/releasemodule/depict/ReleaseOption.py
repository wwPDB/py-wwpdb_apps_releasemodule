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
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import os, sys, string, traceback

def getReleaseManu(name, label, val_list, js_class):
    display_list = [ [ '', ''] ]
    for list in val_list:
        display_list.append(list)
    #
    text = '<select name="' + name + '" id="' + name + '" ' + js_class + '>\n'
    for list in display_list:
        text += '<option value="' + list[0] + '" '
        if label == list[1]:
            text += 'selected'
        text += '>' + list[1] + '</option>\n'
    text += '</select> &nbsp; &nbsp; &nbsp;\n'
    return text

def getReleaseSelectCitation(name, label, newRelease):
    val_list1 = [ [ 'REL_added',       'Release Coord.'              ],
                  [ 'CITATIONUpdate',  'Update citation w/o release' ] ]
    val_list2 = [ [ 'REL_modified',    'Re-release Coord.'           ],
                  [ 'RELOAD_reloaded', 'Re-release  CIF w/o PDB'     ],
                  [ 'CITATIONUpdate',  'Update citation w/o release' ],
                  [ 'OBS_obsolete',    'Obsolete Coord.'             ] ]
    if newRelease:
        return getReleaseManu(name, label, val_list1, 'class="release_status"')
    else:
        return getReleaseManu(name, label, val_list2, 'class="release_status"')
    #

def getReleaseSelect(name, label, newRelease):
    val_list = [ [ 'REL_added',       'Release Coord.'          ],
                 [ 'REL_modified',    'Re-release Coord.'       ],
                 [ 'RELOAD_reloaded', 'Re-release  CIF w/o PDB' ],
                 [ 'OBS_obsolete',    'Obsolete Coord.'         ] ]
    if newRelease:
        return getReleaseManu(name, label, val_list[0:1], 'class="release_status"')
    else:
        return getReleaseManu(name, label, val_list[1:], 'class="release_status"')
    #

def getCheckBox(name, value, label):
    text = '<input type="checkbox" id="' + name + '" name="' + name + '" value="' \
         + value + '" checked /> ' + label + ' &nbsp; &nbsp; &nbsp; \n'
    return text

def processAuthorApprovalType(existing_value, structure_id):
    val_list = [ '', 'implicit', 'explicit' ]
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

def getTextBox(name_prefix, structure_id):
    text = '<input type="text" name="' + name_prefix + '_' + structure_id \
         + '" id="' + name_prefix + '_' + structure_id + '" value="" size="20" /> '
    return text

def getSupersedeIDBox(structure_id):
    text = '<span id="span_supersede_' + structure_id + '" style="display:none">Supersede PDB ID: &nbsp; ' \
         + getTextBox('supersede', structure_id) + '</span> &nbsp; &nbsp; &nbsp; \n'
    return text

def getObsoleteIDBox(structure_id):
    text = '<span id="span_obsolete_' + structure_id + '" style="display:inline">Obsolete PDB IDs: &nbsp; ' \
         + getTextBox('obsolete', structure_id) + '</span> &nbsp; &nbsp; &nbsp; \n'
    return text

def getObsSprInfo(pdb_id, obspr_list):
    text = ''
    for dir in obspr_list:
        if dir['pdb_id'].upper() == pdb_id:
            text += 'Entry ' + dir['pdb_id'] + ' is to supersede entry ' + dir['relace_pdb_id'] + '. '
        else:
            text += 'Entry ' + dir['relace_pdb_id'] + ' is obsoleted by entry ' + dir['pdb_id'] + '. '
        #
    #
    if not text:
        return text
    else:
        return '<br /><span style="color:red;">Warning: ' + text + '</span>\n'
  

def ReleaseOption(dir, flag, newRelease):
    exp_list = [ [ 'recvd_struct_fact',     'status_sf_', 'SF', #'Release SF' ],
                   [ [ 'REL_added',      'Release SF'    ],
                     [ 'REREL_modified', 'Re-release SF' ],
                     [ 'OBS_obsolete',   'Obsolete SF'   ] ] ],
                 [ 'recvd_em_map', 'status_em_', 'EM', #'Release EM ' ],
                   [ [ 'REL_added',      'Release EM'    ],
                     [ 'REREL_modified', 'Re-release EM' ],
                     [ 'OBS_obsolete',   'Obsolete EM'   ] ] ],
                 [ 'recvd_nmr_constraints', 'status_mr_', 'MR', #'Release MR' ],
                   [ [ 'REL_added',      'Release MR'    ],
                     [ 'REREL_modified', 'Re-release MR' ],
                     [ 'OBS_obsolete',   'Obsolete MR'   ] ] ],
                 [ 'recvd_chemical_shifts', 'status_cs_', 'CS', #'Release CS' ] ]
                   [ [ 'REL_added',      'Release CS'    ],
                     [ 'REREL_modified', 'Re-release CS' ],
                     [ 'OBS_obsolete',   'Obsolete CS'   ] ] ] ]
    #
    author_approval_type = ''
    if dir.has_key('author_approval_type') and dir['author_approval_type']:
        author_approval_type = dir['author_approval_type']
    #
    text = ''
    if dir.has_key('pdb_id') and dir['pdb_id']:
        label = 'Re-release Coord.'
        if newRelease:
            label = 'Release Coord.'
        #
        if flag:
            text += getReleaseSelectCitation('status_' + dir['structure_id'], label, newRelease)
        else:
            text += getReleaseSelect('status_' + dir['structure_id'], label, newRelease)
        #
    #
    text += processAuthorApprovalType(author_approval_type, dir['structure_id'])
    #
    for list in exp_list:
        if not dir.has_key(list[0]):
            continue
        #
        if dir[list[0]] != 'Y' and dir[list[0]] != 'y':
            continue
        #
        label = ''
        display_list = list[3][1:]
        if newRelease:
            label = list[3][0][1]
            display_list = list[3][0:1]
        elif (not dir.has_key('pdb_id')) or (not dir['pdb_id']):
            label = list[3][1][1]
        #
        text += list[2] + ': &nbsp; ' + getReleaseManu(list[1] + dir['structure_id'], label, display_list, '')
    #
    if dir.has_key('pdb_id') and dir['pdb_id']:
        text += getSupersedeIDBox(dir['structure_id'])
        text += getObsoleteIDBox(dir['structure_id'])
    #
    if dir.has_key('obspr'):
        text += getObsSprInfo(str(dir['pdb_id']).upper(), dir['obspr'])
    #
    return text
