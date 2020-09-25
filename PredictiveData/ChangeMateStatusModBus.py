import logging
import json
import time
from datetime import datetime
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from configparser import ConfigParser
#import paho.mqtt.client as mqtt
#import paho.mqtt.publish as publish
import sys, os

script_ver = "0.7.0_20200902"
print ("script version   : "+ script_ver)

curent_date_time  = datetime.now()
pathname          = os.path.dirname(sys.argv[0])
working_dir       = os.path.abspath(pathname) 
print ("working directory: " +  working_dir)

config                               = ConfigParser()
config.read(working_dir + '/ChangeMateStatusModBus.cfg')

OutputPath                           = config.get('Connectivity', 'OutputPath')
print("Output path      : " + OutputPath)

mate3_ip                             = config.get('Connectivity', 'mate3_ip')
mate3_modbus                         = config.get('Connectivity', 'mate3_modbus')
sunspec_start_reg                    = 40000
MQTT_active                          = config.get('Connectivity', 'MQTT_active')                        # default = false  -- if active will publish MQTT topics to varoius platforms i.e Home Assistant
MQTT_broker                          = config.get('Connectivity', 'MQTT_broker')                        # your MQTT broker address - i.e 192.168.0.xxx

# Dinamic Data
dinamic_data                         = json.load(open(working_dir + '/dinamic_data.json'))
Sched_1_AC_Mode_local                = dinamic_data["OutbackBlock"]["outback_schedule"]["sched_1_ac_mode"]
OutBack_Sched_1_AC_Mode_Hour_local   = dinamic_data["OutbackBlock"]["outback_schedule"]["sched_1_ac_mode_hour"]
OutBack_Sched_1_AC_Mode_Minute_local = dinamic_data["OutbackBlock"]["outback_schedule"]["sched_1_ac_mode_minute"]
Sched_2_AC_Mode_local                = dinamic_data["OutbackBlock"]["outback_schedule"]["sched_2_ac_mode"]
OutBack_Sched_2_AC_Mode_Hour_local   = dinamic_data["OutbackBlock"]["outback_schedule"]["sched_2_ac_mode_hour"]
OutBack_Sched_2_AC_Mode_Minute_local = dinamic_data["OutbackBlock"]["outback_schedule"]["sched_2_ac_mode_minute"]
Sched_3_AC_Mode_local                = dinamic_data["OutbackBlock"]["outback_schedule"]["sched_3_ac_mode"]
OutBack_Sched_3_AC_Mode_Hour_local   = dinamic_data["OutbackBlock"]["outback_schedule"]["sched_3_ac_mode_hour"]
OutBack_Sched_3_AC_Mode_Minute_local = dinamic_data["OutbackBlock"]["outback_schedule"]["sched_3_ac_mode_minute"]
OutbackBlock_flag                    = dinamic_data["OutbackBlock"]["OutbackBlock_flag"]
Charger_Operating_Mode_local         = dinamic_data["RadianInverterConfigurationBlock"]["charger_operating_mode"]
Grid_Input_Mode_local                = dinamic_data["RadianInverterConfigurationBlock"]["grid_input_mode"]
InverterConfigurationBlock_flag      = dinamic_data["RadianInverterConfigurationBlock"]["InverterConfigurationBlock_flag"]
OB_Charge_Enable_Disable_local       = dinamic_data["OutbackSystemControlBlock"]["Charge_Enable_Disable"]
OutbackSystemControlBlock_flag       = dinamic_data["OutbackSystemControlBlock"]["OutbackSystemControlBlock_flag"]
loop                                 = 0 

# ACmode_list is used to convert numbers in pretty name -- in registry modes are coded like below:
ACmode_list = [
    "Generator",     # 0
    "Support",       # 1
    "GriedTied",     # 2
    "UPS",           # 3
    "Backup",        # 4
    "MiniGrid",      # 5
    "GridZero",      # 6
    "Disabled"]      # 7
# Charge_Enable_Disable_list is used to convert numbers in pretty name -- in registry modes are coded like below:
Charge_Enable_Disable_list = [
    "Default",       #0
    "StartBulk",     #1
    "StopBulk",      #2
    "StartEQ",       #3
    "StopEQ"]        #4

print("variables initialization completed")

