# SolarPowerDiversion

This software is used to maximize usage of available solar power in a Outback Power hybrid solar system.
Full project and necessary hardware configuration is described here: https://hackaday.io/project/162995-solar-power-diverter-outback-power.  
Modbus communication with MATE3/MATE3s was done base on initial idea of Bas: https://github.com/basrijn/Outback_Mate3 

## How does this software work?

The software is divided in two parts:

- PowerDiversion: Python based - the core part, that process input data from MATE3 and push the output on Rapberry PI GPIO
- PredictiveData: Python based - an add-on to further improve power gathering by sending command to MATE3, change some parameters based on seasonality, weather prediction

### PowerDiversion/PowerDiversion.py
Runs on Raspberry PI and gets MATE3 critical data trough a JSON file.
Based on input data analysis, GPIO output are used to activate various AC loads via 5V relays.
PowerDiversion.py script is running once every X minute -- task should be created on Raspberry.
The JSON file used as input, is produced by MonitorMate_ModBus: https://github.com/chinezbrun/MonitorMate_ModBus. 
PowerDiversion and MonitorMate_ModBus were designed to be used together.

PowerDiversion.cfg -- is the configuration file for this script and can be configured based on the needs.
PowerDiversion.sh (is not mandatory) -- is an example of start-up script to run the code at reboot

### PredictiveData/ChangeMateStatusModBus.py
This script is using ModBus protocol to read and WRITE parameters to MATE3.Can be installed on Raspberry or on any other host computer.
ChangeMateStatusModBus.py is running once pe day (recommended) -- task should be created on Host computer.
The main output of the script (current) is to adjust the schedule in MATE3 Flextime (Minigrid and Backup mode).
These adjustments are based on simple input data like month or whether forecast and can be extended in future development

ChangeMateStatusModBus.cfg -- is the configuration file for this script and can be configured based on the needs.

### PredictiveData/weather/weather_api.py
This is the first add-on for PredictiveData and is meant to run API weather https://home.openweathermap.org/, save a JSON file with weather prediction,
record record data in MariaDB in order to be used later on by ChangeMateStatusModBus.py

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


