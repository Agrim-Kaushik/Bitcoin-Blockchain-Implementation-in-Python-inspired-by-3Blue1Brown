#!/usr/bin/env python3
import socket
import json
import time
import argparse
import threading
from Transaction import Transaction

def send_transaction_request(sender_port, receiver_pubkey, amount, fee):
    """Send a transaction request to the sender node"""
    try:
        # Create transaction definition message
        msg = {
            'type': 'create_transaction',
            'receiver_pubkey': receiver_pubkey,
            'amount': amount,
            'fee': fee
        }

        # Connect to sender node
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', sender_port))
        s.sendall(json.dumps(msg).encode())
        s.close()

        print(f"Transaction request sent: {amount} to {receiver_pubkey[:8]}... from node on port {sender_port}")
        return True
    except Exception as e:
        print(f"Error sending transaction: {e}")
        return False

def get_node_pubkey(port):
    """Get public key from a node"""
    try:
        msg = {'type': 'get_pubkey'}
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', port))
        s.sendall(json.dumps(msg).encode())

        data = b''
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
        s.close()

        response = json.loads(data.decode())
        return response['pubkey']
    except Exception as e:
        print(f"Error getting pubkey from port {port}: {e}")
        return None

def load_pubkeys(node_ports):
    """Load public keys from all nodes"""
    print("Loading public keys from nodes...")
    pubkeys = {}
    
    for port in node_ports:
        import os
        
        # Check both possible directory names: miner_node_{port} and node_{port}
        possible_dirs = [f"miner_node_{port}", f"node_{port}"]
        env_path = None
        
        for node_dir in possible_dirs:
            test_path = os.path.join(node_dir, '.env')
            if os.path.exists(test_path):
                env_path = test_path
                break
        
        if env_path:
            with open(env_path, 'r') as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                if line.strip() == 'PUBLIC_KEY_START':
                    pubkey = ''.join(lines[i+1:]).split('PUBLIC_KEY_END')[0].strip()
                    pubkeys[port] = pubkey
                    print(f" Port {port}: {pubkey[:50]}...")
                    break
        else:
            print(f" ERROR: Could not find .env for port {port}")
    
    return pubkeys

def simulate_transaction(sender_port, receiver_port, amount, fee, pubkeys):
    """Simulate a single transaction"""
    if receiver_port not in pubkeys:
        print(f"Error: No public key found for receiver port {receiver_port}")
        return False

    receiver_pubkey = pubkeys[receiver_port]

    # Send directly through socket as a transaction creation request
    # The sender node will handle signing and validation
    try:
        msg = {
            'type': 'create_transaction',
            'receiver_pubkey': receiver_pubkey,
            'amount': amount,
            'fee': fee
        }

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', sender_port))
        s.sendall(json.dumps(msg).encode())
        s.close()

        print(f"Transaction: {amount} (fee: {fee}) from port {sender_port} to port {receiver_port}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Simulate blockchain transactions')
    parser.add_argument('--config', required=True, help='JSON config file with transaction scenarios')

    args = parser.parse_args()

    # Load configuration
    with open(args.config, 'r') as f:
        config = json.load(f)

    # Get all node ports from config
    all_ports = set()
    for tx in config['transactions']:
        all_ports.add(tx['sender_port'])
        all_ports.add(tx['receiver_port'])

    # Load public keys
    pubkeys = load_pubkeys(sorted(all_ports))

    print(f"\nStarting transaction simulation with {len(config['transactions'])} transactions...")
    time.sleep(2)  # Give nodes time to fully start

    # Execute transactions
    for i, tx_config in enumerate(config['transactions']):
        sender_port = tx_config['sender_port']
        receiver_port = tx_config['receiver_port']
        amount = tx_config['amount']
        fee = tx_config.get('fee', 0)
        delay = tx_config.get('delay', 0)
        parallel = tx_config.get('parallel', False)

        if delay > 0:
            print(f"\nWaiting {delay} seconds before next transaction...")
            time.sleep(delay)

        print(f"\n--- Transaction {i+1}/{len(config['transactions'])} ---")

        if parallel:
            # Execute in parallel (non-blocking)
            threading.Thread(
                target=simulate_transaction,
                args=(sender_port, receiver_port, amount, fee, pubkeys),
                daemon=True
            ).start()
        else:
            # Execute sequentially (blocking)
            simulate_transaction(sender_port, receiver_port, amount, fee, pubkeys)

        time.sleep(0.1)  # very Small delay between requests just for safety

    print("\nAll transactions submitted!")
    print("Monitor the node terminals to see transaction processing and mining...")

if __name__ == '__main__':
    main()
