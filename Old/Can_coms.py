import time
import can
import os
from datetime import datetime
import sqlite3

class Levistor:
    def __init__(self):
        os.system('sudo ip link set up can0 type can bitrate 250000')#
        os.system("sudo ifconfig can0 txqueuelen 1000")
        time.sleep(0.1)
        try:
            self.can_int=can.interface.Bus(channel='can0', bustype='socketcan')
        except OSError:
            print('Cannot find CAN Board')
        pass
    
    
     
        
        
    def canread(self):
#                                       
        while True:
            
#             #Current
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
                        CurBit1 = hex(message.data[3])[2:4]
                    elif message.dlc == 8 and message.arbitration_id ==0x500:
                        CurBit2 = hex(message.data[7])[2:4]
                        CurBit3 = hex(message.data[6])[2:4]
                        CurBit4 = hex(message.data[5])[2:4]
            Current = round(int(CurBit1 + CurBit2 + CurBit3 + CurBit4,16)/1000,2)
                
#             
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
                        Voltage = round(int(VolBit1 + VolBit2,16)/1000,2)
             
            
#           
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
                        SOC = message.data[4]
                
            print("Voltage:",Voltage,"V")
            print("Current",Current,"A")            
            print("SOC:",SOC,"%")
            
            

         
#                     conn=sqlite3.connect('Battery_Test.db')
#                     c=conn.cursor()
#                     c.execute("""CREATE TABLE IF NOT EXISTS Battery_Test
#                           (id INTEGER PRIMARY KEY AUTOINCREMENT,
#                             datetime TEXT NOT NULL,
#                            soc REAL)""")
#                 
#                 
#                     current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#                                 
#                 
#                 
#                     c.execute('''INSERT INTO Battery_Test (datetime, soc) VALUES(?,?)''',(current_datetime,sc1))
#                     conn.commit()
#                     conn.close()
        
            
        
        
def main():
    obj=Levistor()
    obj.canread()
  
    
if __name__=='__main__':
    main()
    
                
            