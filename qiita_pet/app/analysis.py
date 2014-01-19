from qiita_pet.app.connections import lview, postgres, r_server
from time import sleep
from json import dumps
from random import randint

##################################
#         Helper functions       #
##################################

def push_notification(user, analysis, job, msg, files=[], done=False):
    '''Creates JSON and takes care of push notification'''
    jsoninfo = {
        'analysis': analysis,
        'job': job,
        'msg': msg,
        'results': files,
    }
    if done:
        jsoninfo['done'] = 1
    else:
        jsoninfo['done'] = 0
    jsoninfo = dumps(jsoninfo)
    #need the rpush and publish for leaving page and if race condition
    try:
        r_server.rpush(user + ":messages", jsoninfo)
        r_server.publish(user, jsoninfo)
    except Exception, e:
        print "Can't push!\n", str(e), "\n", str(jsoninfo)

def finish_job(user, analysis_id, analysis_name, results, datatype, j_type):
    """"""
    # Set job results
    # Create a tuple with the SQL values
    # Format: (SQL list of output files, datatype, job run, analysis id)
    sql_results = ( "{%s}" % ','.join(results), datatype, j_type, analysis_id)

    # Update job in job table to done and with their results
    SQL = "UPDATE qiita_job SET job_done = true, job_results = %s  WHERE \
        job_datatype = %s AND job_type = %s AND analysis_id = %s"
    try:
        pgcursor = postgres.cursor()
        pgcursor.execute(SQL, sql_results)
        postgres.commit()
    except Exception, e:
        pgcursor.close()
        postgres.rollback()
        raise Exception("Can't finish off job!\n"+str(e))

    # Check that all the jobs from current analysis are done
    SQL = "SELECT job_done FROM qiita_job WHERE analysis_id = %s"
    try:
        pgcursor.execute(SQL, (analysis_id,))
        job_status = pgcursor.fetchall()
        pgcursor.close()
    except  Exception, e:
        pgcursor.close()
        postgres.rollback()
        raise Exception("Can't get job status!\n"+str(e))

    # If all done -> call finish analysis
    if all([status[0] for status in job_status]):
        finish_analysis(user, analysis_id, analysis_name)

def finish_analysis(user, analysis_id, analysis_name):
    """"""
    # Update analysis to done in analysis table
    SQL = "UPDATE qiita_analysis SET analysis_done = true WHERE analysis_id = %s"
    try:
        pgcursor = postgres.cursor()
        pgcursor.execute(SQL, (analysis_id,))
        postgres.commit()
        pgcursor.close()
    except Exception, e:
        pgcursor.close()
        postgres.rollback()
        raise Exception("Can't finish off analysis!\n"+str(e))

    # Wipe out all messages from redis list so no longer pushed to user
    for message in r_server.lrange(user + ':messages', 0, -1):
        if analysis_name in str(message):
            r_server.lrem(user + ':messages', message)

    # Finally, push finished state
    push_notification(user, analysis_name, 'done', 'allcomplete')

