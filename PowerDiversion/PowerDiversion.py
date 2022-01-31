# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License at <http://www.gnu.org/licenses/>
# for more details.

import json                                    # module for JSON decoding
import shutil                                  # module for copy file
from pushover import Client
import RPi.GPIO as GPIO
import time
from datetime import datetime, timedelta
from array import *
import statistics
from configparser import ConfigParser
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import sys, os

script_ver = "1.3.1_20220130"
print("---Solar Diversion Power build:", script_ver)

#********************************** subroutines **********************************
#subroutine for pushnotification - pushover app need to be installed
def PushNotification (push):
    try:
        if push_notification == "true":
            client = Client(push_user_key, api_token=push_api_token)
            client.send_message(time.strftime("%H:%M ")+push, title="SolarPowerDiversion")
            return
        return
    except:
        print("PushNotification: failed")

#error log subroutine
def ErrorPrint (str) :
    try:
        with open(InOutDataPath +'raspberry_info.log','r') as file:
            save = file.read()
        with open(InOutDataPath +'raspberry_info.log','w') as file:
            file = open(InOutDataPath +'raspberry_info.log','a')
            file.write(time.strftime("%d/%m/%Y %H:%M:%S "))
            file.write(str + "\r\n")
            print(str)
        with open(InOutDataPath +'raspberry_info.log','a') as file:
            file.write(save)
        file.close()
        
        return
    except OSError:
       print("Errorhandling: double error in ErrorPrint")
        
# close all relays - not used yet
def CloseAll(): 
    GPIO.output(17, GPIO.HIGH)
    load_01 = "inactive"
    GPIO.output(18, GPIO.HIGH)
    load_02 = "inactive"
    return

def mqtt_client():
    return

#********************************** initialization **********************************
print("---starting initialiazation...")
pathname              = os.path.dirname(sys.argv[0])        
fullpathname          = os.path.abspath(pathname)+'/PowerDiversion.cfg' 
print('...config path =', fullpathname)
config                = ConfigParser()
config.read(fullpathname)

