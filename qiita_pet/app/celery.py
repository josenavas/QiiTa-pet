from __future__ import absolute_import

from celery import Celery

celery = Celery('qiita_pet.app.celery', broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['qiita_pet.app.tasks'])

if __name__ == '__main__':
    celery.start()