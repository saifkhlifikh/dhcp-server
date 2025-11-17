#!/usr/bin/env python3
"""
IP Address Pool Manager with Multiple Subnet Support.

Responsibilities:
- Manage multiple subnet pools
- Honor per-subnet reservations
- Select subnet by giaddr, requested IP, or default
- Provide allocation, release, and lookup functions
"""

import ipaddress
import logging

logger = logging.getLogger(__name__)


class Subnet:
    def __init__(self, name, network_cidr, pool_start, pool_end,
                 subnet_mask=None, gateway=None, dns_servers=None, reservations=None):
        self.name = name
        self.network = ipaddress.IPv4Network(network_cidr, strict=False)
        self.subnet_mask = subnet_mask or str(self.network.netmask)
        self.gateway = gateway
        self.dns_servers = dns_servers or []
        self.reservations = {self._normalize_mac(mac): ip for mac, ip in (reservations or {}).items()}
        # Build pool set of strings
        start = ipaddress.IPv4Address(pool_start)
        end = ipaddress.IPv4Address(pool_end)
        self.pool = set()
        cur = start
        while cur <= end:
            self.pool.add(str(cur))
            cur += 1
        # allocated: mac -> ip
        self.allocated = {}

    def _normalize_mac(self, mac):
        mac = mac.replace('-', ':').replace('.', ':').lower()
        parts = mac.split(':')
        if len(parts) == 6:
            return ':'.join(parts)
        return mac

    def has_ip(self, ip):
        try:
            return ipaddress.IPv4Address(ip) in self.network
        except Exception:
            return False

    def is_ip_available(self, ip):
        if ip in self.reservations.values():
            return False
        return ip in self.pool and ip not in self.allocated.values()

    def allocate_for_mac(self, mac, requested_ip=None):
        mac = self._normalize_mac(mac)
        # Reservation for this MAC in this subnet?
        if mac in self.reservations:
            reserved_ip = self.reservations[mac]
            self.allocated[mac] = reserved_ip
            logger.info(f"[{self.name}] MAC {mac} using reserved IP {reserved_ip}")
            return reserved_ip

        # Already allocated?
        if mac in self.allocated:
            return self.allocated[mac]

        # Honor requested IP if available and belongs to this subnet pool
        if requested_ip and requested_ip in self.pool:
            if requested_ip not in self.reservations.values() and requested_ip not in self.allocated.values():
                self.allocated[mac] = requested_ip
                logger.info(f"[{self.name}] Allocated requested IP {requested_ip} to {mac}")
                return requested_ip
            else:
                logger.debug(f"[{self.name}] Requested IP {requested_ip} not available")

        # Allocate first available
        reserved_ips = set(self.reservations.values())
        for ip in sorted(self.pool, key=lambda x: tuple(int(p) for p in x.split('.'))):
            if ip not in reserved_ips and ip not in self.allocated.values():
                self.allocated[mac] = ip
                logger.info(f"[{self.name}] Allocated IP {ip} to {mac}")
                return ip

        logger.warning(f"[{self.name}] No available IPs")
        return None

    def release(self, mac):
        mac = self._normalize_mac(mac)
        if mac in self.allocated:
            ip = self.allocated.pop(mac)
            logger.info(f"[{self.name}] Released IP {ip} for {mac}")
            return True
        return False

    def get_ip_for_mac(self, mac):
        mac = self._normalize_mac(mac)
        if mac in self.reservations:
            return self.reservations[mac]
        return self.allocated.get(mac)


