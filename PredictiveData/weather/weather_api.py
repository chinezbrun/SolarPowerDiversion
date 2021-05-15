import requests
import json
from datetime import datetime
import mysql.connector as mariadb
from configparser import ConfigParser
import sys, os

script_ver = "0.5.0_20210515"
print("script ver  :" + script_ver)

curent_date_time  = datetime.now()
curent_month      = curent_date_time.strftime("%B")
#print(curent_month)
#print(curent_date_time.hour)                   # DPO debug only
#print (curent_date_time.hour)                  # DPO debug only
#print (curent_date_time.day)                   # DPO debug only

pathname          = os.path.dirname(sys.argv[0])
working_dir       = os.path.abspath(pathname) 
print ("working directory: " +  working_dir)

# import configuartion variables       
config            = ConfigParser()
config.read(working_dir +'/weather_api.cfg')
OutputPath        = config.get('Connectivity', 'OutputPath')
host              = config.get('Connectivity', 'host')
db_port           = config.get('Connectivity', 'db_port')
user              = config.get('Connectivity', 'user')
password          = config.get('Connectivity', 'password')
database          = config.get('Connectivity', 'database')
weather_api_token = config.get('Connectivity', 'weather_api_token')
smart_weather     = config.get('smart_weather', 'smart_weather')
clouds_limit_0    = int(config.get('smart_weather', 'clouds_limit_0'))
clouds_limit_1    = int(config.get('smart_weather', 'clouds_limit_1'))
clouds_limit_2    = int(config.get('smart_weather', 'clouds_limit_2'))

mydb              = mariadb.connect(host=host,port=db_port,user=user,password=password,database=database)
r                 = requests.get(weather_api_token)
weather           = r.json()
dinamic_data      = json.load(open(OutputPath +'/dinamic_data.json'))
flextime_data     = json.load(open(working_dir +'/flextime_data.json'))
print ("Output directory: " +  OutputPath)

for n in range(9):
    ID            = weather ["list"][n]["weather"][0]["id"]
    main          = weather ["list"][n]["weather"][0]["main"]
    description   = weather ["list"][n]["weather"][0]["description"]
    clouds        = weather ["list"][n]["clouds"]["all"]
    stamp         = weather ["list"][n]["dt_txt"]
    
    sql="SELECT date,ID,main,description,clouds from weather.forecast where date = '" + stamp +"'"
    mycursor = mydb.cursor()
    mycursor.execute(sql)
    myresult = mycursor.fetchall()
    
    if not myresult:
        val = (stamp,ID,main,description,clouds)
        sql ="INSERT INTO weather.forecast (date,ID,main,description,clouds) VALUES (%s,%s,%s,%s,%s)"
        print ("...recorded :" + str(stamp))
    else:
        val = (ID,main,description,clouds,stamp)
        sql ="UPDATE weather.forecast SET ID=%s,main=%s,description=%s,clouds=%s WHERE date= %s"
        print ("...updated  :" + str(stamp))

    mycursor = mydb.cursor()
    mycursor.execute(sql, val)
    mydb.commit()   

# summary table update based on time of the day
if curent_date_time.hour > 0 and curent_date_time.hour < 12:
    sql="SELECT avg(clouds), date, avg(ID) from forecast where date(date) = date(now()) and hour(date) > 6 and hour(date) < 18"
else:
    sql="SELECT avg(clouds), date, avg(ID) from forecast where date(date) > date(now()) and hour(date) > 6 and hour(date) < 18"
   
mycursor = mydb.cursor()
mycursor.execute(sql)
myresult = mycursor.fetchall()

for x in myresult:
    daily_clouds = int(x[0])
    date         = x[1]
    avg_ID       = int(x[2])

description                   = "others"
if avg_ID == 800: description = "clear sky"
if avg_ID == 801: description = "few clouds: 11-25%"
if avg_ID == 802: description = "scattered clouds: 25-50%"
if avg_ID == 803: description = "broken clouds: 51-84%"
if avg_ID == 804: description = "overcast clouds: 85-100%"

