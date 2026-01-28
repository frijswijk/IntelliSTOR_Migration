#!/usr/bin/env python3
"""
Windows Security Descriptor (ACL) Parser

Parses binary security descriptors stored in hex format.
"""

def parse_sid(data, offset):
    """Parse a Windows SID (Security Identifier) from binary data."""
    revision = data[offset]
    sub_authority_count = data[offset + 1]

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

    # SID size
    sid_size = 8 + (sub_authority_count * 4)

    return sid, sid_size

def parse_ace(data, offset):
    """Parse an Access Control Entry (ACE)."""
    ace_type = data[offset]
    ace_flags = data[offset + 1]
    ace_size = int.from_bytes(data[offset+2:offset+4], 'little')
    access_mask = int.from_bytes(data[offset+4:offset+8], 'little')

    # ACE Types
    ace_types = {
        0x00: "ACCESS_ALLOWED_ACE_TYPE",
        0x01: "ACCESS_DENIED_ACE_TYPE",
        0x02: "SYSTEM_AUDIT_ACE_TYPE",
        0x03: "SYSTEM_ALARM_ACE_TYPE",
        0x05: "ACCESS_ALLOWED_OBJECT_ACE_TYPE",
        0x06: "ACCESS_DENIED_OBJECT_ACE_TYPE",
        0x07: "SYSTEM_AUDIT_OBJECT_ACE_TYPE",
        0x08: "SYSTEM_ALARM_OBJECT_ACE_TYPE",
    }

    # Access Rights (common flags)
    rights = []
    if access_mask & 0x00000001: rights.append("READ_DATA/LIST_DIRECTORY")
    if access_mask & 0x00000002: rights.append("WRITE_DATA/ADD_FILE")
    if access_mask & 0x00000004: rights.append("APPEND_DATA/ADD_SUBDIRECTORY")
    if access_mask & 0x00000008: rights.append("READ_EA")
    if access_mask & 0x00000010: rights.append("WRITE_EA")
    if access_mask & 0x00000020: rights.append("EXECUTE/TRAVERSE")
    if access_mask & 0x00000040: rights.append("DELETE_CHILD")
    if access_mask & 0x00000080: rights.append("READ_ATTRIBUTES")
    if access_mask & 0x00000100: rights.append("WRITE_ATTRIBUTES")
    if access_mask & 0x00010000: rights.append("DELETE")
    if access_mask & 0x00020000: rights.append("READ_CONTROL")
    if access_mask & 0x00040000: rights.append("WRITE_DAC")
    if access_mask & 0x00080000: rights.append("WRITE_OWNER")
    if access_mask & 0x00100000: rights.append("SYNCHRONIZE")
    if access_mask & 0x01000000: rights.append("ACCESS_SYSTEM_SECURITY")
    if access_mask & 0x10000000: rights.append("GENERIC_ALL")
    if access_mask & 0x20000000: rights.append("GENERIC_EXECUTE")
    if access_mask & 0x40000000: rights.append("GENERIC_WRITE")
    if access_mask & 0x80000000: rights.append("GENERIC_READ")

    # Parse SID
    sid, sid_size = parse_sid(data, offset + 8)

    # Well-known SIDs
    well_known_sids = {
        "S-1-1-0": "Everyone",
        "S-1-5-18": "Local System",
        "S-1-5-19": "Local Service",
        "S-1-5-20": "Network Service",
        "S-1-5-32-544": "Administrators",
        "S-1-5-32-545": "Users",
        "S-1-5-32-546": "Guests",
        "S-1-5-32-547": "Power Users",
    }

    sid_name = well_known_sids.get(sid, sid)

    return {
        'type': ace_types.get(ace_type, f"Unknown ({ace_type})"),
        'flags': ace_flags,
        'size': ace_size,
        'access_mask': f"0x{access_mask:08X}",
        'rights': rights if rights else ["FULL_CONTROL" if access_mask == 0x1F01FF else f"Custom (0x{access_mask:08X})"],
        'sid': sid,
        'sid_name': sid_name
    }, ace_size

def parse_acl(data, offset):
    """Parse an Access Control List (ACL)."""
    acl_revision = data[offset]
    acl_size = int.from_bytes(data[offset+2:offset+4], 'little')
    ace_count = int.from_bytes(data[offset+4:offset+6], 'little')

    aces = []
    current_offset = offset + 8  # ACL header is 8 bytes

    for i in range(ace_count):
        ace, ace_size = parse_ace(data, current_offset)
        aces.append(ace)
        current_offset += ace_size

    return {
        'revision': acl_revision,
        'size': acl_size,
        'ace_count': ace_count,
        'aces': aces
    }

