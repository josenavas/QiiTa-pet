#!/usr/bin/env python

__author__ = "Joshua Shorenstein"
__copyright__ = "Copyright 2013, The QiiTa-pet Project"
__credits__ = ["Joshua Shorenstein", "Jose Antonio Navas Molina"]
__license__ = "BSD"
__version__ = "0.2.0-dev"
__maintainer__ = "Joshua Shorenstein"
__email__ = "Joshua.Shorenstein@colorado.edu"
__status__ = "Development"

from redis import Redis
from redis.exceptions import RedisError
from psycopg2 import connect as pg_connect, Error as PostgresError
from IPython.parallel import Client
from IPython.parallel.error import IPythonError

# Set up Redis connection
try:
    r_server = Redis()
except RedisError, e:
    raise RuntimeError("Unable to connect to the REDIS database: %s" % e)

# Set up Postgres connection
try:
    postgres = pg_connect("dbname='qiita' user='defaultuser' \
        password='defaultpassword' host='localhost'")
except PostgresError, e:
    raise RuntimeError("Unable to connect to the POSTGRES database: %s" % e)

# Set up IPython connection
try:
    ipython_client = Client()
    lview = ipython_client.load_balanced_view()
    lview.block = False
except IPythonError, e:
    raise RuntimeError("Unable to connect to the IPython cluster: %s" % e)
