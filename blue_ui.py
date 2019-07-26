import json
from pprint import pprint
from flask import Flask
from flask import render_template
from flask import abort
import time
from datetime import datetime
import sqlite3

debug = True
app = Flask(__name__)

def populateFieldWithEmpty(theDict,theField,theValue=""):
    if(theField not in theDict.keys()):
        theDict[theField] = theValue

    return theDict

@app.route('/getDeviceInfo/<uuid>')
def getDeviceInfo(uuid):
    deviceDetails = None
    if(uuid is not None):
        try:
            
            if(debug == True):
                db = sqlite3.connect('file:blue_hydra.db?mode=ro', uri=True)
            else:
                db = sqlite3.connect('file:/home/pi/blue_hydra/bin/blue_hydra.db?mode=ro', uri=True)
            db.row_factory = dict_factory
            cursor = db.cursor()

            deviceDetailsSQL = "SELECT * from blue_hydra_devices WHERE UUID = ?"
            cursor.execute(deviceDetailsSQL,(uuid,))
            deviceDetails = cursor.fetchone()
            print(deviceDetails)

            db.close()
            #print(returnTotals)

        except Exception as e:
            print(e)
            pass

    if (deviceDetails is None):
        abort(418)

    return(json.dumps(deviceDetails))

@app.route('/getTotals')
def getTotals():
    returnTotals = {}
    try:
        if(debug == True):
            db = sqlite3.connect('file:blue_hydra.db?mode=ro', uri=True)
        else:
            db = sqlite3.connect('file:/home/pi/blue_hydra/bin/blue_hydra.db?mode=ro', uri=True)
        
        
        cursor = db.cursor()

        totalUniqueSQL = "SELECT COUNT( DISTINCT UUID) from blue_hydra_devices WHERE vendor != 'N/A - Random Address'"
        cursor.execute(totalUniqueSQL)
        numTotalUnique = cursor.fetchone()

        
        totalUniqueTodaySQL = "SELECT COUNT( DISTINCT UUID) from blue_hydra_devices WHERE last_seen BETWEEN strftime('%s','now','start of day') AND strftime('%s','now','localtime') AND vendor != 'N/A - Random Address'"
        cursor.execute(totalUniqueTodaySQL)
        numTotalDayUnique = cursor.fetchone()

        
        db.close()

        returnTotals["totals"] = numTotalUnique
        returnTotals["dayTotals"] = numTotalDayUnique
        #print(returnTotals)

    except Exception as e:
        print(e)
        pass

    if (len(returnTotals) == 0):
        abort(418)

    return(json.dumps(returnTotals))

