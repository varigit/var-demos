import gpiod
import sys
import time
import socket
import sys
import os

print("Starting Python GPIOD Daemon")

chip = gpiod.chip("gpiochip4")
led = chip.get_line(0)

config = gpiod.line_request()
config.consumer = "Python LED Control"
config.request_type = gpiod.line_request.DIRECTION_OUTPUT

led.request(config)

server_address = './uds_socket'

# Make sure the socket does not already exist
try:
    os.unlink(server_address)
except OSError:
    if os.path.exists(server_address):
        raise

# Create a UDS socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

# Bind the socket to the port
print('starting up on %s' % server_address)
sock.bind(server_address)

# Listen for incoming connections
sock.listen(1)

while True:
    # Wait for a connection
    print('Waiting for a connection...')
    connection, client_address = sock.accept()
    try:
        print('Client Connected')

        # Receive the data in small chunks and retransmit it
        while True:
            data = connection.recv(16)
            print('Received "%s"' % data)
            if data:
                if data == b'on\n':
                    response = "LED On"
                    led.set_value(0)
                elif data == b'off\n':
                    response = "LED Off"
                    led.set_value(1)
                else:
                    response = "Invalid Command"
                
                print(response)
                
                connection.sendall(bytes(f'{response}\n', 'ascii'))
            else:
                print('No more data from client, disconnecting')
                break
            
    finally:
        # Clean up the connection
        connection.close()