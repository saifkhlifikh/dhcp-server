#!/usr/bin/env python3
"""
DHCP Lease Manager
Handles lease tracking, persistence, and expiration.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class LeaseManager:
    """Manages DHCP leases with persistence."""
    
    def __init__(self, lease_file='leases.json', default_lease_time=86400):
        """
        Initialize lease manager.
        
        Args:
            lease_file (str): Path to lease database file
            default_lease_time (int): Default lease time in seconds (default: 24h)
        """
        self.lease_file = Path(lease_file)
        self.default_lease_time = default_lease_time
        self.leases = {}  # MAC -> lease info
        
        self.load_leases()
    
    def load_leases(self):
        """Load leases from disk."""
        if self.lease_file.exists():
            try:
                with open(self.lease_file, 'r') as f:
                    self.leases = json.load(f)
                logger.info(f"Loaded {len(self.leases)} leases from {self.lease_file}")
            except Exception as e:
                logger.error(f"Failed to load leases: {e}")
                self.leases = {}
        else:
            logger.info("No existing lease file found, starting fresh")
            self.leases = {}
    
    def save_leases(self):
        """Save leases to disk."""
        try:
            with open(self.lease_file, 'w') as f:
                json.dump(self.leases, f, indent=2)
            logger.debug(f"Saved {len(self.leases)} leases to {self.lease_file}")
        except Exception as e:
            logger.error(f"Failed to save leases: {e}")
    
    def create_lease(self, mac_address, ip_address, lease_time=None):
        """
        Create or update a lease.
        
        Args:
            mac_address (str): Client MAC address
            ip_address (str): Assigned IP address
            lease_time (int, optional): Lease time in seconds
        """
        if lease_time is None:
            lease_time = self.default_lease_time
        
        now = datetime.now()
        expires_at = now + timedelta(seconds=lease_time)
        
        self.leases[mac_address] = {
            'ip_address': ip_address,
            'start_time': now.isoformat(),
            'expires_at': expires_at.isoformat(),
            'lease_time': lease_time
        }
        
        self.save_leases()
        logger.info(f"Created lease: {mac_address} -> {ip_address} (expires: {expires_at})")
    
    def get_lease(self, mac_address):
        """
        Get lease information for a MAC address.
        
        Args:
            mac_address (str): Client MAC address
            
        Returns:
            dict: Lease info or None if not found
        """
        return self.leases.get(mac_address)
    
    def release_lease(self, mac_address):
        """
        Release a lease.
        
        Args:
            mac_address (str): Client MAC address
            
        Returns:
            bool: True if released, False if not found
        """
        if mac_address in self.leases:
            released = self.leases.pop(mac_address)
            self.save_leases()
            logger.info(f"Released lease for {mac_address} ({released['ip_address']})")
            return True
        
        return False
    
    def is_lease_valid(self, mac_address):
        """Check if a lease is still valid (not expired)."""
        lease = self.get_lease(mac_address)
        if not lease:
            return False
        
        expires_at = datetime.fromisoformat(lease['expires_at'])
        return datetime.now() < expires_at
    
    def cleanup_expired_leases(self):
        """Remove expired leases."""
        now = datetime.now()
        expired = []
        
        for mac, lease in self.leases.items():
            expires_at = datetime.fromisoformat(lease['expires_at'])
            if now >= expires_at:
                expired.append(mac)
        
        for mac in expired:
            self.leases.pop(mac)
            logger.info(f"Removed expired lease for {mac}")
        
        if expired:
            self.save_leases()
        
        return len(expired)
    
    def get_all_leases(self):
        """Get all active leases."""
        return self.leases.copy()
    
    def get_stats(self):
        """Get lease statistics."""
        total = len(self.leases)
        expired = 0
        now = datetime.now()
        
        for lease in self.leases.values():
            expires_at = datetime.fromisoformat(lease['expires_at'])
            if now >= expires_at:
                expired += 1
        
        return {
            'total': total,
            'active': total - expired,
            'expired': expired
        }