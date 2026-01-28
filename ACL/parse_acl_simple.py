#!/usr/bin/env python3
"""
Simple Windows ACL Parser - Analyzes binary ACL data
"""

def parse_sid_from_bytes(data, offset):
    """Parse a SID from binary data."""
    if offset + 8 > len(data):
        return None, 0

    revision = data[offset]
    sub_authority_count = data[offset + 1]

    # Need enough space for full SID
    sid_size = 8 + (sub_authority_count * 4)
    if offset + sid_size > len(data):
        return None, 0

    # Authority (6 bytes, big-endian)
    authority = int.from_bytes(data[offset+2:offset+8], 'big')

    # Sub-authorities (4 bytes each, little-endian)
    sub_authorities = []
    for i in range(sub_authority_count):
        sa_offset = offset + 8 + (i * 4)
        sa = int.from_bytes(data[sa_offset:sa_offset+4], 'little')
        sub_authorities.append(sa)

    # Build SID string
    sid = f"S-{revision}-{authority}"
    for sa in sub_authorities:
        sid += f"-{sa}"

    return sid, sid_size

def identify_well_known_sid(sid):
    """Identify well-known SIDs."""
    well_known = {
        "S-1-1-0": "Everyone",
        "S-1-2-0": "Local",
        "S-1-3-0": "Creator Owner",
        "S-1-3-1": "Creator Group",
        "S-1-5-18": "Local System",
        "S-1-5-19": "NT Authority\\Local Service",
        "S-1-5-20": "NT Authority\\Network Service",
        "S-1-5-32-544": "BUILTIN\\Administrators",
        "S-1-5-32-545": "BUILTIN\\Users",
        "S-1-5-32-546": "BUILTIN\\Guests",
        "S-1-5-32-547": "BUILTIN\\Power Users",
        "S-1-5-32-551": "BUILTIN\\Backup Operators",
    }

    if sid in well_known:
        return well_known[sid]

    # Check for domain users/groups (S-1-5-21-...)
    if sid.startswith("S-1-5-21-"):
        parts = sid.split('-')
        if len(parts) >= 8:
            rid = int(parts[-1])
            # Common RIDs
            rid_names = {
                500: "Domain Administrator",
                501: "Domain Guest",
                502: "KRBTGT",
                512: "Domain Admins",
                513: "Domain Users",
                514: "Domain Guests",
                515: "Domain Computers",
                516: "Domain Controllers",
                517: "Cert Publishers",
                518: "Schema Admins",
                519: "Enterprise Admins",
                520: "Group Policy Creator Owners",
            }
            domain_sid = '-'.join(parts[:8])
            if rid in rid_names:
                return f"Domain: {rid_names[rid]} (RID: {rid})"
            else:
                return f"Domain User/Group (RID: {rid})"

    return sid

def parse_access_mask(mask):
    """Parse access mask into readable rights."""
    rights = []

    # Generic rights
    if mask & 0x10000000: rights.append("GENERIC_ALL")
    if mask & 0x20000000: rights.append("GENERIC_EXECUTE")
    if mask & 0x40000000: rights.append("GENERIC_WRITE")
    if mask & 0x80000000: rights.append("GENERIC_READ")

    # Standard rights
    if mask & 0x00010000: rights.append("DELETE")
    if mask & 0x00020000: rights.append("READ_CONTROL")
    if mask & 0x00040000: rights.append("WRITE_DAC")
    if mask & 0x00080000: rights.append("WRITE_OWNER")
    if mask & 0x00100000: rights.append("SYNCHRONIZE")

    # Specific rights (file/folder)
    if mask & 0x00000001: rights.append("FILE_READ_DATA/LIST_DIRECTORY")
    if mask & 0x00000002: rights.append("FILE_WRITE_DATA/ADD_FILE")
    if mask & 0x00000004: rights.append("FILE_APPEND_DATA/ADD_SUBDIRECTORY")
    if mask & 0x00000008: rights.append("FILE_READ_EA")
    if mask & 0x00000010: rights.append("FILE_WRITE_EA")
    if mask & 0x00000020: rights.append("FILE_EXECUTE/TRAVERSE")
    if mask & 0x00000040: rights.append("FILE_DELETE_CHILD")
    if mask & 0x00000080: rights.append("FILE_READ_ATTRIBUTES")
    if mask & 0x00000100: rights.append("FILE_WRITE_ATTRIBUTES")

    # Common combinations
    if mask == 0x001F01FF:
        return ["FULL_CONTROL (All Rights)"]
    if mask == 0x00000007:
        return ["READ & EXECUTE"]
    if mask == 0x00000006:
        return ["MODIFY"]

    return rights if rights else [f"Custom: 0x{mask:08X}"]

