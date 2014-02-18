import multiprocessing

name = 'readbox'
bind = '0.0.0.0:8000'
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 60
keepalive = 2
debug = False
spew = False

try:
    from gevent import monkey

    worker_class = 'gevent'

    # this ensures forked processes are patched with gevent/gevent-psycopg2
    def do_post_fork(server, worker):
        monkey.patch_all()

    post_fork = do_post_fork
except ImportError:
    pass