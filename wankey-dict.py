#!/usr/bin/env python

"""wankey-dict.py: Play around with previously pickled email info

Uses the data collected and dumped from wankey-stats.py to compile stats.
Seperated this way to enable offline and faster messing around with the dict info."""

import os
import cPickle

####################
#   Vars:
####################

file = './info.dat'

####################
#   Functions:
####################

def grab_info():
    try:
        f_in = open(file)
    except:
        print 'No dictionary exists. Run wankey-stats.py first to create some output'
        return -1
    else:
        info = cPickle.load(f_in)
        return info


def disp_info(info):
    """Print out the contents of the info dictionary (unprocessed/sorted)"""
    if info['email_sub'] != {}:
        for field in info:
            print 'Field:', field
            for entry in info[field]:
                print '\tEntry:', str(info[field][entry]).zfill(3), entry
    else:
        print 'Dictionary is empty. Please run wankey-stats.py again.'

def parse_info(info):
    """Print out the processed contents of the info dictionary"""
    if info['email_sub'] != {}:
        keys = ('email_sub', 'email_to', 'email_from', )
    else:
        print 'Dictionary is empty. Please run wankey-stats.py again.'

info = grab_info()
if info != -1:
    print '\ndisp_info():\n'
    disp_info(info)
    print '\nparse_info():\n'
    parse_info(info)
