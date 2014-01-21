#!/usr/bin/env python

from __future__ import absolute_import

__author__ = "Joshua Shorenstein"
__copyright__ = "Copyright 2013, The QiiTa-pet Project"
__credits__ = ["Joshua Shorenstein", "Jose Antonio Navas Molina"]
__license__ = "BSD"
__version__ = "0.2.0-dev"
__maintainer__ = "Joshua Shorenstein"
__email__ = "Joshua.Shorenstein@colorado.edu"
__status__ = "Development"

from celery import Celery

celery = Celery('qiita_pet.app.celery', broker='redis://localhost:6379/0',
                backend='redis://localhost:6379/0',
                include=['qiita_pet.app.tasks'])

if __name__ == '__main__':
    celery.start()
