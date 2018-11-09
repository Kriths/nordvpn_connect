# nordvpn_connect

Save some time importing .ovpn to the network manager and entering credentials whenever you want to connect to a NordVPN network. This script will automatically connect you to Nord's recommended connection.

## Requirements
- python3
- openvpn
- nordvpn account

## Setup
Put your nordvpn credentials into a file at `/etc/openvpn/login.conf` and give it the least permissions possible.
~~~
# vi /etc/openvpn/login.conf
# chmod 400 /etc/openvpn/login.conf
~~~

This file should contain only your credentials on one line each:
~~~
myusername
Pa55w0rd
~~~

For ease of use, add the script to your .bash_alias:
~~~
alias vpn='sudo /path/to/git/nordvpn_connect/connect.py'
~~~
In that case you should also mark the script as executable: `chmod +x connect.py`.


## Commands
### vpn up
`vpn up` will check Nord's API for the recommended server and create a connection to that one.

`vpn up <COUNTRY CODE>` allows you to connect to a specific country (e.g. `vpn up us` for USA).

`vpn up us123` will connect you to server us123.


### vpn down
`vpn down` kills the currently active connection spawned by this script.


### vpn status
`vpn status` shows the PID of the running openvpn process and your IP and location info.


### vpn update
Pull a list of servers from NordVPN's CDN and refresh overwrite outdated files on your system.

Just like in the [NordVPN Tutorial](https://nordvpn.com/tutorials/linux/openvpn/), this script will by default save your .ovpn-configs to `/etc/openvpn`. Check their tutorial if your connection with these files fails.