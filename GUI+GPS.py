import time
import sqlite3
from datetime import datetime
import random
from Adafruit_IO import Client
from tkinter import Tk,BOTH
from tkinter.ttk import Frame, Label, Style,Entry,Button
from tkinter import *
import RPi.GPIO as GPIO
import geopy.distance
import random
import serial


class Solex(Frame):
    def __init__(self):
       super().__init__()
       self.output=0
       self.lst = [1,2,3,4]
       self.speed = 0
       self.SOC = 0
       self.charind = "Charging"
       self.teamcom = "Go"
       self.coordsnew = 0
       self.coordsold = 0
       self.power_key = 6
       self.ser = serial.Serial('/dev/ttyS0',115200)
       self.ser.flushInput()
       self.timenew = 0
       self.timeold = 0
       self.power_key = 6
       self.rec_buff = ''
       self.rec_buff2 = ''
       self.time_count = 0
       self.cumulative_distance = 0
       self.velocity = 0
       self.prev_velocity = 0
       self.acceleration = 0
       
       title_label=Label(self.master,text='Solex Interface:',font='Times 25 bold')
       title_label.place(x=100,y=70,anchor='w')
       reg0_label=Label(self.master,text='Speed [Kts]:',font='Times 11')
       reg0_label.place(x=100,y=110,anchor='w')
       self.t1=Entry(bd=2,width="10")
       self.t1.place(x=330,y=100)
       
       reg1_label=Label(self.master,text='Battery SOC [%]:',font='Times 11')
       reg1_label.place(x=100,y=130,anchor='w')
       self.t2=Entry(bd=2,width="10")
       self.t2.place(x=330,y=120)
       
       reg2_label=Label(self.master,text='Charging Indicator:',font='Times 11')
       reg2_label.place(x=100,y=150,anchor='w')
       self.t3=Entry(bd=2,width="10")
       self.t3.place(x=330,y=140)
       
       reg3_label=Label(self.master,text='Team Communications:',font='Times 11')
       reg3_label.place(x=100,y=170,anchor='w')
       self.t4=Entry(bd=2,width="10")
       self.t4.place(x=330,y=160)
       
       self.iniUI()
       self.master.after(1000,self.GetData)  
       self.master.after(1000,self.log_time)
       self.master.after(10000,self.SendData)
    
    def iniUI(self):
        self.master.title("Solex Interface")
        self.pack(fill=BOTH,expand=1)
        Style().configure("TFrame",background="white")
       
    def send_at(self,command,back,timeout):
        rec_buff = ''
        self.ser.write((command+'\r\n').encode())
        time.sleep(timeout)
        if self.ser.inWaiting():
            time.sleep(1)
            rec_buff = self.ser.read(self.ser.inWaiting())
        if rec_buff != '':
            if back not in rec_buff.decode():
                print(self.command + ' ERROR')
                print(self.command + ' self.back:\t' + rec_buff.decode())
                return 0
            else:

                global GPSDATA

                GPSDATA = str(rec_buff.decode())
                print(GPSDATA)
                Cleaned = GPSDATA[25:]

                Lat = Cleaned[:2]
                SmallLat = Cleaned[2:11]
                NorthOrSouth = Cleaned[12]
                Long = Cleaned[14:17]
                SmallLong = Cleaned[17:26]
                EastOrWest = Cleaned[27]
                FinalLat = float(Lat) + (float(SmallLat)/60)
                FinalLong = float(Long) + (float(SmallLong)/60)         
                if NorthOrSouth == 'S': FinalLat = -FinalLat
                if EastOrWest == 'W': FinalLong = -FinalLong
                self.Lat = FinalLat
                self.Lon = FinalLong
                return FinalLat,FinalLong
                return 1
        else:
            print('GPS is not ready')
            return 0
    
    


    def power_on(self):
        print('SIM7600X is starting:')
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.power_key,GPIO.OUT)
        time.sleep(0.1)
        GPIO.output(self.power_key,GPIO.HIGH)
        time.sleep(1)
        GPIO.output(self.power_key,GPIO.LOW)
        time.sleep(1)
        self.ser.flushInput()
        print('SIM7600X is ready')
        self.timeold = datetime.now()
        print(self.timeold)
        self.coordsold = Solex.send_at(self,'AT+CGPSINFO','+CGPSINFO: ',1)
        print(self.coordsold)
    
        
        
    def GetData(self):
        self.coordsnew = Solex.send_at(self,'AT+CGPSINFO','+CGPSINFO: ',1)
        print(self.coordsnew)
        self.timenew = datetime.now()
                
        time_difference = self.timeold - self.timenew

        seconds = time_difference.total_seconds()

        distance_m = geopy.distance.geodesic(self.coordsnew, self.coordsold).m
        self.cumulative_distance += round(distance_m,1)
        self.velocity = round((distance_m / seconds),2)
        self.velocity = abs(self.velocity*1.94384)

        acceleration = round((self.velocity - self.prev_velocity)/seconds,2)
        self.prev_velocity = self.velocity

        print("Velocity:", self.velocity, "kts")
        print("Distance:", distance_m)
        print("Cumulative distance:", self.cumulative_distance, "m")
        print("Acceleration:", self.acceleration, "m/s^2")
                
    
        self.t1.delete(0,'end')
        self.t2.delete(0,'end')
        self.t3.delete(0,'end')
        self.t4.delete(0,'end')
        self.t1.insert(END,str(round(self.velocity,2)))
        self.t2.insert(END,str(round(self.Lon,2)))
        self.t3.insert(END,self.charind)
        self.t4.insert(END,self.teamcom)
        
        
        
        self.coordsold = self.coordsnew
        self.prev_velocity = self.velocity
        self.master.after(1000,self.GetData)
        
    def log_time(self):
        now=datetime.now()
        self.reg_time=now.strftime('%H:%M:%S')
        self.reg_date=now.strftime('%d-%m-%Y')
        self.master.after(1000,self.log_time)
        
    def database_log(self,count):
        conn=sqlite3.connect('SolexData.db')
        c=conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS Solar_inv
                  (Date DATETIME,
                   Time DATETIME,
                   Register_name INTEGER,
                   Description TEXT,
                   Reading REAL,
                   Unit TEXT)""")
        c.execute('INSERT INTO Solar_inv VALUES(?,?,?,?,?,?)',(self.reg_date,self.reg_time,self.reg_num,self.reg_description[count],self.output,self.units[count]))
        conn.commit()
        

    def SendData(self):
        ADAFRUIT_IO_USERNAME = "Solex123"
        ADAFRUIT_IO_KEY = "aio_ffkI22dzKimc1gcEUMz67oOKS4Fz"
        aio=Client(ADAFRUIT_IO_USERNAME,ADAFRUIT_IO_KEY)
        aio.send("solex-velocity",self.velocity)
        self.teamcom = aio.receive("solex-team-message")
        self.teamcom = self.teamcom.value
        print(self.teamcom)
        #aio.send("solex-soc",self.SOC)
        #aio.send("solex-charging-indicator",self.charind)
        self.master.after(10000,self.SendData)
        
def main():
    root=Tk()
    root.geometry("800x800")
    #root.attributes('-fullscreen',True)
    app=Solex()
    app.power_on()
    root.mainloop()
    
 
                         
if __name__=='__main__':
    main()
    
    
    
    
    
    
    
    
