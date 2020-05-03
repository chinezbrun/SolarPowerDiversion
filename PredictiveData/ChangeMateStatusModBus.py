import logging
import time
import mysql.connector as mariadb
from datetime import datetime
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from configparser import ConfigParser
import sys, os

script_ver = "0.5.1_20200503"
print ("script version   : "+ script_ver)

pathname          = os.path.dirname(sys.argv[0])        
fullpathname      = os.path.abspath(pathname)+'/ChangeMateStatusModBus.cfg' 

print ("working directory: " +  str(os.path.abspath(pathname)))

       
config            = ConfigParser()
config.read(fullpathname)

#MATE3 connection
mate3_ip          = config.get('MATE3 connection', 'mate3_ip')
mate3_modbus      = config.get('MATE3 connection', 'mate3_modbus')
sunspec_start_reg = 40000

# SQL Maria DB connection
SQL_active        = config.get('Maria DB connection', 'SQL_active')                             
host              = config.get('Maria DB connection', 'host')
db_port           = config.get('Maria DB connection', 'db_port')
user              = config.get('Maria DB connection', 'user')
password          = config.get('Maria DB connection', 'password')
database          = config.get('Maria DB connection', 'database')
database1         = config.get('Maria DB connection', 'database1')
ServerPath        = config.get('WebServer path', 'ServerPath')   
print("server path      : " + ServerPath)

# Dinamic Data
smart_charge               = config.get('Dinamic data', 'smart_charge')
soc_ok                     = int(config.get('Dinamic data', 'soc_ok'))
soc_min                    = int(config.get('Dinamic data', 'soc_min'))
soc_shdown                 = int(config.get('Dinamic data', 'soc_shdown'))
charger_mode_sc            = config.get('Dinamic data', 'charger_mode_sc')
smart_scheduling           = config.get('Dinamic data', 'smart_scheduling')
smart_weather              = config.get('Dinamic data', 'smart_weather')
clouds_limit_0             = int(config.get('Dinamic data', 'clouds_limit_0'))
clouds_limit_1             = int(config.get('Dinamic data', 'clouds_limit_1'))
clouds_limit_2             = int(config.get('Dinamic data', 'clouds_limit_2'))
OutBack_Sched_1_AC_Mode_WT = int(config.get('Dinamic data', 'OutBack_Sched_1_AC_Mode_WT'))
OutBack_Sched_2_AC_Mode_WT = int(config.get('Dinamic data', 'OutBack_Sched_2_AC_Mode_WT'))
OutBack_Sched_3_AC_Mode_WT = int(config.get('Dinamic data', 'OutBack_Sched_3_AC_Mode_WT'))
ac_mode_sc                 = 'Minigrid'

loop                       = 0 # default - used to count no of verification loops till update complete
minigrid_pos               = 0 # default - no weather inpact
backup_pos                 = 0 # default - no weather inpact
daily_clouds               = 0 # default - clear sky
charger_flag               = 0 # default - no update if is not required by smart charge or external python arguments
ac_mode_flag               = 0 # default - no update if is not required by external python arguments

# ACmode_list is used to convert numbers in readable name 
# in registry there the modes are coded like below list
ACmode_list = [
    "Generator",     # 0
    "Support",       # 1
    "GriedTied",     # 2
    "UPS",           # 3
    "Backup",        # 4
    "MiniGrid",      # 5
    "GridZero",      # 6
    "Disabled"]      # 7

# variable to keep start hour of inverter modes based on month and weather evolution
# first position  is with no weather impact       - clear sky
# second position is weather corrected for clouds - level 1
# third position  is weather corrected for clouds - level 2

minigrid_start = [
    [3,10,10],       # January
    [2,10,10],       # February
    [2,10,10],       # March
    [1,8,10],        # April
    [0,8,10],        # May
    [23,6,8],        # June
    [23,6,8],        # July
    [0,8,8],         # August
    [1,8,10],        # September
    [2,10,10],       # October
    [2,10,10],       # November
    [3,10,10]]       # December

backup_start = [
    [14,13,12],      # January
    [15,14,12],      # February
    [16,15,12],      # March
    [17,16,13],      # April
    [18,17,13],      # May
    [19,18,15],      # June
    [19,18,15],      # July
    [18,17,15],      # August
    [17,16,13],      # September
    [16,15,13],      # October
    [15,14,12],      # November
    [14,13,12]]      # December

