#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ##############################################################################
#
#    Jorge Obiols Software,
#    Copyright (C) 2015-Today JEO <jorge.obiols@gmail.com>
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
###############################################################################


import argparse
import subprocess
import sys

RED = "\033[1;31m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
YELLOW_LIGHT = "\033[33m"
CLEAR = "\033[0;m"


def image_from_dict(image):
    ret = ''
    ret += image['repo']
    if image['dir'] != '':
        ret += '/'
        ret += image['dir']
    if image['ver'] != '':
        ret += ':' + image['ver']
    return ret


def repo_from_dict(dict):
    return dict['repo'] + '/' + dict['dir']


def green(string):
    return GREEN + string + CLEAR


def yellow(string):
    return YELLOW + string + CLEAR


def red(string):
    return RED + string + CLEAR


def yellow_light(string):
    return YELLOW_LIGHT + string + CLEAR


def msgrun(msg):
    print yellow(msg)


def msgdone(msg):
    print green(msg)


def msgerr(msg):
    print red(msg)
    sys.exit()


def msginf(msg):
    print yellow_light(msg)


def client_port(cli):
    port = ''
    for client in CLIENTS:
        if client['client'] == cli:
            port = client['port']
    if port == '':
        msgerr('no ' + client + ' client in this environment')
    return port


def uninstall_environment():
    msgrun('Uninstalling odoo environment ' + ODOOVER)
    subprocess.call(['sudo rm -r ' + HOME], shell=True)
    if raw_input('Delete postgresql directory? (y/n) ') == 'y':
        subprocess.call(['sudo rm -r ' + PSQL], shell=True)
    return True


def install_environment():
    msgrun('Installing odoo environment ' + ODOOVER)

    # if not exist psql create it
    if subprocess.call(['ls ' + PSQL], shell=True):
        subprocess.call(['mkdir ' + PSQL], shell=True)

    # install sources
    subprocess.call(['mkdir -p ' + HOME + 'sources'], shell=True)

    for repo in REPOS:
        msginf('pulling repo ' + repo_from_dict(repo))
        if subprocess.call('git clone -b ' + repo['branch'] +
                                   ' --depth 1 http://github.com/' + repo_from_dict(
                repo) + ' '
                                   + HOME + 'sources/' + repo['dir'], shell=True):
            msgerr('Fail installing environment, uninstall and try again.')

    msgdone('Install Done ' + ODOOVER)
    return True


def update_database():
    db = args.database[0]
    mods = args.module[0]
    cli = args.client[0]

    msgrun('Performing update database on ' + db + ' with module ' + ', '.join(mods))

    if (ODOOVER == '8.0') or (ODOOVER == '8.0.1') or (ODOOVER == 'ou-8.0'):
        subprocess.call(
            'sudo docker run --rm -it \
            -p ' + client_port(cli) + ':8069 \
            -v ' + HOME + cli + '/config:/etc/odoo \
            -v ' + HOME + cli + '/data_dir:/var/lib/odoo \
            -v ' + HOME + '/sources:/mnt/extra-addons \
            --link db-odoo:db \
            --name ' + cli + '-update ' + \
            image_from_dict(ODOO) + ' -- '
                                    ' --stop-after-init -d ' + db + ' -u ' + ', '.join(
                mods)
            , shell=True)

    elif ODOOVER == '7.0':
        subprocess.call(
            'sudo docker run --rm -it \
            -p ' + client_port(cli) + ':8069 \
            -v ' + HOME + cli + '/config:/etc/odoo \
            -v ' + HOME + cli + '/data_dir:/var/lib/odoo \
            -v ' + HOME + 'sources:/mnt/extra-addons \
            --link db-odoo:db \
            --name ' + cli + '-update ' + \
            image_from_dict(ODOO) + ' -- '
                                    ' --db_user=odoo --db_password=odoo --db_host=db ' +
            ' --stop-after-init -d ' + db + ' -u ' + ', '.join(mods)
            , shell=True)

    return True


def _(t):
    print ">", t
    return t

