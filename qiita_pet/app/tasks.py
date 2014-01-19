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
        postgres.rollback()
        raise Exception("Can't remove metaanalysis from database!\n"+str(e))