#!/usr/bin/env python3
"""
Production DHCP Server
A complete DHCP server implementation with RFC 2131 compliance.
"""

import socket
import json
import logging
import struct
from datetime import datetime

from dhcp_packet import DHCPPacket, DHCPMessageType, DHCPOpCode, DHCPOptions
from ip_manager import IPManager
from lease_manager import LeaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_file='config.json'):
    """Load DHCP configuration from JSON file."""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Configuration loaded from {config_file}")
        return config
    except FileNotFoundError:
        logger.error(f"Config file {config_file} not found")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        raise


class DHCPServer:
    """Complete DHCP Server implementation with RFC 2131 compliance."""
    
    def __init__(self, config):
        self.config = config
        self.server_ip = config['server_ip']
        self.subnet_mask = config['subnet_mask']
        self.gateway = config['gateway']
        self.dns_servers = config['dns_servers']
        self.lease_time = config['lease_time']
        
        # Initialize managers
        self.ip_manager = IPManager(
            config['ip_pool_start'],
            config['ip_pool_end']
        )
        self.lease_manager = LeaseManager(
            lease_file='leases.json',
            default_lease_time=self.lease_time
        )
        
        self.server_socket = None
        
    def start(self):
        """Start the DHCP server."""
        logger.info("=" * 60)
        logger.info("Starting DHCP Server...")
        logger.info("=" * 60)
        logger.info(f"Server IP: {self.server_ip}")
        logger.info(f"IP Pool: {self.config['ip_pool_start']} - {self.config['ip_pool_end']}")
        logger.info(f"Subnet Mask: {self.subnet_mask}")
        logger.info(f"Gateway: {self.gateway}")
        logger.info(f"DNS Servers: {', '.join(self.dns_servers)}")
        logger.info(f"Default Lease Time: {self.lease_time}s ({self.lease_time // 3600}h)")
        logger.info("=" * 60)
        
        # Clean up expired leases
        expired = self.lease_manager.cleanup_expired_leases()
        if expired:
            logger.info(f"Cleaned up {expired} expired leases")
        
        # Create UDP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Bind to DHCP server port (67)
        try:
            self.server_socket.bind(('', 67))
            logger.info("✓ Server listening on port 67")
            logger.info("=" * 60)
        except PermissionError:
            logger.error("✗ Permission denied. Run as administrator/root to bind to port 67")
            return
        except Exception as e:
            logger.error(f"✗ Failed to start server: {e}")
            return
        
        # Main server loop
        self.listen()
    
    def listen(self):
        """Listen for DHCP requests."""
        logger.info("Waiting for DHCP requests...\n")
        
        try:
            while True:
                data, address = self.server_socket.recvfrom(1024)
                logger.info(f"📨 Received packet from {address} ({len(data)} bytes)")
                
                try:
                    self.handle_request(data, address)
                except Exception as e:
                    logger.error(f"Error handling request: {e}", exc_info=True)
                
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 60)
            logger.info("Shutting down server...")
            self.print_stats()
            self.server_socket.close()
            logger.info("Server stopped")
            logger.info("=" * 60)
    
    def handle_request(self, data, address):
        """Handle incoming DHCP request."""
        # Parse packet
        try:
            packet = DHCPPacket.parse(data)
        except Exception as e:
            logger.error(f"Failed to parse packet: {e}")
            return
        
        # Get message type
        msg_type = packet.get_message_type()
        if msg_type is None:
            logger.warning("Packet has no message type")
            return
        
        logger.info(f"📋 {packet}")
        
        # Route to appropriate handler
        if msg_type == DHCPMessageType.DISCOVER:
            self.handle_discover(packet, address)
        elif msg_type == DHCPMessageType.REQUEST:
            self.handle_request_packet(packet, address)
        elif msg_type == DHCPMessageType.RELEASE:
            self.handle_release(packet, address)
        else:
            logger.warning(f"Unhandled message type: {DHCPMessageType(msg_type).name}")
    
    def handle_discover(self, packet, address):
        """Handle DHCP DISCOVER message."""
        logger.info("🔍 Processing DISCOVER...")
        
        mac = packet.get_client_mac()
        requested_ip = packet.get_requested_ip()
        
        # Allocate IP
        allocated_ip = self.ip_manager.allocate_ip(mac, requested_ip)
        
        if not allocated_ip:
            logger.error(f"No available IP for {mac}")
            return
        
        # Build OFFER packet
        offer = self.build_offer(packet, allocated_ip)
        
        # Send OFFER
        self.send_packet(offer, address)
        logger.info(f"✓ Sent OFFER: {allocated_ip} to {mac}\n")
    
    def handle_request_packet(self, packet, address):
        """Handle DHCP REQUEST message."""
        logger.info("📝 Processing REQUEST...")
        
        mac = packet.get_client_mac()
        requested_ip = packet.get_requested_ip() or packet.ciaddr
        
        # Check if we can provide this IP
        allocated_ip = self.ip_manager.get_ip(mac)
        
        if allocated_ip and allocated_ip == requested_ip:
            # Create lease
            self.lease_manager.create_lease(mac, allocated_ip, self.lease_time)
            
            # Build ACK packet
            ack = self.build_ack(packet, allocated_ip)
            
            # Send ACK
            self.send_packet(ack, address)
            logger.info(f"✓ Sent ACK: {allocated_ip} to {mac}")
            logger.info(f"✓ Lease created (expires in {self.lease_time // 3600}h)\n")
        else:
            # Send NAK
            logger.warning(f"Cannot provide requested IP {requested_ip} to {mac}")
            # TODO: Implement NAK packet
    
    def handle_release(self, packet, address):
        """Handle DHCP RELEASE message."""
        logger.info("🔓 Processing RELEASE...")
        
        mac = packet.get_client_mac()
        
        # Release lease and IP
        self.lease_manager.release_lease(mac)
        self.ip_manager.release_ip(mac)
        
        logger.info(f"✓ Released IP for {mac}\n")
    
    def build_offer(self, request_packet, offered_ip):
        """Build DHCP OFFER packet."""
        offer = DHCPPacket()
        offer.op = DHCPOpCode.BOOTREPLY
        offer.htype = request_packet.htype
        offer.hlen = request_packet.hlen
        offer.xid = request_packet.xid
        offer.flags = request_packet.flags
        offer.yiaddr = offered_ip
        offer.siaddr = self.server_ip
        offer.chaddr = request_packet.chaddr
        
        # Add options
        offer.options[DHCPOptions.MESSAGE_TYPE] = bytes([DHCPMessageType.OFFER])
        offer.options[DHCPOptions.SERVER_ID] = socket.inet_aton(self.server_ip)
        offer.options[DHCPOptions.LEASE_TIME] = struct.pack('!I', self.lease_time)
        offer.options[DHCPOptions.SUBNET_MASK] = socket.inet_aton(self.subnet_mask)
        offer.options[DHCPOptions.ROUTER] = socket.inet_aton(self.gateway)
        
        # Add DNS servers
        dns_bytes = b''.join(socket.inet_aton(dns) for dns in self.dns_servers)
        offer.options[DHCPOptions.DNS_SERVER] = dns_bytes
        
        return offer
    
    def build_ack(self, request_packet, assigned_ip):
        """Build DHCP ACK packet."""
        ack = DHCPPacket()
        ack.op = DHCPOpCode.BOOTREPLY
        ack.htype = request_packet.htype
        ack.hlen = request_packet.hlen
        ack.xid = request_packet.xid
        ack.flags = request_packet.flags
        ack.yiaddr = assigned_ip
        ack.siaddr = self.server_ip
        ack.chaddr = request_packet.chaddr
        
        # Add options
        ack.options[DHCPOptions.MESSAGE_TYPE] = bytes([DHCPMessageType.ACK])
        ack.options[DHCPOptions.SERVER_ID] = socket.inet_aton(self.server_ip)
        ack.options[DHCPOptions.LEASE_TIME] = struct.pack('!I', self.lease_time)
        ack.options[DHCPOptions.SUBNET_MASK] = socket.inet_aton(self.subnet_mask)
        ack.options[DHCPOptions.ROUTER] = socket.inet_aton(self.gateway)
        
        # Add DNS servers
        dns_bytes = b''.join(socket.inet_aton(dns) for dns in self.dns_servers)
        ack.options[DHCPOptions.DNS_SERVER] = dns_bytes
        
        return ack
    
    def send_packet(self, packet, address):
        """Send DHCP packet."""
        data = packet.build()
        
        # Broadcast to 255.255.255.255:68 (DHCP client port)
        broadcast_address = ('255.255.255.255', 68)
        self.server_socket.sendto(data, broadcast_address)
    
    def print_stats(self):
        """Print server statistics."""
        ip_stats = self.ip_manager.get_stats()
        lease_stats = self.lease_manager.get_stats()
        
        logger.info("\n📊 Server Statistics:")
        logger.info(f"  IP Pool: {ip_stats['allocated']}/{ip_stats['total']} allocated ({ip_stats['utilization']})")
        logger.info(f"  Leases: {lease_stats['active']} active, {lease_stats['expired']} expired")


def main():
    """Main entry point."""
    print("\n")
    print("=" * 60)
    print("  Production DHCP Server - RFC 2131 Compliant")
    print("=" * 60)
    print()
    
    # Load configuration
    config = load_config()
    
    # Create and start server
    server = DHCPServer(config)
    server.start()


if __name__ == "__main__":
    main()