def fetchSeen(elem):
    return elem["seen"]


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@app.route('/fetchAll')
def fetchAllDevices():
    devices = []
    try:
        if(debug == True):
            db = sqlite3.connect('file:blue_hydra.db?mode=ro', uri=True)
        else:
            db = sqlite3.connect('file:/home/pi/blue_hydra/bin/blue_hydra.db?mode=ro', uri=True)
        db.row_factory = dict_factory
        cursor = db.cursor()
        allDevicesSQL = "SELECT uuid,last_seen,lmp_version,le_address_type, address, classic_rssi, le_rssi, name, manufacturer,company,company_type, vendor, classic_minor_class from blue_hydra_devices WHERE vendor != 'N/A - Random Address'"
        cursor.execute(allDevicesSQL)
        db_devices = cursor.fetchall()
        
        for d in db_devices:
            #print(d)
            thisDevice = {}
            device_mode = ""
            uuid = d["uuid"]
            last_seen = d["last_seen"]
            vers = d["lmp_version"]
            address = d["address"]
            address_type = d["le_address_type"]
            rssi_cl = d["classic_rssi"]
            rssi_le = d["le_rssi"]
            name = d["name"]
            comp = d["company"]
            comp_type = d["company_type"]
            manufacturer = d["manufacturer"]
            vendor = d["vendor"]
            d_type = d["classic_minor_class"]

            thisDevice["address"] = address
            thisDevice["type"] = d_type
            thisDevice["name"] = name
            
            
            #last_seen
            #timeNow = time.time()
            #timeDev = last_seen
            #thisDevice["seen"] = int(timeNow - timeDev)
            
            #last_seen 2?
            timeDev = last_seen
            #thisDevice["seen"] = time.ctime(int(timeDev))
            niceTime = datetime.fromtimestamp(timeDev)
            thisDevice["seen"] = datetime.utcfromtimestamp(timeDev).strftime('%Y-%m-%d %H:%M:%S')




            # Figure out what type of BT it is
            

            if(rssi_le is None and rssi_cl is not None):
                #Its classic?
                device_mode = "classic"
                if(vers is not None and vers[0:4] not in ["0x00","0xff","0xFF"]):
                    vers = "CL" + vers.split(" ")[1]
                else:
                    vers = "CL/BR"
            elif (rssi_cl is None and rssi_le is not None):
                device_mode = "le"
                if(vers is not None and vers[0:4] not in ["0x00","0xff","0xFF"]):
                    vers = "LE" + vers.split(" ")[1]
                else:
                    vers = "BTLE"
            elif(rssi_le is None and rssi_cl is None): # we have no rssi?
                device_mode = "classic"
                if(vers is not None and vers[0:4] not in ["0x00","0xff","0xFF"]):
                    vers = "CL" + vers.split(" ")[1]
                else:
                    vers = "CL/BR"
            else:
                vers = "Unknown"

            thisDevice["vers"] = vers
            rssi_levels = None
            
            if(device_mode == "classic" and rssi_cl is not None):
                rssi_levels = json.loads(rssi_cl)
            elif(device_mode == "le"  and rssi_le is not None):
                rssi_levels = json.loads(rssi_le)
           
            lowest_rssi = "0 dBm"
            if(rssi_levels is not None):
                for r in rssi_levels:
                    if (lowest_rssi > r['rssi']):
                        lowest_rssi = r['rssi']

            if(lowest_rssi == "0 dBm"):
                lowest_rssi = "(unknown)"

            thisDevice["rssi"] = lowest_rssi

            #Figure out the manuf
            manuf = "unknown"
            if(device_mode == "classic" or address_type == "public"):
                manuf = vendor
            else:
                if(comp is not None and not comp.lower().startswith("unknown")):
                    manuf = comp
                elif(comp_type is not None and not comp_type.lower().startswith("not assigned")):
                    manuf = comp_type
                elif(manufacturer is not None and not manufacturer.lower().startswith("65535")):
                    manuf = manufacturer
            
            thisDevice["manuf"] = manuf
            thisDevice["uuid"] = uuid
            devices.append(thisDevice)
            

            
            
        db.close()
        
        
        
        #print(returnTotals)

    except Exception as e:
        print(e)
        pass

    if (len(devices) == 0):
        abort(418)

    return(json.dumps({"data":devices}))

@app.route('/parsefile')
def parseJSon(name=None):
    devices = []
    try:
        data = None
        if(debug == True):
            filename = "example.json"
        else:
            filename = "/dev/shm/blue_hydra.json"
        
        with open(filename) as f:
            data = json.load(f)

        #format for datatables

        if(data):
            for uniqueDevice in data:
                '''
                {"address": "58:7A:62:55:09:F1", "company": "Procter & Gamble ", "created": 1563792831, "lap": "55:09:F1", "last_seen": 1563792954, "le_company_data": "03210c022001290704a404", "manuf": "TexasIns", "name": "Oral-B Toothbrush", "rssi": "-88 ", "uuid": "e6f3079d", "vers": "BTLE"}
                '''
                #set the time
                timeNow = time.time()
                timeDev = data[uniqueDevice]["last_seen"]
                data[uniqueDevice]["seen"] = int(timeNow - timeDev)

                #set the name to "" if its not there
                data[uniqueDevice] = populateFieldWithEmpty(data[uniqueDevice],"name")
                data[uniqueDevice] = populateFieldWithEmpty(data[uniqueDevice],"rssi")
                data[uniqueDevice] = populateFieldWithEmpty(data[uniqueDevice],"manuf")
                data[uniqueDevice] = populateFieldWithEmpty(data[uniqueDevice],"type")



                #print(json.dumps(data[uniqueDevice]))
                devices.append(data[uniqueDevice])
    except Exception as e:
        print(e)
        pass
    if (len(devices) == 0):
        
        abort(418)
    devices = sorted(devices, key=fetchSeen)
    return(json.dumps({"data":devices}))


@app.route('/history')
def history(name=None):
    return render_template('./blunicorn/history.html', name=name)

@app.route('/')
@app.route('/index.html')
def index(name=None):
    return render_template('./blunicorn/index.html', name=name)

if __name__ == '__main__':
    app.debug = debug
    app.run(host = '0.0.0.0',port=80)
