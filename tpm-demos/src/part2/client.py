#!/usr/bin/env python3
import socket
import ssl
import sys

SERVER_PORT = 5000

SERVER_CA   = "server_ca.pem"   # CA that signed server cert

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <server_ip_or_hostname>")
        sys.exit(1)

    server_host = sys.argv[1]

    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.load_verify_locations(cafile=SERVER_CA)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        with context.wrap_socket(sock, server_hostname=server_host) as tls_sock:
            tls_sock.connect((server_host, SERVER_PORT))

            command = "GET_SECRET\n"
            print(f"Sending: {command.strip()}")
            tls_sock.sendall(command.encode("utf-8"))

            response = tls_sock.recv(1024)
            print(f"Received: {response.decode().strip()}")

if __name__ == "__main__":
    main()

