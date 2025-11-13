#!/usr/bin/env python3
"""
Simple DHCP Server
A lightweight DHCP server implementation for learning purposes.
"""

import socket
import json
import logging
from datetime import datetime

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
    """Simple DHCP Server implementation."""
    
    def __init__(self, config):
        self.config = config
        self.leases = {}  # Track IP assignments
        self.server_socket = None
        
    def start(self):
        """Start the DHCP server."""
        logger.info("Starting DHCP server...")
        logger.info(f"IP Pool: {self.config['ip_pool_start']} - {self.config['ip_pool_end']}")
        
        # Create UDP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Bind to DHCP server port (67)
        try:
            self.server_socket.bind(('', 67))
            logger.info("Server listening on port 67")
        except PermissionError:
            logger.error("Permission denied. Run as administrator/root to bind to port 67")
            return
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return
        
        # Main server loop
        self.listen()
    
    def listen(self):
        """Listen for DHCP requests."""
        logger.info("Waiting for DHCP requests...")
        
        try:
            while True:
                data, address = self.server_socket.recvfrom(1024)
                logger.info(f"Received packet from {address}")
                # TODO: Parse and handle DHCP packet
                self.handle_request(data, address)
        except KeyboardInterrupt:
            logger.info("\nShutting down server...")
            self.server_socket.close()
    
    def handle_request(self, data, address):
        """Handle incoming DHCP request."""
        # Placeholder - will implement DHCP packet parsing
        logger.info(f"Packet size: {len(data)} bytes")
        # TODO: Implement DHCP DISCOVER, REQUEST, etc.


def main():
    """Main entry point."""
    print("=" * 50)
    print("Simple DHCP Server")
    print("=" * 50)
    
    # Load configuration
    config = load_config()
    
    # Create and start server
    server = DHCPServer(config)
    server.start()


if __name__ == "__main__":
    main()
