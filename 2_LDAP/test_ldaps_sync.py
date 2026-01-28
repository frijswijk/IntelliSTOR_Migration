#!/usr/bin/env python3
"""Test LDAPS connection with SYNC strategy"""

import ldap3
import ssl

# Configuration
server_host = "172.16.103.2"
server_port = 636
bind_dn = "cn=administrator,cn=Users,dc=ldap1test,dc=loc"
password = "Linked3-Shorten-Crestless"

print(f"Testing LDAPS with SYNC strategy: {server_host}:{server_port}")
print("-" * 70)

try:
    # Create permissive SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Try different minimum TLS versions
    for tls_version in [ssl.TLSVersion.TLSv1, ssl.TLSVersion.TLSv1_1, ssl.TLSVersion.TLSv1_2]:
        version_name = str(tls_version).replace('TLSVersion.', '')
        print(f"\nTrying {version_name}...")

        try:
            ssl_context.minimum_version = tls_version

            tls = ldap3.Tls(local_private_key_password=None, ssl_context=ssl_context)

            server = ldap3.Server(
                server_host,
                port=server_port,
                use_ssl=True,
                tls=tls,
                get_info=ldap3.ALL,
                connect_timeout=10
            )

            # Use SYNC strategy explicitly
            conn = ldap3.Connection(
                server,
                user=bind_dn,
                password=password,
                client_strategy=ldap3.SYNC,
                auto_bind=False
            )

            print(f"  Opening connection...")
            conn.open()

            print(f"  Binding...")
            conn.bind()

            if conn.bound:
                print(f"  ✓ Success with {version_name}!")
                print(f"  Server: {conn.server.info.vendor_name}")
                print(f"  Version: {conn.server.info.vendor_version}")
                conn.unbind()
                break
            else:
                print(f"  ✗ Bind failed: {conn.result}")

        except Exception as e:
            print(f"  ✗ Failed: {type(e).__name__}: {e}")

except Exception as e:
    print(f"\n✗ Overall failure: {e}")
    import traceback
    traceback.print_exc()