print("variables initialization completed")

#Check external python arguments - this has priority in dinamic data and will overwrite init values
if len(sys.argv) > 1:
    if sys.argv[1] == 'on' or sys.argv[1] == 'off':
        charger_mode_sc        = sys.argv[1] # new value for chager_mode received via MQTT or other programs
        charger_flag           = 1
        smart_charge           = "false"     # set to false in order to prevent conflicts 
        ac_mode_flag           = 0           # set to zero  in order to prevent conflicts
        print("..'charger_mode_sc' was overwritten: ", charger_mode_sc)
    if sys.argv[1] in ACmode_list:
        ac_mode_sc             = sys.argv[1] # new value for AC mode received via MQTT or other programs
        ac_mode_flag           = 1           
        charger_flag           = 0           # set to zero  in order to prevent conflicts
        smart_charge           = "false"     # set to false in order to prevent conflicts
        smart_scheduling       = "false"     # set to false in order to prevent conflicts
        print("..'ac_mode_sc' was overwritten: ", ac_mode_sc)
        
# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%Y%m%d %H:%M:%S')
logging.getLogger(__name__)

now      = datetime.now()
curent_time = time.localtime()

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

# Subroutines
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
    #print(blocksize) # DPO debug
    return blocksize

def getBlock(basereg):
    #print(basereg) #DPO debug
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

#error log subroutine
def ErrorPrint (str) :
    try:
        with open(ServerPath + "/data/general_info.log","r") as file:
            save = file.read()
        with open(ServerPath + "/data/general_info.log","w") as file:
            file = open(ServerPath + "/data/general_info.log","a")
            file.write(now.strftime("%d/%m/%Y %H:%M:%S "))
            #file.write(str + "\r\n")
            file.write(str + "\n")
            print(str)
        with open(ServerPath + "/data/general_info.log","a") as file:
            file.write(save)
        return
    except OSError:
        print(str,"Error: CMS - Errorhandling block: double error")

print("------------------------------------------------")
print(" Weather module")
print("------------------------------------------------")

# smart weather module
if smart_weather == "true":
    logging.info("Weather module active. Checking forcast")
    try:
        mydb = mariadb.connect(host=host,port=db_port,user=user,password=password,database=database1)
        logging.info(".. MariaDB connected")
        if curent_time.tm_hour > 18:
            sql="SELECT daily_clouds from summary where date = date(now() + INTERVAL 1 DAY)"
        else:
            sql="SELECT daily_clouds from summary where date = date(now())"
        mycursor = mydb.cursor()
        mycursor.execute(sql)
        myresult = mycursor.fetchall()
        for x in myresult:
            daily_clouds=x[0]
            
        if daily_clouds <= clouds_limit_0:
            logging.info("... daily_clouds: " + str(daily_clouds) + "% - normal limit")
            ErrorPrint("Info : CMS - WT: clouds "+ str(daily_clouds) + "% - normal limit")
        if daily_clouds > clouds_limit_0 and daily_clouds <= clouds_limit_1:
            minigrid_pos = 1 # second position in the table 
            backup_pos   = 1 # second position in the table 
            logging.info("... daily_clouds: " + str(daily_clouds) + "% - above limit 1")
            ErrorPrint("Info : CMS - WT: clouds "+ str(daily_clouds) + "% - above limit 1")
        if daily_clouds > clouds_limit_1 and daily_clouds <= clouds_limit_2:
            minigrid_pos = 2 # second position in the table 
            backup_pos   = 2 # second position in the table 
            logging.info("... daily_clouds: " + str(daily_clouds) + "% - above limit 2")
            ErrorPrint("Info : CMS - WT: clouds "+ str(daily_clouds) + "% - above limit 2")
        if daily_clouds > clouds_limit_2:
            OutBack_Sched_1_AC_Mode_WT=4
            OutBack_Sched_2_AC_Mode_WT=4
            OutBack_Sched_3_AC_Mode_WT=65535
            logging.info("... daily_clouds: " + str(daily_clouds) + "% - above limit 3")
            ErrorPrint("Info : CMS - WT: clouds "+ str(daily_clouds) + "% - above limit 3")

        mycursor.close()
        mydb.close()
        logging.info(".. MariaDB closed")
    
    except:
        logging.info(".. MariaDB connection failed")
        ErrorPrint("Error: CMS - MariaDB connection failed")
    
