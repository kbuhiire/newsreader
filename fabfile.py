from __future__ import with_statement
from fabric.api import run, env, sudo, cd, prefix, put
from fabric.contrib import django, files
from contextlib import contextmanager as _contextmanager
import os

SSH_HOME = "~/.ssh"
AUTH_KEYS = "~/.ssh/authorized_keys"
PUB_KEY = "~/.ssh/server_rsa.pub"


def test():
    env.user = 'readbox'
    env.hosts = ['']
    env.key_filename = '~/.ssh/server_rsa'
    env.activate = 'source ~/readbox_env/bin/activate'
    django.settings_module('manhattan.settings_dev')


def deploydb():
    env.user = 'root'
    env.hosts = ['']
    env.key_filename = '~/.ssh/server_rsa'


def deployfirst(host):
    env.user = 'root'
    env.hosts = host
    env.key_filename = '~/.ssh/server_rsa'


def deploy(opt=False):
    server_dict = {
        'action': '',
    }
    env.user = 'ubuntu'
    if not opt:
        env.hosts = server_dict.values()
    else:
        env.hosts = [server_dict[str(opt)]]
    env.activate = 'source ~/readbox_env/bin/activate'
    env.key_filename = '~/.ssh/server_rsa'
    django.settings_module('manhattan.settings')


@_contextmanager
def virtualenv():
    with prefix(env.activate):
        yield


def _get_public_key(key_file):
    with open(os.path.expanduser(key_file)) as fd:
        key = fd.readline().strip()
        return key


def add_key(first=False, filename=PUB_KEY):
    if first:
        sudo('adduser ubuntu')
        sudo('adduser ubuntu sudo')
        sudo('mkdir /home/ubuntu/.ssh')
        sudo('cp .ssh/authorized_keys /home/ubuntu/.ssh/')
        sudo('chown ubuntu /home/ubuntu/.ssh/authorized_keys')
        sudo('chown ubuntu /home/ubuntu/.ssh')
    commands = (
        "mkdir -p %s;"
        "chmod 700 %s;"
        """echo "%s" >> %s;"""
        "chmod 644 %s;"
    )

    t = (SSH_HOME, SSH_HOME, _get_public_key(filename), AUTH_KEYS, AUTH_KEYS)
    command = commands % t
    run(command)
    if first:
        put('config/sshd_config', '/etc/ssh/sshd_config', use_sudo=True)
        sudo('service ssh restart')


def pre_setup_webserver():
    run('ssh-keygen -t rsa -C "email@example.com"')
    run('cat ~/.ssh/id_rsa.pub')


def setup_first():
    sudo('apt-get --yes update')
    sudo('apt-get --yes upgrade')
    sudo('apt-get --yes install python-dev python-pip libevent-dev python-gevent supervisor git libmysqlclient-dev')
    sudo('apt-get --yes install python-software-properties build-essential libxml2-dev libxslt-dev libmemcached-dev')
    run('git config --global user.email "support@readbox.co"')
    run('git config --global user.name "Readbox Server"')
    run('git config --global credential.helper cache')
    sudo('pip install virtualenv')
    run('virtualenv readbox_env')
    with virtualenv():
        run('easy_install setuptools')
        run('pip install gunicorn')
        run('pip install gevent')
        run('git clone git@github.com:vinceprignano/manhattan.git')
        with cd('~/manhattan'):
            run('pip install -r requirements.txt')
            run('cp manhattan/settings_deploy.py manhattan/settings.py')
    with cd('~'):
        run('mkdir logs')


def setup_mysql(update=False):
    if not update:
        sudo('apt-get --yes install python-software-properties')
        sudo('apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xcbcb082a1bb943db')
        sudo("add-apt-repository 'deb http://ftp.osuosl.org/pub/mariadb/repo/5.5/ubuntu precise main'")
        put('config/preferences_mariadb', '/etc/apt/preferences.d/mariadb', use_sudo=True)
        sudo('apt-get --yes update')
        sudo('apt-get --yes upgrade')
        sudo('apt-get --yes install mariadb-server')


