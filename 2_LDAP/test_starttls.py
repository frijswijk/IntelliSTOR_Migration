#!/usr/bin/env python3
"""Test StartTLS on port 389"""

import ldap3
import ssl

# Configuration
server_host = "172.16.103.2"
server_port = 389
bind_dn = "cn=administrator,cn=Users,dc=ldap1test,dc=loc"
password = "Linked3-Shorten-Crestless"

print(f"Testing StartTLS on {server_host}:{server_port}")
print("=" * 70)

try:
    # Create TLS configuration
    tls = ldap3.Tls(validate=ssl.CERT_NONE)

    # Create server without use_ssl (for StartTLS)
    server = ldap3.Server(
        server_host,
        port=server_port,
        use_ssl=False,  # StartTLS starts unencrypted
        tls=tls,
        get_info=ldap3.ALL
    )

    # Create connection
    conn = ldap3.Connection(
        server,
        user=bind_dn,
        password=password,
        auto_bind=False
    )

    print("\nStep 1: Opening connection on port 389...")
    conn.open()
    print("  ✓ Connection opened")

    print("\nStep 2: Starting TLS (StartTLS)...")
    conn.start_tls()
    print("  ✓ TLS started successfully")

    print("\nStep 3: Binding with credentials...")
    if not conn.bind():
        print(f"  ✗ Bind failed: {conn.result}")
    else:
        print("  ✓ Bind successful")
        print(f"\nServer Info:")
        print(f"  Vendor: {conn.server.info.vendor_name}")
        print(f"  Version: {conn.server.info.vendor_version}")
        print(f"  Naming Contexts: {conn.server.info.naming_contexts}")

    conn.unbind()
    print("\n✓✓✓ StartTLS connection SUCCESSFUL! ✓✓✓")
    print("\nThis means your server supports StartTLS on port 389.")
    print("We can configure the tool to use StartTLS instead of LDAPS.")

except Exception as e:
    print(f"\n✗ StartTLS failed: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()

print("=" * 70)
