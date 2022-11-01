import os
import shutil
import logging
import argparse

from wwpdb.utils.config.ConfigInfo import getSiteId
from wwpdb.utils.config.ConfigInfoApp import ConfigInfoAppCommon

from wwpdb.apps.releasemodule.citation.CitationFinder import CitationFinder
from wwpdb.apps.releasemodule.update.AutoReRelease import AutoReRelease

logger = logging.getLogger()

# pylint: disable=logging-format-interpolation


def make_directory(my_directory):
    if not os.path.exists(my_directory):
        logging.info('making directory: {}'.format(my_directory))
        os.makedirs(my_directory)


class CitationUpdate:
    def __init__(self, site_id=None):
        self.wwpdb_site = site_id if site_id else getSiteId()
        cICommon = ConfigInfoAppCommon(self.wwpdb_site)
        self.citation_updates_path = cICommon.get_citation_update_path()
        self.citation_finder_path = cICommon.get_citation_finder_path()
        db_output = "citation_finder_{}.db".format(self.wwpdb_site)
        auto_update_output = "auto_re-release_{}.log".format(self.wwpdb_site)
        self.db_output_path = os.path.join(self.citation_finder_path, db_output)
        self.auto_release_output = os.path.join(self.citation_finder_path, auto_update_output)

    def get_site_id(self):
        logging.info('using site ID: {}'.format(self.wwpdb_site))
        return self.wwpdb_site

    def get_citation_finder_path(self):
        logging.info('citation finder directory {}'.format(self.citation_finder_path))
        return self.citation_finder_path

    def get_db_output(self):
        logging.info('output citation DB to {}'.format(self.db_output_path))
        return self.db_output_path

    def get_auto_rerelease_output_file(self):
        logging.info('output log to {}'.format(self.auto_release_output))
        return self.auto_release_output

    def get_citation_updates_path(self):
        logging.info('citation update directory {}'.format(self.citation_updates_path))
        return self.citation_updates_path

    def make_citation_finder_path(self):
        make_directory(self.citation_finder_path)

    def make_citation_updates_path(self):
        make_directory(self.citation_updates_path)

    def clean_up(self):
        shutil.rmtree(self.citation_updates_path, ignore_errors=True)

    def run_citation_finder(self):
        logging.info('starting citation finder')
        CitationFinder(siteId=self.get_site_id(), path=self.get_citation_updates_path(),
                       output=self.get_db_output()).searchPubmed()
        logging.info('finished citation finder')

    def run_auto_re_release(self):
        logging.info('starting auto re-release')
        AutoReRelease(siteId=self.get_site_id()).ReleaseProcess(outputFile=self.get_auto_rerelease_output_file())
        logging.info('finished auto re-release')


def run_citation_finder(site_id=None):
    cu = CitationUpdate(site_id=site_id)
    cu.make_citation_updates_path()
    cu.make_citation_finder_path()
    cu.run_citation_finder()
    cu.run_auto_re_release()
    cu.clean_up()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', help='debugging', action='store_const', dest='loglevel',
                        const=logging.DEBUG,
                        default=logging.INFO)
    parser.add_argument('--site_id', help='wwPDB site ID', type=str)
    args = parser.parse_args()
    logger.setLevel(args.loglevel)
    run_citation_finder(site_id=args.site_id)
