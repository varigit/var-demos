/*
 * Minimal tutorial TLS client (OpenSSL >= 3.0)
 *
 * - argv: <server_ip_or_hostname>
 * - connects to SERVER_PORT (5000)
 * - verifies server using SERVER_CA ("server_ca.pem")
 * - presents client certificate + TPM-backed key (TPM persistent handle)
 * - sends "GET_SECRET\n"
 * - reads up to 1024 bytes once and prints it
 *
 * Build:
 *   gcc -Wall -Wextra -O2 client.c -o client -lssl -lcrypto
 *
 * Run:
 *   ./client <server_ip_or_hostname>
 */

#define _POSIX_C_SOURCE 200112L

#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <netdb.h>
#include <sys/socket.h>

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/store.h>

#define SERVER_PORT "5000"

#define SERVER_CA   "server_ca.pem"
#define CLIENT_CERT "client.crt"

/* TPM2 provider persistent handle URI */
#define CLIENT_KEY_URI "handle:0x81000001"

/* Simple error helper */
static void openssl_die(const char *fmt, ...) {
    va_list ap;

    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);

    fputc('\n', stderr);

    ERR_print_errors_fp(stderr);
    exit(1);
}

/* Connect to host:port (TCP). Returns socket fd. */
static int tcp_connect(const char *host, const char *port) {
    struct addrinfo hints;
    struct addrinfo *res = NULL;
    struct addrinfo *p = NULL;
    int fd = -1;
    int rc;

    memset(&hints, 0, sizeof(hints));
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_family   = AF_UNSPEC; /* IPv4 or IPv6 */

    rc = getaddrinfo(host, port, &hints, &res);
    if (rc != 0) {
        fprintf(stderr, "getaddrinfo(%s,%s): %s\n", host, port, gai_strerror(rc));
        exit(1);
    }

    for (p = res; p; p = p->ai_next) {
        fd = (int)socket(p->ai_family, p->ai_socktype, p->ai_protocol);
        if (fd < 0) continue;

        if (connect(fd, p->ai_addr, p->ai_addrlen) == 0) {
            break; /* success */
        }

        close(fd);
        fd = -1;
    }

    freeaddrinfo(res);

    if (fd < 0) {
        fprintf(stderr, "connect(%s:%s) failed: %s\n", host, port, strerror(errno));
        exit(1);
    }

    return fd;
}

/*
 * Obtain an EVP_PKEY that references a provider-backed key.
 *
 * For TPM usage with a persistent handle, the URI "handle:0x81000001" is resolved
 * by the TPM provider. The returned EVP_PKEY is an opaque object: it does not
 * contain extractable private key bytes. When TLS needs to sign, OpenSSL invokes
 * the provider implementation, which delegates the signing operation to the TPM.
 */
static EVP_PKEY *load_pkey_from_uri(const char *uri) {
    OSSL_STORE_CTX *store = NULL;
    OSSL_STORE_INFO *info = NULL;
    EVP_PKEY *pkey = NULL;
    int type;

    store = OSSL_STORE_open(uri, NULL, NULL, NULL, NULL);
    if (!store) {
        openssl_die("OSSL_STORE_open failed for '%s'", uri);
    }

    while (!OSSL_STORE_eof(store)) {
        info = OSSL_STORE_load(store);
        if (!info) {
            /* Could be EOF or an error; distinguish via OSSL_STORE_eof() above */
            break;
        }

        type = OSSL_STORE_INFO_get_type(info);
        if (type == OSSL_STORE_INFO_PKEY) {
            pkey = OSSL_STORE_INFO_get1_PKEY(info);
            OSSL_STORE_INFO_free(info);
            info = NULL;
            break;
        }

        OSSL_STORE_INFO_free(info);
        info = NULL;
    }

    if (!pkey && !OSSL_STORE_eof(store)) {
        /* Some error occurred while loading */
        OSSL_STORE_close(store);
        openssl_die("OSSL_STORE_load failed while reading '%s'", uri);
    }

    OSSL_STORE_close(store);

    if (!pkey) {
        openssl_die("No private key found in STORE URI '%s'", uri);
    }

    return pkey;
}

