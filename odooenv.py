#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------------
#
#    Copyright (C) 2016  jeo Software  (http://www.jeo-soft.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# -----------------------------------------------------------------------------------
# Directory structure
#
#   /odoo/postgresql
#   /odoo/odoov-[version]
#       /sources
#       /[clientname1]
#           /config
#               openerp-server.conf
#           /data_dir
#           /log
#
##############################################################################

import argparse
import os
import pwd
from datetime import datetime
import time
import logging
import logging.handlers

from classes import Environment
from classes.git_issues import Issues


def install_client(e):
    # get client to install from params
    client_name = e.get_clients_from_params(cant='one')

    if not os.path.isdir(e.home_dir()):
        e.sc_('sudo mkdir {}'.format(e.home_dir()))
    # change ownership to current user
    username = pwd.getpwuid(os.getuid()).pw_name
    e.sc_('sudo chown {}:{} {}'.format(username, username, e.home_dir()))

    # crear el cli, esto baja el repo customer en el home_dir
    cli = e.get_client(client_name)

    # Creating directory's for installation
    e.sc_('mkdir -p {}{}/config'.format(cli.get_home_dir(), cli.get_name()))
    e.sc_('mkdir -p {}{}/data_dir'.format(cli.get_home_dir(), cli.get_name()))
    e.sc_('mkdir -p {}{}/log'.format(cli.get_home_dir(), cli.get_name()))
    # darle permisos para que la imagen pueda escribir
    e.sc_('chmod -R o+w {}{}'.format(cli.get_home_dir(), cli.get_name()))
    e.sc_('mkdir -p {}sources'.format(cli.get_home_dir()))

    # if not exist postgresql create it
    if not os.path.isdir(e.get_psql_dir()):
        e.sc_('mkdir ' + e.get_psql_dir())

    # if not exist log create it
    if not os.path.isfile(LOG_FILENAME):
        e.sc_('sudo mkdir -p ' + os.path.dirname(LOG_FILENAME))
        e.sc_('sudo touch ' + LOG_FILENAME)
        e.sc_('sudo chmod 666 ' + LOG_FILENAME)

    e.msgrun('Installing client {}'.format(client_name))

    # clone or pull repos as needed
    cli.update_repos()

    # creating config file for client
    param = 'sudo docker run --rm '
    param += '-v {}{}/config:/etc/odoo '.format(cli.get_home_dir(), cli.get_name())
    param += '-v {}sources:/mnt/extra-addons '.format(cli.get_home_dir())
    param += '-v {}{}/data_dir:/var/lib/odoo '.format(cli.get_home_dir(), cli.get_name())
    param += '-v {}{}/log:/var/log/odoo '.format(cli.get_home_dir(), cli.get_name())
    param += '--name {}_tmp '.format(cli.get_name())
    param += '{} '.format(cli.get_image('odoo').get_image())
    param += '-- --stop-after-init -s '
    param += '--db-filter={}_.* '.format(cli.get_name())

    ou = '/opt/openerp/addons,' if client_name == 'ou' else ''
    param += '--addons-path={}{} '.format(ou, cli.get_addons_path())
    param += '--logfile=/var/log/odoo/odoo.log '
    param += '--logrotate '
    e.msginf('creating config file')
    if e.sc_(param):
        e.msgerr('failing to write config file. Aborting')
    e.msgdone('Installing done')


def stop_environment(e):
    images_to_stop = ['postgres', 'aeroo']
    e.msgrun('Stopping images ' + ', '.join(images_to_stop))
    err = 0
    for name in images_to_stop:
        e.msgrun('Stopping image ' + name)
        err += e.sc_('sudo docker stop ' + name)
        err += e.sc_('sudo docker rm ' + name)
    if err:
        e.msgerr("errors stopping images")
    e.msgdone('Images stopped')


def run_environment(e):
    e.msgrun('Running environment images')
    client_name = e.get_clients_from_params('one')
    cli = e.get_client(client_name)

    err = 0
    image = cli.get_image('postgres')
    params = 'sudo docker run -d '
    if e.debug_mode():
        params += '-p 5432:5432 '
    params += '-e POSTGRES_USER=odoo '
    params += '-e POSTGRES_PASSWORD=odoo '
    params += '-v {}::/var/lib/postgresql/data '.format(e.get_psql_dir())
    params += '--restart=always '
    params += '--name {} '.format(image.get_name())
    params += image.get_image()
    err += e.sc_(params)

    image = cli.get_image('aeroo')
    params = 'sudo docker run -d '
    params += '-p 127.0.0.1:8989:8989 '
    params += '--name={}'.format(image.get_name())
    params += '--restart=always '
    params += image.get_image()
    err += e.sc_(params)
    if err:
        e.msgerr('Fail running some images.')
    e.msgdone('images running')


