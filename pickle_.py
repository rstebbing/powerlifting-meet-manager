# pickle_.py

# Imports
import cPickle

# dump
def dump(file_, obj):
    own_fid = False
    if isinstance(file_,basestring):
        file_ = open(file_,'wb')
        own_fid = True

    cPickle.dump(obj, file_, 2)

    if own_fid:
        file_.close()

# load
def load(file_):
    own_fid = False
    if isinstance(file_,basestring):
        file_ = open(file_,'rb')
        own_fid = True

    obj = cPickle.load(file_)

    if own_fid:
        file_.close()

    return obj