# external python arguments - this has priority, dinamic_data will be overwriten
if len(sys.argv) > 1:
    
    if sys.argv[1] == 'on' or sys.argv[1] == 'off':
        Charger_Operating_Mode_local    = sys.argv[1] # new value received 
        OutbackBlock_flag = 0                         # to prevent conflicts
        OutbackSystemControlBlock_flag  = 0
        InverterConfigurationBlock_flag = 1
        print("..'Charger_Operating_Mode_local' was overwritten: ", Charger_Operating_Mode_local)
    
    if sys.argv[1] in ACmode_list:
        Grid_Input_Mode_local           = sys.argv[1] # new value received 
        OutbackBlock_flag = 0                         # to prevent conflicts
        OutbackSystemControlBlock_flag  = 0
        InverterConfigurationBlock_flag = 1
        print("..'Grid_Input_Mode_local' was overwritten: ", Grid_Input_Mode_local)
    
    if sys.argv[1] in Charge_Enable_Disable_list:
        OB_Charge_Enable_Disable_local  = sys.argv[1] # new value received 
        OutbackBlock_flag = 0                         # to prevent conflicts
        InverterConfigurationBlock_flag = 0
        OutbackSystemControlBlock_flag  = 1
        print("..'OB_Charge_Enable_Disable_local' was overwritten: ", OB_Charge_Enable_Disable_local)       

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%Y%m%d %H:%M:%S')
logging.getLogger(__name__)

curent_date_time  = datetime.now()

#error log subroutine
def EventLog (str) :
    try:
        with open(OutputPath + "/data/general_info.log","r") as file:
            save = file.read()
        with open(OutputPath + "/data/general_info.log","w") as file:
            file = open(OutputPath + "/data/general_info.log","a")
            file.write(curent_date_time.strftime("%d/%m/%Y %H:%M:%S "))
            #file.write(str + "\r\n")
            file.write(str + "\n")
            #print(str)
        with open(OutputPath + "/data/general_info.log","a") as file:
            file.write(save)
        return
    except OSError:
        print(str,"Error: CMS - error handling block: double error")

# =================================== ModbusMate subroutines & variables =====================================
# Define the dictionary mapping SUNSPEC DID's to Outback names
# Device IDs definitions = (DID)
# AXS_APP_NOTE.PDF from Outback website has the data
mate3_did = {
    64110: "Outback block",
    64111: "Charge Controller Block",
    64112: "Charge Controller Configuration block",    
    64115: "Split Phase Radian Inverter Real Time Block",
    64116: "Radian Inverter Configuration Block",
    64117: "Single Phase Radian Inverter Real Time Block",
    64113: "FX Inverter Real Time Block",
    64114: "FX Inverter Configuration Block",
    64119: "FLEXnet-DC Configuration Block",
    64118: "FLEXnet-DC Real Time Block",
    64120: "Outback System Control Block",
    101: "SunSpec Inverter - Single Phase",
    102: "SunSpec Inverter - Split Phase",
    103: "SunSpec Inverter - Three Phase",
    64255: "OpticsRE Statistics Block",
    65535: "End of SunSpec"
}

# Read SunSpec Header with logic from pymodbus example
def decode_int16(signed_value):
    """
    Negative numbers (INT16 = short)
      Some manufacturers allow negative values for some registers. Instead of an allowed integer range 0-65535,
      a range -32768 to 32767 is allowed. This is implemented as any received value in the upper range (32768-65535)
      is interpreted as negative value (in the range -32768 to -1).
      This is two’s complement and is described at http://en.wikipedia.org/wiki/Two%27s_complement.
      Help functions to calculate the two’s complement value (and back) are provided in MinimalModbus.
    """

    # Outback has some bugs in their firmware it seems. The FlexNet DC Shunt current measurements
    # return an offset from 65535 for negative values. No reading should ever be higher then 2000. So use that
    # print("int16 RAW: {!s}".format(signed_value))

    if signed_value > 32768+2000:
        return signed_value - 65535
    elif signed_value >= 32768:
        return int(32768 - signed_value)
    else:
        return signed_value
    
#convert decimal to binary string    
def binary(decimal) :
    otherBase = ""
    while decimal != 0 :
        otherBase  =  str(decimal % 2) + otherBase
        decimal    //=  2
    return otherBase
    #return otherBase [::-1] #invert de string    