#read configuration file and load variables
loop_ref              = int(config.get('solarpower', 'loop_ref'))                # default = 10    --numbers of loos until averages are calculated
voltage_ref           = float(config.get('solarpower', 'voltage_ref'))           # default = 52    --used in decision for load 01 (compensated)
voltage_compensated   = config.get('solarpower','voltage_compensated')           # default = true --if true voltage_ref will be temperature compensated with 0 0.12v/grade
max_ac_out_pwr        = int(config.get('solarpower', 'max_ac_out_pwr'))          # default = 2500  --max power/ inverter used to protect inverters for extra loads
divert_pwr_ref        = int(config.get('solarpower', 'divert_pwr_ref'))          # default = 1000  --divertion power to activate load 01
divert_by_state       = config.get('solarpower', 'divert_by_state')              # default = false --if true charger state is used if false baterry_voltage ref is used to activete diversion relay
chargers_PV_ref       = int(config.get('solarpower', 'chargers_PV_ref'))         # default = 90    --used to activate load 01 when no divertion power info available (i.e forced)
soc_min_limit         = int(config.get('solarpower','soc_min_limit'))            # default = 70    --SOC min used for stop level 1 utilities - restauration level SOC_min +5
InOutDataPath         = config.get('solarpower', 'InOutDataPath')                # path            --location for input output data (should be there stastus.json, logs, temperature file)                                   
grid_connect          = config.get('solarpower', 'grid_connect')                 # label           --used during various decision --should be identic with value provided by your device json file (i.e AC Use)
grid_droped           = config.get('solarpower', 'grid_droped')                  # label           --used during various decision --should be identic with value provided by your device json file
floating              = config.get('solarpower', 'floating')                     # label           --used during various decision --should be identic with value provided by your device json file 
absorbtion            = config.get('solarpower', 'absorbtion')                   # label           --used during various decision --should be identic with value provided by your device json file 
equalize              = config.get('solarpower', 'equalize')                     # label           --used during various decision --should be identic with value provided by your device json file 
#inverters             = int(config.get('solarpower', 'inverters'))               # default = 2     --number of inverters in the system used in JSON decoding
#chargers              = int(config.get('solarpower', 'chargers'))                # default = 2     --number of chargers in the system used in JSON decoding
push_notification     = config.get('solarpower', 'push_notificaton')             # default = false -- if true push notification is send to android/iphone - pushbullet app should be installed and configured
push_api_token        = config.get('solarpower', 'push_api_token')               # api_token key is generated by Pushover app
push_user_key         = config.get('solarpower', 'push_user_key')                # user_key is generated by Pushover app
MQTT_active           = config.get('MQTT', 'MQTT_active')                        # default = false  -- if active will publish MQTT topics to varoius platforms i.e Home Assistant
MQTT_broker           = config.get('MQTT', 'MQTT_broker')                        # your MQTT broker address - i.e 192.168.0.xxx
MQTT_topic1           = config.get('MQTT', 'MQTT_topic1')                        # MQTT topics      -- used in all MQTT push
MQTT_topic2           = config.get('MQTT', 'MQTT_topic2')                        # MQTT topics      -- used in all MQTT push
MQTT_topic3           = config.get('MQTT', 'MQTT_topic3')                        # MQTT topics      -- used in all MQTT push
MQTT_topic4           = config.get('MQTT', 'MQTT_topic4')                        # MQTT topics      -- used in all MQTT push
MQTT_topic5           = config.get('MQTT', 'MQTT_topic5')                        # MQTT topics      -- used in all MQTT push
MQTT_topic6           = config.get('MQTT', 'MQTT_topic6')                        # MQTT topics      -- used in all MQTT push
MQTT_topic7           = config.get('MQTT', 'MQTT_topic7')                        # MQTT topics      -- used in all MQTT push
MQTT_topic8           = config.get('MQTT', 'MQTT_topic8')                        # MQTT topics      -- used in all MQTT push
# port configuration - used to count inverters, chargers
port                  = []
inverters             = 0
chargers              = 0 
for n in range (10):
    port.append(config.get('port_map', 'port'+ str(n) ))
    if config.get('port_map', 'port'+ str(n)) == "5":
        inverters = inverters + 1
    if config.get('port_map', 'port'+ str(n)) == "3":
        chargers  = chargers +1

# label used during various decision --should be identic with value provided by your device json file 
boiler_temp_active    = config.get('boiler', 'boiler_temp_active')               # default = false --true if boiler temperature sensor is installed and manitoring system is in place and save data to common folder
boiler_temp_ref       = int(config.get('boiler', 'boiler_temp_ref'))             # default= 70     --max boiler temperature to stop diversion
deltatime_ref         = int(config.get('boiler', 'deltatime_ref'))               # default= 900    --max time in seconds to stop diversion due to no temperature data 

if boiler_temp_active != "true":                                                 # IF no boiler monitoring in place set dummy ref temp, temp and deltatime for running purpose of the script
    boiler_temp_ref   = 70                                                     
    boiler_temp       = 0
    deltatime_ref     = 900  
    deltatime         = 0

#GPIO init
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT, initial=GPIO.HIGH)                                    # load 1 relay    -- used to start additional AC load (level 1) via wireless plug
GPIO.setup(18, GPIO.OUT, initial=GPIO.HIGH)                                    # load 2 relay    -- used to start additional AC load (level 2) via wireless plug
GPIO.setup(22, GPIO.OUT, initial=GPIO.HIGH)                                    # diverter switch -- used to command DC breaker for additional protection 
GPIO.setup(23, GPIO.OUT, initial=GPIO.HIGH)                                    # stopU/P relay   -- used to switch main utilities from Solar to Grid for battery protection
GPIO.setup(24, GPIO.OUT, initial=GPIO.HIGH)                                    # booked but not used in curent version 
GPIO.setup(25, GPIO.OUT, initial=GPIO.HIGH)                                    # booked but not used in curent version

