"""
File:    GetLogMessage.py
Author:  Zukang Feng
Update:  14-Dec-2012
Version: 001  Initial version

"""

__author__  = "Zukang Feng"
__email__   = "zfeng@rcsb.rutgers.edu"
__version__ = "V0.001"

import sys, os, string

def GetLogMessage(logfile):
    if not os.access(logfile, os.F_OK):
        return ''
    #
    statinfo = os.stat(logfile)
    if statinfo.st_size == 0:
        return ''
    #
    f = file(logfile, 'r')
    data = f.read()
    f.close()
    #
    error = ''
    list = data.split('\n')
    for line in list:
        if not line:
            continue
        #
        if line == 'Finished!':
            continue
        #
        error += line + '\n'
    #
    return error

