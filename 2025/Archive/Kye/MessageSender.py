import socket

server_ip = "100.69.35.41"  # Replace with the PyQt machine's IP
server_port = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
message = "Hello from another device!"
sock.sendto(message.encode(), (server_ip, server_port))
print("Message sent!")