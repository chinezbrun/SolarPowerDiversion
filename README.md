# SolarPowerDiversion

This software is used to maximize usage of available solar power in a Outback Power hybrid solar system.
Full project and necessary hardware configuration is described here: https://hackaday.io/project/162995-solar-power-diverter-outback-power.  
Modbus communication with MATE3/MATE3s was done base on initial idea of Bas: https://github.com/basrijn/Outback_Mate3 

## How does this software work?

The software is divided in two parts:

- PowerDiversion: Python based - the core part, that process input data from MATE3 and push the output on Rapberry PI GPIO
- PredictiveData: Python based - an add-on for further improve power gathering by sending command to MATE3, change some parameters based on seasonality, weather prediction

### PowerDiversion/PowerDiversion.py
Runs in a closed loop on Raspberry PI and gets MATE3 critical data trough a JSON file.
As a input the status.json file, produced by MonitorMate_ModBus\DataStreamRelay is used.
PowerDiversion and MonitorMate_ModBus were designed to be used together. ref: https://github.com/chinezbrun/MonitorMate_ModBus

Based on input data analysis, GPIO output are used to activate various AC loads via 5V relays.
Similar commands are sent through MQTT topics, if the options are active.
Pushover notification are send for important events.

PowerDiversion.cfg -- (mandatory) is the configuration file for this script and can be configured based on the needs.
PowerDiversion.sh  -- (information only) is an example of start-up script to run the code at reboot

### PredictiveData/ChangeMateStatusModBus.py
This script is using ModBus protocol to WRITE parameters to MATE3.Can be installed on Raspberry or on any other host computer.

These adjustments are based on provided arguments or simple input in dinamic.data.json.

ChangeMateStatusModBus.py can be started when needed or at least once pe day (recommended) for wheather prediction -- task should be created on Host computer.
Once is started, when no arguments is provided, script will read dinamic_data.json file and if founds any active flags (i.e OutbackBlock_flag	1) will write to Mate values present in that section. "notset" values are ignored. 
Direct arguments, when provided, have priority over the json file. So, if the script is started with a specific argument (i.e  ChangeMateStatusModBus.py MiniGrid) the value will ovewrite any value for that specific target parameter, read from dinamic_data.json.

ChangeMateStatusModBus.cfg -- (mandatory) is the configuration file for this script and can be configured based on the needs.
dinamic_data.json          -- (mandatory) is the input file for this script
valid_argument.txt         -- (information only) is the list of accepted arguments

### PredictiveData/weather/weather_api.py
This is the first add-on for PredictiveData and is meant to run API weather https://home.openweathermap.org/, save weather.json file with weather prediction, record data in MariaDB, update dinamic_data.json in line with weather prediction and flextime_data.json, in order to be used later by ChangeMateStatusModBus.py

### Installation and Execution
---PowerDiversion---
1. Download SolarPowerDiversion and extract it. 
2. Copy SolarPowerDivertion folder content in any Raspberry PI location (my case: /var/www/html/SolarPowerDiversion )
3. Edit the PowerDiversion/PowerDiversion.cfg to your liking.
4. Run PowerDiversion.py. i.e : /usr/bin/python3 /var/www/html/SolarPowerDiversion/PowerDiversion/PowerDiversion.py
   Recommended to have the script to be run also at start-up.  
---PredictiveData----
5. Use weather.sql to create database/tables in your MySQL database. (I suggest phpAdmin to import)
6. Set a task in host computer to run weather_api.py every 3h
7. Edit the PredictiveData/ChangeMateStatusModBus.cfg to your liking.
8. Set a task in host computer to run PredictiveData/ChangeMateStatusModBus.py every day (preferably @ 21:30)