/*
 * Send a single command and read a single response (up to 1024 bytes),
 * matching the Python client structure.
 */
static void handle_command(SSL *ssl, const char *command) {
    unsigned char buf[1024];
    int n;
    int r;

    memset(buf, 0, sizeof(buf));

    printf("Sending: %s", command);

    n = SSL_write(ssl, command, (int)strlen(command));
    if (n <= 0) {
        openssl_die("SSL_write failed");
    }

    r = SSL_read(ssl, buf, (int)sizeof(buf) - 1);
    if (r <= 0) {       /* no empty responses in protocol */
        openssl_die("SSL_read failed or unexpected empty response");
    }

    printf("Received: %s", (char *)buf);
}

int main(int argc, char **argv) {
    const char *server_host;
    SSL_CTX *ctx;
    int fd;
    SSL *ssl;
    long vr;
    EVP_PKEY *pkey;

    if (argc != 2) {
        fprintf(stderr, "Usage: %s <server_ip_or_hostname>\n", argv[0]);
        return 1;
    }
    server_host = argv[1];

    /* OpenSSL 3.x init */
    if (OPENSSL_init_ssl(0, NULL) != 1) {
        openssl_die("OPENSSL_init_ssl failed");
    }

    ctx = SSL_CTX_new(TLS_client_method());
    if (!ctx) {
        openssl_die("SSL_CTX_new failed");
    }

    /* Client and server authentication */
    SSL_CTX_set_verify(ctx, SSL_VERIFY_PEER, NULL);

    if (SSL_CTX_load_verify_locations(ctx, SERVER_CA, NULL) != 1) {
        openssl_die("Failed to load server CA file (%s)", SERVER_CA);
    }

    /* Present client certificate */
    if (SSL_CTX_use_certificate_file(ctx, CLIENT_CERT, SSL_FILETYPE_PEM) != 1) {
        openssl_die("Failed to load client certificate (%s)", CLIENT_CERT);
    }

    /* Load TPM-backed client key from persistent handle */
    pkey = load_pkey_from_uri(CLIENT_KEY_URI);

    if (SSL_CTX_use_PrivateKey(ctx, pkey) != 1) {
        EVP_PKEY_free(pkey);
        openssl_die("SSL_CTX_use_PrivateKey failed for key URI '%s'", CLIENT_KEY_URI);
    }
    EVP_PKEY_free(pkey);
    pkey = NULL;

    if (SSL_CTX_check_private_key(ctx) != 1) {
        openssl_die("Client certificate and TPM key reference do not match");
    }

    /* TCP connect */
    fd = tcp_connect(server_host, SERVER_PORT);

    /* Wrap in TLS and set SNI */
    ssl = SSL_new(ctx);
    if (!ssl) {
        openssl_die("SSL_new failed");
    }

    if (SSL_set_fd(ssl, fd) != 1) {
        openssl_die("SSL_set_fd failed");
    }

    if (SSL_set_tlsext_host_name(ssl, server_host) != 1) {
        openssl_die("Failed to set SNI");
    }

    if (SSL_connect(ssl) != 1) {
        openssl_die("TLS handshake (SSL_connect) failed");
    }

    /* Ensure verification succeeded */
    vr = SSL_get_verify_result(ssl);
    if (vr != X509_V_OK) {
        fprintf(stderr, "Server certificate verification failed: %s\n",
                X509_verify_cert_error_string(vr));
        SSL_free(ssl);
        close(fd);
        SSL_CTX_free(ctx);
        return 2;
    }

    /* send one command, read one response */
    handle_command(ssl, "GET_SECRET\n");

    SSL_shutdown(ssl);
    SSL_free(ssl);
    close(fd);
    SSL_CTX_free(ctx);

    return 0;
}

