#!/usr/bin/env python3
"""Quick test using ldaps:// URL format"""

import ldap3
import ssl

# Configuration
server_host = "172.16.103.2"
server_port = 636
bind_dn = "cn=administrator,cn=Users,dc=ldap1test,dc=loc"
password = "Linked3-Shorten-Crestless"

print(f"Testing ldaps://{server_host}:{server_port}")
print("-" * 50)

try:
    # Create permissive SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1

    tls = ldap3.Tls(local_private_key_password=None, ssl_context=ssl_context)

    # Method 1: Using ldaps:// URL
    server = ldap3.Server(
        f"ldaps://{server_host}:{server_port}",
        tls=tls,
        get_info=ldap3.ALL,
        connect_timeout=10
    )

    print(f"Connecting to: {server}")

    conn = ldap3.Connection(
        server,
        user=bind_dn,
        password=password,
        auto_bind=True
    )

    print("✓ Connection successful!")
    print(f"Server info: {conn.server.info}")

    conn.unbind()

except Exception as e:
    print(f"✗ Connection failed: {e}")
    import traceback
    traceback.print_exc()