def setup_elasticsearch():
    sudo('apt-get update')
    sudo('apt-get --yes install openjdk-7-jre-headless wget')
    sudo('wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-0.90.7.deb')
    sudo('dpkg -i elasticsearch-0.90.7.deb')
    sudo('service elasticsearch start')


def setup_nginx():
    sudo('apt-get --yes install nginx chkconfig')
    sudo('ln -s /usr/lib/insserv/insserv /sbin/insserv')
    put('config/nginx.conf', '/etc/nginx/sites-available/default', use_sudo=True)
    sudo('service nginx start')
    sudo('chkconfig --add nginx')
    sudo('chkconfig nginx on')


def setup_redis():
    sudo('apt-get --yes install redis-server')
    put('config/redis.conf', '/etc/redis/', use_sudo=True)
    sudo('service redis-server stop')
    try:
        sudo('killall redis-server')
    except Exception:
        pass
    sudo('service redis-server start')


def setup_memcached():
    sudo('apt-get --yes install memcached')


def django_syncdb():
    with virtualenv():
            with cd('~/manhattan'):
                run('python manage.py syncdb')


def django_collectstatic(remove=False):
    with virtualenv():
        with cd('~/manhattan'):
            if remove:
                run('rm -r STATIC')
            run('python manage.py collectstatic')


def django_rebuild_index():
    with virtualenv():
        with cd('~/manhattan'):
            run('python manage.py rebuild_index')


def django_migrate(app):
    with virtualenv():
        with cd('~/manhattan'):
            run('python manage.py migrate ' + app)


def django_schemamigration(app):
    with virtualenv():
        with cd('~/manhattan'):
            run('python manage.py schemamigration ' + app + ' --auto')


def install_requirements(full=False):
    with virtualenv():
        with cd('~/manhattan'):
            if full:
                run('pip freeze | xargs pip uninstall -y')
            run('pip install -r requirements.txt')


def pull():
    with virtualenv():
        with cd('~/manhattan'):
            run('git reset --hard')
            run('git clean -f')
            run('git pull')
            run('cp manhattan/settings_deploy.py manhattan/settings.py')


def restart(service, num_workers=4):
    if service == 'workers':
        service = ''
        for x in range(0, num_workers):
            service += ' worker' + str(x)
    sudo('supervisorctl restart ' + service)


def run_gunicorn():
    with virtualenv():
        with cd('~/manhattan'):
            put('config/supervisor/gunicorn.conf', '/etc/supervisor/conf.d/', use_sudo=True)
            sudo('supervisorctl reread')
            sudo('supervisorctl update')
            sudo('supervisorctl start gunicorn')


def run_celerybeat():
    with virtualenv():
        with cd('~/manhattan'):
            put('config/supervisor/celerybeat.conf', '/etc/supervisor/conf.d/', use_sudo=True)
            sudo('supervisorctl reread')
            sudo('supervisorctl update')
            sudo('supervisorctl start celerybeat')


def run_celeryd():
    with virtualenv():
        with cd('~/manhattan'):
            put('config/supervisor/celeryd.conf', '/etc/supervisor/conf.d/', use_sudo=True)
            sudo('supervisorctl reread')
            sudo('supervisorctl update')
            sudo('supervisorctl start celeryd')


def setup_workers(num=0):
    with virtualenv():
        with cd('~/manhattan'):
            with open('config/supervisor/celeryWx.conf') as conf:
                text = conf.read()
                for x in range(0, int(num)):
                    files.append('/etc/supervisor/conf.d/worker' + str(num) + '.conf', text.format(x), use_sudo=True)
                sudo('supervisorctl reread')
                sudo('supervisorctl update')


def status():
    sudo('supervisorctl status')
