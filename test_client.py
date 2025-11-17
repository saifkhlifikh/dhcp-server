#!/usr/bin/env python3
import socket

def send_discover():
    packet = b'\x01'
    packet += b'\x01\x06\x00'
    packet += b'\x12\x34\x56\x78'
    packet += b'\x00' * 24
    packet += b'\xaa\xbb\xcc\xdd\xee\xff' + b'\x00' * 10
    packet += b'\x00' * 192
    packet += b'\x63\x82\x53\x63'
    packet += b'\x35\x01\x01'
    packet += b'\xff'
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(5)
        
        sock.sendto(packet, ('255.255.255.255', 67))
        print("✓ Sent DHCP DISCOVER packet")
        print("  Client MAC: aa:bb:cc:dd:ee:ff")
        print("  Waiting for OFFER...")
        
        try:
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
