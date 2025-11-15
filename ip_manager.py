#!/usr/bin/env python3
"""
IP Address Pool Manager
Manages the allocation of IP addresses from a configured pool with MAC reservations.
"""

import ipaddress
import logging

logger = logging.getLogger(__name__)


class IPManager:
    """Manages IP address allocation from a pool with MAC address reservations."""
    
    def __init__(self, pool_start, pool_end, reservations=None):
        """
        Initialize IP pool with optional MAC reservations.
        
        Args:
            pool_start (str): Starting IP address (e.g., "192.168.1.100")
            pool_end (str): Ending IP address (e.g., "192.168.1.200")
            reservations (dict): MAC to IP mapping for reserved addresses
        """
        self.pool_start = ipaddress.IPv4Address(pool_start)
        self.pool_end = ipaddress.IPv4Address(pool_end)
        self.reservations = reservations or {}
        
        # Normalize MAC addresses in reservations (lowercase, with colons)
        self.reservations = {
            self._normalize_mac(mac): ip 
            for mac, ip in self.reservations.items()
        }
        
        # Generate list of all IPs in pool
        self.pool = set()
        current = self.pool_start
        while current <= self.pool_end:
            self.pool.add(str(current))
            current += 1
        
        # Validate reservations
        self._validate_reservations()
        
        self.allocated = {}  # MAC -> IP mapping for dynamic allocations
        
        logger.info(f"IP Pool initialized: {len(self.pool)} addresses available")
        if self.reservations:
            logger.info(f"Reservations configured: {len(self.reservations)} MAC addresses")
            for mac, ip in self.reservations.items():
                logger.info(f"  Reserved: {mac} -> {ip}")
    
    def _normalize_mac(self, mac):
        """Normalize MAC address to lowercase with colons."""
        # Remove common separators
        mac = mac.replace('-', ':').replace('.', ':').lower()
        # Ensure consistent format
        parts = mac.split(':')
        if len(parts) == 6:
            return ':'.join(parts)
        return mac
    
    def _validate_reservations(self):
        """Validate that reservations don't conflict with each other or pool."""
        # Check for duplicate IPs in reservations
        reserved_ips = list(self.reservations.values())
        if len(reserved_ips) != len(set(reserved_ips)):
            logger.warning("Duplicate IP addresses found in reservations")
        
        # Check if reserved IPs are in valid range (warning only)
        for mac, ip in self.reservations.items():
            try:
                ip_addr = ipaddress.IPv4Address(ip)
                # Reserved IPs can be outside the pool - that's intentional
                if ip in self.pool:
                    logger.info(f"Reservation {mac} -> {ip} uses pool IP (will be excluded from dynamic pool)")
            except ValueError:
                logger.error(f"Invalid IP address in reservation: {mac} -> {ip}")
    
    def allocate_ip(self, mac_address, requested_ip=None):
        """
        Allocate an IP address to a MAC address.
        
        Priority order:
        1. Check if MAC has a reservation
        2. Check if MAC already has an allocation
        3. Honor requested IP if available
        4. Allocate first available IP from pool
        
        Args:
            mac_address (str): Client MAC address
            requested_ip (str, optional): Requested IP address
            
        Returns:
            str: Allocated IP address or None if unavailable
        """
        mac_address = self._normalize_mac(mac_address)
        
        # Priority 1: Check for MAC reservation
        if mac_address in self.reservations:
            reserved_ip = self.reservations[mac_address]
            self.allocated[mac_address] = reserved_ip
            logger.info(f"MAC {mac_address} using reserved IP {reserved_ip}")
            return reserved_ip
        
        # Priority 2: Check if MAC already has an IP
        if mac_address in self.allocated:
            existing_ip = self.allocated[mac_address]
            logger.info(f"MAC {mac_address} already has IP {existing_ip}")
            return existing_ip
        
        # Priority 3: Try to honor requested IP
        if requested_ip and requested_ip in self.pool:
            # Make sure it's not reserved for someone else
            if requested_ip not in self.reservations.values():
                if requested_ip not in self.allocated.values():
                    self.allocated[mac_address] = requested_ip
                    logger.info(f"Allocated requested IP {requested_ip} to {mac_address}")
                    return requested_ip
                else:
                    logger.warning(f"Requested IP {requested_ip} already allocated")
            else:
                logger.warning(f"Requested IP {requested_ip} is reserved for another MAC")
        
        # Priority 4: Allocate first available IP from pool
        reserved_ips = set(self.reservations.values())
        for ip in self.pool:
            # Skip if IP is reserved or already allocated
            if ip not in reserved_ips and ip not in self.allocated.values():
                self.allocated[mac_address] = ip
                logger.info(f"Allocated new IP {ip} to {mac_address}")
                return ip
        
        logger.error(f"No available IPs in pool for {mac_address}")
        return None
    
    def release_ip(self, mac_address):
        """
        Release an IP address from a MAC address.
        
        Note: Reserved IPs are not actually released, just removed from allocated tracking.
        
        Args:
            mac_address (str): Client MAC address
            
        Returns:
            bool: True if released, False if not found
        """
        mac_address = self._normalize_mac(mac_address)
        
        if mac_address in self.allocated:
            released_ip = self.allocated.pop(mac_address)
            
            # Check if this was a reserved IP
            if mac_address in self.reservations:
                logger.info(f"Released reserved IP {released_ip} from {mac_address} (reservation still active)")
            else:
                logger.info(f"Released IP {released_ip} from {mac_address}")
            return True
        
        logger.warning(f"No IP allocated to {mac_address}")
        return False
    
    def get_ip(self, mac_address):
        """Get allocated IP for a MAC address."""
        mac_address = self._normalize_mac(mac_address)
        
        # Check reservation first
        if mac_address in self.reservations:
            return self.reservations[mac_address]
        
        return self.allocated.get(mac_address)
    
    def is_ip_available(self, ip_address):
        """Check if IP is in pool and available."""
        # Not available if it's reserved for someone else
        if ip_address in self.reservations.values():
            return False
        
        return ip_address in self.pool and ip_address not in self.allocated.values()
    
    def is_reserved(self, mac_address):
        """Check if a MAC address has a reservation."""
        mac_address = self._normalize_mac(mac_address)
        return mac_address in self.reservations
    
    def get_reservation(self, mac_address):
        """Get reserved IP for a MAC address."""
        mac_address = self._normalize_mac(mac_address)
        return self.reservations.get(mac_address)
    
    def get_stats(self):
        """Get pool statistics."""
        reserved_ips = set(self.reservations.values())
        pool_ips_reserved = len([ip for ip in reserved_ips if ip in self.pool])
        available = len(self.pool) - len(self.allocated) - pool_ips_reserved
        
        return {
            'total': len(self.pool),
            'allocated': len(self.allocated),
            'reserved': len(self.reservations),
            'available': available,
            'utilization': f"{(len(self.allocated) / len(self.pool) * 100):.1f}%"
        }