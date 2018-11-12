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

def showHelp(cmd=None):
  print("Usage: vpn [up|down|update|status] <server name>")
  print(" vpn up - Connect to best available vpn server")
  print(" vpn up de - Connect to best available vpn server in a country")
  print(" vpn up de123 - Connect to specific vpn server")
  print(" vpn down - Kill vpn connection")
  print(" vpn init - Enter credentials and save to file, then update")
  print(" vpn status - Check if process is currently running")
  print(" vpn update - Download and refresh config file from nord cdn")

def findBestServer(country=None):
  requestUrl = 'https://nordvpn.com/wp-admin/admin-ajax.php?action=servers_recommendations'
  if country is not None:
    countryId = -1
    techs = requests.get('https://nordvpn.com/wp-admin/admin-ajax.php?action=servers_technologies').json()
    for tech in techs:
      if tech['name'] == 'OpenVPN TCP':
        for cnt in tech['countries']:
          if cnt['code'].lower() == country.lower():
            countryId = cnt['id']
            break
        break
    if countryId == -1:
      print("Cound not find country %s" % country)
      exit(1)
    requestUrl += '&filters={"country_id":%d}' % countryId
  servers = requests.get(requestUrl).json()
  return servers[0]['subdomain']

def getRunningPid():
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

  pName, _ = subprocess.Popen(['ps', '-p%d'%pid, '-ocomm='], stdout=subprocess.PIPE).communicate()
  if b'openvpn' in pName:
    return pid
  
  os.remove(PID_FILE)
  return -1


## MAIN HANDLERS
def handleUp(args):
  if getRunningPid() != -1:
    print("Connection already running.")
    exit(1)
  if len(args) == 0:
    server = findBestServer()
  elif args[0] == 'help':
    showHelp('up')
    exit(0)
  elif re.match(r'[a-z]+\d+', args[0]):
    server = args[0]
  elif re.match(r'[a-z]+', args[0]):
    server = findBestServer(args[0])
  else:
    showHelp('up')
    exit(1)

  print("Requresting connection to %s" % server)
  ovpnFile = '%s/ovpn_tcp/%s.nordvpn.com.tcp.ovpn' % (OVPN_CONFIGS, server)
  if not os.path.isfile(ovpnFile):
    print("Could not find server config %s" % server)
    exit(1)
  os.system("sed -i 's,^auth-user-pass$,auth-user-pass %s,g' %s" % (CREDENTIALS_FILE, ovpnFile))
  proc = subprocess.Popen(['openvpn', ovpnFile], shell=False, stdout=subprocess.PIPE)
  with open(PID_FILE, 'w') as pidFile:
    pidFile.write(str(proc.pid))

def handleDown(args):
  pid = getRunningPid()
  if pid == -1:
    print("No process currently running.")
    exit(1)
  os.kill(pid, signal.SIGTERM)
  os.remove(PID_FILE)

def handleUpdate():
  tmpdir = tempfile.mkdtemp()
  zipfile = tmpdir+'/ovpn.zip'
  subprocess.Popen(['wget', '-O'+zipfile, 'https://downloads.nordcdn.com/configs/archives/servers/ovpn.zip'], stdout=subprocess.PIPE).wait()
  subprocess.Popen(['unzip', '-o', '-d'+OVPN_CONFIGS, zipfile], stdout=subprocess.DEVNULL).wait()

def handleStatus():
  pid = getRunningPid()
  if pid == -1:
    print("No process currently running.")
  else:
    print("PID: %d" % pid)
  
  ipInfo = requests.get('http://ifconfig.co/json').json()
  print("Current IP:   " + ipInfo['ip'])
  print("Country:      " + ipInfo['country'])
  print("Approx. City: " + ipInfo['city'])

def handleInit():
  user = input("Username: ")
  passw = getpass.getpass()
  with open(CREDENTIALS_FILE, 'w') as credFile:
    credFile.write('%s\n%s' % (user, passw))
  os.chmod(CREDENTIALS_FILE, 0o400)
  handleUpdate()


# ENTRY POINT
if __name__ == '__main__':
  if os.getuid() != 0 or os.geteuid() != 0:
    print("Most be run as root")
    exit(255)

  # Check arguments
  if len(sys.argv) <= 1:
    showHelp()
    exit(1)

  cmd = sys.argv[1]
  args = sys.argv[2:]
  if cmd == 'up':
    handleUp(args)
  elif cmd == 'down':
    handleDown(args)
  elif cmd == 'update':
    handleUpdate()
  elif cmd == 'status':
    handleStatus()
  elif cmd == 'init':
    handleInit()
  elif cmd == 'help':
    showHelp()
  else:
    showHelp()
    exit(1)
