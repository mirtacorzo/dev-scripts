# dev-scripts
###Docker based  infrastructure management for Odoo v8 v9
Sacar los datos del script
DISCUSION
Pongo los datos del cliente (repos & images) en un repo customer, donde cada cliente es un 
branch.
Cuando hago -c pepe hay que hacer un checkout de pepe en el repo customer y leer los
datos del cliente de ahi. en cualquier comando que tenga un -c

-r -c pepe el tipo se va a bajar el branch. a menos que vea que hay en .git/HEAD y no
lo baje si no hace falta. De todas formas cuando cambio de branch hay que bajarlo por las 
dudas haya cambiado.
En realidad haciendo un pull bajan todos los branches...

Pasaria lo mismo con odooenv, hay que bajarlo por si cambió...
podría agregarle un -p para que haga un pull forzado

Tal vez no sea buena idea poner un repo separado, podríamos poner el archivo
data.json en dev_scripts.

This proyect support [semver](http://semver.org/) 
    
    usage: odooenv.py [-h] [-i] [-U] [-R] [-S] [-r] [-s] [-p] [-l] [-v] [-q] [-n]
                      [-u] [-d DATABASE] [-w NEW_DATABASE] [-m MODULE] [-c CLIENT]
                      [--debug] [--cleanup] [--no-dbfilter] [-H] [--backup]
                      [--backup-list] [--restore] [-t TIMESTAMP]
                      [-Q repo test_file] [-j] [--cron-list] [--translate]
                      [--issues REPO] [-T client milestone]
    
    Odoo environment setup v3.6.0
    
    optional arguments:
      -h, --help            show this help message and exit
      -i, --install-cli     Install clients, requires -c option. You can define
                            multiple clients like this: -c client1 -c client2 -c
                            client3
      -U, --uninstall-cli   Uninstall client and erase all files from environment
                            including database. The command ask for permission to
                            erase database. BE WARNED if say yes, all database
                            files will be erased. BE WARNED AGAIN, database is
                            common to all clients!!!! Required -c option
      -R, --run-env         Run database and aeroo images.
      -S, --stop-env        Stop database and aeroo images.
      -r, --run-cli         Run client odoo images, requieres -c options. Optional
      -s, --stop-cli        Stop client images, requieres -c options.
      -p, --pull-all        Pull all images and repos.
      -l, --list            List all data in this server. Clients and images. with
                            --issues REPO list the github issues from repo
      -v, --verbose         Go verbose mode.
      -q, --quiet           Supress all standard output.
      -n, --no-ip-install   Install no-ip on this server.
      -u, --update-db       Update database requires -d -c and -m options.
      -d DATABASE           Database name.
      -w NEW_DATABASE       New database name.
      -m MODULE             Module to update or all, you can specify multiple -m
                            options.
      -c CLIENT             Client name. You can define multiple clients like
                            this: -c client1 -c client2 -c client3 and so one.
      --debug               This option has three efects: 1.- when doing an update
                            database, (option -u) it forces debug mode. 2.- When
                            running environment it opens port 5432 to access
                            postgres server databases. 3.- when doing a pull
                            (option -p) it clones the full repo i.e. does not
                            issue --depth 1 to git
      --cleanup             Delete all files clients, sources, and databases in
                            this server. It ask about each thing.
      --no-dbfilter         Eliminates dbfilter: The client can see any database.
                            Without this, the client can only see databases
                            starting with clientname_
      -H, --server-help     List server help requieres -c option
      --backup              Lauch backup requieres -d and -c options.
      --backup-list         List available backups with timestamps to restore.
      --restore             Lauch restore requieres -c, -d, -w and -t options.
      -t TIMESTAMP          Timestamp to restore database, see --backup-list for
                            available timestamps.
      -Q repo test_file, --quality-test repo test_file
                            Perform a test, arguments are Repo where test lives,
                            and yml/py test file to run (please include
                            extension). Need -d, -m and -c options Note: for the
                            test to run there must be an admin user with passw
                            admin
      -j, --cron-jobs       Cron Backup. it adds cron jobs for doing backup to a
                            client database. backups twice a day at 12 AM and 12
                            PM. Needs a -c option to tell which client to backup.
      --cron-list           List available cron jobs
      --translate           Generate a po file for a module to translate, need a
                            -r and -m option
      --issues REPO         list formatted and priorized issues from github, used
                            with -l this option supports github API v3 priority is
                            the number between brackets in issue title
      -T client milestone   Tag all repos used by a client with a tag composed for
                            client ntame and milestone from client sources
