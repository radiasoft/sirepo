#!/usr/bin/python

import os
import sys

try:
    (infile1, infile2, outfile) = sys.argv[1:]
    os.system('sddscombine {} {} -merge {}'.format(infile1, infile2, outfile))
except:
    raise RuntimeError('usage: {} <infile> <infile> <outfile>'.format(sys.argv[0]))
