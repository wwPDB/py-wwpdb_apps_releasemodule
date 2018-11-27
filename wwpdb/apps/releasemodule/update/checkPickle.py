##
import cPickle, sys

def readPickle(filename):
    fb = open(filename, 'rb')
    map = cPickle.load(fb)
    fb.close() 
    print map 

if __name__ == '__main__':
    readPickle(sys.argv[1])