#variables init
up_time               = time.time() # count the running time - never reset
uptime_push_time      = time.time() # count the mqtt pushing frecvency for uptime - reset during execution
start_time            = time.time() # count reading frecvency for status.json - reset during execution
loop_time             = time.time()
use_time              = time.time()
load_01               ="inactive"
load_02               ="inactive"
stop_UP               ="inactive"
divert                ="inactive"
gpio_states           = ("on", "off") # readable GPIO states;used in MQTT payload
read_file             = 0 #counter of read atempts
loop_no               = 0
error_count           = 0 # counter of special errors
stamp_ref             =""
ac_use_time           = 0 
ac_drop_time          = 0
no_ac_drop_time       = 0
no_ac_drop_lasttime   = 0
no_ac_use_time        = 0
no_ac_use_lasttime    = 0
no_ac_lasttime        = 0
ac_mode_old           =""
ac_input_voltage_ref  = 220 # used only for push notification in case of no AC

shunt_c_array         = []
battery_voltage_array = []
ac_out_pwr_array      = []
divert_pwr_array      = []
charger_60_PV_array   = []
charger_80_PV_array   = []

#summary of startup parameters
print("---startup parameters")
print("loop_ref:            ", loop_ref)
print("max_ac_out_pwr:      ", max_ac_out_pwr)
print("voltage_ref:         ", voltage_ref)
print("voltage_compensated: ",voltage_compensated)
print("divert_pwr_ref:      ", divert_pwr_ref)
print("chargers_PV_ref:     ", chargers_PV_ref)
print("divert_by_state:     ", divert_by_state)
print("soc_min_limit:       ", soc_min_limit)
print("# of inverters:      ", inverters)
print("# of chargers:       ", chargers)
print("boiler_temp_active:  ", boiler_temp_active)
print("boiler_temp_ref:     ", boiler_temp_ref)
print("deltatime_ref:       ", deltatime_ref)
print("InOutDataPath:       ", InOutDataPath)
print("MQTT active:         ", MQTT_active)

# last check if JSON location is available and exist
if (os.path.isdir(InOutDataPath)) == True:
    print("---initialization completed, starting the main loop")
else:
    print("---initialization failed, InOutDataPath not found")
    
ErrorPrint("START: program ver:" + script_ver)
PushNotification("START: program ver:" + script_ver)

#********************************** start main loop **********************************

