from fabric.api import run, sudo, puts, abort, env, open_shell, local, put
from fabric.colors import green, red, yellow
import os

if os.environ.get('TARDIS_HOME') is None:
    puts(red("You must enter the Tardis first"))
    puts("")
    puts(red("pr0tip: "))
    puts("")
    puts(green("$ git clone git@github.com:CyanogenMod/tardis.git # Private Repository"))
    puts(green("$ source tardis/bin/activate"))
    abort("Unable to read TARDIS_HOME")

env.use_ssh_config = True
env.ssh_config_path = os.path.join(os.environ['TARDIS_HOME'], "config", "ssh_config")
env.key_filename = os.path.join(os.environ['TARDIS_HOME'], "keys", "fab_rsa")

def all():
    env.user = "fabric"
    env.hosts = ['get.galliumos.org:22221']

def uptime():
    run('uptime')

def shell():
    open_shell()

def deploy():
    local("rm -rf dist")
    local("python setup.py bdist_egg")
    sudo("rm -rf /tmp/GetGOS.egg")
    put("dist/GetGOS-*-py*.egg", "/tmp/GetGOS.egg")
    sudo("easy_install /tmp/GetGOS.egg")
    sudo("supervisorctl restart cmbalance")
