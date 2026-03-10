#!/usr/bin/env python3
import socket
import threading

HOST = "0.0.0.0"
PORT = 5000

def handle_command(command: str) -> str:
    command = command.strip()

    if command == "GET_SECRET":
        return "THIS_IS_THE_SECRET"
    else:
        return "UNKNOWN_COMMAND"

def handle_client(conn: socket.socket, addr):
    """Handle one client connection."""
    print(f"[+] Connection from {addr}")

    with conn:
        while True:
            data = conn.recv(1024)
            if not data:
                break

            command = data.decode("utf-8")
            print(f"[{addr}] Received: {command.strip()}")

            response = handle_command(command)
            conn.sendall((response + "\n").encode("utf-8"))

    print(f"[-] Client disconnected: {addr}")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.bind((HOST, PORT))
        server_sock.listen()

        print(f"Server listening on {HOST}:{PORT}")

        while True:
            conn, addr = server_sock.accept()

            # One thread per client
            thread = threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True
            )
            thread.start()

if __name__ == "__main__":
    main()