if date:                            #DPO: run update summary only if results are available  
    date=date.strftime("%Y-%m-%d")
    sql="SELECT daily_clouds from weather.summary where date(date) = '" + date + "'"
    mycursor = mydb.cursor()
    mycursor.execute(sql)
    myresult = mycursor.fetchall()

    if not myresult:
        val = (date,avg_ID,description,daily_clouds)
        sql ="INSERT INTO weather.summary (date,ID,description,daily_clouds) VALUES (%s,%s,%s,%s)"
        print ("...summary insert :",date, "clouds:",daily_clouds,"%","ID:",avg_ID,description)
    else:
        val = (avg_ID,description,daily_clouds, date)
        sql ="UPDATE weather.summary SET ID = %s, description = %s, daily_clouds = %s WHERE date= %s"
        #print ("...summary updated  :" + str(date) + " Avg :" + str(daily_clouds) + " " + str(avg_ID))
        print ("...summary updated :",date, "clouds:", daily_clouds,"%","ID:",avg_ID,description)
        
    mycursor = mydb.cursor()
    mycursor.execute(sql, val)
    mydb.commit()

# smart weather module
if smart_weather == "true":
    print("   Weather module active. Checking forcast")
    curent_month = curent_date_time.strftime("%B")
    if curent_date_time.hour > 18:
        sql="SELECT daily_clouds,date, ID, description from summary where date = date(now() + INTERVAL 1 DAY)"
    else:
        sql="SELECT daily_clouds,date, ID, description from summary where date = date(now())"
    
    mycursor = mydb.cursor()
    mycursor.execute(sql)
    myresult = mycursor.fetchall()
    
    for x in myresult:
        daily_clouds = int(x[0])
        date         = x[1]
        avg_ID       = int(x[2])
        description  = x[3]
    
    date=date.strftime("%Y-%m-%d")

    if daily_clouds <= clouds_limit_0:
        print("...daily_clouds:",daily_clouds,"% - normal limit")
        level = 0
    if daily_clouds > clouds_limit_0 and daily_clouds <= clouds_limit_1:
        print("...daily_clouds:",daily_clouds,"% - above limit 1")
        level = 1
    if daily_clouds > clouds_limit_1 and daily_clouds <= clouds_limit_2:
        print("...daily_clouds:",daily_clouds,"% - above limit 2")
        level = 2
    if daily_clouds > clouds_limit_2:
        print("...daily_clouds:",daily_clouds,"% - above limit 3")
        level = 3
    
    print("...curent month:",curent_month)
    dinamic_data["time_posted"]                                              = str(curent_date_time.strftime("%Y-%m-%d %H:%M:%S"))    
    dinamic_data["time_taken"]                                               = ""
    dinamic_data["OutbackBlock"]["OutbackBlock_flag"]                        = 1    
    dinamic_data["OutbackBlock"]["outback_schedule"]["sched_1_ac_mode"]      = flextime_data["flextime"][curent_month][level]["sched_1_ac_mode"]
    dinamic_data["OutbackBlock"]["outback_schedule"]["sched_1_ac_mode_hour"] = flextime_data["flextime"][curent_month][level]["sched_1_ac_mode_hour"]
    dinamic_data["OutbackBlock"]["outback_schedule"]["sched_2_ac_mode"]      = flextime_data["flextime"][curent_month][level]["sched_2_ac_mode"]
    dinamic_data["OutbackBlock"]["outback_schedule"]["sched_2_ac_mode_hour"] = flextime_data["flextime"][curent_month][level]["sched_2_ac_mode_hour"]
    dinamic_data["OutbackBlock"]["outback_schedule"]["sched_3_ac_mode"]      = flextime_data["flextime"][curent_month][level]["sched_3_ac_mode"]
    dinamic_data["OutbackBlock"]["outback_schedule"]["sched_3_ac_mode_hour"] = flextime_data["flextime"][curent_month][level]["sched_3_ac_mode_hour"]
    dinamic_data["weather"]["date"]                                          = date
    dinamic_data["weather"]["ID"]                                            = avg_ID
    dinamic_data["weather"]["description"]                                   = description
    dinamic_data["weather"]["cloud_coverage"]                                = daily_clouds

    mycursor.close()
    mydb.close()
    print(".. MariaDB closed")
else:
    print("   Weather module inactive")
    mycursor.close()
    mydb.close()
    print(".. MariaDB closed")

#print ("... daily_clouds: "date, daily_clouds, avg_ID, description)

with open(OutputPath +'/dinamic_data.json', 'w') as outfile:
    json.dump(dinamic_data, outfile, indent=1)
with open(working_dir +'/weather.json', 'w') as outfile:
    json.dump(weather, outfile, indent=1)