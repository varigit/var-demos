#!/usr/bin/env python3
import socket
import ssl
import threading

HOST = "0.0.0.0"
PORT = 5000

SERVER_CERT = "server.crt"
SERVER_KEY = "server.key"
CLIENT_CA = "client_ca.pem"

def handle_command(command: str) -> str:
    command = command.strip()

    if command == "GET_SECRET":
        return "THIS_IS_THE_SECRET"
    else:
        return "UNKNOWN_COMMAND"

def handle_client(conn: ssl.SSLSocket, addr):
    client_cert = conn.getpeercert()
    print(f"[+] TLS connection from {addr}")
    print(f" Cipher: {conn.cipher()}")
    print(f" Client cert subject: {client_cert.get('subject')}")

    # Example authorization decision
    cn = None
    for item in client_cert.get("subject", []):
        if item[0][0] == "commonName":
            cn = item[0][1]

    if cn != "trusted-client":
        print("[-] Unauthorized client")
        conn.close()
        returna

    # authorization passed, let's continue

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
    # ---- TLS context (server side) ----
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    context.load_cert_chain(
        certfile=SERVER_CERT,
        keyfile=SERVER_KEY
    )

    # Require client certificates
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=CLIENT_CA)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.bind((HOST, PORT))
        server_sock.listen()
        print(f"TLS server listening on {HOST}:{PORT}")

        while True:
            raw_conn, addr = server_sock.accept()

            # Wrap each connection with TLS
            tls_conn = context.wrap_socket(raw_conn, server_side=True)

            thread = threading.Thread(
                target=handle_client,
                args=(tls_conn, addr),
                daemon=True
            )
            thread.start()

if __name__ == "__main__":
    main()

