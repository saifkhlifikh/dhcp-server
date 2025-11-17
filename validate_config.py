#!/usr/bin/env python3
"""
Configuration Validator (updated for multi-subnet)
"""

import json
import ipaddress
import sys

def is_valid_mac(mac):
    mac_clean = mac.replace(':', '').replace('-', '').replace('.', '')
    if len(mac_clean) != 12: return False
    try:
        int(mac_clean, 16)
        return True
    except ValueError:
        return False

def validate_config(config_file='config.json'):
    print("Validating configuration...")
    with open(config_file, 'r') as f:
        config = json.load(f)

    errors = []
    warnings = []

    if 'subnets' in config:
        subnets = config['subnets']
        if not isinstance(subnets, list) or not subnets:
            errors.append("subnets must be a non-empty list")
        else:
            for s in subnets:
                required = ['network', 'ip_pool_start', 'ip_pool_end']
                for r in required:
                    if r not in s:
                        errors.append(f"Subnet missing required field: {r}")
                # Validate network
                try:
                    net = ipaddress.IPv4Network(s['network'], strict=False)
                except Exception as e:
                    errors.append(f"Invalid network in subnet {s.get('name','')}: {e}")
                # Validate IP pool
                try:
                    start = ipaddress.IPv4Address(s['ip_pool_start'])
                    end = ipaddress.IPv4Address(s['ip_pool_end'])
                    if start > end:
                        errors.append(f"ip_pool_start must be <= ip_pool_end in subnet {s.get('name','')}")
                except Exception as e:
                    errors.append(f"Invalid pool IP in subnet {s.get('name','')}: {e}")
                # Validate reservations
                for mac, ip in s.get('reservations', {}).items():
                    if not is_valid_mac(mac):
                        warnings.append(f"Invalid MAC format in subnet {s.get('name','')}: {mac}")
                    try:
                        ipaddress.IPv4Address(ip)
                    except Exception:
                        errors.append(f"Invalid reserved IP for {mac}: {ip} in subnet {s.get('name','')}")
    else:
        # legacy single-pool checks
        required = ['ip_pool_start', 'ip_pool_end', 'lease_time']
        for r in required:
            if r not in config:
                errors.append(f"Missing required field: {r}")

    # Global reservations
    for mac, ip in config.get('reservations', {}).items():
        if not is_valid_mac(mac):
            warnings.append(f"Invalid MAC format for global reservation: {mac}")
        try:
            ipaddress.IPv4Address(ip)
        except Exception:
            errors.append(f"Invalid IP in global reservation: {mac} -> {ip}")

    if errors:
        print("ERRORS:")
        for e in errors:
            print(" -", e)
        return False
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(" -", w)
    print("Configuration looks valid")
    return True

if __name__ == "__main__":
    cfg = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    ok = validate_config(cfg)
    sys.exit(0 if ok else 1)