def install_client():
    msgrun('Install clients')

    # Calculate addon_path
    path = '/mnt/extra-addons/'
    addon_path = path + REPOS[0]['dir']
    for rep in REPOS[1:]:
        addon_path += ',' + path + rep['dir']
    #    addon_path += ',/opt/openupgrade/addons'
    for cli in args.client:
        msgrun('Installing Odoo image for client ' + cli)

        # Creating directory's for client
        subprocess.call('mkdir -p ' + HOME + cli + '/config', shell=True)
        subprocess.call('mkdir -p ' + HOME + cli + '/data_dir', shell=True)
        subprocess.call('chmod 777 -R ' + HOME + cli, shell=True)

        # creating config file for client
        if subprocess.call(
            'sudo docker run --rm \
            -v ' + HOME + cli + '/config:/etc/odoo \
            -v ' + HOME + 'sources:/mnt/extra-addons \
            -v ' + HOME + cli + '/data_dir:/var/lib/odoo \
            --name ' + cli + ' ' + \
             image_from_dict(ODOO) + ' -- --stop-after-init -s \
            --addons-path=' + addon_path + \
            ' --db-filter=' + cli + '_.*'
                , shell=True):
            msgerr('failiing to write config file. Aborting')
            exit(1)

    msgdone('Installing done')
    return True


def run_aeroo_image():
    if subprocess.call(
                    'sudo docker run -d \
                    -p 127.0.0.1:8989:8989 \
                    --name="aeroo_docs" \
                    --restart=always ' + \
                    image_from_dict(AEROO), shell=True):
        msgerr('Fail running environment.')
        return False
    return True


def run_environment():
    msgrun('Running environment images')
    if ODOOVER == '8.0.1' or ODOOVER == '8.0':
        run_aeroo_image()

    if subprocess.call(
                    'sudo docker run -d \
                    -e POSTGRES_USER=odoo \
                    -e POSTGRES_PASSWORD=odoo \
                    -v ' + PSQL + ':/var/lib/postgresql/data \
                    --restart=always \
                    --name db-odoo ' + \
                    image_from_dict(POSTGRES), shell=True):
        msgerr('Fail running environment')
    else:
        msgdone("Environment up and running")

    return True


def run_developer():
    msgrun('Running environment in developer mode.')

    if ODOOVER == '8.0.1' or ODOOVER == '8.0':
        run_aeroo_image()

    if subprocess.call(
                    'sudo docker run -d \
                    -p 5432:5432 \
                    -e POSTGRES_USER=odoo \
                    -e POSTGRES_PASSWORD=odoo \
                    -v ' + PSQL + ':/var/lib/postgresql/data \
                    --restart=always \
                    --name db-odoo ' + \
                    image_from_dict(POSTGRES), shell=True):
        msgerr('Fail running environment.')
    else:
        msgdone('Environment up and running.')

    return True


def run_client():
    for cli in args.client:
        msgrun('Running image for client ' + cli)
        if ODOOVER == '8.0' or ODOOVER == '8.0.1':
            ok = subprocess.call(
                'sudo docker run -d \
                --link aeroo_docs:aeroo \
                -p ' + client_port(cli) + ':8069 \
                -v ' + HOME + cli + '/config:/etc/odoo \
                -v ' + HOME + cli + '/data_dir:/var/lib/odoo \
                -v ' + HOME + '/sources:/mnt/extra-addons \
                --link db-odoo:db \
                --restart=always \
                --name ' + cli + ' ' + \
                image_from_dict(ODOO) + ' -- --db-filter=' + cli + '_.*', shell=True)
        else:
            ok = subprocess.call(
                'sudo docker run -d \
                -p ' + client_port(cli) + ':8069 \
                -v ' + HOME + cli + '/config:/etc/odoo \
                -v ' + HOME + cli + '/data_dir:/var/lib/odoo \
                -v ' + HOME + 'sources:/mnt/extra-addons \
                --link db-odoo:db \
                --restart=always \
                --name ' + cli + ' ' + \
                image_from_dict(ODOO) + ' -- --db-filter=' + cli + '_.*' +
                ' --db_user=odoo --db_password=odoo --db_host=db'
                , shell=True)
        if not ok:
            msgdone('Client ' + cli + ' up and running')
        else:
            msgerr("Can't run client " + cli + ", by the way... did you run -R ?")

    return True


def stop_client():
    msgrun('stopping clients ' + ', '.join(args.client))
    for cli in args.client:
        msginf('stop image for client ' + cli)
        subprocess.call('sudo docker stop ' + cli, shell=True)
        subprocess.call('sudo docker rm ' + cli, shell=True)

    msgdone('all clients stopped')

    return True


def stop_environment():
    msgrun('Stopping environment')
    if (ODOOVER == '8.0') or (ODOOVER == '8.0.1'):
        images = ['db-odoo', 'aeroo_docs']
    else:
        images = ['db-odoo']

    for name in images:
        msgrun('Stopping image ' + name)
        r1 = subprocess.call('sudo docker stop ' + name, shell=True)
        r2 = subprocess.call('sudo docker rm ' + name, shell=True)
    if r1 + r2:
        msgerr('Fail removing ' + name)
        return False
    msgdone('Environment stopped')

    return True


