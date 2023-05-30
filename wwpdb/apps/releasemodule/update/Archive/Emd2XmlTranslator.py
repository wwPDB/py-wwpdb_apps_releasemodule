##
# File:  Emd2XmlTranslator.py
# Date:  17-Sep-2015
# Updates:
##

__docformat__ = "restructuredtext en"
__author__ = "Zukang Feng"
__email__ = "zfeng@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.07"

import sys,traceback
from wwpdb.utils.emdb.cif_emdb_translator.cif_emdb_translator import CifEMDBTranslator

def cif2xml(cifFile, xmlFile, logFile):
    try:
        translator = CifEMDBTranslator()
        translator.set_logger_logging(log_error=True, error_log_file_name=logFile)
        translator.read_emd_map_v2_cif_file()
        #translator.translate_and_validate(in_cif=cifFile, out_xml=xmlFile)
        translator.translate(in_cif=cifFile, out_xml=xmlFile)
        translator.write_logger_logs(write_error_log=True)
    except:
        traceback.print_exc(file=sys.stderr)
    #

if __name__ == '__main__':
    cif2xml(sys.argv[1], sys.argv[2], sys.argv[3])