print("------------------------------------------------")
print(" MATE3 ModBus Interface")
print("------------------------------------------------")

# Try to build the mate3 MODBUS connection
logging.info("Building MATE3 MODBUS connection")
# Mate3 connection
try:
    logging.info(".. waiting 10 seconds ")
    time.sleep(10)
    client = ModbusClient(mate3_ip, mate3_modbus)
    logging.info(".. Make sure we are indeed connected to an Outback power system")
    reg    = sunspec_start_reg
    size   = getSunSpec(reg)
    #print(reg) #DPO debug
    #print(size) #DPO debug
    if size is None:
        logging.info("We have failed to detect an Outback system. Exciting")
        exit()
except:
    client.close()
    ErrorPrint("Error: CMS - Fail to connect to MATE")
    logging.info(".. Failed to connect to MATE3. Enable SUNSPEC and check port. Exciting")
    exit()
logging.info(".. Connected OK to an Outback system")

#This is the main loop
#--------------------------------------------------------------

startReg = reg + size + 4
while True:
    reg = startReg
    for block in range(0, 30):
        blockResult = getBlock(reg)
        # Mate 3 block
        try:     
            if "Outback block" in blockResult['DID'] :
         
                # autosheduling 1
                # ...reading OutBack_Sched_1_AC_Mode registry
                response = client.read_holding_registers(reg + 409, 1)
                OutBack_Sched_1_AC_Mode = response.registers[0]

                if OutBack_Sched_1_AC_Mode == 65535:                                          # section is just for pretty display of the value
                    Sched_1_AC_Mode = ACmode_list[OutBack_Sched_1_AC_Mode-65528]
                else:
                    Sched_1_AC_Mode = ACmode_list[OutBack_Sched_1_AC_Mode]
                    
                if OutBack_Sched_1_AC_Mode_WT == 65535:                                        # section is just for pretty display of the value for Weather trigger Sched_1_AC_Mode_WT
                    Sched_1_AC_Mode_WT = ACmode_list[OutBack_Sched_1_AC_Mode_WT-65528]
                else:
                    Sched_1_AC_Mode_WT = ACmode_list[OutBack_Sched_1_AC_Mode_WT]                    
             
                response = client.read_holding_registers(reg + 410, 1)                
                OutBack_Sched_1_AC_Mode_Hour = response.registers[0]
                response = client.read_holding_registers(reg + 411, 1)
                OutBack_Sched_1_AC_Mode_Minute = response.registers[0]
                logging.info(".... Outback sch1 [h:mm] " + str(OutBack_Sched_1_AC_Mode_Hour) + ":" + str(OutBack_Sched_1_AC_Mode_Minute) + " " +str(Sched_1_AC_Mode))
                
                if smart_scheduling =="true" and OutBack_Sched_1_AC_Mode != OutBack_Sched_1_AC_Mode_WT:
                    rw = client.write_register(reg + 409, OutBack_Sched_1_AC_Mode_WT)
                    logging.info("......updating Mode 1 to: " + str(Sched_1_AC_Mode_WT))
                    ErrorPrint("Info : CMS - updating Mode 1 to: " + str(Sched_1_AC_Mode_WT))
                    Sched_1_check_flag = 1
                else:
                    Sched_1_check_flag = 0
                    
                if smart_scheduling =="true" and Sched_1_AC_Mode=="MiniGrid" and OutBack_Sched_1_AC_Mode_Hour != minigrid_start[now.month-1][minigrid_pos]:
                    rw = client.write_register(reg + 410, minigrid_start[now.month-1][minigrid_pos])
                    logging.info(".....updating start hour : " + str(minigrid_start[now.month-1][minigrid_pos]))
                    ErrorPrint("Info : CMS - updating MiniGrid start at " + str(minigrid_start[now.month-1][minigrid_pos]))
                    Sched_1_check_flag1 = 1
                else:
                    Sched_1_check_flag1 = 0

                # autosheduling 2
                response = client.read_holding_registers(reg + 412, 1)
                OutBack_Sched_2_AC_Mode = response.registers[0]
                
                if OutBack_Sched_2_AC_Mode == 65535:                                          # section is just for pretty display of the value
                    Sched_2_AC_Mode = ACmode_list[OutBack_Sched_2_AC_Mode-65528]
                else:
                    Sched_2_AC_Mode = ACmode_list[OutBack_Sched_2_AC_Mode]
                    
                if OutBack_Sched_2_AC_Mode_WT == 65535:                                        # section is just for pretty display of the value for Weather trigger Sched_2_AC_Mode_WT
                    Sched_2_AC_Mode_WT = ACmode_list[OutBack_Sched_2_AC_Mode_WT-65528]
                else:
                    Sched_2_AC_Mode_WT = ACmode_list[OutBack_Sched_2_AC_Mode_WT]                    
                
                response = client.read_holding_registers(reg + 413, 1)
                OutBack_Sched_2_AC_Mode_Hour = response.registers[0]
                response = client.read_holding_registers(reg + 414, 1)
                OutBack_Sched_2_AC_Mode_Minute = response.registers[0]
                logging.info(".... Outback sch2 [h:mm] " + str(OutBack_Sched_2_AC_Mode_Hour) + ":" + str(OutBack_Sched_2_AC_Mode_Minute) + " " +str(Sched_2_AC_Mode))
                
                if smart_scheduling =="true" and OutBack_Sched_2_AC_Mode != OutBack_Sched_2_AC_Mode_WT:
                    rw = client.write_register(reg + 412, OutBack_Sched_2_AC_Mode_WT)
                    logging.info("......updating Mode 2 to: " + str(Sched_2_AC_Mode_WT))
                    ErrorPrint("Info : CMS - updating Mode 2 to: " + str(Sched_2_AC_Mode_WT))
                    Sched_2_check_flag = 1
                else:
                    Sched_2_check_flag = 0

                if smart_scheduling =="true" and Sched_2_AC_Mode=="Backup" and OutBack_Sched_2_AC_Mode_Hour != backup_start[now.month-1][backup_pos]:
                    rw = client.write_register(reg + 413, backup_start[now.month-1][backup_pos])
                    logging.info(".....updating start hour : " + str(backup_start[now.month-1][backup_pos]))
                    ErrorPrint("Info : CMS - updating Backup   start at "+ str(backup_start[now.month-1][backup_pos]))
                    Sched_2_check_flag1 = 1
                else:
                    Sched_2_check_flag1 = 0                   
                
                # schedule 3 
                response = client.read_holding_registers(reg + 415, 1)
                OutBack_Sched_3_AC_Mode = response.registers[0]
                
                if OutBack_Sched_3_AC_Mode == 65535:                                          # section is just for pretty display of the value
                    Sched_3_AC_Mode = ACmode_list[OutBack_Sched_3_AC_Mode-65528]
                else:
                    Sched_3_AC_Mode = ACmode_list[OutBack_Sched_3_AC_Mode]
                    
                if OutBack_Sched_3_AC_Mode_WT == 65535:                                        # section is just for pretty display of the value for Weather trigger Sched_2_AC_Mode_WT
                    Sched_3_AC_Mode_WT = ACmode_list[OutBack_Sched_3_AC_Mode_WT-65528]
                else:
                    Sched_3_AC_Mode_WT = ACmode_list[OutBack_Sched_3_AC_Mode_WT]      

                response = client.read_holding_registers(reg + 416, 1)
                OutBack_Sched_3_AC_Mode_Hour = response.registers[0]
                response = client.read_holding_registers(reg + 417, 1)
                OutBack_Sched_3_AC_Mode_Minute = response.registers[0]
                logging.info(".... Outback sch3 [h:mm] " + str(OutBack_Sched_3_AC_Mode_Hour) + ":" + str(OutBack_Sched_3_AC_Mode_Minute) + " " +str(Sched_3_AC_Mode))
               
                if smart_scheduling =="true" and OutBack_Sched_3_AC_Mode != OutBack_Sched_3_AC_Mode_WT:
                    rw = client.write_register(reg + 415, OutBack_Sched_3_AC_Mode_WT)
                    logging.info("......updating Mode 3 to: " + str(Sched_3_AC_Mode_WT))
                    ErrorPrint("Info : CMS - updating Mode 3 to: " + str(Sched_3_AC_Mode_WT))
                    Sched_3_check_flag = 1
                else:
                    Sched_3_check_flag = 0
                    
                if smart_scheduling =="true" and Sched_3_AC_Mode=="Backup" and OutBack_Sched_3_AC_Mode_Hour != backup_start[now.month-1][backup_pos]:
                    rw = client.write_register(reg + 416, backup_start[now.month-1][backup_pos])
                    logging.info(".....updating start hour : " + str(backup_start[now.month-1][backup_pos]))
                    ErrorPrint("Info : CMS - updating Backup   start at "+ str(backup_start[now.month-1][backup_pos]))
                    Sched_3_check_flag1 = 1
                else:
                    Sched_3_check_flag1 = 0