def parse_security_descriptor(hex_string):
    """Parse a Windows Security Descriptor from hex string."""
    # Remove 0x prefix if present
    if hex_string.startswith('0x'):
        hex_string = hex_string[2:]

    # Convert to bytes
    data = bytes.fromhex(hex_string)

    # Parse header
    revision = data[0]
    sbz1 = data[1]
    control = int.from_bytes(data[2:4], 'little')
    owner_offset = int.from_bytes(data[4:8], 'little')
    group_offset = int.from_bytes(data[8:12], 'little')
    sacl_offset = int.from_bytes(data[12:16], 'little')
    dacl_offset = int.from_bytes(data[16:20], 'little')

    # Control flags
    control_flags = []
    if control & 0x0001: control_flags.append("SE_OWNER_DEFAULTED")
    if control & 0x0002: control_flags.append("SE_GROUP_DEFAULTED")
    if control & 0x0004: control_flags.append("SE_DACL_PRESENT")
    if control & 0x0008: control_flags.append("SE_DACL_DEFAULTED")
    if control & 0x0010: control_flags.append("SE_SACL_PRESENT")
    if control & 0x0020: control_flags.append("SE_SACL_DEFAULTED")
    if control & 0x0100: control_flags.append("SE_DACL_AUTO_INHERIT_REQ")
    if control & 0x0200: control_flags.append("SE_SACL_AUTO_INHERIT_REQ")
    if control & 0x0400: control_flags.append("SE_DACL_AUTO_INHERITED")
    if control & 0x0800: control_flags.append("SE_SACL_AUTO_INHERITED")
    if control & 0x1000: control_flags.append("SE_DACL_PROTECTED")
    if control & 0x2000: control_flags.append("SE_SACL_PROTECTED")
    if control & 0x4000: control_flags.append("SE_RM_CONTROL_VALID")
    if control & 0x8000: control_flags.append("SE_SELF_RELATIVE")

    result = {
        'revision': revision,
        'control': f"0x{control:04X}",
        'control_flags': control_flags,
        'owner_offset': owner_offset,
        'group_offset': group_offset,
        'sacl_offset': sacl_offset,
        'dacl_offset': dacl_offset,
    }

    # Parse Owner SID
    if owner_offset > 0 and owner_offset < len(data):
        try:
            owner_sid, _ = parse_sid(data, owner_offset)
            result['owner_sid'] = owner_sid
        except:
            result['owner_sid'] = f"Invalid (offset {owner_offset})"

    # Parse Group SID
    if group_offset > 0 and group_offset < len(data):
        try:
            group_sid, _ = parse_sid(data, group_offset)
            result['group_sid'] = group_sid
        except:
            result['group_sid'] = f"Invalid (offset {group_offset})"

    # Parse DACL
    if dacl_offset > 0 and dacl_offset < len(data):
        try:
            result['dacl'] = parse_acl(data, dacl_offset)
        except Exception as e:
            result['dacl_error'] = str(e)

    # Parse SACL
    if sacl_offset > 0 and sacl_offset < len(data):
        try:
            result['sacl'] = parse_acl(data, sacl_offset)
        except Exception as e:
            result['sacl_error'] = str(e)

    return result

def format_output(sd):
    """Format security descriptor as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("WINDOWS SECURITY DESCRIPTOR (ACL) ANALYSIS")
    lines.append("=" * 70)
    lines.append("")

    lines.append(f"Revision: {sd['revision']}")
    lines.append(f"Control Flags: {sd['control']}")
    for flag in sd['control_flags']:
        lines.append(f"  - {flag}")
    lines.append("")

    if 'owner_sid' in sd:
        lines.append(f"Owner SID: {sd['owner_sid']}")
    if 'group_sid' in sd:
        lines.append(f"Group SID: {sd['group_sid']}")
    lines.append("")

    if 'dacl' in sd:
        dacl = sd['dacl']
        lines.append("DISCRETIONARY ACCESS CONTROL LIST (DACL)")
        lines.append("-" * 70)
        lines.append(f"ACL Revision: {dacl['revision']}")
        lines.append(f"ACL Size: {dacl['size']} bytes")
        lines.append(f"ACE Count: {dacl['ace_count']}")
        lines.append("")

        for i, ace in enumerate(dacl['aces'], 1):
            lines.append(f"ACE #{i}:")
            lines.append(f"  Type: {ace['type']}")
            lines.append(f"  Access Mask: {ace['access_mask']}")
            lines.append(f"  Rights:")
            for right in ace['rights']:
                lines.append(f"    - {right}")
            lines.append(f"  SID: {ace['sid']}")
            lines.append(f"  Account: {ace['sid_name']}")
            lines.append("")

    if 'sacl' in sd:
        sacl = sd['sacl']
        lines.append("SYSTEM ACCESS CONTROL LIST (SACL)")
        lines.append("-" * 70)
        lines.append(f"ACL Revision: {sacl['revision']}")
        lines.append(f"ACE Count: {sacl['ace_count']}")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)

if __name__ == "__main__":
    # Example hex string from user
    hex_acl = "0x94000000010014800000000000000000140000003000000002001C000100000002C0140007000000010100000000000100000000020064000300000000001400070000000101000000000001000000000000240007000000010500000000000515000000D67B9C550F50215711305578728A00000000240007000000010500000000000515000000D67B9C550F50215711305578ED940000"

    print("Parsing Security Descriptor...")
    print(f"Hex length: {len(hex_acl)} characters")

    # Remove 0x prefix
    if hex_acl.startswith('0x'):
        hex_acl = hex_acl[2:]

    data = bytes.fromhex(hex_acl)
    print(f"Data length: {len(data)} bytes")
    print()

    sd = parse_security_descriptor("0x" + hex_acl)
    output = format_output(sd)
    print(output)

    # Extract domain information
    if 'dacl' in sd:
        print("\nDOMAIN INFORMATION:")
        print("-" * 70)
        for ace in sd['dacl']['aces']:
            if ace['sid'].startswith('S-1-5-21-'):
                parts = ace['sid'].split('-')
                if len(parts) >= 8:
                    domain_sid = '-'.join(parts[:8])
                    rid = parts[8]
                    print(f"Domain SID: {domain_sid}")
                    print(f"Relative ID (RID): {rid}")
                    print(f"  - This is likely a domain user or group")
                    print()
