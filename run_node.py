#!/usr/bin/env python3
import argparse
import time
import threading
from Node import Node

def main():
    parser = argparse.ArgumentParser(description='Run a blockchain node')
    parser.add_argument('--name', required=True, help='Node name')
    parser.add_argument('--port', type=int, required=True, help='Port to listen on')
    parser.add_argument('--dir', required=True, help='Node directory')
    parser.add_argument('--miner', action='store_true', help='Enable mining')
    parser.add_argument('--peers', nargs='*', help='Peer ports (e.g., 5001 5002)')

    args = parser.parse_args()

    # Create node
    node = Node(args.name, args.port, args.dir, is_miner=args.miner)

    # Add peers
    if args.peers:
        for peer_port in args.peers:
            node.add_peer('localhost', int(peer_port))

    print(f"[{args.name}] Started {'miner' if args.miner else 'node'} on port {args.port}")
    print(f"[{args.name}] Public key: {node.public_key_str[:50]}...")
    print(f"[{args.name}] Initial balance: {node.get_balance()}")

    # Start mining loop if miner
    if args.miner:
        def mining_loop():
            while True:
                node.mine()
                time.sleep(0.2)  # Mining interval

        mining_thread = threading.Thread(target=mining_loop, daemon=True)
        mining_thread.start()
        print(f"[{args.name}] Mining started")

    # Keep node running
    try:
        while True:
            time.sleep(1)
            # Periodically print status
            if int(time.time()) % 5 == 0:
                balance = node.get_balance()
                mempool_size = len(node.mempool)
                chain_len = len(node.blockchain.chain)
                print(f"[{args.name}] Status - Balance: {balance}, Mempool: {mempool_size}, Chain: {chain_len} blocks")
    except KeyboardInterrupt:
        print(f"\n[{args.name}] Shutting down...")
        node.save_blockchain()

if __name__ == '__main__':
    main()
