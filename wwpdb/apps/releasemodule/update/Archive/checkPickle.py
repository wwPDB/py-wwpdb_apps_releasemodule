##
try:
    import cPickle as pickle
except ImportError:
    import pickle

import sys

def readPickle(filename):
    fb = open(filename, 'rb')
    map = pickle.load(fb)
    fb.close() 
    print map 

if __name__ == '__main__':
    readPickle(sys.argv[1])