def update_db(e):
    mods = e.get_modules_from_params()
    db = e.get_database_from_params()
    cli = e.get_client(e.get_clients_from_params('one'))

    msg = 'Performing update'
    if mods[0] == 'all':
        msg += ' of all modules'
    else:
        msg += ' of module(s) ' + ', '.join(mods)

    msg += ' on database "{}"'.format(db)

    if e.debug_mode():
        msg += ' forcing debug mode'
    e.msgrun(msg)

    params = 'sudo docker run --rm -it '
    params += '-v {}{}/config:/etc/odoo '.format(cli.get_home_dir(), cli.get_name())
    params += '-v {}{}/data_dir:/var/lib/odoo '.format(cli.get_home_dir(), cli.get_name())
    params += '-v {}sources:/mnt/extra-addons '.format(cli.get_home_dir())
    if e.debug_mode():
        params += '-v {}sources/openerp:/usr/lib/python2.7/dist-packages/openerp '.format(
            cli.get_home_dir())
    params += '--link postgres:db '
    params += '{} -- '.format(cli.get_image('odoo').get_image())
    params += '--stop-after-init '
    params += '--logfile=false '
    params += '-d {} '.format(db)
    params += '-u {} '.format(', '.join(mods))
    params += '--log-level=warn '
    if e.debug_mode():
        params += '--debug '
    e.sc_(params)


def update_images_from_list(e, images):
    # avoid image duplicates
    tst_list = []
    unique_images = []
    for img in images:
        if img.getFormattedImage() not in tst_list:
            tst_list.append(img.getFormattedImage())
            unique_images.append(img)

    for img in unique_images:
        params = img.getPullImage()
        e.msginf('pulling image ' + img.getFormattedImage())
        if sc_(params):
            e.msgerr('Fail pulling image ' + img.get_name() + ' - Aborting.')


def update_repos_from_list(e, repos):
    # avoid repo duplicates
    tst_list = []
    unique_repos = []
    for repo in repos:
        if repo.get_formatted_repo() not in tst_list:
            tst_list.append(repo.get_formatted_repo())
            unique_repos.append(repo)
    for repo in unique_repos:
        # hay que actualizar a un tag especifico
        if e.get_tag():
            for command in repo.getTagRepo(e.get_tag()):
                if sc_(command):
                    e.msgerr('Fail installing environment, uninstall and try again.')
        else:
            # Check if repo exists
            if os.path.isdir(repo.getInstDir()):
                e.msginf('pull  ' + repo.get_formatted_repo())
                params = repo.getPullRepo()
            else:
                e.msginf('clone ' + repo.get_formatted_repo())
                params = repo.getCloneRepo(e)

            if sc_(params):
                e.msgerr('Fail installing environment, uninstall and try again.')


def server_help(e):
    client = e.get_clients_from_params('one')
    cli = e.get_client(client)

    params = 'sudo docker run --rm -it '
    params += cli.get_image('odoo').get_image() + ' '
    params += '-- '
    params += '--help '

    if sc_(params):
        e.msgerr("Can't run help")


