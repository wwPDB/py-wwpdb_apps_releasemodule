
import os, sys, string, traceback

from pdbx_v2.trans.InstanceMapper  import InstanceMapper
from wwpdb.api.facade.ConfigInfo   import ConfigInfo

def Convertor(inputfile, outputfile):
    siteId = os.environ['WWPDB_SITE_ID']
    cI = ConfigInfo(siteId)
    #
    im = InstanceMapper(verbose=True, log=sys.stderr)
    im.setMappingFilePath(cI.get('SITE_EXT_DICT_MAP_EMD_FILE_PATH'))
    ok = im.translate(inputfile, outputfile)

if __name__ == '__main__':
    try:
       Convertor(sys.argv[1], sys.argv[2])
    except:
        traceback.print_exc(file=sys.stderr)
    #