def pull_all_images():
    msgrun('Pulling all images for ' + ODOOVER)

    for image in IMAGES:
        msginf('Pulling ' + image_from_dict(image))
        if subprocess.call('sudo docker pull ' + image_from_dict(image), shell=True):
            msgerr('Fail pulling image ' + image_from_dict(image) + ' - Aborting.')

    msgdone('All images ok ' + ODOOVER)

    msgrun('Pulling all repos for ' + ODOOVER)
    for repo in REPOS:
        msginf('pulling repo ' + repo_from_dict(repo))
        if subprocess.call('cd ' + HOME + 'sources/' + repo[
            'dir'] + '&&' + ' sudo git pull', shell=True):
            msgerr('Fail pulling repos, uninstall and try again. By the way... did you run -I ?')

    msgdone('All repos ok ' + ODOOVER)

    return True


def list_data():
    msgrun('Data for this environment - Odoo ' + ODOOVER)
    msgrun('Images ' + 19 * '-')
    for img in IMAGES:
        msgdone(image_from_dict(img))

    msgrun('Repos ' + 20 * '-')
    for rep in REPOS:
        msgdone(repo_from_dict(rep) + '  b ' + rep['branch'])

    msgrun('Clients ' + 18 * '-')
    for client in CLIENTS:
        msgrun(client['port'] + ' ' + client['client'])

    return True


def no_ip_install():
    msgrun('Installing no-ip client')
    subprocess.call('sudo apt-get install make', shell=True)
    subprocess.call('sudo apt-get -y install gcc', shell=True)
    subprocess.call(
        'wget -O /usr/local/src/noip.tar.gz http://www.noip.com/client/linux/noip-duc-linux.tar.gz',
        shell=True)
    subprocess.call('sudo tar -xf noip.tar.gz -C /usr/local/src/', shell=True)
    subprocess.call(
        'sudo wget -P /usr/local/src/ http://www.noip.com/client/linux/noip-duc-linux.tar.gz',
        shell=True)
    subprocess.call('sudo tar xf /usr/local/src/noip-duc-linux.tar.gz -C /usr/local/src/',
                    shell=True)
    subprocess.call('cd /usr/local/src/noip-2.1.9-1 && sudo make install', shell=True)
    msginf("Please answer some questions")
    subprocess.call('sudo rm /usr/local/src/noip-duc-linux.tar.gz', shell=True)
    subprocess.call('sudo cp /usr/local/src/noip-2.1.9-1/debian.noip2.sh  /etc/init.d/',
                    shell=True)
    subprocess.call('sudo chmod +x /etc/init.d/debian.noip2.sh', shell=True)
    subprocess.call('sudo update-rc.d debian.noip2.sh defaults', shell=True)
    subprocess.call('sudo /etc/init.d/debian.noip2.sh restart', shell=True)
    msgdone('no-ip service running')

    # To config defaults noip2 with capital C
    # sudo /usr/local/bin/noip2 -C



    return True


