import os
import shutil
from wwpdb.utils.config.ConfigInfo import getSiteId
from wwpdb.utils.config.ConfigInfoApp import ConfigInfoAppCommon

from wwpdb.apps.releasemodule.citation.CitationFinder import CitationFinder
from wwpdb.apps.releasemodule.update.AutoReRelease import AutoReRelease


def make_directory(my_directory):
    if not os.path.exists(my_directory):
        os.makedirs(my_directory)


class CitationUpdate:

    def __init__(self):
        self.wwpdb_site = getSiteId()
        cICommon = ConfigInfoAppCommon(self.wwpdb_site)
        self.citation_updates_path = cICommon.get_citation_update_path()
        self.citation_finder_path = cICommon.get_citation_finder_path()
        db_output = "citation_finder_{}.db".format(self.wwpdb_site)
        auto_update_output = "auto_re-release_{}.log".format(self.wwpdb_site)
        self.db_output_path = os.path.join(self.citation_updates_path, db_output)
        self.auto_release_output = os.path.join(self.citation_updates_path, auto_update_output)

    def get_site_id(self):
        return self.wwpdb_site

    def get_citation_finder_path(self):
        return self.citation_finder_path

    def get_db_output(self):
        return self.db_output_path

    def get_auto_rerelease_output_file(self):
        return self.auto_release_output

    def get_citation_updates_path(self):
        return self.citation_updates_path

    def make_citation_finder_path(self):
        make_directory(self.citation_finder_path)

    def make_citation_updates_path(self):
        make_directory(self.citation_updates_path)

    def clean_up(self):
        shutil.rmtree(self.citation_updates_path, ignore_errors=True)

    def run_citation_finder(self):
        CitationFinder(siteId=self.get_site_id(), path=self.get_citation_updates_path(),
                       output=self.get_db_output()).searchPubmed()

    def run_auto_re_release(self):
        AutoReRelease(siteId=self.get_site_id()).ReleaseProcess(outputFile=self.get_auto_rerelease_output_file())


def run_citation_finder():
    cu = CitationUpdate()
    cu.make_citation_updates_path()
    cu.make_citation_finder_path()
    cu.run_citation_finder()
    cu.run_auto_re_release()
    cu.clean_up()


if __name__ == '__main__':
    run_citation_finder()
