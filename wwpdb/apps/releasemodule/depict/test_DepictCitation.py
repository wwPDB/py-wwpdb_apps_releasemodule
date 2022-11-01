import os
import sys

from wwpdb.utils.session.WebRequest import InputRequest
from wwpdb.apps.releasemodule.depict.DepictCitation_v2 import DepictCitation
from wwpdb.apps.releasemodule.citation.ReadCitationFinderResult_v2 import ReadCitationFinderResult
#

# This will not run - as ReadCitationFinderResult has changed
cReader = ReadCitationFinderResult(summaryFile=sys.argv[1], pubmedFile=sys.argv[2], verbose=False, log=sys.stderr)  # pylint: disable=unexpected-keyword-arg
list = cReader.getEntryList(sys.argv[3])  # pylint: disable=redefined-builtin
if list:
    reqObj = InputRequest({}, verbose=False, log=sys.stderr)
    reqObj.setValue("TemplatePath", os.path.join("/net/wwpdb_da/da_top/wwpdb_da_test/webapps", "htdocs", "releasemodule", "templates"))
    dp = DepictCitation(reqObj=reqObj, resultList=list, verbose=False, log=sys.stderr)
    content = dp.DoRender()
    print(content)
