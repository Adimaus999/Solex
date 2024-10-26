import socket

host = ""
port = 5000

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #avoid reuse error msg
s.bind((host,port))

print ("Server started. Waiting for connection...")
s.listen()
c, addr = s.accept()
print ("Connection from: ",addr)

while True:
    #data is in bytes format, use decode() to transform it into a string
    data = c.recv(1024)
    if not data:
        break
    value = data.decode()
    print ("Received: ",value)
print ("Disconnected. Exiting.")