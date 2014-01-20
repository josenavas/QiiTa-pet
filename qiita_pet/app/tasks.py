#!/usr/bin/env python

__author__ = "Joshua Shorenstein"
__copyright__ = "Copyright 2013, The QiiTa-pet Project"
__credits__ = ["Joshua Shorenstein", "Jose Antonio Navas Molina"]
__license__ = "BSD"
__version__ = "0.2.0-dev"
__maintainer__ = "Joshua Shorenstein"
__email__ = "Joshua.Shorenstein@colorado.edu"
__status__ = "Development"

from __future__ import absolute_import
from qiita_pet.app.celery import celery
from qiita_pet.app.connections import postgres


@celery.task
def delete_job(user, jobid):
    try:
        pgcursor = postgres.cursor()
        pgcursor.execute('DELETE FROM qiita_job WHERE analysis_id = %s',
                        (jobid,))
        pgcursor.execute('DELETE FROM qiita_analysis WHERE analysis_id = %s',
                        (jobid,))
        postgres.commit()
        pgcursor.close()
    except Exception, e:
        pgcursor.close()
        postgres.rollback()
        raise Exception("Can't remove metaanalysis from database!\n"+str(e))