# smart charging - SC
# read actual charge mode,SOC, compare with config values or the value modified by SOC routine below

            if "Radian Inverter Configuration Block" in blockResult['DID']:
                logging.info(".. Detect a FXR inverter") 
                response = client.read_holding_registers(reg + 24, 1)
                GSconfig_Charger_Operating_Mode = int(response.registers[0])
                logging.info(".... FXR Charger Mode " + str(GSconfig_Charger_Operating_Mode))
                charger_mode='None'
                if GSconfig_Charger_Operating_Mode == 0:   charger_mode ='off'
                if GSconfig_Charger_Operating_Mode == 1:   charger_mode ='on'
                
                if charger_flag == 1 and charger_mode != charger_mode_sc:
                    if charger_mode_sc == 'on':   GSconfig_Charger_Operating_Mode_SC = 1
                    if charger_mode_sc == 'off':  GSconfig_Charger_Operating_Mode_SC = 0
                    rw = client.write_register(reg + 24, GSconfig_Charger_Operating_Mode_SC)
                    charger_mode = GSconfig_Charger_Operating_Mode_SC
                    logging.info("......updating AC charging to: " + str(charger_mode_sc))
                    ErrorPrint("Info : CMS - updating AC charging to: " + str(charger_mode_sc))
                    charger_flag = 1
                else:    
                    charger_flag = 0
                
                response = client.read_holding_registers(reg + 26, 1)
                GSconfig_Grid_Input_Mode = int(response.registers[0])
                logging.info(".... FXR Input mode " + ACmode_list[GSconfig_Grid_Input_Mode])
                if ac_mode_flag == 1 and GSconfig_Grid_Input_Mode != ACmode_list.index(ac_mode_sc):                    
                    rw = client.write_register(reg + 26, ACmode_list.index(ac_mode_sc))
                    logging.info("......updating AC mode to: " + ac_mode_sc)
                    ErrorPrint("Info : CMS - updating AC mode to: " + ac_mode_sc)
                    ac_mode_flag = 1
                else:    
                    ac_mode_flag = 0

