#!/usr/bin/env python3
"""Check what's actually running on port 636"""

import socket
import ssl

server_host = "172.16.103.2"
server_port = 636

print(f"Checking what's on {server_host}:{server_port}")
print("=" * 70)

# Test 1: Can we connect?
print("\nTest 1: TCP Connection")
print("-" * 50)
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((server_host, server_port))
    print("✓ TCP connection successful - port is open")

    # Try to receive any data (some servers send greeting)
    sock.settimeout(2)
    try:
        data = sock.recv(1024)
        if data:
            print(f"  Server sent data: {data[:50]}")
    except socket.timeout:
        print("  No immediate data from server (normal for SSL)")

    sock.close()
except Exception as e:
    print(f"✗ TCP connection failed: {e}")
    exit(1)

# Test 2: What happens when we try SSL?
print("\nTest 2: SSL Handshake Details")
print("-" * 50)

try:
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect((server_host, server_port))

    # Try SSL handshake with maximum verbosity
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    print("Attempting SSL handshake...")
    print(f"  SSL Context: check_hostname={context.check_hostname}, verify_mode={context.verify_mode}")

    # This is where it should fail
    ssl_sock = context.wrap_socket(sock, server_hostname=server_host)

    print("✓ SSL handshake successful!")
    print(f"  Protocol: {ssl_sock.version()}")
    print(f"  Cipher: {ssl_sock.cipher()}")

    ssl_sock.close()

except ssl.SSLError as e:
    print(f"✗ SSL Error: {e}")
    print(f"  Reason: {e.reason if hasattr(e, 'reason') else 'Unknown'}")
    print(f"  Library: {e.library if hasattr(e, 'library') else 'Unknown'}")

except socket.error as e:
    print(f"✗ Socket Error (WinError {e.errno}): {e}")
    print(f"\nThis error typically means:")
    print(f"  - Port 636 is open but NOT configured for SSL/TLS")
    print(f"  - OR the server requires specific SSL parameters")
    print(f"  - OR the server expects a different protocol on this port")

except Exception as e:
    print(f"✗ Unexpected error: {type(e).__name__}: {e}")

print("\n" + "=" * 70)
print("\nRecommendation:")
print("  If you see WinError 10054, the server is rejecting SSL on port 636.")
print("  Try StartTLS on port 389 instead: python test_starttls.py")
print("=" * 70)
