##
# File:  FetchResultParser.py
# Date:  18-Jun-2013
# Updates:
##
"""
Parse Pubmed fetch result xml file.

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

import unicodedata
from xml.dom import minidom

import sys


class UniCodeHandler(object):
    """ Convert non-ascii unicode into ascii code if possible
    """

    def __init__(self):
        # pylint: disable=redundant-u-string-prefix
        self.__unicodeMapping = {
            u'\u00C0': 'A',
            u'\u00C1': 'A',
            u'\u00C2': 'A',
            u'\u00C3': 'A',
            u'\u00C4': 'A',
            u'\u00C6': 'Ae',
            u'\u00C7': 'C',
            u'\u00C8': 'E',
            u'\u00C9': 'E',
            u'\u00CA': 'E',
            u'\u00CB': 'E',
            u'\u00CC': 'I',
            u'\u00CD': 'I',
            u'\u00CE': 'I',
            u'\u00CF': 'I',
            u'\u00D1': 'N',
            u'\u00D2': 'O',
            u'\u00D3': 'O',
            u'\u00D4': 'O',
            u'\u00D5': 'O',
            u'\u00D6': 'O',
            u'\u00D8': 'O',
            u'\u00D9': 'U',
            u'\u00DA': 'U',
            u'\u00DB': 'U',
            u'\u00DC': 'U',
            u'\u00DD': 'Y',
            u'\u00DF': 'ss',
            u'\u00E0': 'a',
            u'\u00E1': 'a',
            u'\u00E2': 'a',
            u'\u00E3': 'a',
            u'\u00E4': 'a',
            u'\u00E5': 'a',
            u'\u00E6': 'ae',
            u'\u00E7': 'c',
            u'\u00E8': 'e',
            u'\u00E9': 'e',
            u'\u00EA': 'e',
            u'\u00EB': 'e',
            u'\u00EC': 'i',
            u'\u00ED': 'i',
            u'\u00EE': 'i',
            u'\u00EF': 'i',
            u'\u00F1': 'n',
            u'\u00F2': 'o',
            u'\u00F3': 'o',
            u'\u00F4': 'o',
            u'\u00F5': 'o',
            u'\u00F6': 'o',
            u'\u00F8': 'o',
            u'\u00F9': 'u',
            u'\u00FA': 'u',
            u'\u00FB': 'u',
            u'\u00FC': 'u',
            u'\u00FD': 'y',
            u'\u00FF': 'y',
            u'\u0100': 'A',
            u'\u0101': 'a',
            u'\u0102': 'A',
            u'\u0103': 'a',
            u'\u0104': 'A',
            u'\u0105': 'a',
            u'\u0106': 'C',
            u'\u0107': 'c',
            u'\u0108': 'C',
            u'\u0109': 'c',
            u'\u010A': 'C',
            u'\u010B': 'c',
            u'\u010C': 'C',
            u'\u010D': 'c',
            u'\u010E': 'D',
            u'\u010F': 'd',
            u'\u0110': 'D',
            u'\u0111': 'd',
            u'\u0112': 'E',
            u'\u0113': 'e',
            u'\u0114': 'E',
            u'\u0115': 'e',
            u'\u0116': 'E',
            u'\u0117': 'e',
            u'\u0118': 'E',
            u'\u0119': 'e',
            u'\u011A': 'E',
            u'\u011B': 'e',
            u'\u011C': 'G',
            u'\u011D': 'g',
            u'\u011E': 'G',
            u'\u011F': 'g',
            u'\u0120': 'G',
            u'\u0121': 'g',
            u'\u0122': 'G',
            u'\u0123': 'g',
            u'\u0124': 'H',
            u'\u0125': 'h',
            u'\u0126': 'H',
            u'\u0127': 'h',
            u'\u0128': 'I',
            u'\u0129': 'i',
            u'\u012A': 'I',
            u'\u012B': 'i',
            u'\u012C': 'I',
            u'\u012D': 'i',
            u'\u012E': 'I',
            u'\u012F': 'i',
            u'\u0130': 'I',
            u'\u0131': 'i',
            u'\u0134': 'J',
            u'\u0135': 'j',
            u'\u0136': 'K',
            u'\u0137': 'k',
            u'\u0139': 'L',
            u'\u013A': 'l',
            u'\u013B': 'L',
            u'\u013C': 'l',
            u'\u013D': 'L',
            u'\u013E': 'l',
            u'\u013F': 'L',
            u'\u0140': 'l',
            u'\u0141': 'L',
            u'\u0142': 'l',
            u'\u0143': 'N',
            u'\u0144': 'n',
            u'\u0145': 'N',
            u'\u0146': 'n',
            u'\u0147': 'N',
            u'\u0148': 'n',
            u'\u014C': 'O',
            u'\u014D': 'o',
            u'\u014E': 'O',
            u'\u014F': 'o',
            u'\u0150': 'O',
            u'\u0151': 'o',
            u'\u0154': 'R',
            u'\u0155': 'r',
            u'\u0156': 'R',
            u'\u0157': 'r',
            u'\u0158': 'R',
            u'\u0159': 'r',
            u'\u015A': 'S',
            u'\u015B': 's',
            u'\u015C': 'S',
            u'\u015D': 's',
            u'\u015E': 'S',
            u'\u015F': 's',
            u'\u0160': 'S',
            u'\u0161': 's',
            u'\u0162': 'T',
            u'\u0163': 't',
            u'\u0164': 'T',
            u'\u0165': 't',
            u'\u0166': 'T',
            u'\u0167': 't',
            u'\u0168': 'U',
            u'\u0169': 'u',
            u'\u016A': 'U',
            u'\u016B': 'u',
            u'\u016C': 'U',
            u'\u016D': 'u',
            u'\u016E': 'U',
            u'\u016F': 'u',
            u'\u0170': 'U',
            u'\u0171': 'u',
            u'\u0172': 'U',
            u'\u0173': 'u',
            u'\u0174': 'W',
            u'\u0175': 'w',
            u'\u0176': 'Y',
            u'\u0177': 'y',
            u'\u0178': 'Y',
            u'\u0179': 'Z',
            u'\u017A': 'z',
            u'\u017B': 'Z',
            u'\u017C': 'z',
            u'\u017D': 'Z',
            u'\u017E': 'z',
            u'\u0180': 'b',
            u'\u0181': 'B',
            u'\u0182': 'B',
            u'\u0183': 'b',
            u'\u0187': 'C',
            u'\u0188': 'c',
            u'\u018A': 'D',
            u'\u018B': 'D',
            u'\u018C': 'd',
            u'\u0191': 'F',
            u'\u0192': 'f',
            u'\u0193': 'G',
            u'\u0197': 'I',
            u'\u0198': 'K',
            u'\u0199': 'k',
            u'\u019A': 'l',
            u'\u019D': 'N',
            u'\u019E': 'n',
            u'\u019F': 'O',
            u'\u01A0': 'O',
            u'\u01A1': 'o',
            u'\u01A4': 'P',
            u'\u01A5': 'p',
            u'\u01AB': 't',
            u'\u01AC': 'T',
            u'\u01AD': 't',
            u'\u01AE': 'T',
            u'\u01AF': 'U',
            u'\u01B0': 'u',
            u'\u01B2': 'V',
            u'\u01B3': 'Y',
            u'\u01B4': 'y',
            u'\u01B5': 'Z',
            u'\u01B6': 'z',
            u'\u01C5': 'D',
            u'\u01C8': 'L',
            u'\u01CB': 'N',
            u'\u01CD': 'A',
            u'\u01CE': 'a',
            u'\u01CF': 'I',
            u'\u01D0': 'i',
            u'\u01D1': 'O',
            u'\u01D2': 'o',
            u'\u01D3': 'U',
            u'\u01D4': 'u',
            u'\u01D5': 'U',
            u'\u01D6': 'u',
            u'\u01D7': 'U',
            u'\u01D8': 'u',
            u'\u01D9': 'U',
            u'\u01DA': 'u',
            u'\u01DB': 'U',
            u'\u01DC': 'u',
            u'\u01DE': 'A',
            u'\u01DF': 'a',
            u'\u01E0': 'A',
            u'\u01E1': 'a',
            u'\u01E4': 'G',
            u'\u01E5': 'g',
            u'\u01E6': 'G',
            u'\u01E7': 'g',
            u'\u01E8': 'K',
            u'\u01E9': 'k',
            u'\u01EA': 'O',
            u'\u01EB': 'o',
            u'\u01EC': 'O',
            u'\u01ED': 'o',
            u'\u01F0': 'j',
            u'\u01F2': 'D',
            u'\u01F4': 'G',
            u'\u01F5': 'g',
            u'\u01F8': 'N',
            u'\u01F9': 'n',
            u'\u01FA': 'A',
            u'\u01FB': 'a',
            u'\u01FE': 'O',
            u'\u01FF': 'o',
            u'\u0200': 'A',
            u'\u0201': 'a',
            u'\u0202': 'A',
            u'\u0203': 'a',
            u'\u0204': 'E',
            u'\u0205': 'e',
            u'\u0206': 'E',
            u'\u0207': 'e',
            u'\u0208': 'I',
            u'\u0209': 'i',
            u'\u020A': 'I',
            u'\u020B': 'i',
            u'\u020C': 'O',
            u'\u020D': 'o',
            u'\u020E': 'O',
            u'\u020F': 'o',
            u'\u0210': 'R',
            u'\u0211': 'r',
            u'\u0212': 'R',
            u'\u0213': 'r',
            u'\u0214': 'U',
            u'\u0215': 'u',
            u'\u0216': 'U',
            u'\u0217': 'u',
            u'\u0218': 'S',
            u'\u0219': 's',
            u'\u021A': 'T',
            u'\u021B': 't',
            u'\u021E': 'H',
            u'\u021F': 'h',
            u'\u0220': 'N',
            u'\u0221': 'd',
            u'\u0224': 'Z',
            u'\u0225': 'z',
            u'\u0226': 'A',
            u'\u0227': 'a',
            u'\u0228': 'E',
            u'\u0229': 'e',
            u'\u022A': 'O',
            u'\u022B': 'o',
            u'\u022C': 'O',
            u'\u022D': 'o',
            u'\u022E': 'O',
            u'\u022F': 'o',
            u'\u0230': 'O',
            u'\u0231': 'o',
            u'\u0232': 'Y',
            u'\u0233': 'y',
            u'\u0234': 'l',
            u'\u0235': 'n',
            u'\u0236': 't',
            u'\u023A': 'A',
            u'\u023B': 'C',
            u'\u023C': 'c',
            u'\u023D': 'L',
            u'\u023E': 'T',
            u'\u023F': 's',
            u'\u0240': 'z',
            u'\u0243': 'B',
            u'\u0246': 'E',
            u'\u0247': 'e',
            u'\u0248': 'J',
            u'\u0249': 'j',
            u'\u024B': 'q',
            u'\u024C': 'R',
            u'\u024D': 'r',
            u'\u024E': 'Y',
            u'\u024F': 'y',
            u'\u0253': 'b',
            u'\u0255': 'c',
            u'\u0256': 'd',
            u'\u0257': 'd',
            u'\u0260': 'g',
            u'\u0266': 'h',
            u'\u0268': 'i',
            u'\u026B': 'l',
            u'\u026C': 'l',
            u'\u026D': 'l',
            u'\u0271': 'm',
            u'\u0272': 'n',
            u'\u0273': 'n',
            u'\u027C': 'r',
            u'\u027D': 'r',
            u'\u027E': 'r',
            u'\u0282': 's',
            u'\u0288': 't',
            u'\u028B': 'v',
            u'\u0290': 'z',
            u'\u0291': 'z',
            u'\u029D': 'j',
            u'\u02A0': 'q',
            u'\u0391': ' Alpha ',
            u'\u0392': ' Beta ',
            u'\u0393': ' Gamma ',
            u'\u0394': ' Delta ',
            u'\u0395': ' Epsilon ',
            u'\u0396': ' Zeta ',
            u'\u0397': ' Eta ',
            u'\u0398': ' Theta ',
            u'\u0399': ' Iota ',
            u'\u039A': ' Kappa ',
            u'\u039B': ' Lambda ',
            u'\u039C': ' Mu ',
            u'\u039D': ' Nu ',
            u'\u039E': ' Xi ',
            u'\u039F': ' Omicron ',
            u'\u03A0': ' Pi ',
            u'\u03A1': ' Rho ',
            u'\u03A3': ' Sigma ',
            u'\u03A4': ' Tau ',
            u'\u03A5': ' Upsilon ',
            u'\u03A6': ' Phi ',
            u'\u03A7': ' Chi ',
            u'\u03A8': ' Psi ',
            u'\u03A9': ' Omega ',
            u'\u03B1': ' alpha ',
            u'\u03B2': ' beta ',
            u'\u03B3': ' gamma ',
            u'\u03B4': ' delta ',
            u'\u03B5': ' epsilon ',
            u'\u03B6': ' zeta ',
            u'\u03B7': ' eta ',
            u'\u03B8': ' theta ',
            u'\u03B9': ' iota ',
            u'\u03BA': ' kappa ',
            u'\u03BB': ' lambda ',
            u'\u03BC': ' mu ',
            u'\u03BD': ' nu ',
            u'\u03BE': ' xi ',
            u'\u03BF': ' omicron ',
            u'\u03C0': ' pi ',
            u'\u03C1': ' rho ',
            u'\u03C2': ' sigmaf ',
            u'\u03C3': ' sigma ',
            u'\u03C4': ' tau ',
            u'\u03C5': ' upsilon ',
            u'\u03C6': ' phi ',
            u'\u03D5': ' phi ',
            u'\u1D60': ' phi ',
            u'\u1D69': ' phi ',
            u'\u1D6D7': ' phi ',
            u'\u1D711': ' phi ',
            u'\u1D74B': ' phi ',
            u'\u1D785': ' phi ',
            u'\u1D7BF': ' phi ',
            u'\u1D6DF': ' phi ',
            u'\u1D719': ' phi ',
            u'\u1D753': ' phi ',
            u'\u1D78D': ' phi ',
            u'\u1D7C7': ' phi ',
            u'\u03C7': ' chi ',
            u'\u03C8': ' psi ',
            u'\u03C9': ' omega ',
            u'\u1D6C': 'b',
            u'\u1D6D': 'd',
            u'\u1D6E': 'f',
            u'\u1D6F': 'm',
            u'\u1D70': 'n',
            u'\u1D71': 'p',
            u'\u1D72': 'r',
            u'\u1D73': 'r',
            u'\u1D74': 's',
            u'\u1D75': 't',
            u'\u1D76': 'z',
            u'\u1D7D': 'p',
            u'\u1D80': 'b',
            u'\u1D81': 'd',
            u'\u1D82': 'f',
            u'\u1D83': 'g',
            u'\u1D84': 'k',
            u'\u1D85': 'l',
            u'\u1D86': 'm',
            u'\u1D87': 'n',
            u'\u1D88': 'p',
            u'\u1D89': 'r',
            u'\u1D8A': 's',
            u'\u1D8C': 'v',
            u'\u1D8D': 'x',
            u'\u1D8E': 'z',
            u'\u1D8F': 'a',
            u'\u1D91': 'd',
            u'\u1D92': 'e',
            u'\u1D96': 'i',
            u'\u1D99': 'u',
            u'\u1E00': 'A',
            u'\u1E01': 'a',
            u'\u1E02': 'B',
            u'\u1E03': 'b',
            u'\u1E04': 'B',
            u'\u1E05': 'b',
            u'\u1E06': 'B',
            u'\u1E07': 'b',
            u'\u1E08': 'C',
            u'\u1E09': 'c',
            u'\u1E0A': 'D',
            u'\u1E0B': 'd',
            u'\u1E0C': 'D',
            u'\u1E0D': 'd',
            u'\u1E0E': 'D',
            u'\u1E0F': 'd',
            u'\u1E10': 'D',
            u'\u1E11': 'd',
            u'\u1E12': 'D',
            u'\u1E13': 'd',
            u'\u1E14': 'E',
            u'\u1E15': 'e',
            u'\u1E16': 'E',
            u'\u1E17': 'e',
            u'\u1E18': 'E',
            u'\u1E19': 'e',
            u'\u1E1A': 'E',
            u'\u1E1B': 'e',
            u'\u1E1C': 'E',
            u'\u1E1D': 'e',
            u'\u1E1E': 'F',
            u'\u1E1F': 'f',
            u'\u1E20': 'G',
            u'\u1E21': 'g',
            u'\u1E22': 'H',
            u'\u1E23': 'h',
            u'\u1E24': 'H',
            u'\u1E25': 'h',
            u'\u1E26': 'H',
            u'\u1E27': 'h',
            u'\u1E28': 'H',
            u'\u1E29': 'h',
            u'\u1E2A': 'H',
            u'\u1E2B': 'h',
            u'\u1E2C': 'I',
            u'\u1E2D': 'i',
            u'\u1E2E': 'I',
            u'\u1E2F': 'i',
            u'\u1E30': 'K',
            u'\u1E31': 'k',
            u'\u1E32': 'K',
            u'\u1E33': 'k',
            u'\u1E34': 'K',
            u'\u1E35': 'k',
            u'\u1E36': 'L',
            u'\u1E37': 'l',
            u'\u1E38': 'L',
            u'\u1E39': 'l',
            u'\u1E3A': 'L',
            u'\u1E3B': 'l',
            u'\u1E3C': 'L',
            u'\u1E3D': 'l',
            u'\u1E3E': 'M',
            u'\u1E3F': 'm',
            u'\u1E40': 'M',
            u'\u1E41': 'm',
            u'\u1E42': 'M',
            u'\u1E43': 'm',
            u'\u1E44': 'N',
            u'\u1E45': 'n',
            u'\u1E46': 'N',
            u'\u1E47': 'n',
            u'\u1E48': 'N',
            u'\u1E49': 'n',
            u'\u1E4A': 'N',
            u'\u1E4B': 'n',
            u'\u1E4C': 'O',
            u'\u1E4D': 'o',
            u'\u1E4E': 'O',
            u'\u1E4F': 'o',
            u'\u1E50': 'O',
            u'\u1E51': 'o',
            u'\u1E52': 'O',
            u'\u1E53': 'o',
            u'\u1E54': 'P',
            u'\u1E55': 'p',
            u'\u1E56': 'P',
            u'\u1E57': 'p',
            u'\u1E58': 'R',
            u'\u1E59': 'r',
            u'\u1E5A': 'R',
            u'\u1E5B': 'r',
            u'\u1E5C': 'R',
            u'\u1E5D': 'r',
            u'\u1E5E': 'R',
            u'\u1E5F': 'r',
            u'\u1E60': 'S',
            u'\u1E61': 's',
            u'\u1E62': 'S',
            u'\u1E63': 's',
            u'\u1E64': 'S',
            u'\u1E65': 's',
            u'\u1E66': 'S',
            u'\u1E67': 's',
            u'\u1E68': 'S',
            u'\u1E69': 's',
            u'\u1E6A': 'T',
            u'\u1E6B': 't',
            u'\u1E6C': 'T',
            u'\u1E6D': 't',
            u'\u1E6E': 'T',
            u'\u1E6F': 't',
            u'\u1E70': 'T',
            u'\u1E71': 't',
            u'\u1E72': 'U',
            u'\u1E73': 'u',
            u'\u1E74': 'U',
            u'\u1E75': 'u',
            u'\u1E76': 'U',
            u'\u1E77': 'u',
            u'\u1E78': 'U',
            u'\u1E79': 'u',
            u'\u1E7A': 'U',
            u'\u1E7B': 'u',
            u'\u1E7C': 'V',
            u'\u1E7D': 'v',
            u'\u1E7E': 'V',
            u'\u1E7F': 'v',
            u'\u1E80': 'W',
            u'\u1E81': 'w',
            u'\u1E82': 'W',
            u'\u1E83': 'w',
            u'\u1E84': 'W',
            u'\u1E85': 'w',
            u'\u1E86': 'W',
            u'\u1E87': 'w',
            u'\u1E88': 'W',
            u'\u1E89': 'w',
            u'\u1E8A': 'X',
            u'\u1E8B': 'x',
            u'\u1E8C': 'X',
            u'\u1E8D': 'x',
            u'\u1E8E': 'Y',
            u'\u1E8F': 'y',
            u'\u1E90': 'Z',
            u'\u1E91': 'z',
            u'\u1E92': 'Z',
            u'\u1E93': 'z',
            u'\u1E94': 'Z',
            u'\u1E95': 'z',
            u'\u1E96': 'h',
            u'\u1E97': 't',
            u'\u1E98': 'w',
            u'\u1E99': 'y',
            u'\u1E9A': 'a',
            u'\u1EA0': 'A',
            u'\u1EA1': 'a',
            u'\u1EA2': 'A',
            u'\u1EA3': 'a',
            u'\u1EA4': 'A',
            u'\u1EA5': 'a',
            u'\u1EA6': 'A',
            u'\u1EA7': 'a',
            u'\u1EA8': 'A',
            u'\u1EA9': 'a',
            u'\u1EAA': 'A',
            u'\u1EAB': 'a',
            u'\u1EAC': 'A',
            u'\u1EAD': 'a',
            u'\u1EAE': 'A',
            u'\u1EAF': 'a',
            u'\u1EB0': 'A',
            u'\u1EB1': 'a',
            u'\u1EB2': 'A',
            u'\u1EB3': 'a',
            u'\u1EB4': 'A',
            u'\u1EB5': 'a',
            u'\u1EB6': 'A',
            u'\u1EB7': 'a',
            u'\u1EB8': 'E',
            u'\u1EB9': 'e',
            u'\u1EBA': 'E',
            u'\u1EBB': 'e',
            u'\u1EBC': 'E',
            u'\u1EBD': 'e',
            u'\u1EBE': 'E',
            u'\u1EBF': 'e',
            u'\u1EC0': 'E',
            u'\u1EC1': 'e',
            u'\u1EC2': 'E',
            u'\u1EC3': 'e',
            u'\u1EC4': 'E',
            u'\u1EC5': 'e',
            u'\u1EC6': 'E',
            u'\u1EC7': 'e',
            u'\u1EC8': 'I',
            u'\u1EC9': 'i',
            u'\u1ECA': 'I',
            u'\u1ECB': 'i',
            u'\u1ECC': 'O',
            u'\u1ECD': 'o',
            u'\u1ECE': 'O',
            u'\u1ECF': 'o',
            u'\u1ED0': 'O',
            u'\u1ED1': 'o',
            u'\u1ED2': 'O',
            u'\u1ED3': 'o',
            u'\u1ED4': 'O',
            u'\u1ED5': 'o',
            u'\u1ED6': 'O',
            u'\u1ED7': 'o',
            u'\u1ED8': 'O',
            u'\u1ED9': 'o',
            u'\u1EDA': 'O',
            u'\u1EDB': 'o',
            u'\u1EDC': 'O',
            u'\u1EDD': 'o',
            u'\u1EDE': 'O',
            u'\u1EDF': 'o',
            u'\u1EE0': 'O',
            u'\u1EE1': 'o',
            u'\u1EE2': 'O',
            u'\u1EE3': 'o',
            u'\u1EE4': 'U',
            u'\u1EE5': 'u',
            u'\u1EE6': 'U',
            u'\u1EE7': 'u',
            u'\u1EE8': 'U',
            u'\u1EE9': 'u',
            u'\u1EEA': 'U',
            u'\u1EEB': 'u',
            u'\u1EEC': 'U',
            u'\u1EED': 'u',
            u'\u1EEE': 'U',
            u'\u1EEF': 'u',
            u'\u1EF0': 'U',
            u'\u1EF1': 'u',
            u'\u1EF2': 'Y',
            u'\u1EF3': 'y',
            u'\u1EF4': 'Y',
            u'\u1EF5': 'y',
            u'\u1EF6': 'Y',
            u'\u1EF7': 'y',
            u'\u1EF8': 'Y',
            u'\u1EF9': 'y',
            u'\u1EFE': 'Y',
            u'\u1EFF': 'y',
            u'\u2C60': 'L',
            u'\u2C61': 'l',
            u'\u2C62': 'L',
            u'\u2C63': 'P',
            u'\u2C64': 'R',
            u'\u2C65': 'a',
            u'\u2C66': 't',
            u'\u2C67': 'H',
            u'\u2C68': 'h',
            u'\u2C69': 'K',
            u'\u2C6A': 'k',
            u'\u2C6B': 'Z',
            u'\u2C6C': 'z',
            u'\u2C6E': 'M',
            u'\u2C71': 'v',
            u'\u2C72': 'W',
            u'\u2C73': 'w',
            u'\u2C74': 'v',
            u'\u2C78': 'e',
            u'\u2C7A': 'o',
            u'\uA740': 'K',
            u'\uA741': 'k',
            u'\uA742': 'K',
            u'\uA743': 'k',
            u'\uA744': 'K',
            u'\uA745': 'k',
            u'\uA748': 'L',
            u'\uA749': 'l',
            u'\uA74A': 'O',
            u'\uA74B': 'o',
            u'\uA74C': 'O',
            u'\uA74D': 'o',
            u'\uA750': 'P',
            u'\uA751': 'p',
            u'\uA752': 'P',
            u'\uA753': 'p',
            u'\uA754': 'P',
            u'\uA755': 'p',
            u'\uA756': 'Q',
            u'\uA757': 'q',
            u'\uA758': 'Q',
            u'\uA759': 'q',
            u'\uA75E': 'V',
            u'\uA75F': 'v'
        }

        self.__unicodeAngstromMapping = {
            u'\u212B': ' angstrom ',
            u'\u00C5': ' angstrom '
        }

        self.__unicodeLetterAMapping = {
            u'\u212B': 'A',
            u'\u00C5': 'A'
        }

        self.__greekLetter = ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta', 'Eta',
                              'Theta', 'Iota', 'Kappa', 'Lambda', 'Mu', 'Nu', 'Xi',
                              'Omicron', 'Pi', 'Rho', 'Sigma', 'Tau', 'Upsilon', 'Phi',
                              'Chi', 'Psi', 'Omega', 'alpha', 'beta', 'gamma', 'delta',
                              'epsilon', 'zeta', 'eta', 'theta', 'iota', 'kappa', 'lambda',
                              'mu', 'nu', 'xi', 'omicron', 'pi', 'rho', 'sigmaf',
                              'sigma', 'tau', 'upsilon', 'phi', 'chi', 'psi', 'omega']
        #

    def process(self, input_data, angstromFlag):
        if not input_data:
            return input_data
        #
        data = self.__processUniCode(input_data, self.__unicodeMapping)
        if angstromFlag:
            data = self.__processUniCode(data, self.__unicodeAngstromMapping)
        else:
            data = self.__processUniCode(data, self.__unicodeLetterAMapping)
        #
        data = unicodedata.normalize('NFKD', data).encode('ascii', 'xmlcharrefreplace')
        if sys.version_info[0] > 2:
            data = data.decode('ascii')
        data = str(data)
        data = data.replace('  ', ' ')
        data = data.replace(' .', '.')
        data = data.strip()
        for word in self.__greekLetter:
            data = data.replace('- ' + word, '-' + word)
            data = data.replace(word + ' -', word + '-')
        return data

    def __processUniCode(self, input_data, Mapping):
        data = u''  # pylint: disable=redundant-u-string-prefix
        for c in input_data:
            if c in Mapping:
                data += Mapping[c]
            else:
                data += c
        return data


class FetchResultParser(object):
    """Parse Pubmed fetch result xml file, return pubmed information list
    """

    def __init__(self, xmlfile=None):
        self.__xmlfile = xmlfile
        self.__pubmedInfoList = []
        self.__codeHandler = UniCodeHandler()
        self._parseXml()

    def getPubmedInfoList(self):
        return self.__pubmedInfoList

    def _parseXml(self):
        try:
            __doc = minidom.parse(self.__xmlfile)
            self.__pubmedInfoList = self._parseDoc(__doc)
        except:  # noqa: E722 pylint: disable=bare-except
            pass

    def _parseDoc(self, doc):
        infolist = []
        entryList = doc.getElementsByTagName('PubmedArticle')
        if len(entryList) > 0:
            for entry in entryList:
                try:
                    doi = ''
                    info = {}
                    for node in entry.childNodes:
                        if node.nodeType != node.ELEMENT_NODE:
                            continue
                        #
                        if node.tagName == 'MedlineCitation':
                            info = self._processMedlineCitationNode(node)
                        elif node.tagName == 'PubmedData':
                            doi = self._processPubmedDataNode(node)
                        #
                    #
                    if info:
                        if doi and ('pdbx_database_id_DOI' not in info):
                            info['pdbx_database_id_DOI'] = doi
                        #
                        infolist.append(info)
                    #
                except:  # noqa: E722 pylint: disable=bare-except
                    continue
            #
        #
        return infolist

    def _processMedlineCitationNode(self, entry):
        id = ''  # pylint: disable=redefined-builtin
        info = {}
        for node in entry.childNodes:
            if node.nodeType != node.ELEMENT_NODE:
                continue
            #
            if node.tagName == 'PMID':
                id = str(node.firstChild.data)
            #
            elif node.tagName == 'Article':
                for childnode in node.childNodes:
                    if childnode.nodeType != childnode.ELEMENT_NODE:
                        continue
                    #
                    if childnode.tagName == 'Journal':
                        self._parseJournalInfo(childnode.childNodes, info)
                    #
                    elif childnode.tagName == 'ArticleDate':
                        if ('year' not in info) or (not info['year']):
                            for grandchildnode in childnode.childNodes:
                                if grandchildnode.nodeType != grandchildnode.ELEMENT_NODE:
                                    continue
                                #
                                if grandchildnode.tagName == 'Year':
                                    info['year'] = self._processNodes(grandchildnode.childNodes, False)
                                #
                            #
                        #
                    elif childnode.tagName == 'ArticleTitle':
                        info['title'] = self._processNodes(childnode.childNodes, True)
                    elif childnode.tagName == 'Pagination':
                        self._parsePageInfo(childnode.childNodes, info)
                    elif childnode.tagName == 'AuthorList':
                        self._parseAuthorList(childnode.childNodes, info)
                    elif childnode.tagName == 'ELocationID':
                        if childnode.hasAttribute('EIdType') and childnode.hasAttribute('ValidYN'):
                            EIdType = childnode.getAttribute('EIdType')
                            ValidYN = childnode.getAttribute('ValidYN')
                            if EIdType == 'doi' and ValidYN == 'Y':
                                info['pdbx_database_id_DOI'] = self._processNodes(childnode.childNodes, False)
                            #
                        #
                    #
                #
            elif node.tagName == 'MedlineJournalInfo':
                if 'journal_abbrev' in info:
                    continue
                #
                for childnode in node.childNodes:
                    if childnode.nodeType != childnode.ELEMENT_NODE:
                        continue
                    #
                    if childnode.tagName == 'MedlineTA':
                        info['journal_abbrev'] = self._processNodes(childnode.childNodes, False)
                    #
                #
            #
        #
        if id and info:
            info['pdbx_database_id_PubMed'] = id
        #
        return info

    def _processPubmedDataNode(self, entry):
        doi = ''
        for node in entry.childNodes:
            if node.nodeType != node.ELEMENT_NODE:
                continue
            #
            if node.tagName == 'ArticleIdList':
                for childnode in node.childNodes:
                    if childnode.nodeType != childnode.ELEMENT_NODE:
                        continue
                    #
                    if childnode.tagName == 'ArticleId':
                        if childnode.hasAttribute('IdType'):
                            IdType = childnode.getAttribute('IdType')
                            if IdType == 'doi':
                                doi = self._processNodes(childnode.childNodes, False)
                            #
                        #
                    #
                #
            #
        #
        return doi

    def _parseJournalInfo(self, childNodes, info):
        for node in childNodes:
            if node.nodeType != node.ELEMENT_NODE:
                continue
            #
            if node.tagName == 'ISSN':
                info['journal_id_ISSN'] = self._processNodes(node.childNodes, False)
            elif node.tagName == 'JournalIssue':
                self._parseJournalIssue(node.childNodes, info)
            elif node.tagName == 'ISOAbbreviation':
                info['journal_abbrev'] = self._processNodes(node.childNodes, False)
        #

    def _parseJournalIssue(self, childNodes, info):
        for node in childNodes:
            if node.nodeType != node.ELEMENT_NODE:
                continue
            #
            if node.tagName == 'Volume':
                info['journal_volume'] = self._processNodes(node.childNodes, False)
            elif node.tagName == 'PubDate':
                for childnode in node.childNodes:
                    if childnode.nodeType != childnode.ELEMENT_NODE:
                        continue
                    #
                    if childnode.tagName == 'Year':
                        info['year'] = self._processNodes(childnode.childNodes, False)
                    #
                #

    #               if (not info.has_key('year')) or (not info['year']):
    #                   for childnode in node.childNodes:
    #                       if childnode.nodeType != childnode.ELEMENT_NODE:
    #                           continue
    #                       #
    #                       if childnode.tagName == 'MedlineDate':
    #                           info['year'] = self._processNodes(childnode.childNodes, False)
    #                       #
    #                   #
    #               #
    #
    #

    def _parsePageInfo(self, childNodes, info):
        for node in childNodes:
            if node.nodeType != node.ELEMENT_NODE:
                continue
            #
            if node.tagName == 'MedlinePgn':
                pages = self._processNodes(node.childNodes, False)
                if not pages:
                    continue
                #
                first = pages
                last = pages
                plist = pages.split('-')
                if len(plist) == 2:
                    first = plist[0].strip()
                    last = plist[1].strip()
                    if len(last) < len(first):
                        idx = len(first) - len(last)
                        last = first[0:idx] + last
                    #
                #
                info['page_first'] = first
                info['page_last'] = last
            #
        #

    def _parseAuthorList(self, childNodes, info):
        authorListString = ''
        authorListArray = []
        for node in childNodes:
            if node.nodeType != node.ELEMENT_NODE or \
                    node.tagName != 'Author':
                continue
            #
            initial = ''
            lastName = ''
            suffix = ''
            orcid = ''
            for childnode in node.childNodes:
                if childnode.nodeType != childnode.ELEMENT_NODE:
                    continue
                #
                if childnode.tagName == 'LastName':
                    lastName = self._processNodes(childnode.childNodes, False)
                elif childnode.tagName == 'Initials':
                    initial = self._processNodes(childnode.childNodes, False)
                elif childnode.tagName == 'Suffix':
                    suffix = self._processNodes(childnode.childNodes, False)
                    # if suffix and (not suffix.endswith('.')):
                    if (suffix == 'Jr') or (suffix == 'Sr'):
                        suffix += '.'
                    #
                elif childnode.tagName == 'Identifier':
                    if childnode.hasAttribute('Source'):
                        Source = childnode.getAttribute('Source')
                        if Source == 'ORCID':
                            orcid = self._processNodes(childnode.childNodes, False)
                            orcid = orcid.replace(' ', '').replace('http://orcid.org/', '').replace(
                                'https://orcid.org/', '')
                        #
                    #
                #
            #
            if not initial or not lastName:
                continue
            #
            initialWithDot = ''
            for c in initial:
                initialWithDot += c + '.'
            #
            if suffix:
                lastName += ' ' + suffix
            #
            if authorListString:
                authorListString += ','
            #
            authorListString += initialWithDot + lastName
            authorListArray.append({"name": lastName + ", " + initialWithDot, "orcid": orcid})
        #
        if authorListString:
            info['author'] = authorListString
        #
        if authorListArray:
            info['author_list'] = authorListArray
        #

    def _processNodes(self, childNodes, angstromFlag):
        text = ''
        for node in childNodes:
            if node.nodeType == node.ELEMENT_NODE:
                if text:
                    text += ' '
                #
                text += self._processNodes(node.childNodes, angstromFlag)
            else:
                if text:
                    text += ' '
                #
                text += self._processData(node, angstromFlag)
            #
        #
        return text

    def _processData(self, node, angstromFlag):
        if not node:
            return ''
        #
        return self.__codeHandler.process(node.data, angstromFlag)


if __name__ == "__main__":
    parser = FetchResultParser(sys.argv[1])
    pList = parser.getPubmedInfoList()
    for pdir in pList:
        for k, v in pdir.items():
            if isinstance(v, tuple) or isinstance(v, list) or isinstance(v, dict):
                print(k + '=')
                print(v)
            else:
                print(k + '=' + str(v))
            #
        #
    #