def docker_install():
    msgrun('Installing docker')
    subprocess.call('wget -qO- https://get.docker.com/ | sh', shell=True)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Odoo environment setup v 1.0')
    parser.add_argument('version',
                        choices=['7.0', '7.0.1', '8.0', '8.0.1', '8.0.2', 'ou-8.0'])
    parser.add_argument('-U', '--uninstall-env', action='store_true',
                        help='Uninstall and erase all files from environment including \
                              databases. WARNING all database files will be erased.')
    parser.add_argument('-I', '--install-env', action='store_true',
                        help="Install all files and odoo repos needed")
    parser.add_argument('-i', '--install-cli', action='store_true',
                        help="Install all clients, requires -c options")
    parser.add_argument('-R', '--run-env', action='store_true',
                        help="Run database and aeroo images.")
    parser.add_argument('-D', '--run-dev', action='store_true',
                        help="Run database and aeroo images for developer mode (local db access).")
    parser.add_argument('-r', '--run-cli', action='store_true',
                        help="Run client odoo images, requieres -c options.")
    parser.add_argument('-S', '--stop-env', action='store_true',
                        help="Stop database and aeroo images.")
    parser.add_argument('-s', '--stop-cli', action='store_true',
                        help="Stop client images, requieres -c options.")
    parser.add_argument('-p', '--pull-all', action='store_true', help="Pull all images")
    parser.add_argument('-l', '--list', action='store_true',
                        help="List all data in this server. Clients and images.")
    parser.add_argument('-c', '--client', dest='client', action='append',
                        help="Client name. You can specify more than one as \
                        -c alexor -c danone -c tenaris ... etc.")
    parser.add_argument('-n', '--no-ip-install', action='store_true',
                        help="Install no-ip on this server")
    parser.add_argument('-k', '--docker-install', action='store_true',
                        help="Install docker on this server")

    parser.add_argument('-u', '--update-database', action='store_true',
                        help="Update database requires -d -c and -m options")
    parser.add_argument('-d', '--database', dest='database', action='store', nargs=1,
                        help="Database to update")
    parser.add_argument('-m', '--module', dest='module', action='append', nargs=1,
                        help="Module to update or all, you can specify multiple -m options")

    args = parser.parse_args()

    ########################################
    # Constant Definitins
    ODOOVER = args.version

    HOME = '~/odoo-' + ODOOVER + '/'
    PSQL = '~/postgresql-' + ODOOVER + '/'

    # version estable
    if ODOOVER == '8.0':
        # images
        ODOO = {'repo': 'jobiols', 'dir': 'odoo-adhoc', 'ver': '8.0'}
        AEROO = {'repo': 'jobiols', 'dir': 'aeroo-docs', 'ver': 'latest'}
        POSTGRES = {'repo': 'postgres', 'dir': '', 'ver': '9.4'}
        BACKUP = {'repo': 'jobiols', 'dir': 'backup', 'ver': ''}
        IMAGES = [ODOO, AEROO, POSTGRES, BACKUP]

        # clients
        CLIENTS = [{'client': 'str', 'port': '8070'},
                   {'client': 'makeover', 'port': '8069'}]

        # repos
        REPOS = [{'repo': 'jobiols', 'dir': 'odoo-addons', 'branch': '8.0'},
                 {'repo': 'jobiols', 'dir': 'odoo-argentina', 'branch': '8.0'},
                 {'repo': 'jobiols', 'dir': 'aeroo_reports', 'branch': '8.0'},
                 {'repo': 'jobiols', 'dir': 'server-tools', 'branch': '8.0'},
                 {'repo': 'jobiols', 'dir': 'web', 'branch': '8.0'},
                 {'repo': 'jobiols', 'dir': 'management-system', 'branch': '8.0'},
                 {'repo': 'jobiols', 'dir': 'knowledge', 'branch': '8.0'},
        ]

    elif ODOOVER == '7.0':
        # images
        ODOO = {'repo': 'jobiols',
                'dir': 'odoo-adhoc',
                'ver': '7.0'}
        POSTGRES = {'repo': 'postgres',
                    'dir': '',
                    'ver': '9.4'}
        BACKUP = {'repo': 'jobiols',
                  'dir': 'backup',
                  'ver': ''}
        IMAGES = [ODOO, POSTGRES, BACKUP]

        # clients
        CLIENTS = [{'client': 'makeover', 'port': '8069'},
                   {'client': 'pirulo', 'port': '8070'}]

        # repos
        REPOS = [{'repo': 'jobiols', 'dir': 'odoo-addons', 'branch': '7.0'},
                 {'repo': 'jobiols', 'dir': 'localizacion', 'branch': '7.0'},
                 {'repo': 'jobiols', 'dir': 'server-tools', 'branch': '7.0'},
                 {'repo': 'jobiols', 'dir': 'str', 'branch': '7.0'}
        ]

    # Version de experimentación
    elif ODOOVER == '7.0.1':
        # images
        ODOO = {'repo': 'jobiols',
                'dir': 'odoo-adhoc',
                'ver': '7.0.1'}
        POSTGRES = {'repo': 'postgres',
                    'dir': '',
                    'ver': '9.4'}
        BACKUP = {'repo': 'jobiols',
                  'dir': 'backup',
                  'ver': ''}
        IMAGES = [ODOO, POSTGRES, BACKUP]

        # clients
        CLIENTS = [{'client': 'makeover', 'port': '8069'},
                   {'client': 'pirulo', 'port': '8070'}]

        # repos
        REPOS = [{'repo': 'jobiols', 'dir': 'odoo-addons', 'branch': '7.0'},
                 {'repo': 'jobiols', 'dir': 'localizacion', 'branch': '7.0'},
                 {'repo': 'jobiols', 'dir': 'server-tools', 'branch': '7.0'},
                 {'repo': 'jobiols', 'dir': 'str', 'branch': '7.0'},
                 {'repo': 'jobiols', 'dir': 'odoo-mailchimp-tools', 'branch': 'master'}
        ]

    # utlima version estable de la Open Upgrade
    elif ODOOVER == 'ou-8.0':
        # images
        ODOO = {'repo': 'jobiols',
                'dir': 'docker-openupgrade',
                'ver': '8.0'}
        POSTGRES = {'repo': 'postgres',
                    'dir': '',
                    'ver': '9.4'}
        IMAGES = [ODOO, POSTGRES]

        # clients
        CLIENTS = [{'client': 'makeover', 'port': '8069'},
                   {'client': 'jeo', 'port': '8070'}]

        # repos
        REPOS = [{'repo': 'ingadhoc', 'dir': 'odoo-addons', 'branch': '8.0'},
                 {'repo': 'ingadhoc', 'dir': 'odoo-argentina', 'branch': '8.0'},
                 {'repo': 'oca', 'dir': 'server-tools', 'branch': '8.0'},
                 {'repo': 'jobiols', 'dir': 'str', 'branch': '8.0'}
        ]

    # ultima version de adhoc
    elif ODOOVER == '8.0.1':
        # images
        ODOO = {'repo': 'adhoc',
                'dir': 'odoo-adhoc',
                'ver': '8.0'}
        AEROO = {'repo': 'jobiols',
                 'dir': 'aeroo-docs',
                 'ver': 'latest'}
        POSTGRES = {'repo': 'postgres',
                    'dir': '',
                    'ver': '9.4'}
        BACKUP = {'repo': 'jobiols',
                  'dir': 'backup',
                  'ver': ''}
        IMAGES = [ODOO, AEROO, POSTGRES, BACKUP]

        # clients
        CLIENTS = [{'client': 'jeo', 'port': '8070'},
                   {'client': 'makeover', 'port': '8050'}]

        # repos
        REPOS = [{'repo': 'ingadhoc', 'dir': 'odoo-addons', 'branch': '8.0.x'},
                 {'repo': 'ingadhoc', 'dir': 'odoo-argentina', 'branch': '8.0.x'},
                 {'repo': 'aeroo', 'dir': 'aeroo_reports', 'branch': '8.0'},
                 {'repo': 'oca', 'dir': 'server-tools', 'branch': '8.0'},
                 {'repo': 'oca', 'dir': 'web', 'branch': '8.0'},
                 {'repo': 'oca', 'dir': 'management-system', 'branch': '8.0'},
                 {'repo': 'oca', 'dir': 'knowledge', 'branch': '8.0'},
                 {'repo': 'oca', 'dir': 'margin-analysis', 'branch': '8.0'},
                 {'repo': 'jobiols', 'dir': 'str', 'branch': '7.0'},
                 {'repo': 'oca', 'dir': 'account-financial-reporting', 'branch': '8.0'}
        ]

    # version experimental
    elif ODOOVER == '8.0.2':
        # images
        ODOO = {'repo': 'adhoc',
                'dir': 'odoo-adhoc',
                'ver': '8.0'}
        AEROO = {'repo': 'jobiols',
                 'dir': 'aeroo-docs',
                 'ver': 'latest'}
        POSTGRES = {'repo': 'postgres',
                    'dir': '',
                    'ver': '9.4'}
        BACKUP = {'repo': 'jobiols',
                  'dir': 'backup',
                  'ver': ''}
        IMAGES = [ODOO, AEROO, POSTGRES, BACKUP]

        # clients
        CLIENTS = [{'client': 'str', 'port': '8069'},
                   {'client': 'makeover', 'port': '8070'}]

        # repos jobiols
        REPOS = [{'repo': 'ingadhoc', 'dir': 'odoo-addons', 'branch': '8.0.x'},
                 {'repo': 'ingadhoc', 'dir': 'odoo-argentina', 'branch': '8.0.x'},
                 {'repo': 'aeroo', 'dir': 'aeroo_reports', 'branch': '8.0'},
                 {'repo': 'oca', 'dir': 'server-tools', 'branch': '8.0'},
                 {'repo': 'oca', 'dir': 'web', 'branch': '8.0'},
                 {'repo': 'oca', 'dir': 'management-system', 'branch': '8.0'},
                 {'repo': 'oca', 'dir': 'knowledge', 'branch': '8.0'},
                 {'repo': 'oca', 'dir': 'margin-analysis', 'branch': '8.0'}
        ]

    ########################################
    # Check for valid client
    if args.client != None:
        for cli in args.client:
            client_port(cli)

    if args.uninstall_env:
        uninstall_environment()
    if args.install_env:
        install_environment()
    if args.install_cli:
        install_client()
    if args.stop_env:
        stop_environment()
    if args.run_env:
        run_environment()
    if args.run_dev:
        run_developer()
    if args.stop_cli:
        stop_client()
    if args.run_cli:
        run_client()
    if args.pull_all:
        pull_all_images()
    if args.list:
        list_data()
    if args.no_ip_install:
        no_ip_install()
    if args.docker_install:
        docker_install()
    if args.update_database:
        update_database()