def quality_test(e):
    """
    Corre un test especifico, los parametros necesarios son:
    -T repositorio test_file.py -d database -c cliente -m modulo
    """
    cli = e.get_client(e.get_clients_from_params('one'))
    repo_name, test_file = e.get_qt_args_from_params()
    module_name = e.get_modules_from_params()[0]
    db = e.get_database_from_params()

    # chequear si el repo está dentro de los repos del cliente
    repos_lst = []
    for repo in cli.get_repos():
        repos_lst.append(repo.get_name())
    if not repo_name in repos_lst:
        e.msgerr('Client "{}" does not own "{}" repo'.format(cli.get_name(), repo_name))

    msg = 'Performing test {} on repo {} for client {} and database {}'.format(
        test_file, repo_name, cli.get_name(), db)
    e.msgrun(msg)

    params = 'sudo docker run --rm -it '
    params += '-v {}{}/config:/etc/odoo '.format(cli.get_home_dir(), cli.get_name())
    params += '-v {}{}/data_dir:/var/lib/odoo '.format(cli.get_home_dir(), cli.get_name())
    params += '-v {}sources:/mnt/extra-addons '.format(cli.get_home_dir())
    #    params += '-v {}sources/openerp:/usr/lib/python2.7/dist-packages/openerp '.format(
    #        cli.get_home_dir())
    #    params += '-v {}sources/image-sources:/usr/local/lib/python2.7/dist-packages '.format(
    #        cli.get_home_dir())
    params += '--link postgres:db '
    params += '{} -- '.format(cli.get_image('odoo').get_image())
    params += '--stop-after-init '
    params += '--logfile=false '
    params += '-d {} '.format(db)
    params += '--log-level=test '
    params += '--test-enable '
    #    params += '-u {} '.format(repo_name)
    params += '--test-file=/mnt/extra-addons/{}/{}/tests/{} '.format(
        repo_name, module_name, test_file)
    sc_(params)


def run_client(e):
    client_name = e.get_clients_from_params('one')
    cli = e.get_client(client_name)
    txt = 'Running image for client {}'.format(client_name)
    if e.debug_mode():
        txt += ' with debug mode on port {}'.format(cli.get_port())
    e.msgrun(txt)
    if e.debug_mode():
        params = 'sudo docker run --rm -it '
    else:
        params = 'sudo docker run -d '
    params += '--link aeroo:aeroo '
    params += '-p {}:8069 '.format(cli.get_port())
    params += '-v {}{}/config:/etc/odoo '.format(cli.get_home_dir(), cli.get_name())
    params += '-v {}{}/data_dir:/var/lib/odoo '.format(cli.get_home_dir(),
                                                       cli.get_name())
    params += '-v {}sources:/mnt/extra-addons '.format(cli.get_home_dir())
    if e.debug_mode():
        # si es openupgrade el sourcesname es upgrade, sino es openerp
        sourcesname = 'openerp' if client_name != 'ou' else 'upgrade'
        params += '-v {}sources/{}:/usr/lib/python2.7/dist-packages/openerp '.format(
            cli.get_home_dir(), sourcesname)
    params += '-v {}{}/log:/var/log/odoo '.format(cli.get_home_dir(), cli.get_name())
    params += '--link postgres:db '
    if not e.debug_mode():
        params += '--restart=always '
    params += '--name {} '.format(cli.get_name())
    params += '{} '.format(cli.get_image('odoo').get_image())
    if not e.no_dbfilter():
        params += '-- --db-filter={}_.* '.format(cli.get_name())
    if not e.debug_mode():
        params += '--logfile=/var/log/odoo/odoo.log '
    else:
        params += '--logfile=False '
    if e.sc_(params):
        e.msgerr("Can't run client {}, Tip: run sudo docker rm -f {}".format(
            cli.get_name(), cli.get_name()))
    e.msgdone('Client {}  up and running on port ()'.format(client_name, cli.get_port()))


def stop_client(e):
    client_name = e.get_clients_from_params('one')
    e.msgrun('stopping client {}'.format(client_name))
    if e.sc_('sudo docker stop ' + client_name):
        e.msgerr('cannot stop client ' + client_name)
    if e.sc_('sudo docker rm ' + client_name):
        e.msgerr('cannot remove client ' + client_name)
    e.msgdone('client stopped')


def pull_all(e):
    client_name = e.get_clients_from_params('one')
    e.msgrun('--- Pulling all images for client {}'.format(client_name))
    cli = e.get_client(client_name)
    for img in cli.get_images():
        img.update
    e.msgdone('All images ok ')
    e.msgrun('--- Pulling all repos for client {}'.format(client_name))
    for rep in cli.get_repos():
        rep.update
    e.msgdone('All repos ok ')


