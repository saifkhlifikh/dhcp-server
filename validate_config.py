#!/usr/bin/env python3
"""
Configuration Validator
Validates DHCP server configuration including reservations.
"""

import json
import ipaddress
import sys


def validate_config(config_file='config.json'):
    """Validate configuration file."""
    print("Validating configuration...")
    print("=" * 60)
    
    errors = []
    warnings = []
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Config file '{config_file}' not found")
        return False
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        return False
    
    # Required fields
    required_fields = ['server_ip', 'subnet_mask', 'gateway', 'dns_servers', 
                      'ip_pool_start', 'ip_pool_end', 'lease_time']
    
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        print("\nERRORS:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    # Validate IP addresses
    try:
        ipaddress.IPv4Address(config['server_ip'])
        print(f"Server IP: {config['server_ip']} (valid)")
    except ValueError:
        errors.append(f"Invalid server_ip: {config['server_ip']}")
    
    try:
        ipaddress.IPv4Address(config['subnet_mask'])
        print(f"Subnet Mask: {config['subnet_mask']} (valid)")
    except ValueError:
        errors.append(f"Invalid subnet_mask: {config['subnet_mask']}")
    
    try:
        ipaddress.IPv4Address(config['gateway'])
        print(f"Gateway: {config['gateway']} (valid)")
    except ValueError:
        errors.append(f"Invalid gateway: {config['gateway']}")
    
    # Validate DNS servers
    for dns in config['dns_servers']:
        try:
            ipaddress.IPv4Address(dns)
        except ValueError:
            errors.append(f"Invalid DNS server: {dns}")
    print(f"DNS Servers: {', '.join(config['dns_servers'])} (valid)")
    
    # Validate IP pool
    try:
        pool_start = ipaddress.IPv4Address(config['ip_pool_start'])
        pool_end = ipaddress.IPv4Address(config['ip_pool_end'])
        
        if pool_start > pool_end:
            errors.append("ip_pool_start must be less than or equal to ip_pool_end")
        else:
            pool_size = int(pool_end) - int(pool_start) + 1
            print(f"IP Pool: {config['ip_pool_start']} - {config['ip_pool_end']} ({pool_size} addresses)")
    except ValueError as e:
        errors.append(f"Invalid IP pool: {e}")
    
    # Validate reservations
    if 'reservations' in config:
        print(f"\nReservations: {len(config['reservations'])} configured")
        reserved_ips = set()
        
        for mac, ip in config['reservations'].items():
            # Validate MAC format
            if not is_valid_mac(mac):
                warnings.append(f"Invalid MAC address format: {mac}")
            
            # Validate IP
            try:
                ip_addr = ipaddress.IPv4Address(ip)
                
                # Check for duplicate IPs
                if ip in reserved_ips:
                    errors.append(f"Duplicate reserved IP: {ip}")
                reserved_ips.add(ip)
                
                # Check if in pool (warning only)
                if pool_start <= ip_addr <= pool_end:
                    warnings.append(f"Reserved IP {ip} is in dynamic pool range")
                
                print(f"  {mac} -> {ip} (valid)")
                
            except ValueError:
                errors.append(f"Invalid reserved IP for {mac}: {ip}")
    else:
        print("\nReservations: None configured")
    
    # Print results
    print("\n" + "=" * 60)
    
    if errors:
        print("\nERRORS FOUND:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
    
    print("\nConfiguration is valid!")
    return True


def is_valid_mac(mac):
    """Check if MAC address format is valid."""
    # Remove common separators
    mac_clean = mac.replace(':', '').replace('-', '').replace('.', '')
    
    # Should be 12 hex characters
    if len(mac_clean) != 12:
        return False
    
    try:
        int(mac_clean, 16)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    success = validate_config(config_file)
    sys.exit(0 if success else 1)