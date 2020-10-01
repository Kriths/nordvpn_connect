#!/usr/bin/env python3
import os
import re
import sys
import subprocess
import signal
import tempfile
import requests
import getpass

PID_FILE = '/run/nvpn.pid'
OVPN_CONFIGS = '/etc/openvpn'
CREDENTIALS_FILE = '/etc/openvpn/login.conf'


def show_help(cmd=None):
    print("Usage: vpn [up|down|update|status] <server name> [options]")
    print(" vpn up - Connect to best available vpn server")
    print(" vpn up de - Connect to best available vpn server in a country")
    print(" vpn up de123 - Connect to specific vpn server")
    print(" vpn up -t / -u  - Switch between tcp and udp (default: -u)")
    print(" vpn down - Kill vpn connection")
    print(" vpn init - Enter credentials and save to file, then update")
    print(" vpn status - Check if process is currently running")
    print(" vpn update - Download and refresh config file from nord cdn")


def find_best_server(proto, country=None):
    request_url = 'https://nordvpn.com/wp-admin/admin-ajax.php?action=servers_recommendations'
    tech_name = 'OpenVPN %s' % proto.upper()
    if country is not None:
        country_id = -1
        techs = requests.get('https://nordvpn.com/wp-admin/admin-ajax.php?action=servers_technologies').json()
        for tech in techs:
            if tech['name'] == tech_name:
                for cnt in tech['countries']:
                    if cnt['code'].lower() == country.lower():
                        country_id = cnt['id']
                        break
                break
        if country_id == -1:
            print("Could not find country %s" % country)
            sys.exit(1)
        request_url += '&filters={"country_id":%d}' % country_id
    servers = requests.get(request_url).json()
    return servers[0]['hostname'].split('.')[0]


def get_running_pid():
    try:
        with open(PID_FILE, 'r') as pidFile:
            line = pidFile.readline()
    except IOError:
        return -1

    try:
        pid = int(line)
    except ValueError:
        os.remove(PID_FILE)
        return -1

    p_name, _ = subprocess.Popen(['ps', '-p%d' % pid, '-ocomm='], stdout=subprocess.PIPE).communicate()
    if b'openvpn' in p_name:
        return pid

    os.remove(PID_FILE)
    return -1


# MAIN HANDLERS
def handle_up(args):
    if get_running_pid() != -1:
        print("Connection already running.")
        sys.exit(1)

    req_server = None
    proto = 'UDP'
    for arg in args:
        if arg == '--tcp' or arg == '-t':
            proto = 'TCP'
        elif arg == '--udp' or arg == '-u':
            proto = 'UDP'
        elif not arg[0] == '-':
            req_server = arg
        else:
            print('Unknown command: %s' % arg)
            show_help('up')
            sys.exit(1)

    if not req_server:
        server = find_best_server(proto)
    elif req_server == 'help':
        show_help('up')
        sys.exit(0)
    elif re.match(r'[a-z]+\d+', req_server):
        server = req_server
    elif re.match(r'[a-z]+', req_server):
        server = find_best_server(proto, req_server)
    else:
        show_help('up')
        sys.exit(1)

    print("Requesting connection to %s.%s" % (proto, server))
    ovpn_file = '%s/ovpn_%s/%s.nordvpn.com.%s.ovpn' % (OVPN_CONFIGS, proto.lower(), server, proto.lower())
    if not os.path.isfile(ovpn_file):
        print("Could not find server config %s" % server)
        sys.exit(1)
    os.system("sed -i 's,^auth-user-pass$,auth-user-pass %s,g' %s" % (CREDENTIALS_FILE, ovpn_file))
    proc = subprocess.Popen(['openvpn', ovpn_file], shell=False, stdout=subprocess.PIPE)
    with open(PID_FILE, 'w') as pidFile:
        pidFile.write(str(proc.pid))


def handle_down(args):
    pid = get_running_pid()
    if pid == -1:
        print("No process currently running.")
        sys.exit(1)
    os.kill(pid, signal.SIGTERM)
    os.remove(PID_FILE)


def handle_update():
    tmpdir = tempfile.mkdtemp()
    zipfile = tmpdir + '/ovpn.zip'
    subprocess.Popen(['wget', '-O' + zipfile, 'https://downloads.nordcdn.com/configs/archives/servers/ovpn.zip'],
                     stdout=subprocess.PIPE).wait()
    subprocess.Popen(['unzip', '-o', '-d' + OVPN_CONFIGS, zipfile], stdout=subprocess.DEVNULL).wait()


def handle_status():
    pid = get_running_pid()
    if pid == -1:
        print("No process currently running.")
    else:
        print("PID: %d" % pid)

    ip_info = requests.get('https://ifconfig.co/json').json()
    print("Current IP:   " + ip_info['ip'])
    print("Country:      " + ip_info['country'])
    if 'city' in ip_info:
        print("Approx. City: " + ip_info['city'])


def handle_init():
    user = input("Username: ")
    passw = getpass.getpass()
    with open(CREDENTIALS_FILE, 'w') as credFile:
        credFile.write('%s\n%s' % (user, passw))
    os.chmod(CREDENTIALS_FILE, 0o400)
    handle_update()


# ENTRY POINT
def main():
    if os.getuid() != 0 or os.geteuid() != 0:
        print("Most be run as root")
        sys.exit(255)

    # Check arguments
    if len(sys.argv) <= 1:
        show_help()
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == 'up':
        handle_up(args)
    elif cmd == 'down':
        handle_down(args)
    elif cmd == 'update':
        handle_update()
    elif cmd == 'status':
        handle_status()
    elif cmd == 'init':
        handle_init()
    elif cmd == 'help':
        show_help()
    else:
        show_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
