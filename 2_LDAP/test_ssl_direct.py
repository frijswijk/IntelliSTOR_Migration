#!/usr/bin/env python3
"""
Direct SSL connection test to diagnose LDAPS issues.
This script attempts various SSL/TLS configurations to identify what works.
"""

import ssl
import socket
import sys

def test_ssl_connection(host, port):
    """Test SSL connection with various configurations."""

    print(f"\n{'='*70}")
    print(f"Testing SSL connection to {host}:{port}")
    print(f"{'='*70}\n")

    # Test 1: Basic socket connection
    print("Test 1: Basic socket connection (no SSL)")
    print("-" * 50)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        print(f"✓ Socket connection successful")
        sock.close()
    except Exception as e:
        print(f"✗ Socket connection failed: {e}")
        return

    # Test 2: SSL with CERT_NONE (no verification)
    print("\nTest 2: SSL connection with CERT_NONE")
    print("-" * 50)
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)

        ssl_sock = context.wrap_socket(sock, server_hostname=host)
        ssl_sock.connect((host, port))

        print(f"✓ SSL connection successful")
        print(f"  Protocol: {ssl_sock.version()}")
        print(f"  Cipher: {ssl_sock.cipher()}")

        cert = ssl_sock.getpeercert()
        if cert:
            print(f"  Certificate: {cert.get('subject', 'N/A')}")

        ssl_sock.close()

    except Exception as e:
        print(f"✗ SSL connection failed: {e}")
        print(f"  Error type: {type(e).__name__}")

    # Test 3: SSL with minimum TLS 1.0
    print("\nTest 3: SSL with TLS 1.0+")
    print("-" * 50)
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.minimum_version = ssl.TLSVersion.TLSv1

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)

        ssl_sock = context.wrap_socket(sock, server_hostname=host)
        ssl_sock.connect((host, port))

        print(f"✓ SSL connection successful with TLS 1.0+")
        print(f"  Protocol: {ssl_sock.version()}")
        print(f"  Cipher: {ssl_sock.cipher()}")

        ssl_sock.close()

    except Exception as e:
        print(f"✗ SSL connection failed: {e}")

    # Test 4: SSL with TLS 1.2+
    print("\nTest 4: SSL with TLS 1.2+")
    print("-" * 50)
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)

        ssl_sock = context.wrap_socket(sock, server_hostname=host)
        ssl_sock.connect((host, port))

        print(f"✓ SSL connection successful with TLS 1.2+")
        print(f"  Protocol: {ssl_sock.version()}")
        print(f"  Cipher: {ssl_sock.cipher()}")

        ssl_sock.close()

    except Exception as e:
        print(f"✗ SSL connection failed: {e}")

    # Test 5: Try with ldap3
    print("\nTest 5: ldap3 connection")
    print("-" * 50)
    try:
        import ldap3

        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1

        tls = ldap3.Tls(local_private_key_password=None, ssl_context=ssl_context)

        server = ldap3.Server(
            host,
            port=port,
            use_ssl=True,
            tls=tls,
            get_info=ldap3.NONE,
            connect_timeout=10
        )

        conn = ldap3.Connection(server, auto_bind=False)
        conn.open()

        print(f"✓ ldap3 connection successful")
        print(f"  Server: {server}")

        conn.unbind()

    except Exception as e:
        print(f"✗ ldap3 connection failed: {e}")
        print(f"  Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*70}")
    print("SSL connection tests completed")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_ssl_direct.py <host> [port]")
        print("Example: python test_ssl_direct.py 172.16.103.2 636")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 636

    test_ssl_connection(host, port)