def find_all_sids_in_data(data):
    """Scan through data to find all SID patterns."""
    results = []

    # Look for SID patterns (starts with revision=1, sub-auth count, then authority)
    for i in range(len(data) - 8):
        if data[i] == 0x01:  # Revision 1
            sub_auth_count = data[i + 1]

            # Reasonable range for sub-authority count
            if 0 < sub_auth_count <= 15:
                sid, size = parse_sid_from_bytes(data, i)
                if sid:
                    # Look back for possible access mask (4 bytes before SID)
                    access_mask = None
                    if i >= 4:
                        access_mask = int.from_bytes(data[i-4:i], 'little')

                    results.append({
                        'offset': i,
                        'sid': sid,
                        'name': identify_well_known_sid(sid),
                        'access_mask': access_mask,
                        'size': size
                    })

    return results

def analyze_hex_acl(hex_string):
    """Analyze hex ACL string."""
    # Remove 0x prefix if present
    if hex_string.startswith('0x'):
        hex_string = hex_string[2:]

    data = bytes.fromhex(hex_string)

    print("=" * 80)
    print("WINDOWS ACL BINARY ANALYSIS")
    print("=" * 80)
    print(f"\nData length: {len(data)} bytes ({len(hex_string)} hex chars)")
    print()

    # Show first 64 bytes in hex
    print("First 64 bytes (hex):")
    for i in range(0, min(64, len(data)), 16):
        hex_part = ' '.join(f'{b:02X}' for b in data[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        print(f"  {i:04X}: {hex_part:<48} {ascii_part}")
    print()

    # Find all SIDs
    sids = find_all_sids_in_data(data)

    print(f"Found {len(sids)} SID(s) in the binary data:")
    print("-" * 80)

    for idx, sid_info in enumerate(sids, 1):
        print(f"\nSID #{idx}:")
        print(f"  Offset: 0x{sid_info['offset']:04X} ({sid_info['offset']} bytes)")
        print(f"  SID: {sid_info['sid']}")
        print(f"  Account: {sid_info['name']}")

        if sid_info['access_mask'] is not None:
            print(f"  Possible Access Mask: 0x{sid_info['access_mask']:08X}")
            rights = parse_access_mask(sid_info['access_mask'])
            print(f"  Permissions:")
            for right in rights:
                print(f"    - {right}")

    # Extract domain information
    print("\n" + "=" * 80)
    print("DOMAIN INFORMATION")
    print("=" * 80)

    domain_sids = [s for s in sids if s['sid'].startswith('S-1-5-21-')]
    if domain_sids:
        # Extract domain SID (without RID)
        first_domain_sid = domain_sids[0]['sid']
        parts = first_domain_sid.split('-')
        if len(parts) >= 8:
            domain_sid = '-'.join(parts[:8])
            print(f"\nDomain SID: {domain_sid}")
            print(f"  Domain ID components:")
            print(f"    - {parts[4]}: 0x{int(parts[4]):08X}")
            print(f"    - {parts[5]}: 0x{int(parts[5]):08X}")
            print(f"    - {parts[6]}: 0x{int(parts[6]):08X}")
            print(f"    - {parts[7]}: 0x{int(parts[7]):08X}")
            print()

            print(f"Users/Groups in this ACL:")
            for sid_info in domain_sids:
                parts = sid_info['sid'].split('-')
                rid = parts[-1]
                print(f"  - RID {rid}: {sid_info['name']}")
    else:
        print("\nNo domain SIDs found (only well-known SIDs)")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    # Your hex ACL
    hex_acl = "0x94000000010014800000000000000000140000003000000002001C000100000002C0140007000000010100000000000100000000020064000300000000001400070000000101000000000001000000000000240007000000010500000000000515000000D67B9C550F50215711305578728A00000000240007000000010500000000000515000000D67B9C550F50215711305578ED940000"

    analyze_hex_acl(hex_acl)
