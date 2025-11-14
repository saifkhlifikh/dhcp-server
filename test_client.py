#!/usr/bin/env python3
"""Simple DHCP client to test the server"""
import socket

def send_discover():
    """Send a DHCP DISCOVER packet."""
    # Create minimal DHCP DISCOVER packet
    packet = b'\x01'  # BOOTREQUEST
    packet += b'\x01\x06\x00'  # Hardware type (Ethernet), length, hops
    packet += b'\x12\x34\x56\x78'  # Transaction ID
    packet += b'\x00' * 24  # Secs, flags, ciaddr, yiaddr, siaddr, giaddr
    packet += b'\xaa\xbb\xcc\xdd\xee\xff' + b'\x00' * 10  # Client MAC address
    packet += b'\x00' * 192  # Server name (64) + boot file (128)
    packet += b'\x63\x82\x53\x63'  # Magic cookie
    packet += b'\x35\x01\x01'  # DHCP Message Type = DISCOVER
    packet += b'\xff'  # End option
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(5)
        
        # Send DISCOVER
        sock.sendto(packet, ('255.255.255.255', 67))
        print("✓ Sent DHCP DISCOVER packet")
        print("  Client MAC: aa:bb:cc:dd:ee:ff")
        print("  Waiting for OFFER...")
        
        # Try to receive OFFER
        try:
            # Bind to client port to receive response
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client_sock.bind(('', 68))
            client_sock.settimeout(5)
            
            response, addr = client_sock.recvfrom(1024)
            print(f"✓ Received OFFER from {addr}")
            print(f"  Response length: {len(response)} bytes")
            
            client_sock.close()
        except socket.timeout:
            print("⚠ No OFFER received (timeout - server might not be running)")
        except PermissionError:
            print("⚠ Cannot bind to port 68 (need admin privileges)")
            print("  But DISCOVER was sent successfully!")
        
        sock.close()
        
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("DHCP Test Client")
    print("=" * 50)
    print()
    send_discover()
    print()
    print("Check your DHCP server logs for activity!")