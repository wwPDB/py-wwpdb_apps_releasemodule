##
# File:  TimeUtil.py
# Date:  27-Jun-2013
# Updates:
##
"""

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

import time


class TimeUtil(object):
    """
    """
    def __init__(self):
        """
        """
        self.__currenttime = time.time()
        self.__cutoffday = 0
        self.__cutoffday_start = 0
        self.__getCutOffDay()
        self.__nextWednesday = self.__getFormatDate(self.__cutoffday)
        self.__startDay = self.__getFormatDate(self.__cutoffday_start)
        self.__currentDay = self.__getFormatDate(0)
        self.__releaseDatePDBFormat = self.__getPDBFormatDate(self.__cutoffday)

    def CutOffDay(self):
        """
        """
        return self.__cutoffday

    def NextWednesday(self):
        """
        """
        return self.__nextWednesday

    def PDBFormatReleaseDate(self):
        """
        """
        return self.__releaseDatePDBFormat

    def StartDay(self):
        """
        """
        return self.__startDay

    def EndDay(self):
        """
        """
        return self.__currentDay

    def Today(self):
        """
        """
        return self.__currentDay

    def __getCutOffDay(self):
        """
        """
        localtime = time.localtime(self.__currenttime)
        # 0 to 6 (0 is Monday)
        if localtime[6] == 0:
            self.__cutoffday = 9
            self.__cutoffday_start = -3
        elif localtime[6] == 1:
            self.__cutoffday = 8
            self.__cutoffday_start = -4
        elif localtime[6] == 2:
            self.__cutoffday = 7
            self.__cutoffday_start = -5
        elif localtime[6] == 3:
            self.__cutoffday = 6
            self.__cutoffday_start = -6
        elif localtime[6] == 4:
            self.__cutoffday = 5
            self.__cutoffday_start = 0
        elif localtime[6] == 5:
            self.__cutoffday = 11
            self.__cutoffday_start = -1
        elif localtime[6] == 6:
            self.__cutoffday = 10
            self.__cutoffday_start = -2

    def __getFormatDate(self, i_day):
        """
        """
        futuretime = self.__check_daylight_saving(self.__currenttime, self.__currenttime + i_day * 86400)
        return time.strftime("%Y-%m-%d", time.localtime(futuretime))

    def __getPDBFormatDate(self, i_day):
        """
        """
        futuretime = self.__check_daylight_saving(self.__currenttime, self.__currenttime + i_day * 86400)
        return time.strftime("%d-%b-%y", time.localtime(futuretime)).upper()

    def __check_daylight_saving(self, currenttime, futuretime):
        """
        """
        current_flag = time.localtime(currenttime).tm_isdst
        future_flag = time.localtime(futuretime).tm_isdst
        if (current_flag == 0) and (future_flag > 0):
            return (futuretime - 3600)
        elif (current_flag > 0) and (future_flag == 0):
            return (futuretime + 3600)
        else:
            return futuretime
        #


if __name__ == '__main__':
    t = TimeUtil()
    print((t.NextWednesday()))