#FLEXNET Block
                
            if "FLEXnet-DC Real Time Block" in blockResult['DID']:
                logging.info(".. Detect a FLEXnet-DC Real Time Block")   
                response = client.read_holding_registers(reg + 27, 1)
                fn_state_of_charge = int(response.registers[0])
                logging.info(".... FN State of Charge " + str(fn_state_of_charge))
                
                if smart_charge =="true" and fn_state_of_charge <= soc_min and charger_mode == 'off':
                    charger_mode_sc = 'on'
                    logging.info("......SOC below min limit " + str(fn_state_of_charge))
                    ErrorPrint("Info : CMS - SC: SOC " + str(fn_state_of_charge) + "% - below min limit")
                    charger_flag = 1
                elif smart_charge =="true" and fn_state_of_charge >= soc_ok and charger_mode == 'on':
                    charger_mode_sc = 'off'
                    logging.info("......SOC reached safe limit " + str(fn_state_of_charge))
                    ErrorPrint("Info : CMS - SC: SOC " + str(fn_state_of_charge) + "% - safe limit")
                    charger_flag = 1

        except:
            ErrorPrint("Error: CMS - unknown error in main block") 

        if "End of SunSpec" not in blockResult['DID']:
            reg = reg + blockResult['size'] + 2
        else:
            #client.close()
            #logging.info(".. Mate connection closed ")
            break

    if Sched_1_check_flag == 0 and Sched_1_check_flag1 == 0 and Sched_2_check_flag == 0 and Sched_2_check_flag1 ==0 and \
       Sched_3_check_flag == 0 and Sched_3_check_flag1 == 0 and charger_flag == 0 and ac_mode_flag == 0:
        if loop >0:
            logging.info(".. verification completed in " + str(loop) +" loop: all good")
            ErrorPrint("Info : CMS - update completed")
        client.close()
        logging.info(".. Mate connection closed ")
        logging.info("Exiting ")
        break           # DPO - remark it if continuous loop needed
    else:
        logging.info(".. verification loop " +  str(loop))
        time.sleep(1)
        loop = loop + 1 # only for reporting purpose
    
