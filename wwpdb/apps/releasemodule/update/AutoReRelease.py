##
# File:  AutoReRelease.py
# Date:  28-Feb-2018
# Updates:
##
"""

This software was developed as part of the World Wide Protein Data Bank
Common Deposition and Annotation System Project

Copyright (c) 2018 wwPDB

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

import logging
import operator
import os
import sys
from wwpdb.io.locator.PathInfo import PathInfo
from wwpdb.utils.config.ConfigInfoApp import ConfigInfoAppCommon
from wwpdb.utils.session.WebRequest import InputRequest

from wwpdb.apps.releasemodule.update.MultiUpdateProcess import MultiUpdateProcess
from wwpdb.apps.releasemodule.utils.CombineDbApi import CombineDbApi


class AutoReRelease(object):
    def __init__(self, siteId=None, verbose=False, log=sys.stderr):
        """
        """
        self.__siteId = siteId
        self.__verbose = verbose
        self.__lfh = log
        self.__cICommon = ConfigInfoAppCommon(self.__siteId)
        self.__citationPath = self.__cICommon.get_citation_finder_path()
        self.__sObj = None
        self.__sessionId = None
        self.__sessionPath = None
        #
        self.__reqObj = InputRequest({}, verbose=self.__verbose, log=self.__lfh)
        self.__reqObj.setValue("TopSessionPath", self.__cICommon.get_site_web_apps_top_sessions_path())
        self.__reqObj.setValue("TopPath", self.__cICommon.get_site_web_apps_top_path())
        self.__reqObj.setValue("TemplatePath",
                               os.path.join(self.__cICommon.get_site_web_apps_top_path(), "htdocs", "releasemodule",
                                            "templates"))
        self.__reqObj.setValue("WWPDB_SITE_ID", self.__siteId)
        self.__reqObj.setValue("option", "citation_update")
        self.__reqObj.setValue("task", "Citation Finder")
        self.__getSession()
        #
        self.__pI = PathInfo(siteId=self.__siteId, sessionPath=self.__sessionPath, verbose=False, log=self.__lfh)

    def ReleaseProcess(self, outputFile):
        """
        """
        citationResultFile = os.path.join(self.__citationPath, "citation_finder_" + self.__siteId + ".db")
        if not os.access(citationResultFile, os.F_OK):
            self.__lfh.write("AutoReRelease.ReleaseProcess() - %s file not found.\n" % citationResultFile)
            return
        #
        annotEntryMap = self.__deserialize(citationResultFile)
        entryList = self.__findMatchEntryList(annotEntryMap)
        if not entryList:
            self.__lfh.write("AutoReRelease.ReleaseProcess() - found %d entries.\n" % len(entryList))
            ofh = open(outputFile, "w")
            ofh.write("No entry has been re-released this week.\n")
            ofh.close()
            return
        #
        updOp = MultiUpdateProcess(reqObj=self.__reqObj, updateList=entryList, verbose=self.__verbose, log=self.__lfh)
        updatedEntryList = updOp.autoRun()
        #
        self.__lfh.write("AutoReRelease.ReleaseProcess() - found %d entries.\n" % len(entryList))
        for entryInfo in entryList:
            for key1, value1 in entryInfo.items():
                if key1 == "pubmed":
                    for key2, value2 in value1[0].items():
                        self.__lfh.write("pubmed %r=%r\n" % (key2, value2))
                    #
                else:
                    self.__lfh.write("%r=%r\n" % (key1, value1))
                #
            #
            self.__lfh.write("\n")
        #
        self.__lfh.write("AutoReRelease.ReleaseProcess() - updated %d entries.\n" % len(updatedEntryList))
        #
        ofh = open(outputFile, "w")
        if updatedEntryList:
            if len(updatedEntryList) > 1:
                for entryInfo in updatedEntryList:
                    entryInfo.append(entryInfo[1] + '_' + entryInfo[0])
                #
                updatedEntryList.sort(key=operator.itemgetter(3))
                #
                ofh.write("The Following entries have been re-released with citation update:\n\n")
            else:
                ofh.write("The Following entry has been re-released with citation update:\n\n")
            #
            ofh.write("Dep ID         Ann   IDs\n")
            for entryInfo in updatedEntryList:
                ofh.write("%-12s   %-3s   %s\n" % (entryInfo[0], entryInfo[1], entryInfo[2]))
                self.__lfh.write("%-12s   %-3s   %s\n" % (entryInfo[0], entryInfo[1], entryInfo[2]))
            #
        else:
            ofh.write("No entry has been re-released this week.\n")
        #
        ofh.close()

    def __getSession(self):
        """ Join existing session or create new session as required.
        """
        #
        self.__sObj = self.__reqObj.newSessionObj()
        self.__sessionId = self.__sObj.getId()
        self.__sessionPath = self.__sObj.getPath()
        if (self.__verbose):
            self.__lfh.write("------------------------------------------------------\n")
            self.__lfh.write("+AutoReRelease._getSession() - creating/joining session %s\n" % self.__sessionId)
            self.__lfh.write("+AutoReRelease._getSession() - session path %s\n" % self.__sessionPath)
        #

    def __deserialize(self, pickleFile):
        """ Read citation finder result
        """
        fb = open(pickleFile, "rb")
        annotEntryMap = pickle.load(fb)
        fb.close()
        return annotEntryMap

    def __findMatchEntryList(self, annotEntryMap):
        """ Find entry list with matched PUBMED ID or DOI citation
        """
        dbUtil = CombineDbApi(siteId=self.__siteId, path=self.__sessionPath, verbose=self.__verbose, log=self.__lfh)
        entryList = []
        entryIdMap = {}
        pubmedInfoMap = {}
        for _ann, dataList in annotEntryMap.items():
            for dataDict in dataList:
                if ("status_code" not in dataDict) or (dataDict["status_code"] != "REL"):
                    continue
                #
                if dataDict["structure_id"] in entryIdMap:
                    continue
                #
                entryIdMap[dataDict["structure_id"]] = "include"
                #
                if ("pubmed" not in dataDict) or (not dataDict["pubmed"]):
                    continue
                #
                pubmedInfo = self.__getMatchPubmedInfo(dataDict)
                if not pubmedInfo:
                    continue
                #
                EntryInfo = dbUtil.getEntryInfo([dataDict["structure_id"]])
                if (not EntryInfo) or ("status_code" not in EntryInfo[0]) or (EntryInfo[0]["status_code"] != "REL"):
                    continue
                #
                if ("post_rel_recvd_coord" in EntryInfo[0]) and (EntryInfo[0]["post_rel_recvd_coord"].upper() == "Y"):
                    continue
                #
                isDEPLocked = False
                if ("locking" in EntryInfo[0]) and EntryInfo[0]["locking"]:
                    locking = EntryInfo[0]["locking"].upper()
                    if locking.find("DEP") != -1:
                        isDEPLocked = True
                    #
                #
                if not isDEPLocked:
                    continue
                #
                newDataDict = {}
                for item in ("bmrb_id", "comb_ids", "emdb_id", "exp_method", "pdb_id", "wf_status_code"):
                    if (item in EntryInfo[0]) and EntryInfo[0][item]:
                        newDataDict[item] = EntryInfo[0][item]
                    #
                #
                for item_pair in (("annotator", "rcsb_annotator"), ("approval_type", "author_approval_type"),
                                  ("da_status_code", "status_code"), ("entry", "structure_id")):
                    if (item_pair[1] in EntryInfo[0]) and EntryInfo[0][item_pair[1]]:
                        newDataDict[item_pair[0]] = EntryInfo[0][item_pair[1]]
                    #
                #
                newDataDict["status_code"] = "REREL"
                newDataDict["directory"] = "modified"
                newDataDict["option"] = "citation_update"
                if ("emdb_id" in newDataDict) and newDataDict["emdb_id"]:
                    newDataDict["emdb_release"] = True
                #
                pubmedInfo["id"] = "primary"
                newDataDict["pubmed"] = [pubmedInfo]
                entryList.append(newDataDict)
                if not pubmedInfo["pdbx_database_id_PubMed"] in pubmedInfoMap:
                    pubmedInfoMap[pubmedInfo["pdbx_database_id_PubMed"]] = pubmedInfo
                #
            #
        #
        if pubmedInfoMap:
            pubmed_file = "pubmed.db"
            fb = open(os.path.join(self.__sessionPath, pubmed_file), "wb")
            pickle.dump(pubmedInfoMap, fb)
            fb.close()
            #
            self.__reqObj.setValue("pubmed_file", pubmed_file)
        #
        return entryList

    def __getMatchPubmedInfo(self, dataDict):
        """ Check if existing PUBMED ID or DOI matches with citation finder result
        """
        readUnwantedFalg = False
        unwanted_pubmed_list = []
        #
        for pdir in dataDict["pubmed"]:
            foundMatch = False
            for item in ("pdbx_database_id_PubMed", "pdbx_database_id_DOI"):
                if (item not in dataDict) or (not dataDict[item]) or (item not in pdir) or (not pdir[item]):
                    continue
                #
                if str(dataDict[item]).strip() == str(pdir[item]).strip():
                    foundMatch = True
                #
                break
            #
            if not foundMatch:
                continue
            #
            # Get marked unwanted pubmed ID list
            #
            if not readUnwantedFalg:
                readUnwantedFalg = True
                unwanted_pubmed_list = self.__getUnwantedPubMedIDList(dataDict["structure_id"])
            #
            if pdir["pdbx_database_id_PubMed"] in unwanted_pubmed_list:
                continue
            #
            for item in ("page_first", "page_last"):
                if (item not in pdir) or (not pdir[item]):
                    continue
                #
                if not pdir[item].isdigit():
                    pdir[item] = ""
                #
            #
            hasDifference = False
            for item in (
                    "pdbx_database_id_PubMed", "pdbx_database_id_DOI", "page_first", "page_last", "journal_volume", "year"):
                if (item not in pdir) or (not pdir[item]):
                    continue
                #
                if (item not in dataDict) or (not dataDict[item]) or (
                        str(dataDict[item]).strip() != str(pdir[item]).strip()):
                    hasDifference = True
                    break
                #
            #
            if hasDifference:
                return pdir
            #
            if ('similarity_score' in pdir) and (float(pdir['similarity_score']) > 0.9):
                continue
            #
            return pdir
        #
        return {}

    def __getUnwantedPubMedIDList(self, structure_id):
        """ Get unwanted pubmed ID list
        """
        try:
            archiveDirPath = self.__pI.getDirPath(dataSetId=structure_id, wfInstanceId=None, contentType="model",
                                                  formatType="pdbx",
                                                  fileSource="archive", versionId="latest", partNumber=1)
            #
            pickle_file = os.path.join(archiveDirPath, "marked_pubmed_id.pic")
            if not os.access(pickle_file, os.F_OK):
                return []
            #
            fb = open(pickle_file, "rb")
            pubmed_id_list = pickle.load(fb)
            fb.close()
            return pubmed_id_list
        except:  # noqa: E722 pylint: disable=bare-except
            return []
        #


if __name__ == '__main__':
    # Create logger
    logger = logging.getLogger()
    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] [%(module)s.%(funcName)s] %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)

    releaseUtil = AutoReRelease(siteId=os.environ["WWPDB_SITE_ID"], verbose=True, log=sys.stderr)
    releaseUtil.ReleaseProcess(sys.argv[1])
