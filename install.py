#! /usr/bin/python
import os
import urllib2

from subprocess import call

SALT_HIGHSTATE_COMMAND = 'salt-call state.highstate'
SALT_INSTALLER_COMMAND = "sudo sh /tmp/bootstrap_salt.sh git develop"
SALT_DOWNLOAD_COMMAND = "curl -o /tmp/bootstrap_salt.sh -L https://bootstrap.saltstack.com"
SALT_RESTART_COMMAND = "service salt-minion restart"
python_git_pkg = 'python-git'
minion_file = '/etc/salt/minion'
MINION_FILE_CONTENT = """
file_client: local

fileserver_backend:
  - git

gitfs_base: master

gitfs_remotes:
  - https://github.com/Junar/datal-formula.git

pillar_roots:
  base:
    - /srv/salt/pillar

"""
MINION_PILLAR_DIR = '/srv/salt/pillar'
MINION_PILLAR_TOP_FILE_CONTENT = """
base:
  '*':
    - general
    {% if salt['file.file_exists']('/srv/salt/pillar/local.sls') %}
    - local
    {% endif %}
"""


def install_salt():
    print("Instalando SaltStack / Installing SaltStack")
    call(SALT_DOWNLOAD_COMMAND, shell=True)
    call(SALT_INSTALLER_COMMAND, shell=True)


def restart_salt():
    print("Reiniciando SaltStack / Restarting SaltStack")
    return call(SALT_RESTART_COMMAND, shell=True)


def install_deps():
    print("Instalando dependencias / Installing deps")
    return call('apt-get install {} -y'.format(python_git_pkg), shell=True)


def salt_configuration():
    print("Configurando SaltStack / Setting up SaltStack")

    # Minion file content
    f = open(minion_file, 'w')
    f.writelines(MINION_FILE_CONTENT)
    f.close()

    # Pillar directory
    if not os.path.exists(MINION_PILLAR_DIR):
        os.makedirs(MINION_PILLAR_DIR)

    # Get Pillars
    fname = '{}/general.sls'.format(MINION_PILLAR_DIR)
    url = 'https://raw.githubusercontent.com/Junar/datal-formula/master/pillar.example'
    response = urllib2.urlopen(url)
    content = response.read()
    open(fname, 'w').write(content)

    # Minion pillar top file content
    f = open(MINION_PILLAR_DIR + '/top.sls', 'w')
    f.writelines(MINION_PILLAR_TOP_FILE_CONTENT)
    f.close()


def run_highstate():
    print("Instalando Datal / Installing Datal")
    return call(SALT_HIGHSTATE_COMMAND, shell=True)

install_salt()
install_deps()
salt_configuration()
restart_salt()
run_highstate()
