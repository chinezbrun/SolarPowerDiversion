import requests
import json
import pprint                       # DPO debug - doar pentru a vizualiza JSON - nu este mandatory
import mysql.connector as mariadb

script_ver = "0.2.20191012"
print("script ver  :" + script_ver)

host       ="192.168.0.100"
db_port    ="3307"
user       ="arduino" 
password   ='arduinotest'
database   ='weather'

mydb       = mariadb.connect(host=host,port=db_port,user=user,password=password,database=database)
r          = requests.get('http://api.openweathermap.org/data/2.5/forecast?id=683506&APPID=2ab7224dd023269296389b449fd32057')
data       = r.json()
#pprint.pprint(data)                 # DPO debug - doar pentru a vizualiza JSON - nu este mandatory

for n in range(9):
    ID                 = data ["list"][n]["weather"][0]["id"]
    main               = data ["list"][n]["weather"][0]["main"]
    description        = data ["list"][n]["weather"][0]["description"]
    clouds             = data ["list"][n]["clouds"]["all"]
    stamp              = data ["list"][n]["dt_txt"]
    
    #print("------------------------------------------")
    #print ("ID           : " + str(ID))
    #print ("stamp        : " + str(stamp))
    #print ("general      : " + str(main))
    #print ("descriere    : " + str(description))
    #print ("nori         : " + str(clouds) + "%")
    #print ("avg nori     : " + str(avg_clouds) +"%")
    #print ("...")

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

# summary table update
sql="SELECT avg(clouds), date from forecast where date > now() and hour(date) > 3 and hour(date) < 21"
mycursor = mydb.cursor()
mycursor.execute(sql)
myresult = mycursor.fetchall()

for x in myresult:
    avg_clouds =x[0]
    date=x[1]
    
date=date.strftime("%Y-%m-%d")

sql="SELECT daily_clouds from weather.summary where date(date) = '" + date + "'"
mycursor = mydb.cursor()
mycursor.execute(sql)
myresult = mycursor.fetchall()

if not myresult:
    val = (date,avg_clouds)
    sql ="INSERT INTO weather.summary (date,daily_clouds) VALUES (%s,%s)"
    print ("...summary insert :" + str(date))
else:
    val = (avg_clouds, date)
    sql ="UPDATE weather.summary SET daily_clouds = %s WHERE date= %s"
    print ("...summary updated  :" + str(date))

mycursor = mydb.cursor()
mycursor.execute(sql, val)
mydb.commit()

mycursor.close()
mydb.close()

#with open('//192.168.0.100/web/MonitorMate_mod/Weather/weather.json', 'w') as outfile:      #from laptop
with open('weather.json', 'w') as outfile:
    json.dump(data, outfile)