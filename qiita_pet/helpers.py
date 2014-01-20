#!/usr/bin/env python

__author__ = "Joshua Shorenstein"
__copyright__ = "Copyright 2013, The QiiTa-pet Project"
__credits__ = ["Joshua Shorenstein"]
__license__ = "BSD"
__version__ = "0.2.0-dev"
__maintainer__ = "Joshua Shorenstein"
__email__ = "Joshua.Shorenstein@colorado.edu"
__status__ = "Development"

from os import walk


def get_available_analyses():
    combined = [analysis.split('.')[0] for analysis in
                walk('templates/meta_opts/combined').next()[2]]
    single = [analysis.split('.')[0] for analysis in
              walk('templates/meta_opts/single').next()[2]]
    combined.remove('OTU_Table')
    single.remove('OTU_Table')
    return single, combined
