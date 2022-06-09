##
# File:  OSVersion.py
# Date:  19-Nove-2021  E. Peisach
#
# Updated:
#
##
"""
Utility to identify operating system particulars
"""
__docformat__ = "restructuredtext en"
__author__ = "Ezra Peisach"
__email__ = "peisach@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.01"

import distro


class OSVersion(object):
    __osdata = None

    def __getOsInfo(self):
        if self.__osdata is None:
            self.__osdata = distro.info()

    def IsRhelLike(self):
        """Determines if O/S is like redhat.  Works with centos, fedora, and rocky linux"""

        self.__getOsInfo()

        like = self.__osdata.get("like", "")

        if "rhel" in like:
            return True

        return False

    def IsRhel8Like(self):
        """Returns True if systm like RHEL 8"""

        if self.IsRhelLike():
            major = self.__osdata.get("version_parts", {}).get("major")
            if major == "8":
                return True

        return False


def main():
    osv = OSVersion()
    print(osv.IsRhel8Like())


if __name__ == main():
    main()