class IPManager:
    """Top-level manager that handles multiple subnets."""

    def __init__(self, subnet_configs=None, global_reservations=None):
        """
        subnet_configs: list of dicts with subnet configuration
        global_reservations: optional dict of mac->ip for backward compatibility
        """
        self.subnets = []
        self.global_reservations = {self._normalize_mac(k): v for k, v in (global_reservations or {}).items()}
        if subnet_configs:
            for s in subnet_configs:
                name = s.get('name') or f"{s.get('ip_pool_start')}-{s.get('ip_pool_end')}"
                subnet = Subnet(
                    name=name,
                    network_cidr=s.get('network') or f"{s.get('ip_pool_start')}/32",
                    pool_start=s['ip_pool_start'],
                    pool_end=s['ip_pool_end'],
                    subnet_mask=s.get('subnet_mask'),
                    gateway=s.get('gateway'),
                    dns_servers=s.get('dns_servers', []),
                    reservations=s.get('reservations', {})
                )
                # exclude reserved IPs from dynamic pool if they overlap (info only)
                self.subnets.append(subnet)
        logger.info(f"Initialized IPManager with {len(self.subnets)} subnet(s)")

    def _normalize_mac(self, mac):
        mac = mac.replace('-', ':').replace('.', ':').lower()
        parts = mac.split(':')
        if len(parts) == 6:
            return ':'.join(parts)
        return mac

    def _find_subnet_by_giaddr(self, giaddr):
        if not giaddr:
            return None
        for subnet in self.subnets:
            # Check if giaddr is the gateway or inside the subnet network
            if subnet.gateway and giaddr == subnet.gateway:
                return subnet
            if subnet.has_ip(giaddr):
                return subnet
        return None

    def _find_subnet_by_requested_ip(self, requested_ip):
        if not requested_ip:
            return None
        for subnet in self.subnets:
            if subnet.has_ip(requested_ip):
                return subnet
        return None

    def allocate_ip(self, mac, requested_ip=None, giaddr=None):
        """
        Returns tuple (ip, subnet) where subnet is Subnet object.
        Allocation strategy:
          1) global reservation
          2) subnet selection by giaddr
          3) subnet selection by requested_ip
          4) fallback to first subnet with available IP
        """
        mac_norm = self._normalize_mac(mac)

        # Global reservation check
        if mac_norm in self.global_reservations:
            ip = self.global_reservations[mac_norm]
            # find subnet that owns this IP
            subnet = self._find_subnet_by_requested_ip(ip)
            # If not found, just return ip with None subnet (outside configured subnets)
            return ip, subnet

        # 1. try giaddr
        subnet = self._find_subnet_by_giaddr(giaddr)
        if subnet:
            ip = subnet.allocate_for_mac(mac, requested_ip=requested_ip)
            return ip, subnet

        # 2. try requested_ip subnet
        subnet = self._find_subnet_by_requested_ip(requested_ip)
        if subnet:
            ip = subnet.allocate_for_mac(mac, requested_ip=requested_ip)
            return ip, subnet

        # 3. fallback: first subnet with available IP
        for subnet in self.subnets:
            ip = subnet.allocate_for_mac(mac, requested_ip=None)
            if ip:
                return ip, subnet

        return None, None

    def get_ip(self, mac):
        mac_norm = self._normalize_mac(mac)
        # check global reservations
        if mac_norm in self.global_reservations:
            return self.global_reservations[mac_norm]
        # check per-subnet allocations/reservations
        for subnet in self.subnets:
            ip = subnet.get_ip_for_mac(mac)
            if ip:
                return ip
        return None

    def release_ip(self, mac):
        mac_norm = self._normalize_mac(mac)
        for subnet in self.subnets:
            if subnet.release(mac):
                return True
        return False

    def get_stats(self):
        total = sum(len(s.pool) for s in self.subnets)
        allocated = sum(len(s.allocated) for s in self.subnets)
        reserved = sum(len(s.reservations) for s in self.subnets) + len(self.global_reservations)
        return {
            'total': total,
            'allocated': allocated,
            'reserved': reserved,
            'subnets': [{ 'name': s.name, 'network': str(s.network), 'allocated': len(s.allocated), 'reserved': len(s.reservations) } for s in self.subnets]
        }