def get_common_block(basereg):
    """ Read and return the sunspec common information
    block.
    :returns: A dictionary of the common block information
    """
    length = 69
    response = client.read_holding_registers(basereg, length + 2)
    decoder = BinaryPayloadDecoder.fromRegisters(response.registers,
                                                 byteorder=Endian.Big,
                                                 wordorder=Endian.Big)
    return {
        'SunSpec_ID': decoder.decode_32bit_uint(),
        'SunSpec_DID': decoder.decode_16bit_uint(),
        'SunSpec_Length': decoder.decode_16bit_uint(),
        'Manufacturer': decoder.decode_string(size=32),
        'Model': decoder.decode_string(size=32),
        'Options': decoder.decode_string(size=16),
        'Version': decoder.decode_string(size=16),
        'SerialNumber': decoder.decode_string(size=32),
        'DeviceAddress': decoder.decode_16bit_uint(),
        'Next_DID': decoder.decode_16bit_uint(),
        'Next_DID_Length': decoder.decode_16bit_uint(),
    }

# Read SunSpec header
def getSunSpec(basereg):
    # Read two bytes from basereg, a SUNSPEC device will start with 0x53756e53
    # As 8bit ints they are 21365, 28243
    try:
        response = client.read_holding_registers(basereg, 2)
    except:
        return None

    if response.registers[0] == 21365 and response.registers[1] == 28243:
        logging.info(".. SunSpec device found. Reading Manufacturer info")
    else:
        return None
    # There is a 16 bit string at basereg + 4 that contains Manufacturer
    response = client.read_holding_registers(basereg + 4, 16)
    decoder  = BinaryPayloadDecoder.fromRegisters(response.registers,
                                                 byteorder=Endian.Big,
                                                 wordorder=Endian.Big)
    manufacturer = decoder.decode_string(16)
    
    if "OUTBACK_POWER" in str(manufacturer.upper()):
        logging.info(".. Outback Power device found")
    else:
        logging.info(".. Not an Outback Power device. Detected " + manufacturer)
        return None
    try:
        register = client.read_holding_registers(basereg + 3)
    except:
        return None
    blocksize = int(register.registers[0])
    return blocksize

def getBlock(basereg):
    try:
        register = client.read_holding_registers(basereg)
    except:
        return None
    blockID = int(register.registers[0])
    # Peek at block style
    try:
        register = client.read_holding_registers(basereg + 1)
    except:
        return None
    blocksize = int(register.registers[0])
    blockname = None
    try:
        blockname = mate3_did[blockID]
        # print "Detected a " + mate3_did[blockID] + " at " + str(basereg) + " with size " + str(blocksize)
    except:
        print("ERROR: Unknown device type with DID=" + str(blockID))
    return {"size": blocksize, "DID": blockname}

