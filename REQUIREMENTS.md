### Requirements & Dependencies
- Raspbery PI
- Python 3.6->3.7 with required modules installed:
sudo python3 -m pip install --upgrade pip     # first upgrade your PIP 
sudo python3 -m pip install mysql-connector   # used for Maria DB access 2.2.9
sudo python3 -m pip install pymodbus          # used for Mate mosbus connections 2.4.0
sudo python3 -m pip install configparser      # used in all scripts 5.0.2
sudo python3 -m pip install datetime          # used in all scripts, not clear if is not in standard package 4.3
sudo python3 -m pip install paho-mqtt         # used for mqtt packets 1.5.0 
sudo python3 -m pip install python-pushover   # used for text notification 0.4
sudo python3 -m pip install RPi.GPIO          # in standard package
sudo python3 -m pip install statistics        # in standard package
- WEB server with phpMyAdmin up and running 
- MonitorMate_Modbus up and running is mandatory; PowerDiversion use only the status.json file 
instalation here: https://github.com/chinezbrun/MonitorMate_ModBus. 
- Pushover for phone notification; account details are needed for config file
