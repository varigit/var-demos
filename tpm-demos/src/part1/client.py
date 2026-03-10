#!/usr/bin/env python3
import socket
import sys

SERVER_PORT = 5000

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <server_ip_or_hostname>")
        sys.exit(1)

    server_host = sys.argv[1]

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_host, SERVER_PORT))

        command = "GET_SECRET\n"
        print(f"Sending: {command.strip()}")
        sock.sendall(command.encode("utf-8"))

        response = sock.recv(1024)
        print(f"Received: {response.decode('utf-8').strip()}")

if __name__ == "__main__":
    main()