def list_data(e):
    # if --issues option get issues from github
    if args.repo:
        iss = Issues(args.repo[0])
        try:
            for issue in iss.get_issues():
                for line in issue.lines():
                    e.msginf(line)
        except Exception as ex:
            e.msgerr(str(ex))
        return True

    if args.client:
        client_names = args.client
    else:
        client_names = e.get_clients_form_dict()

    clients = []
    for cn in client_names:
        clients.append(e.get_client(cn))

    for cli in clients:
        e.msginf('client -- {} -- on port {}'.format(cli.get_name(), cli.get_port()))
        e.msgrun(3 * '-' +
                 ' Images ' +
                 72 * '-')
        for img in cli.get_images():
            e.msgrun('   {}'.format(img.getFormattedImage()))
        e.msgrun(' ')
        e.msgrun(3 * '-' + 'branch' +
                 4 * '-' + 'repository' +
                 25 * '-' + 'instalation dir' +
                 20 * '-')
        lenrep = lendir = 0
        for repo in cli.get_repos():
            l = len(repo.get_formatted_repo())
            lenrep = l if l > lenrep else lenrep
            l = len(repo.getInstDir())
            lendir = l if l > lendir else lendir
        for repo in cli.get_repos():
            msg = '   {repo:<{len}} '.format(repo=repo.get_formatted_repo(), len=lenrep)
            msg += '{dir:<{len}}'.format(dir=repo.getInstDir(), len=lendir)
            e.msgrun(msg)

def post_backup(e):
    clientName = e.get_clients_from_params('one')
    client = e.get_client(clientName)
    backup_dir = client.get_backup_dir()

    # verify what to do before backup, default is backup housekeeping
    #    TODO Definir si hacemos backup a la S3

    limit_seconds = time.time() - 10 * 60 * 60 * 24

    # walk the backup dir
    for root, dirs, files in os.walk(backup_dir):
        for file in files:
            filename, file_extension = os.path.splitext(file)
            seconds = os.path.getctime(root + file)
            if seconds < limit_seconds:
                e.sc_('sudo rm ' + root + file)
                # os.remove(root+file)
                logger.info('Removed backup file "%s"', file)

    # watch for upload-backup cmdfile and execute
    for root, dirs, files in os.walk(backup_dir):
        for file in files:
            if file[-13:] == 'upload-backup':
                e.sc_(backup_dir + file)


def backup(e):
    """
    Launch a database backup, with docker image 'backup'. The backup file lives in
    client_name/backup
    """

    dbname = e.get_database_from_params()
    clientName = e.get_clients_from_params('one')
    e.msgrun('Backing up database ' + dbname + ' of client ' + clientName)

    client = e.get_client(clientName)
    img = client.get_image('backup')

    params = 'sudo docker run --rm -i '
    params += '--link postgres:db '
    params += '--volumes-from ' + clientName + ' '
    params += '-v ' + client.get_backup_dir() + ':/backup '
    params += '--env DBNAME=' + dbname + ' '
    params += img.get_image() + ' backup'
    try:
        if e.sc_(params):
            e.msgerr('failing backup. Aborting')
    except Exception as ex:
        logger.error('Failing backup %s', str(ex))
        e.msgerr('failing backup. Aborting' + str(ex))

    e.msgdone('Backup done')
    logger.info('Backup database "%s"', dbname)

    post_backup(e)
    return True


def restore(e):
    dbname = e.get_database_from_params()
    clientName = e.get_clients_from_params('one')
    timestamp = e.get_timestamp_from_params()
    new_dbname = e.get_new_database_from_params()
    if dbname == new_dbname:
        e.msgerr('new dbname should be different from old dbname')

    e.msgrun(
        'Restoring database ' + dbname + ' of client ' + clientName + ' onto database ' + new_dbname)

    client = e.get_client(clientName)
    img = client.get_image('backup')

    params = 'sudo docker run --rm -i '
    params += '--link postgres:db '
    params += '--volumes-from ' + clientName + ' '
    params += '-v ' + client.get_backup_dir() + ':/backup '
    params += '--env NEW_DBNAME=' + new_dbname + ' '
    params += '--env DBNAME=' + dbname + ' '
    params += '--env DATE=' + timestamp + ' '
    params += img.get_image() + ' restore'

    if e.sc_(params):
        e.msgerr('failing restore. Aborting')

    e.msgdone('Restore done')
    logger.info('Restore database %s', dbname)
    return True


