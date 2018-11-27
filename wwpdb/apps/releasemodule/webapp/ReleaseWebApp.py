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
__author__    = "Zukang Feng"
__email__     = "zfeng@rcsb.rutgers.edu"
__license__   = "Creative Commons Attribution 3.0 Unported"
__version__   = "V0.07"

import cPickle, os, sys, tarfile, time, types, string, traceback, ntpath, threading, shutil
from json import loads, dumps
from time import localtime, strftime

from wwpdb.api.facade.ConfigInfo                                import ConfigInfo
from wwpdb.utils.rcsb.WebRequest                                import InputRequest,ResponseContent
from wwpdb.apps.releasemodule.citation.ReadCitationFinderResult import ReadCitationFinderResult
from wwpdb.apps.releasemodule.depict.Depict                     import Depict
from wwpdb.apps.releasemodule.depict.DepictCitation             import DepictCitation
from wwpdb.apps.releasemodule.depict.DepictCitationForm         import DepictCitationForm
from wwpdb.apps.releasemodule.depict.DepictRemovalMark          import DepictRemovalMark
from wwpdb.apps.releasemodule.update.CitationFormParser         import CitationFormParser
from wwpdb.apps.releasemodule.update.EntryFormParser            import EntryFormParser
from wwpdb.apps.releasemodule.update.FormParser                 import FormParser
from wwpdb.apps.releasemodule.update.UpdateFile                 import UpdateFile
from wwpdb.apps.releasemodule.utils.DBUtil                      import DBUtil
from wwpdb.apps.releasemodule.utils.StatusDbApi                 import StatusDbApi
from wwpdb.apps.releasemodule.utils.Utility                     import *
from wwpdb.utils.rcsb.PathInfo                                  import PathInfo
#

