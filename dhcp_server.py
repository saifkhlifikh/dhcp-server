#!/usr/bin/env python3
"""
Production DHCP Server (updated for multiple-subnet support)
"""

import socket
import json
import logging
import struct

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
    with open(config_file, 'r') as f:
        return json.load(f)


class DHCPServer:
    def __init__(self, config):
        self.config = config
        self.server_ip = config.get('server_ip')  # can be None if multiple subnets
        self.lease_time = config['lease_time']
        # Setup IPManager with subnets or fallback single-pool legacy fields
        subnets = config.get('subnets')
        global_res = config.get('reservations', {})
        if subnets:
            self.ip_manager = IPManager(subnet_configs=subnets, global_reservations=global_res)
        else:
            # Backwards compatibility: synthesize a single-subnet config
            single_sub = {
                'name': 'default',
                'network': f"{config['ip_pool_start']}/32",
                'ip_pool_start': config['ip_pool_start'],
                'ip_pool_end': config['ip_pool_end'],
                'subnet_mask': config.get('subnet_mask'),
                'gateway': config.get('gateway'),
                'dns_servers': config.get('dns_servers', []),
                'reservations': global_res
            }
            self.ip_manager = IPManager(subnet_configs=[single_sub], global_reservations={})

        self.lease_manager = LeaseManager(
            lease_file='leases.json',
            default_lease_time=self.lease_time
        )

        self.server_socket = None

    def start(self):
        logger.info("Starting DHCP Server (multi-subnet enabled)")
        expired = self.lease_manager.cleanup_expired_leases()
        if expired:
            logger.info(f"Cleaned up {expired} expired leases")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            self.server_socket.bind(('', 67))
            logger.info("Server listening on port 67")
        except PermissionError:
            logger.error("Permission denied. Run as admin/root to bind to port 67")
            return
        self.listen()

    def listen(self):
        logger.info("Waiting for DHCP requests...")
        try:
            while True:
                data, address = self.server_socket.recvfrom(4096)
                try:
                    self.handle_request(data, address)
                except Exception as e:
                    logger.error(f"Error handling request: {e}", exc_info=True)
        except KeyboardInterrupt:
            logger.info("Shutting down")
            self.server_socket.close()

    def handle_request(self, data, address):
        packet = DHCPPacket.parse(data)
        msg_type = packet.get_message_type()
        if msg_type is None:
            logger.warning("Packet has no message type")
            return
        logger.info(f"Message type: {DHCPMessageType(msg_type).name} from {packet.get_client_mac()}")
        if msg_type == DHCPMessageType.DISCOVER:
            self.handle_discover(packet, address)
        elif msg_type == DHCPMessageType.REQUEST:
            self.handle_request_packet(packet, address)
        elif msg_type == DHCPMessageType.RELEASE:
            self.handle_release(packet, address)
        else:
            logger.warning(f"Unhandled message type: {msg_type}")

    def handle_discover(self, packet, address):
        mac = packet.get_client_mac()
        requested_ip = packet.get_requested_ip()
        giaddr = getattr(packet, 'giaddr', None)
        allocated_ip, subnet = self.ip_manager.allocate_ip(mac, requested_ip=requested_ip, giaddr=giaddr)
        if not allocated_ip:
            logger.error("No available IP")
            return
        offer = self.build_offer(packet, allocated_ip, subnet)
        self.send_packet(offer)
        logger.info(f"Sent OFFER {allocated_ip} (subnet={subnet.name if subnet else 'unknown'}) to {mac}")

    def handle_request_packet(self, packet, address):
        mac = packet.get_client_mac()
        requested_ip = packet.get_requested_ip() or packet.ciaddr
        giaddr = getattr(packet, 'giaddr', None)
        # Determine which subnet this request is for (if any)
        # ip_manager.get_ip checks reservations and allocations
        allocated_ip = self.ip_manager.get_ip(mac)
        if allocated_ip and allocated_ip == requested_ip:
            # determine subnet object for options
            subnet = self.ip_manager._find_subnet_by_requested_ip(allocated_ip)
            self.lease_manager.create_lease(mac, allocated_ip, self.lease_time)
            ack = self.build_ack(packet, allocated_ip, subnet)
            self.send_packet(ack)
            logger.info(f"Sent ACK {allocated_ip} to {mac}")
        else:
            logger.warning(f"Cannot provide requested IP {requested_ip} to {mac}")
            # TODO: implement NAK

    def handle_release(self, packet, address):
        mac = packet.get_client_mac()
        self.lease_manager.release_lease(mac)
        self.ip_manager.release_ip(mac)
        logger.info(f"Released IP for {mac}")

    def build_offer(self, request_packet, offered_ip, subnet):
        offer = DHCPPacket()
        offer.op = DHCPOpCode.BOOTREPLY
        offer.htype = request_packet.htype
        offer.hlen = request_packet.hlen
        offer.xid = request_packet.xid
        offer.flags = request_packet.flags
        offer.yiaddr = offered_ip
        offer.siaddr = (subnet.gateway if subnet and subnet.gateway else self.server_ip)
        offer.chaddr = request_packet.chaddr

        offer.options[DHCPOptions.MESSAGE_TYPE] = bytes([DHCPMessageType.OFFER])
        offer.options[DHCPOptions.SERVER_ID] = socket.inet_aton(offer.siaddr)
        offer.options[DHCPOptions.LEASE_TIME] = struct.pack('!I', self.lease_time)
        # subnet-specific options
        if subnet:
            offer.options[DHCPOptions.SUBNET_MASK] = socket.inet_aton(subnet.subnet_mask)
            if subnet.gateway:
                offer.options[DHCPOptions.ROUTER] = socket.inet_aton(subnet.gateway)
            if subnet.dns_servers:
                dns_bytes = b''.join(socket.inet_aton(d) for d in subnet.dns_servers)
                offer.options[DHCPOptions.DNS_SERVER] = dns_bytes
        return offer

    def build_ack(self, request_packet, assigned_ip, subnet):
        ack = DHCPPacket()
        ack.op = DHCPOpCode.BOOTREPLY
        ack.htype = request_packet.htype
        ack.hlen = request_packet.hlen
        ack.xid = request_packet.xid
        ack.flags = request_packet.flags
        ack.yiaddr = assigned_ip
        ack.siaddr = (subnet.gateway if subnet and subnet.gateway else self.server_ip)
        ack.chaddr = request_packet.chaddr

        ack.options[DHCPOptions.MESSAGE_TYPE] = bytes([DHCPMessageType.ACK])
        ack.options[DHCPOptions.SERVER_ID] = socket.inet_aton(ack.siaddr)
        ack.options[DHCPOptions.LEASE_TIME] = struct.pack('!I', self.lease_time)
        if subnet:
            ack.options[DHCPOptions.SUBNET_MASK] = socket.inet_aton(subnet.subnet_mask)
            if subnet.gateway:
                ack.options[DHCPOptions.ROUTER] = socket.inet_aton(subnet.gateway)
            if subnet.dns_servers:
                dns_bytes = b''.join(socket.inet_aton(d) for d in subnet.dns_servers)
                ack.options[DHCPOptions.DNS_SERVER] = dns_bytes
        return ack

    def send_packet(self, packet):
        data = packet.build()
        broadcast_address = ('255.255.255.255', 68)
        self.server_socket.sendto(data, broadcast_address)