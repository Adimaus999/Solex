import time
import sqlite3
from datetime import datetime
import random
from Adafruit_IO import Client
from tkinter import Tk,BOTH
from tkinter.ttk import Frame, Label, Style,Entry,Button
from tkinter import *

class Solex(Frame):
    def __init__(self):
       super().__init__()
       self.output=0
       self.lst = [1,2,3,4]
       self.speed = 0
       self.SOC = 0
       self.charind = "Charging"
       self.teamcom = "Go"
       
       title_label=Label(self.master,text='Solex Interface:',font='Times 16 bold')
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
    
    def iniUI(self):
        #create a window
        self.master.title("Solex Interface")
        self.pack(fill=BOTH,expand=1)
        Style().configure("TFrame",background="white")
       
        
        
    def GetData(self):
        
        self.speed =  random.uniform(50, 50.0001)
        self.SOC = random.uniform(50, 50.0001)
        
        self.t1.delete(0,'end')
        self.t2.delete(0,'end')
        self.t3.delete(0,'end')
        self.t4.delete(0,'end')
        self.t1.insert(END,str(round(self.speed,2)))
        self.t2.insert(END,str(round(self.SOC,2)))
        self.t3.insert(END,self.charind)
        self.t4.insert(END,self.teamcom)
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
    app.senddata()
    root.mainloop()
 
                         
if __name__=='__main__':
    main()