def decode_backup(root, filename):
    """
    from root and filename generates human readable filename
    i.e.: jeo_datos_201511022236

    :param root: directory where backups reside
    :param filename: backup filename without extension
    :return: formatted filename
    """

    # size of bkp
    path = os.path.join(root, filename + '.dump')
    try:
        size = os.stat(path).st_size
    except:
        size = 0

    # plus size of tar
    path = os.path.join(root, filename + '.tar')
    try:
        size += os.stat(path).st_size
    except:
        size += 0

    size = size / 1000000

    # strip db name
    a = len(filename) - 13
    dbname = filename[0:a]

    # strip date
    date = filename[-12:]
    dt = datetime.strptime(date, '%Y%m%d%H%M')

    # format date
    fdt = datetime.strftime(dt, '%d/%m/%Y %H:%M')
    n = 15 - len(dbname)

    return dbname + n * ' ' + fdt + '  [' + date + '] ' + str(size) + 'M'


def backup_list(e):
    # if no -c option get all clients else get -c clients
    if args.client is None:
        clients = []
        for cli in e.get_clients_form_dict():
            clients.append(cli.get_name())
    else:
        clients = e.get_clients_from_params()

    for clientName in clients:
        cli = e.get_client(clientName)
        dir = cli.get_backup_dir()

        filenames = []
        # walk the backup dir
        for root, dirs, files in os.walk(dir):
            for file in files:
                # get the .dump files and decode it to human redable format
                filename, file_extension = os.path.splitext(file)
                if file_extension == '.dump':
                    filenames.append(filename)

        if len(filenames):
            filenames.sort()
            e.msgrun('List of available backups for client ' + clientName)
            for fn in filenames:
                e.msginf(decode_backup(root, fn))


def cleanup(e):
    if raw_input('Delete ALL databases for ALL clients SURE?? (y/n) ') == 'y':
        e.msginf('deleting all databases!')
        e.sc_('sudo rm -r ' + e.get_psql_dir())

    if raw_input('Delete clients and sources SURE?? (y/n) ') == 'y':
        e.msginf('deleting all client and sources!')
        e.sc_('sudo rm -r ' + e._home_template + '*')


def cron_jobs(e):
    dbname = e.get_database_from_params()
    client = e.get_clients_from_params('one')
    e.msginf('Adding cron jobs to this server')
    croncmd = 'odooenv.py --backup -d {} -c {} > /var/log/odoo/bkp.log #Added by odooenv.py'.format(
        dbname, client)
    cronjob = '0 0,12 * * * {}'.format(croncmd)
    command = '(sudo crontab -l | grep -v "{}" ; echo "{}") | sudo crontab - '.format(
        croncmd, cronjob)
    e.sc_(command)


def cron_list(e):
    e.msginf('List of cron backup jobs on this server')
    e.sc_('sudo crontab -l | grep "#Added by odooenv.py"')


def tag_repos(e):
    """ Tag all repos defined for this client
    """
    client, milestone = e.get_tag()
    tag = client + '-' + milestone
    e.msginf('tagging repos with ' + tag)


def issues(e):
    e.msginf('issues')