while True:   
    try:
        # start with reading json data        
        if (time.time() - start_time) >10:                                        # try every 10 sec 
            start_time            = time.time() 
            read_file             = read_file+1
            
            # JSON opening and decoding
            data                  = json.load(open(InOutDataPath + 'status.json'))
            stamp                 = data["time"]["server_local_time"]

            # data sanity check
            json_inverters = 0
            json_chargers  = 0
            for n in range (len(data["devices"])):
                address   = int (data["devices"][n]["address"])
                device_id = (data["devices"][n]["device_id"])
                label     = data["devices"][n]["label"]
                if device_id == 5:
                    json_inverters += 1
                if device_id == 3:
                    json_chargers += 1                    
                #if port[n+1] != port[address]:
                    #print ("json device mapping found on port",  n+1, port[n+1], "vs", port [address], "mismatch")
            if json_inverters != inverters:
                print ("expected", inverters, "inverters, found", json_inverters, "trying to autocorrect")
                inverters = json_inverters
            if json_chargers != chargers:
                print ("expected", chargers, "chargers, found", json_chargers,"trying to autocorrect")
                chargers  = json_chargers

            pos = 0 
            operational_mode      = data["devices"][pos]["operational_mode"]
            ac_mode               = data["devices"][pos]["ac_mode"]
            ac_output_voltage     = data["devices"][pos]["ac_output_voltage"]
            ac_input_voltage      = data["devices"][pos]["ac_input_voltage"]
            inverter_current      = data["devices"][pos]["inverter_current"]
            buy_current           = data["devices"][pos]["buy_current"]

            if inverters == 2:
                pos = pos+1               
                inverter_current1 = data["devices"][pos]["inverter_current"]
                buy_current1      = data["devices"][pos]["buy_current"]
            else:
                inverter_current1 = 0
                buy_current1      = 0
            if  chargers == 1:
                pos = pos+1   
                charger_60_mode   = data["devices"][pos]["charge_mode"]
                charger_60_PV     = data["devices"][pos]["pv_voltage"]
                charger_80_mode   = "none"
                charger_80_PV     = 0
            if  chargers == 2:
                pos=pos +1 
                charger_60_mode   = data["devices"][pos]["charge_mode"]
                charger_60_PV     = data["devices"][pos]["pv_voltage"]
                pos = pos +1
                charger_80_mode   = data["devices"][pos]["charge_mode"]
                charger_80_PV     = data["devices"][pos]["pv_voltage"]
            
            pos=pos +1
            shunt_c               =-(data["devices"][pos]["shunt_c_current"])       # revert the negative value of shunt    
            battery_voltage       = data["devices"][pos]["battery_voltage"]
            soc                   = data["devices"][pos]["soc"]
            battery_temp          = data["devices"][pos]["battery_temp"]
            divert_pwr            = battery_voltage * shunt_c
            ac_out_pwr            = ac_output_voltage * (inverter_current + buy_current + inverter_current1 + buy_current1)

            # if temperature compensation is active ajust voltage_ref_compens with temp
            if voltage_compensated == "true":
                voltage_ref_compens = voltage_ref+ (25 - battery_temp)*0.12
            else:
                voltage_ref_compens = voltage_ref

            # check if the JSON file was changed then increment loops, read and analyse                                 
            if stamp != stamp_ref:
                print("---------------------------------------loop:", loop_no+1)
                stamp_ref = stamp
                loop_time = time.time()
                loop_no   = loop_no+1
                
                # statistics module --make std, averages ...
                shunt_c_array.append(shunt_c)
                battery_voltage_array.append(battery_voltage)
                divert_pwr_array.append(divert_pwr)
                ac_out_pwr_array.append(ac_out_pwr)
                charger_60_PV_array.append(charger_60_PV)
                charger_80_PV_array.append(charger_80_PV)

                # if boiler and boiler temp sensor exist, read boiler_temp
                if boiler_temp_active == "true":
                    with open(InOutDataPath + 'boiler_temp.txt', 'r') as temp:
                        lines     = temp.read().splitlines()
                        if lines:                                                      # check if file is empty
                            last_line = lines[-1]         
                            if last_line[31] == "g":                                   # checklast digit
                                boiler_temp = float(last_line[27:31])                  # character 27-31 converted to numbers temp with one digit         
                            else:
                                boiler_temp = float(last_line[27:30])                  # character 27-32 converted to numbers temp with 2 digits
                            temp_time = last_line[0:19]                                # caracter 0-19 to get the string of the date and time
    
                        else:
                            ErrorPrint("Alert: No data in temperature file")
                            temp_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")   # dummy data
                            boiler_temp = 70                                           # dummy data
                        FMT       ="%d-%m-%Y %H:%M:%S"                                 # format of the datetime
                        temp_time = time.strptime(temp_time, FMT)                      # format the temp_time according FMT
                        time_now  = time.localtime()                                   # get localtime
                        deltatime = (time.mktime(time_now)-time.mktime(temp_time))     # get delta in seconds between two times
                
                # in case of AC lost send push notification 
                if ac_input_voltage <100 and ac_input_voltage_ref != 0:
                    ErrorPrint("Info : Grid lost -- SOC: " + str(soc))
                    PushNotification("Info : Grid lost -- SOC: " + str(soc))
                    ac_input_voltage_ref=0
                if ac_input_voltage >180 and ac_input_voltage_ref != 220:
                    ErrorPrint("Info : Grid restored -- SOC: " + str(soc))
                    PushNotification("Info : Grid restored -- SOC: " + str(soc))
                    ac_input_voltage_ref=220

                #GPIO block
                # protection: inverter overpower
                if ac_out_pwr>max_ac_out_pwr and load_01=="active" and load_02=="active":
                    GPIO.output(18, GPIO.HIGH)
                    load_02 = "inactive"
                    ErrorPrint("Alert: Power peak: "+ str(ac_out_pwr)+" -> load_02 STOP")
                elif ac_out_pwr>max_ac_out_pwr and load_01=="active" and load_02=="inactive":
                    GPIO.output(17, GPIO.HIGH)
                    load_01 = "inactive"
                    GPIO.output(18, GPIO.HIGH)
                    load_02 = "inactive"
                    ErrorPrint("Alert: Power peak: "+ str(ac_out_pwr)+" -> load_01 & 02 STOP")
                    
                #GPIO block
                #protection: if SOC is low then stop first floor and utilities 
                if soc<soc_min_limit and stop_UP=="inactive":   
                    GPIO.output(23, GPIO.LOW)
                    stop_UP = "active"
                    ErrorPrint("Alert: Low SOC:" + str(soc) + " -> Solar U/P stopped")
                    PushNotification("Alert: Low SOC:" + str(soc) + " -> Solar U/P stopped")
                elif soc>(soc_min_limit + 5) and stop_UP=="active":  
                    GPIO.output(23, GPIO.HIGH)
                    stop_UP = "inactive"
                    ErrorPrint("Alert: SOC OK:" +str(soc) + " -> Solar U/P restored")
                    PushNotification("Alert: SOC OK:" +str(soc) + " -> Solar U/P restored")
                elif soc>(soc_min_limit + 5):  
                    GPIO.output(23, GPIO.HIGH)
                    stop_UP = "inactive"
                    
                #GPIO block    
                #activate power divert relay
                if divert_by_state == "true" and deltatime<deltatime_ref and boiler_temp<boiler_temp_ref and\
                     charger_60_PV > 70 or charger_80_PV > 70 and\
                    (charger_60_mode==floating or charger_80_mode==floating or\
                    charger_60_mode==absorbtion or charger_80_mode==absorbtion or\
                    charger_60_mode==equalize or charger_80_mode==equalize):
                    GPIO.output(22, GPIO.LOW)
                    divert = "active"
                elif divert_by_state == "false" and deltatime<deltatime_ref and boiler_temp<boiler_temp_ref and battery_voltage > (voltage_ref_compens):
                    GPIO.output(22, GPIO.LOW)
                    divert = "active"
                elif divert == "active" and divert_by_state == "false"and deltatime<deltatime_ref and boiler_temp<boiler_temp_ref and battery_voltage > (voltage_ref_compens - 0.5):
                    GPIO.output(22, GPIO.LOW)
                    divert = "active"                   
                elif divert == "active" and divert_by_state == "false" and battery_voltage < (voltage_ref_compens - 0.5):
                    GPIO.output(22, GPIO.HIGH)
                    divert = "inactive"
                elif deltatime<deltatime_ref and boiler_temp>boiler_temp_ref: 
                    GPIO.output(22, GPIO.HIGH)
                    divert="inactive_forced"
                elif deltatime>deltatime_ref:                                                              #protection : boiler temp - same file from long time >   900 
                    GPIO.output(22, GPIO.HIGH)
                    divert = "inactive_nodata"
                    ErrorPrint("Alert: No boiler temp data for:"+ str(int(deltatime/60))+ " min!")                  
                else:
                    GPIO.output(22, GPIO.HIGH)
                    divert = "inactive"
                    
                #reporting: measure time on grid, on battery, no grid
                now = datetime.now()
                if ac_mode==grid_connect:
                    ac_use_time         = ac_use_time + (time.time()-use_time)
                    ac_mode_old         = ac_mode
                    use_time            = time.time()
                    no_ac_drop_lasttime = 0
                    no_ac_use_lasttime  = 0
                if ac_input_voltage > 100 and ac_mode==grid_droped :                    
                    ac_drop_time        = ac_drop_time + (time.time()-use_time)
                    ac_mode_old         = ac_mode
                    use_time            = time.time()
                    no_ac_drop_lasttime = 0
                    no_ac_use_lasttime  = 0
                if  ac_input_voltage < 100 and ac_mode==grid_droped and ac_mode_old =="": # drop and no AC after restart
                    ac_mode_old=ac_mode
                if ac_input_voltage < 100 and ac_mode_old==grid_droped:                    
                    no_ac_drop_time     = no_ac_drop_time + (time.time()-use_time)
                    no_ac_drop_lasttime = no_ac_drop_lasttime + (time.time()-use_time)
                    use_time = time.time()
                if ac_input_voltage < 100 and ac_mode_old==grid_connect:                    
                    no_ac_use_time     = no_ac_use_time+ (time.time()-use_time)
                    no_ac_use_lasttime = no_ac_use_lasttime + (time.time()-use_time)
                    use_time           = time.time()
                    
                #if ac_mode=="NO AC": # Syn version
                if ac_input_voltage < 100:                    
                    no_ac_lasttime     = no_ac_drop_lasttime + no_ac_use_lasttime
                   
                now                    = datetime.now()
                start_reset_time       = now.replace(hour=6, minute=0, second=0, microsecond=0)
                end_reset_time         = now.replace(hour=6, minute=1, second=0, microsecond=0)
                
                if start_reset_time < now < end_reset_time:
                     print("---------------------------------.time reset")
                     ErrorPrint("Info : reset solar /grid usage time")
                     ac_drop_time      = 0
                     no_ac_drop_time   = 0
                     ac_use_time       = 0 
                     no_ac_use_time    = 0
                     no_ac_lasttime    = 0

            # calculate uptime of the script - for health and reporting purpose
            # MQTT GPIO block push status - reporting purpose 
            if (time.time() - uptime_push_time) >60:                                 # try every 60 sec 
                uptime_push_time = time.time()
                uptime = round((time.time()- up_time)/86400,3)
                if MQTT_active=='true':
                    publish.single(MQTT_topic1, uptime, hostname=MQTT_broker)                      #uptime every minute
                    publish.single(MQTT_topic2, gpio_states[GPIO.input(17)], hostname=MQTT_broker) #divert AC load1
                    publish.single(MQTT_topic3, gpio_states[GPIO.input(18)], hostname=MQTT_broker) #divert AC load2
                    publish.single(MQTT_topic4, gpio_states[GPIO.input(22)], hostname=MQTT_broker) #divert DC
                    publish.single(MQTT_topic5, gpio_states[GPIO.input(23)], hostname=MQTT_broker) #stop U/P low SOC

            #GPIO block    
            # protection: the same file for long time 
            if (time.time() - loop_time)>300:
                GPIO.output(17, GPIO.HIGH)
                load_01 = "inactive"
                GPIO.output(18, GPIO.HIGH)
                load_02 = "inactive"
                ErrorPrint("Alert: Same JSON file for:" + str(int((time.time() - loop_time)/60)) +" min!")            
           
            if loop_no >= loop_ref:
                shunt_c_avg         = round(statistics.mean(shunt_c_array),2)
                battery_voltage_avg = round(statistics.mean(battery_voltage_array),2)
                divert_pwr_avg      = int(statistics.mean(divert_pwr_array))
                divert_pwr_std      = int(statistics.stdev(divert_pwr_array))/2    # standard dev / 2
                divert_pwr_cor      = divert_pwr_avg - divert_pwr_std
                ac_out_pwr_avg      = int(statistics.mean(ac_out_pwr_array))
                charger_60_PV_avg   = int(statistics.mean(charger_60_PV_array))
                charger_80_PV_avg   = int(statistics.mean(charger_80_PV_array))
                chargers_PV_avg     = (charger_80_PV_avg + charger_60_PV_avg) / 2

                # GPIO block
                #load_02 control   
                if load_01 =="active" and ac_out_pwr_avg < (max_ac_out_pwr-500) and divert_pwr_cor > divert_pwr_ref :
                    GPIO.output(18, GPIO.LOW)
                    load_02 = "active"
                elif load_01 =="active" and divert=="inactive_forced" and chargers_PV_avg > chargers_PV_ref and \
                     (charger_60_mode==floating or charger_80_mode==floating or charger_60_mode==absorbtion or charger_80_mode==absorbtion or\
                      charger_60_mode==equalize or charger_80_mode==equalize):
                    GPIO.output(18, GPIO.LOW)
                    load_02 = "active"
                elif load_01 =="active" and load_02 =="active" and divert_pwr_cor >100:
                    GPIO.output(18, GPIO.LOW)
                    load_02 = "active"
                elif  load_01=="active" and load_02 =="active" and divert=="inactive_forced" and battery_voltage_avg > voltage_ref_compens:
                    GPIO.output(18, GPIO.LOW)
                    load_02 = "active"
                elif load_01 =="active" and load_02 =="active" and divert=="active" and divert_pwr_cor <100:
                    GPIO.output(18, GPIO.HIGH)
                    load_02 = "inactive_skip"
                elif  load_01=="active" and load_02 =="active" and divert=="inactive_forced" and battery_voltage_avg < voltage_ref_compens:
                    GPIO.output(18, GPIO.HIGH)
                    load_02 = "inactive_skip" 
                else:
                    GPIO.output(18, GPIO.HIGH)
                    load_02 = "inactive"
                    
                #GPIO block
                # load_01 control
                if ac_mode == grid_droped  and ac_out_pwr_avg < (max_ac_out_pwr-500) and divert_pwr_cor > divert_pwr_ref: 
                    GPIO.output(17, GPIO.LOW)
                    load_01 = "active"
                elif ac_mode == grid_droped  and ac_out_pwr_avg < (max_ac_out_pwr-500) and divert=="inactive_forced" and chargers_PV_avg > chargers_PV_ref and \
                     (charger_60_mode==floating or charger_80_mode==floating or charger_60_mode==absorbtion or charger_80_mode==absorbtion or\
                      charger_60_mode==equalize or charger_80_mode==equalize):  
                    GPIO.output(17, GPIO.LOW)
                    load_01 = "active"
                elif ac_mode == grid_droped  and load_01=="active" and load_02=="active" and battery_voltage_avg > voltage_ref_compens:                    
                    GPIO.output(17, GPIO.LOW)
                    load_01 = "active"
                elif ac_mode == grid_droped  and load_01=="active" and load_02=="inactive" and divert_pwr_cor >100:                    
                    GPIO.output(17, GPIO.LOW)
                    load_01 = "active"                    
                elif ac_mode == grid_droped  and load_01=="active" and load_02=="inactive_skip":                    
                    GPIO.output(17, GPIO.LOW)
                    load_01 = "active"
                elif ac_mode == grid_droped  and load_01=="active" and divert=="inactive_forced" and battery_voltage_avg > voltage_ref_compens:                    
                    GPIO.output(17, GPIO.LOW)
                    load_01 = "active"
                else:    
                    GPIO.output(17, GPIO.HIGH)
                    load_01 = "inactive"
                    GPIO.output(18, GPIO.HIGH)
                    load_02 = "inactive"
                    
                # printing block
                print("stamp:", stamp,)
                print("up_time:", uptime," reads:", read_file," loops:", loop_no)
                print("GRID__time/pwr_cut[h]:  ", round(ac_use_time/3600,1),"/",round(no_ac_use_time/3600,1))
                print("SOLAR_time/pwr_cut[h]:  ", round(ac_drop_time/3600,1),"/",round(no_ac_drop_time/3600,1))
                print("Last pwr_cut[h]:        ", round(no_ac_lasttime/3600,1))
                print("shunt_c[A]:             ", shunt_c_avg)
                print("battery_voltage[V]:     ", battery_voltage_avg, " SOC[%]:",soc)
                print("ref_voltage_comp[V}:    ", voltage_ref_compens)
                print("ac_out_pwr[W]:          ", ac_out_pwr_avg)
                print("divert_pwr[W]:          ", divert_pwr_avg,       " corrected[W]:",divert_pwr_cor)
                print("boiler_temperature:     ", boiler_temp)
                print("FM60Mode:               ", charger_60_mode,     " PV[V]:",charger_60_PV_avg)
                print("FM80Mode:               ", charger_80_mode,     " PV[V]:",charger_80_PV_avg)
                print("OperationalMode:        ", operational_mode)
                print("grid:                   ", ac_mode)
                print("ac_input_voltage:       ", ac_input_voltage)
                print("Diverter relay:         ", divert)
                print("Load_01 relay:          ", load_01)
                print("Load_02 relay:          ", load_02)
                print("Stop utilities relay:   ", stop_UP)
                
                # write logfile block
                with open(InOutDataPath + 'raspberry_data.log','r') as file:
                    save = file.read()
                with open(InOutDataPath + 'raspberry_data.log','w') as file:
                    file.write("--------------------------------------" + "\r\n")
                    file.write("stamp:" + str(stamp) +"\r\n")
                    file.write("up_time:" + str(uptime)  + " reads:" + str(read_file) + " loops:" + str(loop_no) +"\r\n")
                    file.write("GRID__time/pwr_cut[h]: " + str(round(ac_use_time/3600,1)) + "/" + str(round(no_ac_use_time/3600,1)) + "\r\n")
                    file.write("SOLAR_time/pwr_cut[h]: " + str(round(ac_drop_time/3600,1)) + "/" + str(round(no_ac_drop_time/3600,1)) + "\r\n")
                    file.write("Last_pwr_cut[h]:       " + str(round(no_ac_lasttime/3600,1)) + "\r\n")
                    file.write("shunt_c[A]:            " + str(shunt_c_avg) +"\r\n")
                    file.write("battery_voltage[V]:    " + str(battery_voltage_avg) + " SOC[%]:"+ str(soc) + "\r\n")
                    file.write("ref_voltage_comp[V]:   " + str(voltage_ref_compens) + "\r\n")
                    file.write("ac_out_pwr[W]:         " + str(ac_out_pwr_avg)  +"\r\n")
                    file.write("divert_pwr[W]:         " + str(divert_pwr_avg)  + " [corrected]:" + str(divert_pwr_cor) + "\r\n")
                    file.write("boiler_temperature:    " + str(boiler_temp)     + "\r\n")
                    file.write("FX60Mode:              " + str(charger_60_mode) + " PV [V]:"+ str(charger_60_PV_avg) + "\r\n")
                    file.write("FX80Mode:              " + str(charger_80_mode) + " PV [V]:"+ str(charger_80_PV_avg) + "\r\n")
                    file.write("OperationalMode:       " + str(operational_mode)+ "\r\n")                              
                    file.write("grid:                  " + str(ac_mode) +"\r\n")
                    file.write("ac_input_voltage[V}:   " + str(ac_input_voltage)+ "\r\n")
                    file.write("Diverter relay:        " + str(divert)  + "\r\n")
                    file.write("Load_01 relay:         " + str(load_01) + "\r\n")
                    file.write("Load_02 relay:         " + str(load_02) + "\r\n")
                    file.write("Stop utilities relay:  " + str(stop_UP) + "\r\n")
                    
                with open(InOutDataPath + 'raspberry_data.log',"a") as file:
                    file.write(save)
                file.close()

                # reset loop variables before exit loop IF
                read_file             = 0
                error_count           = 0
                loop_no               = 0
                divert_pwr_array      = []
                ac_out_pwr_array      = []
                shunt_c_array         = []
                battery_voltage_array = []
                charger_60_PV_array   = []
                charger_80_PV_array   = []
           
    #error treatment block
    except FileNotFoundError as e:
        ErrorPrint("Error: FileNotFound - "+ str(e))
    except ValueError as e:  # includes simplejson.decoder.JSONDecodeError
        shutil.copy(InOutDataPath + 'status.json', InOutDataPath + 'status_error.json') 
        ErrorPrint("Error: ValueError - " + str(e))
    except TypeError as e:
        ErrorPrint("Error: TypeError - " + str(e))
    except KeyboardInterrupt:
        ErrorPrint("STOP : Exiting...keyboardInterupt")
        PushNotification("STOP : Exiting...keyboardInterupt")
        GPIO.cleanup()
        raise SystemExit
    except OSError:
        time.sleep(120) # time to restore connection
        ErrorPrint("Error: OSError - host is down!")
        print("Info : OSError - delay applyed")
    except Exception as e:
        if error_count < 3:
            ErrorPrint("Error: Unexpected...- "+ str(e))
            error_count = error_count + 1
        elif error_count < 4:
            #ErrorPrint("Error: Unexpected...- "+ str(e))
            ErrorPrint("Info: Preparing exit and restart")
            error_count = error_count + 1        
        else:            
            ErrorPrint("STOP: Exiting...- "+ str(e))
            PushNotification("STOP: Exiting...- "+ str(e))
            GPIO.cleanup()
            raise SystemExit
