#!/usr/bin/env python3
"""
IP Address Pool Manager
Manages the allocation of IP addresses from a configured pool.
"""

import ipaddress
import logging

logger = logging.getLogger(__name__)


class IPManager:
    """Manages IP address allocation from a pool."""
    
    def __init__(self, pool_start, pool_end):
        """
        Initialize IP pool.
        
        Args:
            pool_start (str): Starting IP address (e.g., "192.168.1.100")
            pool_end (str): Ending IP address (e.g., "192.168.1.200")
        """
        self.pool_start = ipaddress.IPv4Address(pool_start)
        self.pool_end = ipaddress.IPv4Address(pool_end)
        
        # Generate list of all IPs in pool
        self.pool = set()
        current = self.pool_start
        while current <= self.pool_end:
            self.pool.add(str(current))
            current += 1
        
        self.allocated = {}  # MAC -> IP mapping
        logger.info(f"IP Pool initialized: {len(self.pool)} addresses available")
    
    def allocate_ip(self, mac_address, requested_ip=None):
        """
        Allocate an IP address to a MAC address.
        
        Args:
            mac_address (str): Client MAC address
            requested_ip (str, optional): Requested IP address
            
        Returns:
            str: Allocated IP address or None if unavailable
        """
        # Check if MAC already has an IP
        if mac_address in self.allocated:
            existing_ip = self.allocated[mac_address]
            logger.info(f"MAC {mac_address} already has IP {existing_ip}")
            return existing_ip
        
        # Try to honor requested IP
        if requested_ip and requested_ip in self.pool:
            if requested_ip not in self.allocated.values():
                self.allocated[mac_address] = requested_ip
                logger.info(f"Allocated requested IP {requested_ip} to {mac_address}")
                return requested_ip
            else:
                logger.warning(f"Requested IP {requested_ip} already allocated")
        
        # Allocate first available IP
        for ip in self.pool:
            if ip not in self.allocated.values():
                self.allocated[mac_address] = ip
                logger.info(f"Allocated new IP {ip} to {mac_address}")
                return ip
        
        logger.error(f"No available IPs in pool for {mac_address}")
        return None
    
    def release_ip(self, mac_address):
        """
        Release an IP address from a MAC address.
        
        Args:
            mac_address (str): Client MAC address
            
        Returns:
            bool: True if released, False if not found
        """
        if mac_address in self.allocated:
            released_ip = self.allocated.pop(mac_address)
            logger.info(f"Released IP {released_ip} from {mac_address}")
            return True
        
        logger.warning(f"No IP allocated to {mac_address}")
        return False
    
    def get_ip(self, mac_address):
        """Get allocated IP for a MAC address."""
        return self.allocated.get(mac_address)
    
    def is_ip_available(self, ip_address):
        """Check if IP is in pool and available."""
        return ip_address in self.pool and ip_address not in self.allocated.values()
    
    def get_stats(self):
        """Get pool statistics."""
        return {
            'total': len(self.pool),
            'allocated': len(self.allocated),
            'available': len(self.pool) - len(self.allocated),
            'utilization': f"{(len(self.allocated) / len(self.pool) * 100):.1f}%"
        }