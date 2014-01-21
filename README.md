QiiTa-pet
=================

Qiita web frontend based on a tornado-redis-celery setup with a login system, push notifications on celery jobs, and file uploads.

REQUIREMENTS
=================

Programs
> Python 2.7
>
> redis-server 2.6.16
>
> postgreSQL 9.3.0
>
> IPython 1.1.0

Python libraries
> tornado 3.1.1
>
> redis 2.8.0
>
> tornadoredis 2.4.15
>
> celery 3.1.7
>
> psycopg2 2.5.1

RUNING THE EXAMPLE
=================

Add the base folder to your PYTHONPATH.

> export PYTHONPATH=/path/to/QiiTa-pet/

Start the background daemons for redis-server and postgreSQL.

Start an IPython cluster:

> ipcluster start -n 4

Start the celery workers from the qiita_pet folder:

> celery -A app worker --concurrency 4

For the postgres database setup, follow the instructions in create_tables.sql

Start the webserver by running:

> python webserver.py

Navigate to http://localhost:8888 and create a user/pass to log in with. Everything else should be self explanatory.

KNOWN ISSUES
=================
Websockets issue with Safari in non-localhost setting.
