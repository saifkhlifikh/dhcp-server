#!/usr/bin/env python3
"""
DHCP Packet Parser
Handles parsing and building DHCP packets according to RFC 2131.
"""

import struct
import socket
import logging
from enum import IntEnum

logger = logging.getLogger(__name__)


class DHCPMessageType(IntEnum):
    """DHCP Message Types (RFC 2132, Option 53)"""
    DISCOVER = 1
    OFFER = 2
    REQUEST = 3
    DECLINE = 4
    ACK = 5
    NAK = 6
    RELEASE = 7
    INFORM = 8


class DHCPOpCode(IntEnum):
    """DHCP Operation Codes"""
    BOOTREQUEST = 1  # Client to server
    BOOTREPLY = 2    # Server to client


class DHCPOptions:
    """DHCP Option Codes (RFC 2132)"""
    SUBNET_MASK = 1
    ROUTER = 3
    DNS_SERVER = 6
    REQUESTED_IP = 50
    LEASE_TIME = 51
    MESSAGE_TYPE = 53
    SERVER_ID = 54
    PARAMETER_LIST = 55
    END = 255


class DHCPPacket:
    """
    DHCP Packet structure according to RFC 2131.
    
    Format:
    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |     op (1)    |   htype (1)   |   hlen (1)    |   hops (1)    |
    +---------------+---------------+---------------+---------------+
    |                            xid (4)                            |
    +-------------------------------+-------------------------------+
    |           secs (2)            |           flags (2)           |
    +-------------------------------+-------------------------------+
    |                          ciaddr  (4)                          |
    +---------------------------------------------------------------+
    |                          yiaddr  (4)                          |
    +---------------------------------------------------------------+
    |                          siaddr  (4)                          |
    +---------------------------------------------------------------+
    |                          giaddr  (4)                          |
    +---------------------------------------------------------------+
    |                          chaddr  (16)                         |
    +---------------------------------------------------------------+
    |                          sname   (64)                         |
    +---------------------------------------------------------------+
    |                          file    (128)                        |
    +---------------------------------------------------------------+
    |                          options (variable)                   |
    +---------------------------------------------------------------+
    """
    
    MAGIC_COOKIE = b'\x63\x82\x53\x63'  # 99.130.83.99
    
    def __init__(self):
        # Header fields
        self.op = 0           # Message op code
        self.htype = 1        # Hardware address type (1 = Ethernet)
        self.hlen = 6         # Hardware address length
        self.hops = 0         # Client sets to zero
        self.xid = 0          # Transaction ID
        self.secs = 0         # Seconds elapsed
        self.flags = 0        # Flags
        self.ciaddr = '0.0.0.0'  # Client IP address
        self.yiaddr = '0.0.0.0'  # Your (client) IP address
        self.siaddr = '0.0.0.0'  # Server IP address
        self.giaddr = '0.0.0.0'  # Gateway IP address
        self.chaddr = b''     # Client hardware address
        self.sname = b''      # Server host name
        self.file = b''       # Boot file name
        self.options = {}     # DHCP options
        
    @staticmethod
    def parse(data):
        """Parse raw DHCP packet data."""
        if len(data) < 236:
            raise ValueError(f"DHCP packet too short: {len(data)} bytes (minimum 236)")
        
        packet = DHCPPacket()
        
        try:
            # Unpack fixed-size header (first 236 bytes)
            header = struct.unpack('!BBBB I HH 4s 4s 4s 4s 16s 64s 128s', data[:236])
            
            packet.op = header[0]
            packet.htype = header[1]
            packet.hlen = header[2]
            packet.hops = header[3]
            packet.xid = header[4]
            packet.secs = header[5]
            packet.flags = header[6]
            packet.ciaddr = socket.inet_ntoa(header[7])
            packet.yiaddr = socket.inet_ntoa(header[8])
            packet.siaddr = socket.inet_ntoa(header[9])
            packet.giaddr = socket.inet_ntoa(header[10])
            packet.chaddr = header[11][:packet.hlen]
            packet.sname = header[12]
            packet.file = header[13]
            
        except struct.error as e:
            raise ValueError(f"Failed to unpack DHCP header: {e}")
        
        # Parse options (after magic cookie)
        packet.options = {}
        
        if len(data) > 236:
            options_data = data[236:]
            
            # Check if we have enough data for magic cookie
            if len(options_data) >= 4:
                magic = options_data[:4]
                
                # Check magic cookie
                if magic == DHCPPacket.MAGIC_COOKIE:
                    try:
                        packet.options = DHCPPacket._parse_options(options_data[4:])
                    except Exception as e:
                        logger.warning(f"Failed to parse options: {e}")
                        packet.options = {}
                else:
                    logger.warning(f"Invalid DHCP magic cookie")
                    logger.warning(f"  Expected: {DHCPPacket.MAGIC_COOKIE.hex()}")
                    logger.warning(f"  Received: {magic.hex()}")
                    logger.warning(f"  Packet length: {len(data)} bytes")
            else:
                logger.debug(f"No options data (packet length: {len(data)})")
        
        return packet
    
    @staticmethod
    def _parse_options(options_data):
        """Parse DHCP options field."""
        options = {}
        i = 0
        
        while i < len(options_data):
            option_code = options_data[i]
            
            # End option
            if option_code == DHCPOptions.END:
                break
            
            # Pad option
            if option_code == 0:
                i += 1
                continue
            
            # Get option length
            if i + 1 >= len(options_data):
                break
                
            option_length = options_data[i + 1]
            
            if i + 2 + option_length > len(options_data):
                break
            
            # Extract option data
            option_data = options_data[i + 2:i + 2 + option_length]
            options[option_code] = option_data
            
            i += 2 + option_length
        
        return options
    
    def build(self):
        """Build DHCP packet as bytes."""
        # Pack header
        packet = struct.pack(
            '!BBBB I HH 4s 4s 4s 4s',
            self.op,
            self.htype,
            self.hlen,
            self.hops,
            self.xid,
            self.secs,
            self.flags,
            socket.inet_aton(self.ciaddr),
            socket.inet_aton(self.yiaddr),
            socket.inet_aton(self.siaddr),
            socket.inet_aton(self.giaddr)
        )
        
        # Add chaddr (pad to 16 bytes)
        chaddr_padded = self.chaddr + (b'\x00' * (16 - len(self.chaddr)))
        packet += chaddr_padded
        
        # Add sname (pad to 64 bytes)
        sname_padded = self.sname + (b'\x00' * (64 - len(self.sname)))
        packet += sname_padded
        
        # Add file (pad to 128 bytes)
        file_padded = self.file + (b'\x00' * (128 - len(self.file)))
        packet += file_padded
        
        # Add magic cookie
        packet += self.MAGIC_COOKIE
        
        # Add options
        for code, value in self.options.items():
            packet += bytes([code, len(value)]) + value
        
        # Add end option
        packet += bytes([DHCPOptions.END])
        
        return packet
    
    def get_message_type(self):
        """Get DHCP message type."""
        if DHCPOptions.MESSAGE_TYPE in self.options:
            return self.options[DHCPOptions.MESSAGE_TYPE][0]
        return None
    
    def get_client_mac(self):
        """Get client MAC address as string."""
        return ':'.join(f'{b:02x}' for b in self.chaddr)
    
    def get_requested_ip(self):
        """Get requested IP address."""
        if DHCPOptions.REQUESTED_IP in self.options:
            return socket.inet_ntoa(self.options[DHCPOptions.REQUESTED_IP])
        return None
    
    def __str__(self):
        """String representation of packet."""
        msg_type = self.get_message_type()
        msg_type_name = DHCPMessageType(msg_type).name if msg_type else "UNKNOWN"
        
        return (
            f"DHCP {msg_type_name} Packet\n"
            f"  Transaction ID: 0x{self.xid:08x}\n"
            f"  Client MAC: {self.get_client_mac()}\n"
            f"  Client IP: {self.ciaddr}\n"
            f"  Your IP: {self.yiaddr}\n"
            f"  Server IP: {self.siaddr}\n"
            f"  Options: {len(self.options)}"
        )