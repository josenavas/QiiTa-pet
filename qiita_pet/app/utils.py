#!/usr/bin/env python

__author__ = "Joshua Shorenstein"
__copyright__ = "Copyright 2013, The QiiTa-pet Project"
__credits__ = ["Joshua Shorenstein", "Jose Antonio Navas Molina"]
__license__ = "BSD"
__version__ = "0.2.0-dev"
__maintainer__ = "Joshua Shorenstein"
__email__ = "Joshua.Shorenstein@colorado.edu"
__status__ = "Development"

from time import localtime


class MetaAnalysisData(object):
    def __init__(self):
        self.user = ''
        self.analysis = ''
        self.studies = []
        self.datatypes = []
        self.metadata = []
        self.jobs = {}
        self.options = {}

    def __str__(self):
        buildstr = "USER: " + self.user
        buildstr += "\nJOB: " + self.analysis
        buildstr += "\nSTUDIES: " + str(self.studies)
        buildstr += "\nDATATYPES: " + str(self.datatypes)
        buildstr += "\nMETADATA: " + str(self.metadata)
        buildstr += "\nANALYSES: " + str(self.jobs)
        buildstr += "\nOPTIONS: " + str(self.options)
        return buildstr

    #tornado sends form data in unicode, convert to ascii for ease of use
    def set_user(self, user):
        self.user = user.encode('ascii')

    def set_analysis(self, analysis):
        if analysis == '':
            time = localtime()
            self.analysis = '-'.join(map(str, [time.tm_year, time.tm_mon,
                                               time.tm_mday, time.tm_hour,
                                               time.tm_min, time.tm_sec]))
        else:
            self.analysis = analysis.encode('ascii')

    def set_studies(self, studies):
        self.studies = [study.encode('ascii') for study in studies]

    def set_datatypes(self, datatypes):
        self.datatypes = [datatype.encode('ascii') for datatype in datatypes]

    def set_metadata(self, metadata):
        self.metadata = [m.encode('ascii') for m in metadata]

    def set_jobs(self, datatype, jobs):
        self.jobs[datatype] = [a.encode('ascii') for a in jobs]

    def set_options(self, datatype, analysis, options):
        self.options[datatype + ':' + analysis] = options

    def add_datatype(self, datatype):
        if type(datatype) is not str:
            raise TypeError("datatype should be string!")
        self.datatypes.append(datatype)

    def get_user(self):
        return self.user

    def get_analysis(self):
        return self.analysis

    def get_studies(self):
        return self.studies

    def get_datatypes(self):
        return self.datatypes

    def get_metadata(self):
        return self.metadata

    def get_jobs(self, datatype):
        if datatype in self.jobs.keys():
            return self.jobs[datatype]
        else:
            raise ValueError('Datatype not part of analysis!')

    def get_options(self, datatype, analysis):
        if datatype + ':' + analysis in self.options.keys():
            return self.options[datatype + ':' + analysis]
        else:
            raise ValueError('Datatype or analysis passed not part of '
                             'analysis!')

    def iter_options(self, datatype, analysis):
        if datatype + ':' + analysis in self.options.keys():
            optdict = self.options[datatype + ':' + analysis]
            for opt in optdict:
                yield opt, optdict[opt]
        else:
            raise ValueError('Datatype or analysis passed not part of '
                             'analysis!')

    def html(self):
        html = ['<table width="100%"><tr><td width="34%""><h3>Studies</h3>']

        for study in self.get_studies():
            html.append('%s<br />' % study)

        html.append('</td><td width="33%"><h3>Metadata</h3>')

        for metadata in self.get_metadata():
            html.append('%s<br />' % metadata)

        html.append('</td><td width="33%"><h3>Datatypes</h3>')

        for datatype in self.get_datatypes():
            html.append('%s<br />' % datatype)

        html.append('</td><tr></table>')

        html.append('<h3>Option Settings</h3>')

        for datatype in self.get_datatypes():
            for job in self.get_jobs(datatype):
                html.append(''.join(['<table width=32%" style="display: \
                            inline-block;"><tr><td><b>', datatype, ' - ',
                            job, '</b></td></tr><tr><td>']))

                for opt, value in self.iter_options(datatype, job):
                    html.append(''.join([opt, ':', str(value), '<br />']))
                html.append('</td></tr></table>')

        return ' '.join(html)