if __name__ == '__main__':
    LOG_FILENAME = '/var/log/odooenv/odooenv.log'
    try:
        # Set up a specific logger with our desired output level
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # Add the log message handler to the logger
        handler = logging.handlers.RotatingFileHandler(
            LOG_FILENAME, maxBytes=2000000, backupCount=5)

        # formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)

        logger.addHandler(handler)
    except Exception as ex:
        logger = logging.getLogger(__name__)
        print 'Warning!, problems with logfile', str(ex)

    parser = argparse.ArgumentParser(description='Odoo environment setup v3.6.0')
    parser.add_argument('-i', '--install-cli',
                        action='store_true',
                        help="Install client, requires -c option.")

    parser.add_argument('-R', '--run-env',
                        action='store_true',
                        help="Run database and aeroo images.")

    parser.add_argument('-S', '--stop-env',
                        action='store_true',
                        help="Stop database and aeroo images.")

    parser.add_argument('-r', '--run-cli',
                        action='store_true',
                        help="Run client odoo images, requieres -c options. Optional")

    parser.add_argument('-s', '--stop-cli',
                        action='store_true',
                        help="Stop client images, requieres -c options.")

    parser.add_argument('-p', '--pull-all',
                        action='store_true',
                        help="Pull all images and repos for a client. Needs -c")

    parser.add_argument('-l', '--list',
                        action='store_true',
                        help="List all data in this server. Clients and images. with "
                             "-c option list only one client and with --issues REPO "
                             "option list the github issues from repo")

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Go verbose mode.")

    parser.add_argument('-q', '--quiet',
                        action='store_true',
                        help="Supress all standard output.")

    parser.add_argument('-n', '--no-ip-install',
                        action='store_true',
                        help="Install no-ip on this server.")

    parser.add_argument('-u', '--update-db',
                        action='store_true',
                        help="Update database requires -d -c and -m options.")

    parser.add_argument('-d',
                        action='store',
                        nargs=1,
                        dest='database',
                        help="Database name.")

    parser.add_argument('-w',
                        action='store',
                        nargs=1,
                        dest='new_database',
                        help="New database name.")

    parser.add_argument('-m',
                        action='append',
                        dest='module',
                        help="Module to update or all, you can specify multiple -m \
                        options.")

    parser.add_argument('-c',
                        action='append',
                        dest='client',
                        help="Client name")

    parser.add_argument('--debug',
                        action='store_true',
                        help='This option has three efects: 1.- when doing an update database, '
                             '(option -u) it forces debug mode. 2.- When running environment '
                             'it opens port 5432 to access postgres server databases. 3.- when '
                             'doing a pull (option -p) it clones the full repo i.e. does not '
                             'issue --depth 1 to git ')

    parser.add_argument('--cleanup',
                        action='store_true',
                        help='Delete all files clients, sources, and databases in this '
                             'server. It ask about each thing.')

    parser.add_argument('--no-dbfilter',
                        action='store_true',
                        help='Eliminates dbfilter: The client can see any database. '
                             'Without this, the client can only see databases starting '
                             'with clientname_')

    parser.add_argument('-H', '--server-help',
                        action='store_true',
                        help="List server help requieres -c option")

    parser.add_argument('--backup',
                        action='store_true',
                        help="Lauch backup requieres -d and -c options.")

    parser.add_argument('--backup-list',
                        action='store_true',
                        help="List available backups with timestamps to restore.")

    parser.add_argument('--restore',
                        action='store_true',
                        help="Lauch restore requieres -c, -d, -w and -t options.")

    parser.add_argument('-t',
                        action='store',
                        nargs=1,
                        dest='timestamp',
                        help="Timestamp to restore database, see --backup-list for "
                             "available timestamps.")

    parser.add_argument('-Q', '--quality-test',
                        action='store',
                        metavar=('repo', 'test_file'),
                        nargs=2,
                        dest='quality_test',
                        help="Perform a test, arguments are Repo where test lives, "
                             "and yml/py test file to run (please include extension). "
                             "Need -d, -m and -c options "
                             "Note: for the test to run there must be an admin user "
                             "with passw admin")

    parser.add_argument('-j', '--cron-jobs',
                        action='store_true',
                        help='Cron Backup. it adds cron jobs for doing backup to a '
                             'client database. backups twice a day at 12 AM and 12 PM. '
                             'Needs a -c option to tell which client to backup.')

    parser.add_argument('--cron-list',
                        action='store_true',
                        help="List available cron jobs")

    parser.add_argument('--translate',
                        action='store_true',
                        help="Generate a po file for a module to translate, need a -r "
                             "and -m option")

    parser.add_argument('--issues',
                        dest='repo',
                        nargs=1,
                        action='store',
                        help="list formatted and priorized issues from github, "
                             "used with -l this option supports github API v3 "
                             "priority is the number between brackets in issue title")

    parser.add_argument('-T',
                        action='store',
                        nargs=2,
                        metavar=('client', 'milestone'),
                        dest='tag_repos',
                        help="Tag all repos used by a client with a tag composed for "
                             "client ntame and milestone from client sources")

    args = parser.parse_args()
    enviro = Environment(args)

    if args.install_cli:
        install_client(enviro)
    if args.stop_env:
        stop_environment(enviro)
    if args.run_env:
        run_environment(enviro)
    if args.stop_cli:
        stop_client(enviro)
    if args.run_cli:
        run_client(enviro)
    if args.pull_all:
        pull_all(enviro)
    if args.list:
        list_data(enviro)
    if args.update_db:
        update_db(enviro)
    if args.backup:
        backup(enviro)
    if args.restore:
        restore(enviro)
    if args.backup_list:
        backup_list(enviro)
    if args.cleanup:
        cleanup(enviro)
    if args.server_help:
        server_help(enviro)
    if args.cron_jobs:
        cron_jobs(enviro)
    if args.cron_list:
        cron_list(enviro)
    if args.quality_test:
        quality_test(enviro)
    if args.tag_repos:
        tag_repos(enviro)