def OutbackBlock():
    global OutbackBlock_flag
    loop = 0
    while loop < 3 :
        # autoscheduling 1 -- reading registries
        response = client.read_holding_registers(reg + 409, 1)
        OutBack_Sched_1_AC_Mode = response.registers[0]
        response = client.read_holding_registers(reg + 410, 1)                
        OutBack_Sched_1_AC_Mode_Hour = response.registers[0]
        response = client.read_holding_registers(reg + 411, 1)
        OutBack_Sched_1_AC_Mode_Minute = response.registers[0]
        
        if OutBack_Sched_1_AC_Mode == 65535:
            Sched_1_AC_Mode = ACmode_list[OutBack_Sched_1_AC_Mode-65528]
        else:
            Sched_1_AC_Mode = ACmode_list[OutBack_Sched_1_AC_Mode]
        
        if Sched_1_AC_Mode_local == "Disabled":
            OutBack_Sched_1_AC_Mode_local = 65535
        elif Sched_1_AC_Mode_local not in ACmode_list :
            OutBack_Sched_1_AC_Mode_local = None
        else:
            OutBack_Sched_1_AC_Mode_local = ACmode_list.index(Sched_1_AC_Mode_local)
        
        logging.info(".... schedule_1 [h:mm] " + str(OutBack_Sched_1_AC_Mode_Hour) + ":" + str(OutBack_Sched_1_AC_Mode_Minute) + " " + str(Sched_1_AC_Mode))
        
       
        # autoscheduling 1 -- write OutBack_Sched_1_AC_Mode registry
        if  Sched_1_AC_Mode_local != "notset" and Sched_1_AC_Mode_local in ACmode_list and OutBack_Sched_1_AC_Mode != OutBack_Sched_1_AC_Mode_local:
            rw = client.write_register(reg + 409, OutBack_Sched_1_AC_Mode_local)
            logging.info(".... updating sch_1 to: " + str(Sched_1_AC_Mode_local))
            Sched_1_AC_Mode_flag = 1
        else:
            Sched_1_AC_Mode_flag = 0
        # autoscheduling 1 -- write OutBack_Sched_1_AC_Mode_Hour registry    
        if  OutBack_Sched_1_AC_Mode_Hour_local != "notset" and OutBack_Sched_1_AC_Mode_Hour_local in range(24) and OutBack_Sched_1_AC_Mode_Hour != OutBack_Sched_1_AC_Mode_Hour_local:
            rw = client.write_register(reg + 410, OutBack_Sched_1_AC_Mode_Hour_local)
            logging.info(".... updating sch_1 hour : " + str(OutBack_Sched_1_AC_Mode_Hour_local))
            Sched_1_AC_Mode_Hour_flag = 1
        else:
            Sched_1_AC_Mode_Hour_flag = 0

        # autoscheduling 2 -- reading registries
        response = client.read_holding_registers(reg + 412, 1)
        OutBack_Sched_2_AC_Mode = response.registers[0]
        response = client.read_holding_registers(reg + 413, 1)                
        OutBack_Sched_2_AC_Mode_Hour = response.registers[0]
        response = client.read_holding_registers(reg + 414, 1)
        OutBack_Sched_2_AC_Mode_Minute = response.registers[0]
        
        if OutBack_Sched_2_AC_Mode == 65535:
            Sched_2_AC_Mode = ACmode_list[OutBack_Sched_2_AC_Mode-65528]
        else:
            Sched_2_AC_Mode = ACmode_list[OutBack_Sched_2_AC_Mode]
        
        if Sched_2_AC_Mode_local == "Disabled":
            OutBack_Sched_2_AC_Mode_local = 65535
        elif Sched_2_AC_Mode_local not in ACmode_list :
            OutBack_Sched_2_AC_Mode_local = None           
        else:
            OutBack_Sched_2_AC_Mode_local = ACmode_list.index(Sched_2_AC_Mode_local)
       
        logging.info(".... schedule_2 [h:mm] " + str(OutBack_Sched_2_AC_Mode_Hour) + ":" + str(OutBack_Sched_2_AC_Mode_Minute) + " " + str(Sched_2_AC_Mode))
        
        # autoscheduling 2 -- write OutBack_Sched_2_AC_Mode registry
        if Sched_2_AC_Mode_local != "notset" and Sched_2_AC_Mode_local in ACmode_list and OutBack_Sched_2_AC_Mode != OutBack_Sched_2_AC_Mode_local:
            rw = client.write_register(reg + 412, OutBack_Sched_2_AC_Mode_local)
            logging.info(".... updating sch_2 to: " + str(Sched_2_AC_Mode_local))
            Sched_2_AC_Mode_flag = 1
        else:
            Sched_2_AC_Mode_flag = 0
            
        # autoscheduling 2 -- write OutBack_Sched_2_AC_Mode_Hour registry    
        if  OutBack_Sched_2_AC_Mode_Hour_local != "notset" and OutBack_Sched_2_AC_Mode_Hour_local in range(24) and OutBack_Sched_2_AC_Mode_Hour != OutBack_Sched_2_AC_Mode_Hour_local:
            rw = client.write_register(reg + 413, OutBack_Sched_2_AC_Mode_Hour_local)
            logging.info(".... updating sch_2 hour : " + str(OutBack_Sched_2_AC_Mode_Hour_local))
            Sched_2_AC_Mode_Hour_flag = 1
        else:
            Sched_2_AC_Mode_Hour_flag = 0 
 
        # autoscheduling 3 -- reading registries
        response = client.read_holding_registers(reg + 415, 1)
        OutBack_Sched_3_AC_Mode = response.registers[0]
        response = client.read_holding_registers(reg + 416, 1)                
        OutBack_Sched_3_AC_Mode_Hour = response.registers[0]
        response = client.read_holding_registers(reg + 417, 1)
        OutBack_Sched_3_AC_Mode_Minute = response.registers[0]
        
        if OutBack_Sched_3_AC_Mode == 65535:
            Sched_3_AC_Mode = ACmode_list[OutBack_Sched_3_AC_Mode-65528]
        else:
            Sched_3_AC_Mode = ACmode_list[OutBack_Sched_3_AC_Mode]
        
        if Sched_3_AC_Mode_local == "Disabled":
            OutBack_Sched_3_AC_Mode_local = 65535
        elif Sched_3_AC_Mode_local not in ACmode_list :
            OutBack_Sched_3_AC_Mode_local = None           
        else:
            OutBack_Sched_3_AC_Mode_local = ACmode_list.index(Sched_3_AC_Mode_local)
        
        logging.info(".... schedule_3 [h:mm] " + str(OutBack_Sched_3_AC_Mode_Hour) + ":" + str(OutBack_Sched_3_AC_Mode_Minute) + " " + str(Sched_3_AC_Mode))
        
        # autoscheduling 3 -- write OutBack_Sched_3_AC_Mode registry
        if Sched_3_AC_Mode_local != "notset" and Sched_3_AC_Mode_local in ACmode_list and OutBack_Sched_3_AC_Mode != OutBack_Sched_3_AC_Mode_local:
            rw = client.write_register(reg + 415, OutBack_Sched_3_AC_Mode_local)
            logging.info(".... updating sch_3 to: " + str(Sched_3_AC_Mode_local))
            Sched_3_AC_Mode_flag = 1
        else:
            Sched_3_AC_Mode_flag = 0
            
        # autoscheduling 3 -- write OutBack_Sched_3_AC_Mode_Hour registry    
        if  OutBack_Sched_3_AC_Mode_Hour_local != "notset" and OutBack_Sched_3_AC_Mode_Hour_local in range(24) and OutBack_Sched_3_AC_Mode_Hour != OutBack_Sched_3_AC_Mode_Hour_local:
            rw = client.write_register(reg + 416, OutBack_Sched_3_AC_Mode_Hour_local)
            logging.info(".... updating sch_3 hour : " + str(OutBack_Sched_3_AC_Mode_Hour_local))
            Sched_3_AC_Mode_Hour_flag = 1
        else:
            Sched_3_AC_Mode_Hour_flag = 0
 
        if Sched_1_AC_Mode_flag == 0 and Sched_1_AC_Mode_Hour_flag == 0 and\
           Sched_2_AC_Mode_flag == 0 and Sched_2_AC_Mode_Hour_flag == 0 and\
           Sched_3_AC_Mode_flag == 0 and Sched_3_AC_Mode_Hour_flag == 0:
                       
            dinamic_data["OutbackBlock"]["outback_schedule"]["sched_1_ac_mode"]        = "notset"
            dinamic_data["OutbackBlock"]["outback_schedule"]["sched_1_ac_mode_hour"]   = "notset"
            dinamic_data["OutbackBlock"]["outback_schedule"]["sched_1_ac_mode_minute"] = "notset"
            dinamic_data["OutbackBlock"]["outback_schedule"]["sched_2_ac_mode"]        = "notset"
            dinamic_data["OutbackBlock"]["outback_schedule"]["sched_2_ac_mode_hour"]   = "notset"
            dinamic_data["OutbackBlock"]["outback_schedule"]["sched_2_ac_mode_minute"] = "notset"
            dinamic_data["OutbackBlock"]["outback_schedule"]["sched_3_ac_mode"]        = "notset"
            dinamic_data["OutbackBlock"]["outback_schedule"]["sched_3_ac_mode_hour"]   = "notset"
            dinamic_data["OutbackBlock"]["outback_schedule"]["sched_3_ac_mode_minute"] = "notset"
            dinamic_data["OutbackBlock"]["OutbackBlock_flag"]                          = 0
            OutbackBlock_flag                    = 0
            break
        else:
            loop = loop + 1
            logging.info(".... verification loop " +  str(loop))

    if OutbackBlock_flag == 0:
        logging.info(".... verification completed in " + str(loop) +" loop: all good")
        EventLog("Info : CMS - sch_1 to " + str(OutBack_Sched_1_AC_Mode_Hour) + ":" + str(OutBack_Sched_1_AC_Mode_Minute) + " " + str(Sched_1_AC_Mode))
        EventLog("Info : CMS - sch_2 to " + str(OutBack_Sched_2_AC_Mode_Hour) + ":" + str(OutBack_Sched_2_AC_Mode_Minute) + " " + str(Sched_2_AC_Mode))
        EventLog("Info : CMS - sch_3 to " + str(OutBack_Sched_3_AC_Mode_Hour) + ":" + str(OutBack_Sched_3_AC_Mode_Minute) + " " + str(Sched_3_AC_Mode))
    else:
        logging.info(".... verification failed")
        EventLog("Info : CMS - update failed")
    
    dinamic_data["time_taken"] = str(curent_date_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    with open(working_dir +'/dinamic_data.json', 'w') as outfile:
        json.dump(dinamic_data, outfile, indent=1)
    
    return

def OutbackSystemControlBlock():
    global OutbackSystemControlBlock_flag
    loop = 0
    while loop <= 3 :
        response = client.read_holding_registers(reg + 5, 1)
        OB_Charge_Enable_Disable = int(response.registers[0])
        logging.info(".... Curent charging mode " + Charge_Enable_Disable_list[OB_Charge_Enable_Disable])
        
        if OB_Charge_Enable_Disable_local in Charge_Enable_Disable_list and OB_Charge_Enable_Disable_local != Charge_Enable_Disable_list[OB_Charge_Enable_Disable]:
            rw = client.write_register(reg + 5, Charge_Enable_Disable_list.index(OB_Charge_Enable_Disable_local))
            logging.info("......updating charging mode to: " + OB_Charge_Enable_Disable_local)
            EventLog("Info : CMS - updating charging mode to: " + OB_Charge_Enable_Disable_local)
            Charge_Enable_Disable_flag = 1
        else:    
            Charge_Enable_Disable_flag = 0
            dinamic_data["OutbackSystemControlBlock"]["Charge_Enable_Disable"] = "notset"
       
        if Charge_Enable_Disable_flag == 0 :
            dinamic_data["OutbackSystemControlBlock"]["OutbackSystemControlBlock_flag"] = 0           
            OutbackSystemControlBlock_flag = 0
            break
        else:
            loop = loop + 1
            logging.info(".... verification loop " +  str(loop))
    
    return

def RadianInverterConfigurationBlock():
    global InverterConfigurationBlock_flag
    loop = 0
    while loop <= 3 :
        #GSconfig_Charger_Operating_Mode
        response = client.read_holding_registers(reg + 24, 1)
        GSconfig_Charger_Operating_Mode = int(response.registers[0])
        logging.info(".... FXR Charger Mode " + str(GSconfig_Charger_Operating_Mode))
        
        Charger_Operating_Mode='None'
        if GSconfig_Charger_Operating_Mode == 0:   Charger_Operating_Mode ='off'
        if GSconfig_Charger_Operating_Mode == 1:   Charger_Operating_Mode ='on'
        
        if Charger_Operating_Mode_local != "notset" and Charger_Operating_Mode != Charger_Operating_Mode_local:
            if Charger_Operating_Mode_local == 'on':   GSconfig_Charger_Operating_Mode_SC = 1
            if Charger_Operating_Mode_local == 'off':  GSconfig_Charger_Operating_Mode_SC = 0
            rw = client.write_register(reg + 24, GSconfig_Charger_Operating_Mode_SC)
            Charger_Operating_Mode = GSconfig_Charger_Operating_Mode_SC
            logging.info("......updating AC charging to: " + str(Charger_Operating_Mode_local))
            EventLog("Info : CMS - updating AC charging to: " + str(Charger_Operating_Mode_local))
            Charger_Operating_Mode_flag = 1
            #if MQTT_active=='true' : publish.single('home-assistant/solar/solar_Charger_Operating_Mode', Charger_Operating_Mode_local, hostname=MQTT_broker)
        else:    
            Charger_Operating_Mode_flag = 0
            dinamic_data["RadianInverterConfigurationBlock"]["charger_operating_mode"] = "notset"
        
        # GSconfig_Grid_Input_Mode
        response = client.read_holding_registers(reg + 26, 1)
        GSconfig_Grid_Input_Mode = int(response.registers[0])
        logging.info(".... FXR Input mode " + ACmode_list[GSconfig_Grid_Input_Mode])
        
        if Grid_Input_Mode_local in ACmode_list and GSconfig_Grid_Input_Mode != ACmode_list.index(Grid_Input_Mode_local):                    
            rw = client.write_register(reg + 26, ACmode_list.index(Grid_Input_Mode_local))
            logging.info("......updating AC mode to: " + Grid_Input_Mode_local)
            EventLog("Info : CMS - updating AC mode to: " + Grid_Input_Mode_local)
            Grid_Input_Mode_flag = 1
            #if MQTT_active=='true' : publish.single('home-assistant/solar/solar_grid_input_mode', Grid_Input_Mode_local, hostname=MQTT_broker)
        else:    
            Grid_Input_Mode_flag = 0
            dinamic_data["RadianInverterConfigurationBlock"]["grid_input_mode"] = "notset"
       
        if Grid_Input_Mode_flag == 0 and Charger_Operating_Mode_flag == 0:
            dinamic_data["RadianInverterConfigurationBlock"]["InverterConfigurationBlock_flag"] = 0           
            InverterConfigurationBlock_flag = 0
            break
        else:
            loop = loop + 1
            logging.info(".... verification loop " +  str(loop))
    
    if InverterConfigurationBlock_flag == 0:
        logging.info(".... verification completed in " + str(loop) +" loop: all good")
    else:
        logging.info(".... verification failed")
        EventLog("Info : CMS - update failed")
        
    dinamic_data["time_taken"] = str(curent_date_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    with open(working_dir +'/dinamic_data.json', 'w') as outfile:
        json.dump(dinamic_data, outfile, indent=1)    

    return 

def FLEXnetDCRealTimeBlock():
    logging.info(".. Detect a FLEXnet-DC Real Time Block")  
    return


# =======================================This is the main loop =====================================
print("------------------------------------------------")
print(" MATE3 ModBus Interface")
print("------------------------------------------------")

# Try to build the mate3 MODBUS connection
try:
    logging.info("Building MATE3 MODBUS connection")
    logging.info(".. waiting 10 seconds ")
    time.sleep(10)
    client = ModbusClient(mate3_ip, mate3_modbus)
    logging.info(".. Make sure we are indeed connected to an Outback power system")
    reg    = sunspec_start_reg
    size   = getSunSpec(reg)
    if size is None:
        logging.info("We have failed to detect an Outback system. Exciting")
        client.close()
        exit()
except:
    client.close()
    EventLog("Error: CMS - Fail to connect to MATE")
    logging.info(".. Failed to connect to MATE3. Enable SUNSPEC and check port. Exciting")
    exit()
logging.info(".. Connected OK to an Outback system")

# scanning blocks
startReg = reg + size + 4
while True:
    reg = startReg
    check = 0
    for block in range(0, 30):
        blockResult = getBlock(reg)
        
        if "Outback block" in blockResult['DID']:
            logging.info(".. Detect a Outback Block")
            if OutbackBlock_flag == 1: OutbackBlock()
            
        if "Outback System Control Block" in blockResult['DID']:
            logging.info(".. Detect a Outback System Control Block")
            if OutbackSystemControlBlock_flag == 1: OutbackSystemControlBlock()
            
        if "Radian Inverter Configuration Block" in blockResult['DID']: 
            logging.info(".. Detect a FXR inverter")
            RadianInverterConfigurationBlock()

        if "FLEXnet-DC Real Time Block" in blockResult['DID']: FLEXnetDCRealTimeBlock()
        
        if "End of SunSpec" not in blockResult['DID']:
            reg = reg + blockResult['size'] + 2
        else:
            break
    write=0 
    if write == 0:
        if loop >0:
            logging.info(".. verification completed in " + str(loop) +" loop: all good")
            EventLog("Info : CMS - update completed")
        client.close()
        logging.info(".. Mate connection closed ")
        logging.info("Exiting ")
        break           # DPO - remark it if continuous loop needed
    else:
        logging.info(".. verification loop " +  str(loop))
        time.sleep(1)
        loop = loop + 1 # only for reporting purpose
    
