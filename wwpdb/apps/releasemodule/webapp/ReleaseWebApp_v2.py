##
# File:  ReleaseWebApp.py
# Date:  27-Jun-2013
# Updates:
##
"""
Chemeditor web request and response processing modules.

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

try:
    import cPickle as pickle
except ImportError:
    import pickle as pickle

import os
import sys
import tarfile
import traceback

from wwpdb.utils.config.ConfigInfo import ConfigInfo
from wwpdb.utils.config.ConfigInfoApp import ConfigInfoAppCommon
from wwpdb.utils.session.WebRequest import InputRequest, ResponseContent
from wwpdb.apps.releasemodule.citation.ReadCitationFinderResult_v2 import ReadCitationFinderResult
from wwpdb.apps.releasemodule.depict.DepictAnnotatorHistory import DepictAnnotatorHistory
from wwpdb.apps.releasemodule.depict.DepictCitation_v2 import DepictCitation
from wwpdb.apps.releasemodule.depict.DepictCitationForm_v2 import DepictCitationForm
from wwpdb.apps.releasemodule.depict.DepictEntryHistory import DepictEntryHistory
from wwpdb.apps.releasemodule.depict.DepictReleaseInfo import DepictReleaseInfo
from wwpdb.apps.releasemodule.depict.DepictRemovalMark import DepictRemovalMark
from wwpdb.apps.releasemodule.depict.DepictRequest import DepictRequest
from wwpdb.apps.releasemodule.update.CitationFormParser_v2 import CitationFormParser
from wwpdb.apps.releasemodule.update.EntryFormParser_v2 import EntryFormParser
from wwpdb.apps.releasemodule.update.MultiUpdateProcess import MultiUpdateProcess
from wwpdb.apps.releasemodule.update.UpdateFormParser import UpdateFormParser
from wwpdb.apps.releasemodule.utils.CombineDbApi import CombineDbApi
from wwpdb.apps.releasemodule.utils.Utility import FindFiles, FindLogFiles
from wwpdb.io.locator.PathInfo import PathInfo
#


class ReleaseWebApp(object):
    """Handle request and response object processing for release module web application.

    """
    def __init__(self, parameterDict=None, verbose=False, log=sys.stderr, siteId="WWPDB_DEV"):
        """
        Create an instance of `ReleaseWebApp` to manage a release module web request.

         :param `parameterDict`: dictionary storing parameter information from the web request.
             Storage model for GET and POST parameter data is a dictionary of lists.
         :param `verbose`:  boolean flag to activate verbose logging.
         :param `log`:      stream for logging.

        """
        if parameterDict is None:
            parameterDict = {}

        self.__verbose = verbose
        self.__lfh = log
        self.__debug = False
        self.__siteId = siteId
        self.__cI = ConfigInfo(self.__siteId)
        self.__topPath = self.__cI.get('SITE_WEB_APPS_TOP_PATH')
        #

        if isinstance(parameterDict, dict):
            self.__myParameterDict = parameterDict
        else:
            self.__myParameterDict = {}

        if self.__verbose:
            self.__lfh.write("+ReleaseWebApp.__init() - REQUEST STARTING ------------------------------------\n")
            self.__lfh.write("+ReleaseWebApp.__init() - dumping input parameter dictionary \n")
            # self.__lfh.write("%s" % (''.join(self.__dumpRequest())))

        self.__reqObj = InputRequest(self.__myParameterDict, verbose=self.__verbose, log=self.__lfh)

        self.__topSessionPath = self.__cI.get('SITE_WEB_APPS_TOP_SESSIONS_PATH')
        self.__templatePath = os.path.join(self.__topPath, "htdocs", "releasemodule", "templates")
        #
        self.__reqObj.setValue("TopSessionPath", self.__topSessionPath)
        self.__reqObj.setValue("TemplatePath", self.__templatePath)
        self.__reqObj.setValue("TopPath", self.__topPath)
        self.__reqObj.setValue("WWPDB_SITE_ID", self.__siteId)
        os.environ["WWPDB_SITE_ID"] = self.__siteId
        #
        self.__reqObj.setReturnFormat(return_format="html")
        #
        if self.__verbose:
            self.__lfh.write("-----------------------------------------------------\n")
            self.__lfh.write("+ReleaseWebApp.__init() Leaving _init with request contents\n")
            self.__reqObj.printIt(ofh=self.__lfh)
            self.__lfh.write("---------------ReleaseWebApp - done -------------------------------\n")
            self.__lfh.flush()

    def doOp(self):
        """ Execute request and package results in response dictionary.

        :Returns:
             A dictionary containing response data for the input request.
             Minimally, the content of this dictionary will include the
             keys: CONTENT_TYPE and REQUEST_STRING.
        """
        stw = ReleaseWebAppWorker(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        rC = stw.doOp()
        if self.__debug:
            rqp = self.__reqObj.getRequestPath()
            self.__lfh.write("+ReleaseWebApp.doOp() operation %s\n" % rqp)
            self.__lfh.write("+ReleaseWebApp.doOp() return format %s\n" % self.__reqObj.getReturnFormat())
            if rC is not None:
                self.__lfh.write("%s" % (''.join(rC.dump())))
            else:
                self.__lfh.write("+ReleaseWebApp.doOp() return object is empty\n")

        #
        # Package return according to the request return_format -
        #
        return rC.get()

    def __dumpRequest(self):  # pylint: disable=unused-private-member
        """Utility method to format the contents of the internal parameter dictionary
           containing data from the input web request.

           :Returns:
               ``list`` of formatted text lines
        """
        retL = []
        retL.append("\n-----------------ReleaseWebApp().__dumpRequest()-----------------------------\n")
        retL.append("Parameter dictionary length = %d\n" % len(self.__myParameterDict))
        for k, vL in self.__myParameterDict.items():
            retL.append("Parameter %30s :" % k)
            for v in vL:
                retL.append(" ->  %s\n" % v)
        retL.append("-------------------------------------------------------------\n")
        return retL


class ReleaseWebAppWorker(object):
    def __init__(self, reqObj=None, verbose=False, log=sys.stderr):
        """
         Worker methods for the chemical component editor application

         Performs URL - application mapping and application launching
         for chemical component editor tool.

         All operations can be driven from this interface which can
         supplied with control information from web application request
         or from a testing application.
        """
        self.__verbose = verbose
        self.__lfh = log
        self.__reqObj = reqObj
        self.__siteId = str(self.__reqObj.getValue("WWPDB_SITE_ID"))
        self.__cI = ConfigInfo(self.__siteId)
        self.__cICommon = ConfigInfoAppCommon(self.__siteId)
        self.__annotator = str(self.__reqObj.getValue('annotator'))
        self.__owner = str(self.__reqObj.getValue('owner'))
        if not self.__owner and self.__annotator:
            self.__owner = self.__annotator
        #
        self.__appPathD = {'/service/environment/dump': '_dumpOp',
                           '/service/release/get_anno_list': '_GetAnnoListOp',
                           '/service/release/start': '_StandaloneOp',
                           '/service/release/new_session/wf': '_WorkflowOp',
                           '/service/release/citation_finder': '_CitationFinderPage',
                           '/service/release/citation_update': '_CitationUpdatePage',
                           '/service/release/release_onhold': '_RequestReleasePage',
                           '/service/release/expired_onhold': '_ExpiredEntryPage',
                           '/service/release/release_entry': '_ReleasedEntryPage',
                           # '/service/release/check_marked_pubmed_id': '_MarkedPubmedIDPage',
                           '/service/release/check_marked_pubmed_id': '_DisPlayMarkedPubmedIDOp',
                           '/service/release/update': '_UpdateOp',
                           '/service/release/citation_request': '_CitationRequestOp',
                           '/service/release/entry_request': '_EntryRequestOp',
                           '/service/release/marked_pubmed_request': '_MarkedPubmedRequestOp',
                           '/service/release/mark_pubmed_id': '_MarkPubmedIDOp',
                           '/service/release/remove_marked_pubmed': '_RemoveMarkedPubmedIDOp',
                           '/service/release/download_file': '_downloadFilePage',
                           '/service/release/download_logfile': '_downloadLogFilePage',
                           '/service/release/download_file_with_fileid': '_downloadWithFileIdOp',
                           '/service/release/download_file_with_filepath': '_downloadWithFilePathOp',
                           '/service/release/view_entry_history': '_viewEntryHistoryOp',
                           '/service/release/view_entry_history_detail': '_viewEntryHistoryDetailOp',
                           '/service/release/view_release_history': '_viewAnnotatorHistoryOp',
                           '/service/release/view_release_info': '_viewReleaseInfoOp'
                           }

    def doOp(self):
        """Map operation to path and invoke operation.

            :Returns:

            Operation output is packaged in a ResponseContent() object.
        """
        return self.__doOpException()

    # def __doOpNoException(self):
    #     """Map operation to path and invoke operation.  No exception handling is performed.

    #         :Returns:

    #         Operation output is packaged in a ResponseContent() object.
    #     """
    #     #
    #     reqPath = self.__reqObj.getRequestPath()
    #     if reqPath not in self.__appPathD:
    #         # bail out if operation is unknown -
    #         rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
    #         rC.setError(errMsg='Unknown operation')
    #         return rC
    #     else:
    #         mth = getattr(self, self.__appPathD[reqPath], None)
    #         rC = mth()
    #     return rC

    def __doOpException(self):
        """Map operation to path and invoke operation.  Exceptions are caught within this method.

            :Returns:

            Operation output is packaged in a ResponseContent() object.
        """
        #
        try:
            reqPath = self.__reqObj.getRequestPath()
            if reqPath not in self.__appPathD:
                # bail out if operation is unknown -
                rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
                rC.setError(errMsg='Unknown operation')
            else:
                mth = getattr(self, self.__appPathD[reqPath], None)
                rC = mth()
            return rC
        except:  # noqa: E722 pylint: disable=bare-except
            traceback.print_exc(file=self.__lfh)
            rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
            rC.setError(errMsg='Operation failure')
            return rC

    ################################################################################################################
    # ------------------------------------------------------------------------------------------------------------
    #      Top-level REST methods
    # ------------------------------------------------------------------------------------------------------------
    #
    def _dumpOp(self):
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        rC.setHtmlList(self.__reqObj.dump(format='html'))
        return rC

    def _GetAnnoListOp(self):
        """ Get Annotator selection list
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._GetAnnoListOp() Starting now\n")
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        dbUtil = CombineDbApi(siteId=self.__siteId, verbose=self.__verbose, log=self.__lfh)
        #
        rC.setText(text=self.__getAnnotatorSelection(dbUtil, '', 'annotator'))
        return rC

    def _StandaloneOp(self):
        """ Launch release module first-level interface
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._StandaloneOp() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="html")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        dbUtil = CombineDbApi(siteId=self.__siteId, path=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        #
        myD = {}
        myD['sessionid'] = self.__sessionId
        myD['identifier'] = str(self.__reqObj.getValue('identifier'))
        myD['filesource'] = str(self.__reqObj.getValue('filesource'))
        myD['instance'] = str(self.__reqObj.getValue('instance'))
        myD['annotator'] = self.__annotator
        myD['owner_selection'] = self.__getAnnotatorSelection(dbUtil, self.__owner, 'owner')
        citPath = self.__cICommon.get_citation_finder_path()
        resultFile = os.path.join(citPath, 'citation_finder_' + self.__siteId + '.db')
        self.__lfh.write("+ReleaseWebAppWorker._StandaloneOp() resultFile %s\n" % resultFile)
        if not os.access(resultFile, os.F_OK):
            resultFile = os.path.join(citPath, 'citation_finder_WWPDB_DEPLOY_TEST.db')
        #
        cReader = ReadCitationFinderResult(path=self.__sessionPath, dbUtil=dbUtil, siteId=self.__siteId, pickleFile=resultFile,
                                           verbose=self.__verbose, log=self.__lfh)
        entryList = cReader.getEntryList(self.__owner)
        if entryList:
            self.__reqObj.setValue('task', 'Citation Finder')
            self.__reqObj.setValue('owner', self.__owner)
            self.__reqObj.setValue('sessionPath', self.__sessionPath)
            dp = DepictCitation(reqObj=self.__reqObj, resultList=entryList, verbose=self.__verbose, log=self.__lfh)
            myD['result_list'] = dp.DoRender()
        else:
            myD['result_list'] = self.__returnNotFound(self.__owner)
        #
        rC.setHtmlText(self.__processTemplate('release_launch_tmplt.html', myD))
        #
        return rC

    def _WorkflowOp(self):
        """ Launch release module first-level interface
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._WorkflowOp() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="html")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        dbUtil = CombineDbApi(siteId=self.__siteId, path=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        #
        entryId = str(self.__reqObj.getValue('identifier'))
        citation_update = str(self.__reqObj.getValue('citation_update'))
        myD = {}
        myD['sessionid'] = self.__sessionId
        myD['identifier'] = entryId
        myD['filesource'] = str(self.__reqObj.getValue('filesource'))
        myD['instance'] = str(self.__reqObj.getValue('instance'))
        myD['annotator'] = self.__annotator
        myD['owner_selection'] = self.__getAnnotatorSelection(dbUtil, self.__owner, 'owner')
        #
        entryList = []
        if (citation_update == 'pubmed') and entryId:
            myDir = {}
            myDir['sessionid'] = self.__sessionId
            myDir['annotator'] = self.__annotator
            myDir['identifier'] = entryId
            myDir['task'] = 'Citation Update with Pubmed'
            myD['result_list'] = self.__processTemplate('citation_request/input_form_with_pubmed_tmplt.html', myDir)
        elif (citation_update == 'no_pubmed') and entryId:
            myDir = {}
            myDir['sessionid'] = self.__sessionId
            myDir['annotator'] = self.__annotator
            myDir['identifier'] = entryId
            myDir['task'] = 'Citation Update without Pubmed'
            myD['result_list'] = self.__processTemplate('citation_request/input_form_without_pubmed_tmplt.html', myDir)
        else:
            if entryId:
                entryList = dbUtil.getEntryInfo([entryId])
            else:
                entryList = dbUtil.getRequestReleaseEntryInfo(self.__owner)
            #
            if entryList:
                self.__reqObj.setValue('task', 'Entries to be released')
                self.__reqObj.setValue('owner', self.__owner)
                myD['result_list'] = self.__depcitRequestForm(entryList=entryList, autoSelection=True)
            else:
                myDir = {}
                myDir['sessionid'] = self.__sessionId
                myDir['annotator'] = self.__annotator
                myDir['task'] = 'Entries to be released'
                myD['result_list'] = self.__processTemplate('request/input_form_tmplt.html', myDir)
            #
        #
        rC.setHtmlText(self.__processTemplate('release_launch_tmplt.html', myD))
        #
        return rC

    def __depcitRequestForm(self, entryList=None, autoSelection=False):
        if entryList is None:
            entryList = []

        self.__reqObj.setValue('FormTemplate', 'request/request_form_tmplt.html')
        self.__reqObj.setValue('RowTemplate', 'request/request_row_tmplt.html')
        self.__reqObj.setValue('option', 'request_release')
        items = self.__getItemList('request/request_item_list')
        dp = DepictRequest(reqObj=self.__reqObj, resultList=entryList, itemList=items, verbose=self.__verbose, log=self.__lfh)
        return dp.DoRender(autoSelectionFlag=autoSelection)

    def _CitationFinderPage(self):
        """ Launch citation finder page
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._CitationFinderPage() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        #
        citPath = self.__cICommon.get_citation_finder_path()
        resultFile = os.path.join(citPath, 'citation_finder_' + self.__siteId + '.db')
        self.__lfh.write("+ReleaseWebAppWorker._StandaloneOp() resultFile %s\n" % resultFile)
        if not os.access(resultFile, os.F_OK):
            resultFile = os.path.join(citPath, 'citation_finder_WWPDB_DEPLOY_TEST.db')
        #
        cReader = ReadCitationFinderResult(path=self.__sessionPath, dbUtil=None, siteId=self.__siteId, pickleFile=resultFile,
                                           verbose=self.__verbose, log=self.__lfh)
        entryList = cReader.getEntryList(self.__owner)
        if entryList:
            self.__reqObj.setValue('sessionPath', self.__sessionPath)
            dp = DepictCitation(reqObj=self.__reqObj, resultList=entryList, verbose=self.__verbose, log=self.__lfh)
            rC.setText(text=dp.DoRender())
        else:
            rC.setText(text=self.__returnNotFound(self.__owner))
        #
        return rC

    def _CitationUpdatePage(self):
        """ Launch citation update starting page
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._CitationUpdatePage() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        myD = {}
        myD['sessionid'] = self.__sessionId
        myD['annotator'] = self.__annotator
        myD['identifier'] = str(self.__reqObj.getValue('identifier'))
        myD['task'] = str(self.__reqObj.getValue('task'))
        #
        if myD['task'] == 'Citation Update with Pubmed':
            rC.setText(text=self.__processTemplate('citation_request/input_form_with_pubmed_tmplt.html', myD))
        else:
            rC.setText(text=self.__processTemplate('citation_request/input_form_without_pubmed_tmplt.html', myD))
        #
        return rC

    def _RequestReleasePage(self):
        """ Launch requested release page based on author's input status
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._RequestReleasePage() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        dbUtil = CombineDbApi(siteId=self.__siteId, path=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        entryList = dbUtil.getRequestReleaseEntryInfo(self.__owner)
        #
        if entryList:
            rC.setText(text=self.__depcitRequestForm(entryList=entryList))
        else:
            myDir = {}
            myDir['sessionid'] = self.__sessionId
            myDir['annotator'] = self.__annotator
            myDir['task'] = str(self.__reqObj.getValue('task'))
            rC.setText(text=self.__processTemplate('request/input_form_tmplt.html', myDir))
        #
        return rC

    def _ExpiredEntryPage(self):
        """ Launch expired entry release page based on author's input initial
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._ExpiredEntryPage() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        dbUtil = CombineDbApi(siteId=self.__siteId, path=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        entryList = dbUtil.getExpiredEntryInfo(self.__owner)
        #
        if entryList:
            rC.setText(text=self.__depcitRequestForm(entryList=entryList))
        else:
            returnText = '<h1 style="text-align:center">' + str(self.__reqObj.getValue('task')) + '</h1></br>' \
                + '<h2 style="text-align:center">No entry found.</h2>'
            rC.setText(text=returnText)
        #
        return rC

    def _ReleasedEntryPage(self):
        """ Launch released entries page based on author's initial
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._ReleasedEntryPage() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        dbUtil = CombineDbApi(siteId=self.__siteId, path=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        entryList = []
        id_list = self.__getReleasedEntryList(dbUtil)
        if id_list:
            entryList = dbUtil.getEntryInfo(id_list)
        #
        if entryList:
            self.__reqObj.setValue('FormTemplate', 'request/pull_from_release_form_tmplt.html')
            self.__reqObj.setValue('RowTemplate', 'request/pull_from_release_row_tmplt.html')
            self.__reqObj.setValue('option', 'pull_release')
            items = self.__getItemList('request/pull_item_list')
            dp = DepictRequest(reqObj=self.__reqObj, resultList=entryList, itemList=items, verbose=self.__verbose, log=self.__lfh)
            rC.setText(text=dp.DoRender())
        else:
            rC.setText(text=self.__returnNotFound(self.__owner))
        #
        return rC

    def _MarkedPubmedIDPage(self):
        """ Launch review marked pubmed ID page
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._MarkedPubmedIDPage() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        myD = {}
        myD['sessionid'] = self.__sessionId
        myD['annotator'] = self.__annotator
        myD['task'] = str(self.__reqObj.getValue('task'))
        #
        rC.setText(text=self.__processTemplate('citation_finder/marked_pubmed_input_form_tmplt.html', myD))
        return rC

    def _UpdateOp(self):
        """ Launch update operation
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._UpdateOp() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        frmParser = UpdateFormParser(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        errContent = frmParser.getErrorContent()
        if errContent:
            rC.setError(errMsg=errContent)
            return rC
        #
        updOp = MultiUpdateProcess(reqObj=self.__reqObj, updateList=frmParser.getUpdateList(), verbose=self.__verbose, log=self.__lfh)
        updOp.run()
        errContent = updOp.getErrorContent()
        rtnContent = updOp.getReturnContent()
        if errContent:
            rC.setError(errMsg=errContent)
        else:
            rC.setText(text=rtnContent)
        #
        return rC

    def _CitationRequestOp(self):
        """ Launch request operation
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._CitationRequestOp() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        citationformflag = str(self.__reqObj.getValue('citationformflag'))
        requestParser = CitationFormParser(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        content = requestParser.getErrorContent()
        self.__lfh.write("+ReleaseWebAppWorker._CitationRequestOp() content=%r\n" % content)
        if content:
            rC.setError(errMsg=content)
            return rC
        #
        entryList = requestParser.getEntryList()
        self.__lfh.write("+ReleaseWebAppWorker._CitationRequestOp() entryList=%d\n" % len(entryList))
        if entryList:
            self.__reqObj.setValue('sessionPath', self.__sessionPath)
            if citationformflag == 'yes':
                dp = DepictCitationForm(reqObj=self.__reqObj, resultList=entryList, verbose=self.__verbose, log=self.__lfh)
                context = dp.DoRender()
            else:
                dp = DepictCitation(reqObj=self.__reqObj, resultList=entryList, verbose=self.__verbose, log=self.__lfh)
                context = dp.DoRender(finderFlag=False)
            rC.setText(text=context)
        else:
            rC.setError(errMsg='Unknown error')

        #
        return rC

    def _EntryRequestOp(self):
        """ Launch request operation
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._EntryRequestOp() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        requestParser = EntryFormParser(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        content = requestParser.getErrorContent()
        if content:
            rC.setError(errMsg=content)
            return rC
        #
        entryList = requestParser.getEntryList()
        if entryList:
            rC.setText(text=self.__depcitRequestForm(entryList=entryList))
        else:
            rC.setError(errMsg='Unknown error')
        #
        return rC

    def _DisPlayMarkedPubmedIDOp(self):
        """ Display all marked pubmed IDs for PROC, AUTH, HPUB, HOLD, REPL, AUCO, REUP, WAIT, REFI entries
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._DisPlayMarkedPubmedIDOp() Starting now\n")
        #
        statusList = ['PROC', 'AUTH', 'HPUB', 'HOLD', 'REPL', 'AUCO', 'REUP', 'WAIT', 'REFI', 'REL']
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        dbUtil = CombineDbApi(siteId=self.__siteId, path=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        entryList = dbUtil.getEntriesWithStatusList(self.__owner, statusList)
        foundList = []
        if entryList:
            pI = PathInfo(siteId=self.__siteId, sessionPath=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
            for dataDict in entryList:
                try:
                    archiveDirPath = pI.getDirPath(dataSetId=dataDict['structure_id'], wfInstanceId=None, contentType='model',
                                                   formatType='pdbx', fileSource='archive', versionId='latest', partNumber=1)
                    pickle_file = os.path.join(archiveDirPath, 'marked_pubmed_id.pic')
                    if os.access(pickle_file, os.F_OK):
                        foundList.append(dataDict)
                    #
                except:  # noqa: E722 pylint: disable=bare-except
                    traceback.print_exc(file=self.__lfh)
                #
            #
        #
        if foundList:
            drm = DepictRemovalMark(reqObj=self.__reqObj, resultList=foundList, verbose=self.__verbose, log=self.__lfh)
            rC.setText(text=drm.DoRender())
        else:
            rC.setText(text=self.__returnNotFound(self.__owner))
        #
        return rC

    def _MarkedPubmedRequestOp(self):
        """ Launch check marked pubmed ID operation
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._MarkedPubmedRequestOp() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        requestParser = EntryFormParser(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        content = requestParser.getErrorContent()
        if content:
            rC.setError(errMsg=content)
            return rC
        #
        entryList = requestParser.getEntryList()
        if entryList:
            drm = DepictRemovalMark(reqObj=self.__reqObj, resultList=entryList, verbose=self.__verbose, log=self.__lfh)
            rC.setText(text=drm.DoRender())
        else:
            rC.setError(errMsg='Unknown error')
        #
        return rC

    def _MarkPubmedIDOp(self):
        """ Mark unwanted pubmed IDs
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._MarkPubmedIDOp() Starting now\n")
        #
        self.__getSession()
        #
        identifier = str(self.__reqObj.getValue('identifier')).upper()
        pubmed_id = str(self.__reqObj.getValue('pubmed_id'))
        #
        pI = PathInfo(siteId=self.__siteId, sessionPath=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        archiveDirPath = pI.getDirPath(dataSetId=identifier, wfInstanceId=None, contentType='model', formatType='pdbx',
                                       fileSource='archive', versionId='latest', partNumber=1)
        pickle_file = os.path.join(archiveDirPath, 'marked_pubmed_id.pic')
        #
        pubmed_id_list = []
        if os.access(pickle_file, os.F_OK):
            fb = open(pickle_file, 'rb')
            pubmed_id_list = pickle.load(fb)
            fb.close()
        #
        pubmed_id_list.append(pubmed_id)
        if len(pubmed_id_list) > 1:
            pubmed_id_list = sorted(set(pubmed_id_list))
        #
        fb = open(pickle_file, 'wb')
        pickle.dump(pubmed_id_list, fb)
        fb.close()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        rC.setText(text='Mark ' + identifier + ' as unwanted.')
        #
        return rC

    def _RemoveMarkedPubmedIDOp(self):
        """ Remove marked pubmed IDs
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._RemoveMarkedPubmedIDOp() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        combList = self.__reqObj.getValueList('combine_id')
        if not combList:
            rC.setError(errMsg='No pubmed ID selected')
            return rC
        #
        map = {}  # pylint: disable=redefined-builtin
        for comb_id in combList:
            clist = comb_id.split(':')
            if clist[0] in map:
                if not clist[1] in map[clist[0]]:
                    map[clist[0]].append(clist[1])
                #
            else:
                pubmed_id_list = []
                pubmed_id_list.append(clist[1])
                map[clist[0]] = pubmed_id_list
            #
        #
        pI = PathInfo(siteId=self.__siteId, sessionPath=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        content = ''
        for structure_id, pubmed_id_list in map.items():
            content += '\n' + structure_id + ': Removed ' + ','.join(pubmed_id_list)
            #
            archiveDirPath = pI.getDirPath(dataSetId=structure_id, wfInstanceId=None, contentType='model', formatType='pdbx',
                                           fileSource='archive', versionId='latest', partNumber=1)
            pickle_file = os.path.join(archiveDirPath, 'marked_pubmed_id.pic')
            #
            existing_pubmed_id_list = []
            if os.access(pickle_file, os.F_OK):
                fb = open(pickle_file, 'rb')
                existing_pubmed_id_list = pickle.load(fb)
                fb.close()
            #
            updated_pubmed_id_list = []
            for pmid in existing_pubmed_id_list:
                if pmid not in pubmed_id_list:
                    updated_pubmed_id_list.append(pmid)
                #
            #
            if updated_pubmed_id_list:
                fb = open(pickle_file, 'wb')
                pickle.dump(updated_pubmed_id_list, fb)
                fb.close()
            else:
                os.remove(pickle_file)
            #
        #
        rC.setText(text=content)
        return rC

    def _downloadFilePage(self):
        """ Launch download file interface
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebApp._downloadFilePage() Starting now\n")
        #
        self.__getSession()
        ungzip_flag = str(self.__reqObj.getValue('ungzip'))
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        filelist = FindFiles(self.__sessionPath)
        if not filelist:
            rC.setText(text='<h3 style="text-align:center">No entry updated</h3>')
        else:
            # for f in ('all_files.tar.gz', 'all_files.tar'):
            #    filename = os.path.join(self.__sessionPath, f)
            #    if os.access(filename, os.F_OK):
            #        os.remove(filename)
            #    #
            #
            content = ''
            filelist.sort()
            if len(filelist) > 1:
                if ungzip_flag == 'true':
                    fname = 'all_files.tar'
                else:
                    fname = 'all_files.tar.gz'
                # for f in filelist:
                #    if f.endswith('.gz'):
                #        fname = 'all_files.tar'
                #        break
                #    #
                #
                tarfilename = os.path.join(self.__sessionPath, fname)
                if ungzip_flag == 'true':
                    tar = tarfile.open(tarfilename, 'w')
                else:
                    tar = tarfile.open(tarfilename, 'w:gz')
                for f in filelist:
                    filename = os.path.join(self.__sessionPath, f)
                    tar.add(filename, arcname=f)
                #
                tar.close()
                filelist.insert(0, fname)
            #
            for f in filelist:
                myD = {}
                myD['sessionid'] = self.__sessionId
                myD['fileid'] = f
                content += self.__processTemplate('one_file_tmplt.html', myD) + '\n'
            #
            rC.setText(text=content)
        #
        return rC

    def _downloadLogFilePage(self):
        """ Launch download log file interface
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebApp._downloadLogFilePage() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        #
        filelist = FindLogFiles(self.__sessionPath)
        if not filelist:
            rC.setText(text='<h3 style="text-align:center">No log file</h3>')
        else:
            content = ''
            filelist.sort()
            for f in filelist:
                myD = {}
                myD['sessionid'] = self.__sessionId
                myD['fileid'] = f
                content += self.__processTemplate('one_file_tmplt.html', myD) + '\n'
            #
            rC.setText(text=content)
        #
        return rC

    def _downloadWithFileIdOp(self):
        """ Download file with fileid
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebApp._downloadWithFileIdOp() Starting now\n")
        #
        self.__getSession()
        fileId = str(self.__reqObj.getValue('fileid'))
        filePath = os.path.join(self.__sessionPath, fileId)
        #
        self.__reqObj.setReturnFormat(return_format="binary")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        rC.setBinaryFile(filePath, attachmentFlag=True)
        return rC

    def _downloadWithFilePathOp(self):
        """ Download file with filepath
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebApp._downloadWithFilePathOp() Starting now\n")
        #
        filePath = str(self.__reqObj.getValue('filepath'))
        #
        self.__reqObj.setReturnFormat(return_format="binary")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        rC.setBinaryFile(filePath, attachmentFlag=True)
        return rC

    def _viewEntryHistoryOp(self):
        """ Launch entry release history view
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebApp._viewEntryHistoryOp() Starting now\n")
        #
        self.__reqObj.setReturnFormat(return_format="html")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        myD = {}
        myD['identifier'] = str(self.__reqObj.getValue('identifier'))
        dp = DepictEntryHistory(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        rC.setHtmlText(self.__processTemplate('view/view_entry_history_tmplt.html', dp.get()))
        return rC

    def _viewEntryHistoryDetailOp(self):
        """ Get entry release history details
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebApp._viewEntryHistoryDetailOp() Starting now\n")
        #
        dp = DepictEntryHistory(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        rC.setText(text=dp.getText())
        #
        return rC

    def _viewAnnotatorHistoryOp(self):
        """ Launch release history view
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebApp._viewAnnotatorHistoryOp() Starting now\n")
        #
        dp = DepictAnnotatorHistory(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        returnText = dp.DoRender()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        if returnText:
            rC.setText(text=returnText)
        else:
            rC.setText(text=self.__returnNotFound(self.__owner))
        #
        return rC

    def _viewReleaseInfoOp(self):
        """ Launch release info. view
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebApp._viewReleaseInfoOp() Starting now\n")
        #
        dp = DepictReleaseInfo(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        returnText = dp.DoRender()
        #
        self.__reqObj.setReturnFormat(return_format="json")
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        if returnText:
            rC.setText(text=returnText)
        else:
            rC.setText(text=self.__returnNotFound(self.__owner))
        #
        return rC

    def __getAnnotatorSelection(self, dbUtil, annotator, name_id):
        """ Generate annotator initials selection list
        """
        site = 'RCSB'
        if self.__cI.get('WWPDB_SITE_LOC').lower() == 'pdbe':
            site = 'PDBe'
        elif self.__cI.get('WWPDB_SITE_LOC').lower() == 'pdbj':
            site = 'PDBj'
        elif self.__cI.get('WWPDB_SITE_LOC').lower() == 'pdbc':
            site = 'PDBc'
        #
        anno_list = self.__getAnnotatorList(dbUtil, site)
        if not anno_list:
            return ''
        #
        anno_list.insert(0, '')
        if name_id == 'owner':
            if site in ['RCSB', 'PDBj', 'PDBc']:
                anno_list.append('OTHER')
            #
            anno_list.append('ALL')
        #
        text = '<select name="' + name_id + '" id="' + name_id + '">\n'
        for anno in anno_list:
            text += '<option value="' + anno + '" '
            if anno == annotator:
                text += 'selected'
            text += '>' + anno + '</option>\n'
        text += '</select>\n'
        return text

    def __getAnnotatorList(self, dbUtil, site):
        argList = []
        if site:
            argList = [site]
        #
        return dbUtil.getFunctionCall(True, 'getAnnoList', argList)

    def __getItemList(self, fn):
        """ Get Item List
        """
        tPath = self.__reqObj.getValue("TemplatePath")
        fPath = os.path.join(tPath, fn)
        ifh = open(fPath, 'r')
        sIn = ifh.read()
        ifh.close()
        #
        tmp_list = sIn.split('\n')
        item_list = []
        for v in tmp_list:
            v = v.strip()
            if v:
                item_list.append(v)
            #
        #
        return item_list

    def __returnNotFound(self, annotator):
        myD = {}
        myD['annotator'] = annotator
        myD['task'] = str(self.__reqObj.getValue('task'))
        return self.__processTemplate('not_found_tmplt.html', myD)

    def __getSession(self):
        """ Join existing session or create new session as required.
        """
        #
        # pylint: disable=attribute-defined-outside-init
        self.__sObj = self.__reqObj.newSessionObj()
        self.__sessionId = self.__sObj.getId()
        self.__sessionPath = self.__sObj.getPath()
        # self.__rltvSessionPath = self.__sObj.getRelativePath()
        if (self.__verbose):
            self.__lfh.write("------------------------------------------------------\n")
            self.__lfh.write("+ReleaseWebAppWorker.__getSession() - creating/joining session %s\n" % self.__sessionId)
            self.__lfh.write("+ReleaseWebAppWorker.__getSession() - session path %s\n" % self.__sessionPath)

    def __getReleasedEntryList(self, dbUtil):
        """ Get released entry Id list
        """
        id_list = []
        anno_list = [self.__owner]
        if self.__owner == 'ALL':
            anno_list = self.__getAnnotatorList(dbUtil, '')
        #
        for ann in anno_list:
            anno_indexfile = os.path.join(self.__cI.get('SITE_ARCHIVE_STORAGE_PATH'), 'for_release', 'index', ann + '.index')
            if not os.access(anno_indexfile, os.F_OK):
                continue
            #
            fb = open(anno_indexfile, 'rb')
            annoPickle = pickle.load(fb)
            fb.close()
            if ('entryDir' not in annoPickle) or (not annoPickle['entryDir']):
                continue
            #
            for entry_id, idMap in annoPickle['entryDir'].items():
                found = False
                for id_type in ('pdb_id', 'emdb_id'):
                    if (id_type not in idMap) or (not idMap[id_type]):
                        continue
                    #
                    upper_id = idMap[id_type].upper()
                    lower_id = idMap[id_type].lower()
                    for release_dir in ('added', 'modified', 'obsolete', 'reloaded', 'emd'):
                        if os.access(os.path.join(self.__cI.get('SITE_ARCHIVE_STORAGE_PATH'), 'for_release', release_dir, upper_id), os.F_OK) or \
                           os.access(os.path.join(self.__cI.get('SITE_ARCHIVE_STORAGE_PATH'), 'for_release', release_dir, lower_id), os.F_OK):
                            found = True
                            break
                        #
                    #
                    if found:
                        break
                    #
                #
                if found:
                    id_list.append(entry_id)
                #
            #
        #
        if id_list:
            id_list = sorted(set(id_list))
        #
        return id_list

    # def __loadAnnotatorPickle(self):
    #     """ Load annotator.index pickle file
    #     """
    #     anno_indexfile = os.path.join(self.__cI.get('SITE_ARCHIVE_STORAGE_PATH'), 'for_release', 'index', self.__owner + '.index')
    #     if os.access(anno_indexfile, os.F_OK):
    #         fb = open(anno_indexfile, 'rb')
    #         pickleData = pickle.load(fb)
    #         fb.close()
    #         return pickleData
    #     #
    #     return {}

    def __processTemplate(self, fn, parameterDict=None):
        """ Read the input HTML template data file and perform the key/value substitutions in the
            input parameter dictionary.

            :Params:
                ``parameterDict``: dictionary where
                key = name of subsitution placeholder in the template and
                value = data to be used to substitute information for the placeholder

            :Returns:
                string representing entirety of content with subsitution placeholders now replaced with data
        """
        if parameterDict is None:
            parameterDict = {}

        tPath = self.__reqObj.getValue("TemplatePath")
        fPath = os.path.join(tPath, fn)
        ifh = open(fPath, 'r')
        sIn = ifh.read()
        ifh.close()
        return (sIn % parameterDict)


def test_main():
    sTool = ReleaseWebApp()
    d = sTool.doOp()
    for k, v in d.items():
        sys.stdout.write("Key - %s  value - %r\n" % (k, v))


if __name__ == "__main__":
    test_main()