class ReleaseWebApp(object):
    """Handle request and response object processing for release module web application.
    
    """
    def __init__(self,parameterDict={},verbose=False,log=sys.stderr,siteId="WWPDB_DEV"):
        """
        Create an instance of `ReleaseWebApp` to manage a release module web request.

         :param `parameterDict`: dictionary storing parameter information from the web request.
             Storage model for GET and POST parameter data is a dictionary of lists.
         :param `verbose`:  boolean flag to activate verbose logging.
         :param `log`:      stream for logging.
          
        """
        self.__verbose=verbose
        self.__lfh=log
        self.__debug=False
        self.__siteId=siteId
        self.__cI=ConfigInfo(self.__siteId)
        self.__topPath=self.__cI.get('SITE_WEB_APPS_TOP_PATH')
        #

        if type( parameterDict ) == types.DictType:
            self.__myParameterDict=parameterDict
        else:
            self.__myParameterDict={}

        if (self.__verbose):
            self.__lfh.write("+ReleaseWebApp.__init() - REQUEST STARTING ------------------------------------\n" )
            self.__lfh.write("+ReleaseWebApp.__init() - dumping input parameter dictionary \n" )                        
            #self.__lfh.write("%s" % (''.join(self.__dumpRequest())))
            
        self.__reqObj=InputRequest(self.__myParameterDict,verbose=self.__verbose,log=self.__lfh)
        
        self.__topSessionPath  = self.__cI.get('SITE_WEB_APPS_TOP_SESSIONS_PATH')
        self.__templatePath = os.path.join(self.__topPath,"htdocs","releasemodule","templates")
        #
        self.__reqObj.setValue("TopSessionPath", self.__topSessionPath)
        self.__reqObj.setValue("TemplatePath",   self.__templatePath)
        self.__reqObj.setValue("TopPath",        self.__topPath)
        self.__reqObj.setValue("WWPDB_SITE_ID",  self.__siteId)
        os.environ["WWPDB_SITE_ID"]=self.__siteId
        #
        self.__reqObj.setReturnFormat(return_format="html")
        #
        if (self.__verbose):
            self.__lfh.write("-----------------------------------------------------\n")
            self.__lfh.write("+ReleaseWebApp.__init() Leaving _init with request contents\n" )            
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
        stw=ReleaseWebAppWorker(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        rC=stw.doOp()
        if (self.__debug):
            rqp=self.__reqObj.getRequestPath()
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

    def __dumpRequest(self):
        """Utility method to format the contents of the internal parameter dictionary
           containing data from the input web request.

           :Returns:
               ``list`` of formatted text lines 
        """
        retL=[]
        retL.append("\n\-----------------ReleaseWebApp().__dumpRequest()-----------------------------\n")
        retL.append("Parameter dictionary length = %d\n" % len(self.__myParameterDict))            
        for k,vL in self.__myParameterDict.items():
            retL.append("Parameter %30s :" % k)
            for v in vL:
                retL.append(" ->  %s\n" % v)
        retL.append("-------------------------------------------------------------\n")                
        return retL

class ReleaseWebAppWorker(object):
    def __init__(self, reqObj=None, verbose=False,log=sys.stderr):
        """
         Worker methods for the chemical component editor application

         Performs URL - application mapping and application launching
         for chemical component editor tool.
         
         All operations can be driven from this interface which can
         supplied with control information from web application request
         or from a testing application.
        """
        self.__verbose=verbose
        self.__lfh=log
        self.__reqObj=reqObj
        self.__siteId  = str(self.__reqObj.getValue("WWPDB_SITE_ID"))
        self.__cI=ConfigInfo(self.__siteId)
        self.__annotator = str(self.__reqObj.getValue('annotator'))
        self.__owner = str(self.__reqObj.getValue('owner'))
        if not self.__owner and self.__annotator:
            self.__owner = self.__annotator
        #
        self.__appPathD={'/service/environment/dump':          '_dumpOp',
                         '/service/release/get_anno_list':     '_GetAnnoListOp',
                         '/service/release/start':             '_StandaloneOp',
                         '/service/release/new_session/wf':    '_WorkflowOp',
                         '/service/release/citation_finder':   '_CitationFinderPage',
                         '/service/release/citation_update':   '_CitationUpdatePage',
                         '/service/release/release_onhold':    '_RequestReleasePage',
#                        '/service/release/status_update':     '_StatusUpdatePage',
                         '/service/release/release_entry':     '_ReleasedEntryPage',
#                        '/service/release/check_marked_pubmed_id': '_MarkedPubmedIDPage',
                         '/service/release/check_marked_pubmed_id': '_DisPlayMarkedPubmedIDOp',
                         '/service/release/update':            '_UpdateOp',
                         '/service/release/citation_request':  '_CitationRequestOp',
                         '/service/release/entry_request':     '_EntryRequestOp',
                         '/service/release/marked_pubmed_request': '_MarkedPubmedRequestOp',
                         '/service/release/mark_pubmed_id':    '_MarkPubmedIDOp',
                         '/service/release/remove_marked_pubmed': '_RemoveMarkedPubmedIDOp',
                         '/service/release/download_file':     '_downloadFilePage',
                         '/service/release/download_logfile':  '_downloadLogFilePage'
                         }
        
    def doOp(self):
        """Map operation to path and invoke operation.  
        
            :Returns:

            Operation output is packaged in a ResponseContent() object.
        """
        return self.__doOpException()
    
    def __doOpNoException(self):
        """Map operation to path and invoke operation.  No exception handling is performed.
        
            :Returns:

            Operation output is packaged in a ResponseContent() object.
        """
        #
        reqPath=self.__reqObj.getRequestPath()
        if not self.__appPathD.has_key(reqPath):
            # bail out if operation is unknown -
            rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
            rC.setError(errMsg='Unknown operation')
            return rC
        else:
            mth=getattr(self,self.__appPathD[reqPath],None)
            rC=mth()
        return rC

    def __doOpException(self):
        """Map operation to path and invoke operation.  Exceptions are caught within this method.
        
            :Returns:

            Operation output is packaged in a ResponseContent() object.
        """
        #
        try:
            reqPath=self.__reqObj.getRequestPath()
            if not self.__appPathD.has_key(reqPath):
                # bail out if operation is unknown -
                rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
                rC.setError(errMsg='Unknown operation')
            else:
                mth=getattr(self,self.__appPathD[reqPath],None)
                rC=mth()
            return rC
        except:
            traceback.print_exc(file=self.__lfh)
            rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
            rC.setError(errMsg='Operation failure')
            return rC

    ################################################################################################################
    # ------------------------------------------------------------------------------------------------------------
    #      Top-level REST methods
    # ------------------------------------------------------------------------------------------------------------
    #
    def _dumpOp(self):
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        rC.setHtmlList(self.__reqObj.dump(format='html'))
        return rC

    def _GetAnnoListOp(self):
        """ Get Annotator selection list
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._GetAnnoListOp() Starting now\n")
        #
        self.__reqObj.setReturnFormat(return_format="json")        
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        rC.setText(text=self.__getAnnotatorList('', 'annotator'))
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
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        myD = {}
        myD['sessionid']  = self.__sessionId
        myD['identifier'] = str(self.__reqObj.getValue('identifier'))
        myD['filesource'] = str(self.__reqObj.getValue('filesource'))
        myD['instance']   = str(self.__reqObj.getValue('instance'))
        myD['annotator']  = self.__annotator
        myD['owner_selection']  = self.__getAnnotatorList(self.__owner, 'owner')
        citPath = os.path.join(self.__cI.get('SITE_DEPLOY_PATH'), 'reference', 'citation_finder')
        resultFile = os.path.join(citPath, 'citation_finder_' + self.__siteId + '.db')
        self.__lfh.write("+ReleaseWebAppWorker._StandaloneOp() resultFile %s\n" % resultFile)
        if not os.access(resultFile, os.F_OK):
            resultFile = os.path.join(citPath, 'citation_finder_WWPDB_DEPLOY_TEST.db')
        #
        cReader = ReadCitationFinderResult(path=self.__sessionPath, siteId=self.__siteId, pickleFile=resultFile, verbose=False, log=sys.stderr)
        entryList = cReader.getEntryList(self.__owner)
        if entryList:
            entryList = self.__getEntryCombInfo(entryList)
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
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        entryId = str(self.__reqObj.getValue('identifier'))
        myD = {}
        myD['sessionid']  = self.__sessionId
        myD['identifier'] = entryId
        myD['filesource'] = str(self.__reqObj.getValue('filesource'))
        myD['instance']   = str(self.__reqObj.getValue('instance'))
        myD['annotator']  = self.__annotator
        myD['owner_selection']  = self.__getAnnotatorList(self.__owner, 'owner')
        #
        db = DBUtil(siteId=self.__siteId,verbose=self.__verbose,log=self.__lfh)
        if entryId:
            entryList = []
            entryList.append(entryId)
            entryList = db.getEntryInfo(entryList)
        else:
            entryList = db.getRequestReleaseEntryInfo(self.__owner)
        if entryList:
            entryList = self.__getEntryCombInfo(entryList)
            self.__reqObj.setValue('task', 'Entries to be released')
            self.__reqObj.setValue('owner', self.__owner)
            myD['result_list'] = self.__depcitRequestForm(entryList)
        else:
            myDir = {}
            myDir['sessionid'] = self.__sessionId
            myDir['annotator'] = self.__annotator
            myDir['task']      = 'Entries to be released'
            myD['result_list'] = self.__processTemplate('request/input_form_tmplt.html', myDir)
        #
        rC.setHtmlText(self.__processTemplate('release_launch_tmplt.html', myD))
        #
        return rC

    def __depcitRequestForm(self, entryList):
        self.__reqObj.setValue('FormTemplate', 'request/request_form_tmplt.html')
        self.__reqObj.setValue('RowTemplate', 'request/request_row_tmplt.html')
        self.__reqObj.setValue('option', 'request_release')
        items = self.__getItemList('request/request_item_list')
        dp = Depict(reqObj=self.__reqObj, resultList=entryList, itemList=items, verbose=self.__verbose, log=self.__lfh)
        return dp.DoRender()

    def _CitationFinderPage(self):
        """ Launch citation finder page
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._CitationFinderPage() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")        
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        #
        citPath = os.path.join(self.__cI.get('SITE_DEPLOY_PATH'), 'reference', 'citation_finder')
        resultFile = os.path.join(citPath, 'citation_finder_' + self.__siteId + '.db')
        self.__lfh.write("+ReleaseWebAppWorker._StandaloneOp() resultFile %s\n" % resultFile)
        if not os.access(resultFile, os.F_OK):
            resultFile = os.path.join(citPath, 'citation_finder_WWPDB_DEPLOY_TEST.db')
        #
        filename = getFileName(self.__sessionPath, 'pubmed', 'cif')
        outputFile = os.path.join(self.__sessionPath, filename)
        cReader = ReadCitationFinderResult(path=self.__sessionPath, siteId=self.__siteId, pickleFile=resultFile, verbose=False, log=sys.stderr)
        entryList = cReader.getEntryList(self.__owner)
        if entryList:
            entryList = self.__getEntryCombInfo(entryList)
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
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        myD = {}
        myD['sessionid'] = self.__sessionId
        myD['annotator'] = self.__annotator
        myD['task']      = str(self.__reqObj.getValue('task'))
        #
        if myD['task'] == 'Citation Update with Pubmed':
            rC.setText(text=self.__processTemplate('citation_request/input_form_with_pubmed_tmplt.html', myD))
        else:
            rC.setText(text=self.__processTemplate('citation_request/input_form_without_pubmed_tmplt.html', myD))
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
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        db = DBUtil(siteId=self.__siteId,verbose=self.__verbose,log=self.__lfh)
        entryList = db.getRequestReleaseEntryInfo(self.__owner)
        #
        if entryList:
            entryList = self.__getEntryCombInfo(entryList)
            rC.setText(text=self.__depcitRequestForm(entryList))
        else:
            myDir = {}
            myDir['sessionid'] = self.__sessionId
            myDir['annotator'] = self.__annotator
            myDir['task']      = str(self.__reqObj.getValue('task'))
            rC.setText(text=self.__processTemplate('request/input_form_tmplt.html', myDir))
        #
        return rC

#   def _StatusUpdatePage(self):
#       """ Launch status update page
#       """
#       if (self.__verbose):
#           self.__lfh.write("+ReleaseWebAppWorker._StatusUpdatePage() Starting now\n")
#       #
#       self.__getSession()
#       #
#       self.__reqObj.setReturnFormat(return_format="json")        
#       rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
#       #
#       db = DBUtil(siteId=self.__siteId,verbose=self.__verbose,log=self.__lfh)
#       list = db.getAuthEntryInfo(self.__owner)
#       #
#       if list:
#           list = self.__getBmrbEmdbIDs(list)
#           self.__reqObj.setValue('FormTemplate', 'status/status_form_tmplt.html')
#           self.__reqObj.setValue('RowTemplate', 'status/status_row_tmplt.html')
#           self.__reqObj.setValue('option', 'status_update')
#           items = self.__getItemList('status/status_item_list')
#           dp = Depict(reqObj=self.__reqObj, resultList=list, itemList=items, verbose=self.__verbose, log=self.__lfh)
#           rC.setText(text=dp.DoRender())
#       else:
#           rC.setText(text=self.__returnNotFound(self.__owner))
#       #
#       return rC

    def _ReleasedEntryPage(self):
        """ Launch requested release page based on author's input status
        """
        if (self.__verbose):
            self.__lfh.write("+ReleaseWebAppWorker._ReleasedEntryPage() Starting now\n")
        #
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")        
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        db = DBUtil(siteId=self.__siteId,verbose=self.__verbose,log=self.__lfh)
        id_list = db.getRelEntryId(self.__owner)
        #
        entry_emd_id_mapping = {}
        topReleaseDir = os.path.join(self.__cI.get('SITE_ARCHIVE_STORAGE_PATH'), 'for_release')
        anno_indexfile = os.path.join(topReleaseDir, 'index', self.__annotator + '.index')
        if os.access(anno_indexfile, os.F_OK):
            fbr = open(anno_indexfile, 'rb')
            entry_index = cPickle.load(fbr)
            fbr.close()
            released_list = []
            for entry_id,dir in entry_index.items():
                found = False
                for k,v in dir.items():
                    for release_dir in ( 'added', 'modified', 'obsolete', 'reloaded', 'emd' ):
                        entry_dir = os.path.join(topReleaseDir, release_dir, v)
                        if os.access(entry_dir, os.F_OK):
                            found = True
                            break
                        #
                    #
                    if found:
                        if k == 'emd':
                            entry_emd_id_mapping[entry_id] = v
                        #
                        break
                    #
                #
                if found:
                    released_list.append(entry_id)
                #
            #
            if released_list:
                id_list.extend(released_list)
                id_list = sorted(set(id_list))
            #
        #
        entryList = []
        if id_list:
            entryList = self.__getEntryCombInfoWithIdList(db.getEntryInfo(id_list), id_list)
        #
        if entryList:
            self.__reqObj.setValue('FormTemplate', 'request/pull_from_release_form_tmplt.html')
            self.__reqObj.setValue('RowTemplate', 'request/pull_from_release_row_tmplt.html')
            self.__reqObj.setValue('option', 'pull_release')
            items = self.__getItemList('request/pull_item_list')
            dp = Depict(reqObj=self.__reqObj, resultList=entryList, itemList=items, verbose=self.__verbose, log=self.__lfh)
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
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        myD = {}
        myD['sessionid'] = self.__sessionId
        myD['annotator'] = self.__annotator
        myD['task']      = str(self.__reqObj.getValue('task'))
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
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        frmParser = FormParser(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        content = frmParser.getErrorContent()
        if content:
            #rC.setText(text=content)
            rC.setError(errMsg=content)
            return rC
        #
        updateList = frmParser.getUpdateList()
        updateList = self.__getEntryCombInfo(updateList)
        updOp = UpdateFile(reqObj=self.__reqObj, updateList=updateList, verbose=self.__verbose, log=self.__lfh)
        task = str(self.__reqObj.getValue('task'))
        if task == 'Entries in release pending':
            updOp.PullRelease()
        else:
            updOp.DoUpdate()
        content = updOp.getErrorContent()
        if content:
            rC.setError(errMsg=content)
            return rC
        rC.setText(text=updOp.getReturnContent())
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
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        citationformflag = str(self.__reqObj.getValue('citationformflag'))
        requestParser = CitationFormParser(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        content = requestParser.getErrorContent()
        if content:
            rC.setError(errMsg=content)
            return rC
        #
        entryList = requestParser.getEntryList()
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
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        requestParser = EntryFormParser(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        content = requestParser.getErrorContent()
        if content:
            rC.setError(errMsg=content)
            return rC
        #
        entryList = requestParser.getEntryList()
        if entryList:
            rC.setText(text=self.__depcitRequestForm(entryList))
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
        statusList = [ "'PROC'", "'AUTH'", "'HPUB'", "'HOLD'", "'REPL'", "'AUCO'", "'REUP'", "'WAIT'", "'REFI'" ]
        self.__getSession()
        #
        self.__reqObj.setReturnFormat(return_format="json")        
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        foundList = []
        db = DBUtil(siteId=self.__siteId,verbose=self.__verbose,log=self.__lfh)
        idlist = db.getEntriesWithStatusList(self.__owner, ','.join(statusList))
        entryList = db.getEntryInfo(idlist)
        if entryList:
            entryList = self.__getEntryCombInfo(entryList)
            pI = PathInfo(siteId=self.__siteId, sessionPath=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
            for dir in entryList:
                try:
                    archiveDirPath = pI.getDirPath(dataSetId=dir['structure_id'], wfInstanceId=None, contentType='model', \
                            formatType='pdbx', fileSource='archive', versionId='latest', partNumber=1)
                    pickle_file = os.path.join(archiveDirPath, 'marked_pubmed_id.pic')
                    if os.access(pickle_file, os.F_OK):
                        foundList.append(dir)
                    #
                except:
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
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        requestParser = EntryFormParser(reqObj=self.__reqObj, verbose=self.__verbose, log=self.__lfh)
        content = requestParser.getErrorContent()
        if content:
            rC.setError(errMsg=content)
            return rC
        #
        idlist = requestParser.getEntryList()
        if idlist:
            db = DBUtil(siteId=self.__siteId,verbose=self.__verbose,log=self.__lfh)
            list = db.getEntryInfo(idlist)
            drm = DepictRemovalMark(reqObj=self.__reqObj, resultList=list, verbose=self.__verbose, log=self.__lfh)
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
        archiveDirPath = pI.getDirPath(dataSetId=identifier, wfInstanceId=None, contentType='model', formatType='pdbx', \
                              fileSource='archive', versionId='latest', partNumber=1)
        pickle_file = os.path.join(archiveDirPath, 'marked_pubmed_id.pic')
        #
        pubmed_id_list = []
        if os.access(pickle_file, os.F_OK):
            fb = open(pickle_file, 'rb')
            pubmed_id_list = cPickle.load(fb)
            fb.close()
        #
        pubmed_id_list.append(pubmed_id)
        if len(pubmed_id_list) > 1:
            pubmed_id_list = sorted(set(pubmed_id_list))
        #
        fb = open(pickle_file, 'wb')
        cPickle.dump(pubmed_id_list, fb)
        fb.close()
        #
        self.__reqObj.setReturnFormat(return_format="json")        
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
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
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        combList = self.__reqObj.getValueList('combine_id')
        if not combList:
            rC.setError(errMsg='No pubmed ID selected')
            return rC
        #
        map = {}
        for comb_id in combList:
            list = comb_id.split(':')
            if map.has_key(list[0]):
                if not list[1] in map[list[0]]:
                    map[list[0]].append(list[1])
                #
            else:
                pubmed_id_list = []
                pubmed_id_list.append(list[1])
                map[list[0]] = pubmed_id_list
            #
        #
        pI = PathInfo(siteId=self.__siteId, sessionPath=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        content = ''
        for structure_id,pubmed_id_list in map.items():
            content += '\n' + structure_id + ': Removed ' + ','.join(pubmed_id_list)
            #
            archiveDirPath = pI.getDirPath(dataSetId=structure_id, wfInstanceId=None, contentType='model', formatType='pdbx', \
                                  fileSource='archive', versionId='latest', partNumber=1)
            pickle_file = os.path.join(archiveDirPath, 'marked_pubmed_id.pic')
            #
            existing_pubmed_id_list = []
            if os.access(pickle_file, os.F_OK):
                fb = open(pickle_file, 'rb')
                existing_pubmed_id_list = cPickle.load(fb)
                fb.close()
            #
            updated_pubmed_id_list = []
            for id in existing_pubmed_id_list:
                if not id in pubmed_id_list:
                    updated_pubmed_id_list.append(id)
                #
            #
            if updated_pubmed_id_list:
                fb = open(pickle_file, 'wb')
                cPickle.dump(updated_pubmed_id_list, fb)
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
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
        #
        filelist = FindFiles(self.__sessionPath)
        if not filelist:
            rC.setText(text='<h3 style="text-align:center">No entry updated</h3>')
        else:
            #for f in ('all_files.tar.gz', 'all_files.tar'):
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
                #for f in filelist:
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
                myD['instanceid'] = ''
                myD['fileid'] = f
                content += self.__processTemplate('one_file_tmplt.html', myD) + '\n'
            #
            rC.setText(text=content)
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
        rC = ResponseContent(reqObj=self.__reqObj, verbose=self.__verbose,log=self.__lfh)
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
                myD['instanceid'] = ''
                myD['fileid'] = f
                content += self.__processTemplate('one_file_tmplt.html', myD) + '\n'
            #
            rC.setText(text=content)
        return rC

    def __getAnnotatorList(self, annotator, name_id):
        """ Generate annotator initials selection list
        """
        site = 'RCSB'
        if self.__cI.get('WWPDB_SITE_LOC').lower() == 'pdbe':
            site = 'PDBe'
        elif self.__cI.get('WWPDB_SITE_LOC').lower() == 'pdbj':
            site = 'PDBj'
        #
        statusDB = StatusDbApi(siteId=self.__siteId, verbose=self.__verbose, log=self.__lfh)
        anno_list = statusDB.getAnnoList(siteId=site) 
        anno_list.insert(0, '')
        self.__site = self.__cI.get('WWPDB_SITE_LOC')
        """
        tPath =self.__reqObj.getValue("TemplatePath")
        fPath=os.path.join(tPath,'annotator_list')
        ifh=open(fPath,'r')
        sIn=ifh.read()
        ifh.close()
        #
        anno_list = sIn.split('\n')
        anno_list.sort()
        if anno_list[0] != '':
            anno_list.insert(0, '')
        #
        """
        text = '<select name="' + name_id + '" id="' + name_id + '">\n'
        for anno in anno_list:
            text += '<option value="' + anno + '" '
            if anno == annotator:
                text += 'selected'
            text += '>' + anno + '</option>\n'
        text += '</select>\n'
        return text

    def __getItemList(self, fn):
        """ Get Item List
        """
        tPath = self.__reqObj.getValue("TemplatePath")
        fPath = os.path.join(tPath, fn)
        ifh=open(fPath,'r')
        sIn=ifh.read()
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

    def __getEntryCombInfo(self, entryList):
        """
        """
        id_list = []
        for entryDir in entryList:
            entryId = ''
            if entryDir.has_key('entry') and entryDir['entry']:
                entryId = entryDir['entry']
            elif entryDir.has_key('structure_id') and entryDir['structure_id']:
                entryId = entryDir['structure_id']
            #
            if entryId:
                id_list.append(entryId)
            #
        #
        return self.__getEntryCombInfoWithIdList(entryList, id_list)

    def __getEntryCombInfoWithIdList(self, entryList, id_list):
        """
        """
        statusDB = StatusDbApi(siteId=self.__siteId, verbose=self.__verbose, log=self.__lfh)
        message,return_list,return_map = statusDB.getEntryListFromIDList(entry_ids=id_list)
        return getCombinationInfo(entryList, return_map)

    def __returnNotFound(self, annotator):
        myD = {}
        myD['annotator']  = annotator
        myD['task'] = str(self.__reqObj.getValue('task'))
        return self.__processTemplate('not_found_tmplt.html', myD)

    def __getSession(self):
        """ Join existing session or create new session as required.
        """
        #
        self.__sObj=self.__reqObj.newSessionObj()
        self.__sessionId=self.__sObj.getId()
        self.__sessionPath=self.__sObj.getPath()
        self.__rltvSessionPath=self.__sObj.getRelativePath()
        if (self.__verbose):
            self.__lfh.write("------------------------------------------------------\n")                    
            self.__lfh.write("+ReleaseWebAppWorker.__getSession() - creating/joining session %s\n" % self.__sessionId)
            self.__lfh.write("+ReleaseWebAppWorker.__getSession() - session path %s\n" % self.__sessionPath)            

    def __processTemplate(self,fn,parameterDict={}):
        """ Read the input HTML template data file and perform the key/value substitutions in the
            input parameter dictionary.
            
            :Params:
                ``parameterDict``: dictionary where
                key = name of subsitution placeholder in the template and
                value = data to be used to substitute information for the placeholder
                
            :Returns:
                string representing entirety of content with subsitution placeholders now replaced with data
        """
        tPath =self.__reqObj.getValue("TemplatePath")
        fPath=os.path.join(tPath,fn)
        ifh=open(fPath,'r')
        sIn=ifh.read()
        ifh.close()
        return (  sIn % parameterDict )

if __name__ == '__main__':
    sTool=ReleaseWebApp()
    d=sTool.doOp()
    for k,v in d.items():
        sys.stdout.write("Key - %s  value - %r\n" % (k,v))
