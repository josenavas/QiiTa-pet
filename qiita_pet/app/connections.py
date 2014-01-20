from redis import Redis
from psycopg2 import connect as pg_connect
from IPython.parallel import Client

# Set up Redis connection
try:
    r_server = Redis()
except:
    raise RuntimeError("ERROR: unable to connect to the REDIS database.")

# Set up Postgres connection
try:
    postgres = pg_connect("dbname='qiita' user='defaultuser' \
        password='defaultpassword' host='localhost'")
except:
    raise RuntimeError("ERROR: unable to connect to the POSTGRES database.")

# Set up IPython connection
try:
    ipython_client = Client()
    lview = ipython_client.load_balanced_view()
    lview.block = False
except:
    raise RuntimeError("ERROR: unable to connect to the IPython server")