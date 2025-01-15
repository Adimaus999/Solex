import time
import sqlite3
from datetime import datetime
import random
from Adafruit_IO import Client
from tkinter import Tk,BOTH
from tkinter.ttk import Frame, Label, Style,Entry,Button
from tkinter import *
import can
import os
import random
        
        
    

class Solex(Frame):
    def __init__(self):
        super().__init__()
       
        os.system('sudo ip link set up can0 type can bitrate 250000')#
        os.system("sudo ifconfig can0 txqueuelen 1000")
        time.sleep(0.1)
        try:
            self.can_int=can.interface.Bus(channel='can0', bustype='socketcan')
        except OSError:
            print('Cannot find CAN Board')
        pass
        self.BatterySOC = 0
        self.BatteryPower = 0
        self.BatteryVoltage = 0
        self.BatteryCurrent = 0
        self.CurBit1 = 0
        self.CurBit2 = 0
        self.CurBit3 = 0
        self.CurBit4 = 0
       
        title_label=Label(self.master,text='Solex Interface:',font='Times 48 bold')
        title_label.place(x=100,y=70,anchor='w')
        reg0_label=Label(self.master,text='Battery SOC [%]:',font='Times 32')
        reg0_label.place(x=100,y=120,anchor='w')
        self.t1=Entry(bd=2,width="10")
        self.t1.place(x=330,y=100)

        reg1_label=Label(self.master,text='Battery Power [W]:',font='Times 32')
        reg1_label.place(x=100,y=180,anchor='w')
        self.t2=Entry(bd=2,width="10")
        self.t2.place(x=330,y=120)

        reg2_label=Label(self.master,text='Battery Voltage [V]:',font='Times 32')
        reg2_label.place(x=100,y=230,anchor='w')
        self.t3=Entry(bd=2,width="10")
        self.t3.place(x=330,y=140)

        reg3_label=Label(self.master,text='Battery Current [A]:',font='Times 32')
        reg3_label.place(x=100,y=280,anchor='w')
        self.t4=Entry(bd=2,width="10")
        self.t4.place(x=330,y=160)



        self.iniUI()
        self.master.after(20000,self.Get_Data)  
        self.master.after(20000,self.Data_Log)
    
    def iniUI(self):
        #create a window
        self.master.title("Solex Interface")
        self.pack(fill=BOTH,expand=1)
        Style().configure("TFrame",background="white")
       
        
        
    
        
    def Get_Data(self):
        
        frame1=can.Message(arbitration_id=0x001,data=[42,129,2,0,0,0,0,0],extended_id=False)# Current
        self.can_int.send(frame1)            
        for i in range(3):
            time.sleep(0.5)
            message = self.can_int.recv(timeout=1)
            if message is None:
                time.sleep(0.1)
            else:
                if message.arbitration_id==0x5ff:
                    time.sleep(0.1)
                elif message.dlc==5 and message.arbitration_id==0x500:
                    self.CurBit1 = hex(message.data[3])[2:4]
                elif message.dlc == 8 and message.arbitration_id ==0x500:
                    self.CurBit2 = hex(message.data[7])[2:4]
                    self.CurBit3 = hex(message.data[6])[2:4]
                    self.CurBit4 = hex(message.data[5])[2:4]
        self.BatteryCurrent = round(int(self.CurBit1 + self.CurBit2 + self.CurBit3 + self.CurBit4,16)/1000,2)
            
        
        frame1=can.Message(arbitration_id=0x001,data=[9,129,1,0,0,0,0,0],extended_id=False)# Voltage
        self.can_int.send(frame1)
        
        for i in range(2):
            time.sleep(0.5)
            message = self.can_int.recv(timeout=1)
            if message is None:
                time.sleep(0.1)
            else:
                if message.dlc == 7 and message.data[0] == 9:
                    
                    VolBit1 = hex(message.data[5])[2:4]
                    VolBit2 = hex(message.data[6])[2:4]
                    self.BatteryVoltage = round(int(VolBit1 + VolBit2,16)/1000,2)
         
        
      
        frame1=can.Message(arbitration_id=0x001,data=[13,129,1,0,0,0,0,0],extended_id=False)# SOC
        self.can_int.send(frame1)
        
        for i in range(2):
            time.sleep(0.5)
            message = self.can_int.recv(timeout=1)
            if message is None:
                time.sleep(0.1)
            else:
                if message.arbitration_id==0x5ff:
                    time.sleep(0.1)
                elif message.dlc == 7 and message.data[0] ==13:
                    self.BatterySOC = message.data[4]
        self.BatteryPower = self.BatteryVoltage*self.BatteryCurrent    
        print("Voltage:",self.BatteryVoltage,"V")
        print("Current",self.BatteryCurrent,"A")            
        print("SOC:",self.BatterySOC,"%")
        print("Power:",self.BatteryPower,"W")
        
        
        self.t1.delete(0,'end')
        self.t2.delete(0,'end')
        self.t3.delete(0,'end')
        self.t4.delete(0,'end')
        
        self.t1.insert(END,str(self.BatterySOC))
        self.t2.insert(END,str(self.BatteryPower))
        self.t3.insert(END,str(self.BatteryVoltage))
        self.t4.insert(END,str(self.BatteryCurrent))
        
        self.master.after(20000,self.Get_Data)
        
        
            
    def Data_Log(self):
        conn=sqlite3.connect('Solex_Battery.db')
        c=conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS Solex_Battery
              (id INTEGER PRIMARY KEY AUTOINCREMENT,
                Date TEXT NOT NULL,
                Time TEXT NOT NULL,
               BatterySOC REAL,
               BatteryPower REAL,
               BatteryVoltage REAL,
               BatteryCurrent REAL)""")
        
        now=datetime.now()
        time=now.strftime('%H:%M:%S')
        date=now.strftime('%d-%m-%Y')
        c.execute('''INSERT INTO Solex_Battery (Date,Time,BatterySOC,BatteryPower,BatteryVoltage,BatteryCurrent) VALUES(?,?,?,?,?,?)''',(date,time,self.BatterySOC,self.BatteryPower,self.BatteryVoltage,self.BatteryCurrent))
        conn.commit()
        conn.close()
        self.master.after(20000,self.Data_Log)
        
        
    def IoT(self):
        ADAFRUIT_IO_USERNAME = "Solex123"
        ADAFRUIT_IO_KEY = "aio_ffkI22dzKimc1gcEUMz67oOKS4Fz"
        aio=Client(ADAFRUIT_IO_USERNAME,ADAFRUIT_IO_KEY)
        self.key = ["solex-acceleration"]
        aio.send(self.key,self.lst[0])
        #self.master.after(5000,self.IoT)
    def senddata(self):
        print(self.lst[0])
        ADAFRUIT_IO_USERNAME = "Solex123"
        ADAFRUIT_IO_KEY = "aio_ffkI22dzKimc1gcEUMz67oOKS4Fz"
        aio=Client(ADAFRUIT_IO_USERNAME,ADAFRUIT_IO_KEY)
        aio.send("solex-velocity",self.speed)
        aio.send("solex-soc",self.SOC)
        aio.send("solex-charging-indicator",self.charind)
        self.master.after(10000,self.senddata)
        
def main():
    root=Tk()
    root.geometry("450x300")
    app=Solex()
    #app.senddata()
    root.mainloop()
 
                         
if __name__=='__main__':
    main()


