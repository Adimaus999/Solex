import socket

host = ''
port = 5000

s = socket.socket()
s.connect((host,port))
print("Connected to",host)

while True:
    message = "data"
    s.send(message.encode())  #convert to bytes then send