@lview.remote(block=False)
def switchboard(user, analysis_data):
    '''Fires off all analyses for a given job.

    INPUTS:
        user: username of user requesting job
        analysis_data: MetaAnalysisData object with all information in it.

    OUTPUT: NONE '''

    analysis_name = analysis_data.get_analysis()

    # Insert analysis into the postgres analysis table
    SQL = '''INSERT INTO qiita_analysis (qiita_username, analysis_name, 
        analysis_studies, analysis_metadata, analysis_timestamp) VALUES 
        (%s, %s, %s, %s, 'now') RETURNING analysis_id'''
    sql_studies_list = "{%s}" % ','.join(analysis_data.get_studies())
    sql_metadata_list = "{%s}" % ','.join(analysis_data.get_metadata())
    parameters = (user, analysis_name, sql_studies_list, sql_metadata_list)
    try:
        pgcursor = postgres.cursor()
        pgcursor.execute(SQL, parameters)
        analysis_id = pgcursor.fetchone()[0]
        postgres.commit()
    except Exception, e:
        postgres.rollback()
        raise RuntimeError("Can't add meta analysis to table!\n"+str(e))

    # Insert all jobs into jobs table
    SQL = """INSERT INTO qiita_job (analysis_id, job_datatype, job_type, 
        job_options) VALUES (%s, %s, %s, %s)"""
    jobs_list = []
    for datatype in analysis_data.get_datatypes():
        for analysis in analysis_data.get_jobs(datatype):
            jobs_list.append( (str(analysis_id), datatype, analysis, 
                dumps(analysis_data.get_options(datatype, analysis))))
    try:
        pgcursor.executemany(SQL, jobs_list)
        postgres.commit()
        pgcursor.close()
    except Exception, e:
        pgcursor.close()
        postgres.rollback()
        raise RuntimeError("Can't add metaanalysis jobs to table!\n"+str(e))

    # BLAH
    functions_dict = {
        'Alpha_Diversity': Alpha_Diversity,
        'Beta_Diversity': Beta_Diversity,
        'Procrustes': Procrustes
    }

    # Submit the jobs
    for datatype in analysis_data.get_datatypes():
        for analysis in analysis_data.get_jobs(datatype):
            opts = analysis_data.get_options(datatype, analysis)
            functions_dict[analysis](user, analysis_id, analysis_name,
                                     datatype, opts)

    # Celery dependent
    # analgroup = []
    # for datatype in analysis_data.get_datatypes():
    #     for analysis in analysis_data.get_analyses(datatype):
    #         s = signature('app.tasks.'+analysis, args=(user, jobname, datatype,
    #             analysis_data.get_options(datatype, analysis)))
    #         analgroup.append(s)
    # job = group(analgroup)
    # res = job.apply_async()
    # results = res.join()
    # End of Celery dependent

##################################
#       Analysis functions       #
##################################

@lview.remote(block=False)
def OTU_Table(user, jobname, datatype, opts):
    push_notification(user, jobname, datatype + ':OTU_Table', 'Running')
    try:
        sleep(randint(1,5))
        results = ["placeholder.html"]
        push_notification(user, jobname, datatype + ':OTU_Table', 'Completed',
            results, done=True)
    except Exception, e:
        push_notification(user, jobname, datatype + ':OTU_Table',
            'ERROR: ' + str(e), done=True)
    #MUST RETURN IN FORMAT (results, datatype, analysis)
    return [results, datatype, 'OTU_Table']


@lview.remote(block=False)
def TopiaryExplorer_Visualization(user, jobname, datatype, opts):
    push_notification(user, jobname, 
        datatype + ':TopiaryExplorer_Visualization', 'Running')
    try:
        sleep(randint(5,20))
        results = ["placeholder.html"]
        push_notification(user, jobname, 
            datatype + ':TopiaryExplorer_Visualization', 'Completed',
            results, done=True)
    except Exception, e:
        push_notification(user, jobname, datatype + ':TopiaryExplorer_Visualization',
            'ERROR: ' + str(e), done=True)
    #MUST RETURN IN FORMAT (results, datatype, analysis)
    return [results, datatype, 'TopiaryExplorer_Visualization']


@lview.remote(block=False)
def Heatmap(user, jobname, datatype, opts):
    push_notification(user, jobname, datatype + ':Heatmap', 'Running')
    try:
        sleep(randint(5,20))
        results = ["placeholder.html"]
        push_notification(user, jobname, datatype + ':Heatmap', 'Completed',
            results, done=True)
    except Exception, e:
        push_notification(user, jobname, datatype + ':Heatmap',
            'ERROR: ' + str(e), done=True)
    #MUST RETURN IN FORMAT (results, datatype, analysis)
    return [results, datatype, 'Heatmap']


@lview.remote(block=False)
def Heatmap(user, jobname, datatype, opts):
    push_notification(user, jobname, datatype + ':Heatmap', 'Running')
    try:
        sleep(randint(5,20))
        results = ["placeholder.html"]
        push_notification(user, jobname, datatype + ':Heatmap', 'Completed',
            results, done=True)
    except Exception, e:
        push_notification(user, jobname, datatype + ':Heatmap',
            'ERROR: ' + str(e), done=True)
    #MUST RETURN IN FORMAT (results, datatype, analysis)
    return [results, datatype, 'Heatmap']


