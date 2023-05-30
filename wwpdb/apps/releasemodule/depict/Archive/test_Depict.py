import os
import sys

from wwpdb.utils.session.WebRequest import InputRequest
from wwpdb.apps.releasemodule.depict.Depict import Depict
from wwpdb.apps.releasemodule.utils.DBUtil import DBUtil
#

reqObj = InputRequest({}, verbose=False, log=sys.stderr)
reqObj.setValue("TemplatePath", os.path.join("/net/wwpdb_da/da_top/wwpdb_da_test/webapps", "htdocs", "releasemodule", "templates"))
reqObj.setValue('FormTemplate', 'request/request_form_tmplt.html')
reqObj.setValue('RowTemplate', 'request/request_row_tmplt.html')

items = ['structure_id', 'pdb_id', 'author_approval_type', 'status_code',
         'author_release_status_code', 'exp_method', 'initial_deposition_date',
         'date_hold_coordinates']
annotator = "CS"
db = DBUtil(verbose=False, log=sys.stderr)
list = db.getAuthEntryInfo(annotator)
dp = Depict(reqObj=reqObj, resultList=list, itemList=items, verbose=False, log=sys.stderr)
content = dp.DoRender()
print(content)
