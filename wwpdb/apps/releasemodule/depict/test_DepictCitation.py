import os,sys

from wwpdb.utils.rcsb.WebRequest import InputRequest,ResponseContent
from wwpdb.apps.releasemodule.depict.DepictCitation import DepictCitation
from wwpdb.apps.releasemodule.citation.ReadCitationFinderResult import ReadCitationFinderResult
#

cReader = ReadCitationFinderResult(summaryFile=sys.argv[1],pubmedFile=sys.argv[2],annotator=sys.argv[3],verbose=False, log=sys.stderr)
list = cReader.getEntryList()
if list:
    reqObj=InputRequest({},verbose=False,log=sys.stderr)
    reqObj.setValue("TemplatePath", os.path.join("/net/wwpdb_da/da_top/wwpdb_da_test/webapps","htdocs","releasemodule","templates"))
    dp = DepictCitation(reqObj=reqObj, resultList=list, verbose=False, log=sys.stderr)
    content = dp.DoRender()
    print content