@lview.remote(block=False)
def Heatmap(user, jobname, datatype, opts):
    push_notification(user, jobname, datatype + ':Heatmap', 'Running')
    try:
        sleep(randint(5,20))
        results = ["placeholder.html"]
        push_notification(user, jobname, datatype + ':Heatmap', 'Completed',
            results, done=True)
    except Exception, e:
        push_notification(user, jobname, datatype + ':Heatmap',
            'ERROR: ' + str(e), done=True)
    #MUST RETURN IN FORMAT (results, datatype, analysis)
    return [results, datatype, 'Heatmap']


@lview.remote(block=False)
def Taxonomy_Summary(user, jobname, datatype, opts):
    push_notification(user, jobname, datatype + ':Taxonomy_Summary', 'Running')
    try:
        sleep(randint(5,20))
        results = ["placeholder.html"]
        push_notification(user, jobname, datatype + ':Taxonomy_Summary', 'Completed',
            results, done=True)
    except Exception, e:
        push_notification(user, jobname, datatype + ':Taxonomy_Summary',
            'ERROR: ' + str(e), done=True)
    #MUST RETURN IN FORMAT (results, datatype, analysis)
    return [results, datatype, 'Taxonomy_Summary']


@lview.remote(block=False)
def Alpha_Diversity(user, analysis_id, analysis_name, datatype, opts):
    # Push the job has been started
    push_notification(user, analysis_name, datatype + ':Alpha_Diversity', 'Running')
    try:
        # Run the actual job
        sleep(randint(5,10))
        results = ["static/demo/alpha/%s/alpha_rarefaction_plots/rarefaction_plots.html" % datatype.lower()]
        # Push the job is done
        push_notification(user, analysis_name, datatype + ':Alpha_Diversity', 'Completed',
            results, done=True)
    except Exception, e:
        # Push the job failed
        push_notification(user, analysis_name, datatype + ':Alpha_Diversity',
            'ERROR: ' + str(e), done=True)
    # Finish the job
    finish_job(user, analysis_id, analysis_name, results, datatype, 'Alpha_Diversity')

@lview.remote(block=False)
def Beta_Diversity(user, analysis_id, analysis_name, datatype, opts):
    # Push the job has been started
    push_notification(user, analysis_name, datatype + ':Beta_Diversity', 'Running')
    try:
        # Run the actual job
        sleep(randint(10,20))
        if datatype=="16S":
            results = ["static/demo/beta/emperor/unweighted_unifrac_16s/index.html", "static/demo/beta/emperor/weighted_unifrac_16s/index.html",]
        else:
            results = ["static/demo/beta/emperor/%s/index.html" % datatype.lower()]
        # Push the job is done
        push_notification(user, analysis_name, datatype + ':Beta_Diversity', 'Completed',
            results, done=True)
    except Exception, e:
        # Push the job failed
        push_notification(user, analysis_name, datatype + ':Beta_Diversity',
            'ERROR: ' + str(e), done=True)
    # Finish the job
    finish_job(user, analysis_id, analysis_name, results, datatype, 'Beta_Diversity')


@lview.remote(block=False)
def Procrustes(user, analysis_id, analysis_name, datatype, opts):
    # Push the job has been started
    push_notification(user, analysis_name, datatype + ':Procrustes', 'Running')
    try:
        # Run the actual job
        sleep(randint(20,20))
        results = ["static/demo/combined/plots/index.html"]
        # Push the job is done
        push_notification(user, analysis_name, datatype + ':Procrustes', 'Completed',
            results, done=True)
    except Exception, e:
        # Push the job failed
        push_notification(user, analysis_name, datatype + ':Procrustes',
            'ERROR: ' + str(e), done=True)
    # Finish the job
    finish_job(user, analysis_id, analysis_name, results, datatype, 'Procrustes')


@lview.remote(block=False)
def Network_Analysis(user, jobname, datatype, opts):
    push_notification(user, jobname, datatype + ':Network_Analysis', 'Running')
    try:
        sleep(randint(5,20))
        results = ["placeholder.html"]
        push_notification(user, jobname, datatype + ':Network_Analysis', 'Completed',
            results, done=True)
    except Exception, e:
        push_notification(user, jobname, datatype + ':Network_Analysis',
            'ERROR: ' + str(e), done=True)
    #MUST RETURN IN FORMAT (results, datatype, analysis)
    return [results, datatype, 'Network_Analysis']