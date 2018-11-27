##
# File:  Emd2XmlTranslator.py
# Date:  17-Sep-2015
# Updates:
##

__docformat__ = "restructuredtext en"
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import os, sys
from cifEMDBTranslator import CifEMDBTranslator

def cif2xml(input, output):
    translator = CifEMDBTranslator()
    translator.readCifFile(input)
    translator.translateCif2Xml()
    translator.writeXmlFile(output)

if __name__ == '__main__':
    cif2xml(sys.argv[1], sys.argv[2])
