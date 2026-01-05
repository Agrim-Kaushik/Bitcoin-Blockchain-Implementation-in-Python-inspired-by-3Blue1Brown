import random
import threading
import socket
import json
import time
import os
import traceback
from Block import Block
from Blockchain import Blockchain
from Transaction import Transaction, create_reward_transaction
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

class Node:
    """Base node class with transaction signing and validation"""
#====================================================================================
#                               NODE SETUP
#====================================================================================
    def __init__(self, name, port, node_dir, is_miner=False):
        self.name = name
        self.port = port
        self.node_dir = node_dir
        self.is_miner = is_miner
        self.blockchain = Blockchain()
        self.mempool = []
        self.lock = threading.Lock()
        self.peers = []  # List of (host, port) tuples
        self.socket = None
        
        # Load or generate keys
        os.makedirs(node_dir, exist_ok=True)
        self.private_key, self.public_key = self.load_or_generate_keys()
        self.public_key_str = self.public_key_to_string(self.public_key).strip()
        
        # Ensure blockchain.json exists with at least the genesis block
        self.ensure_blockchain_file()

        # Load blockchain
        self.load_blockchain()
        
        # Start listening for connections
        self.start_server()

        # Start periodic chain synchronization
        sync_thread = threading.Thread(target=self.periodic_chain_sync, daemon=True)
        sync_thread.start()
    
    def load_or_generate_keys(self):
        """Load keys from .env or generate new ones"""
        env_path = os.path.join(self.node_dir, '.env')
        
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
                private_pem = None
                public_pem = None
                
                for i, line in enumerate(lines):
                    if line.strip() == 'PRIVATE_KEY_START':
                        private_pem = ''.join(lines[i+1:]).split('PRIVATE_KEY_END')[0].strip()
                    if line.strip() == 'PUBLIC_KEY_START':
                        public_pem = ''.join(lines[i+1:]).split('PUBLIC_KEY_END')[0].strip()
                
                if private_pem and public_pem:
                    private_key = serialization.load_pem_private_key(
                        private_pem.encode(),
                        password=None,
                        backend=default_backend()
                    )
                    public_key = serialization.load_pem_public_key(
                        public_pem.encode(),
                        backend=default_backend()
                    )
                    return private_key, public_key
        
        # Generate new keys through ecdsa
        private_key = ec.generate_private_key(
            ec.SECP256K1(),
            backend=default_backend()
        )

        public_key = private_key.public_key()

        # Save to .env
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        with open(env_path, 'w') as f:
            f.write('PRIVATE_KEY_START\n')
            f.write(private_pem)
            f.write('PRIVATE_KEY_END\n\n')
            f.write('PUBLIC_KEY_START\n')
            f.write(public_pem)
            f.write('PUBLIC_KEY_END\n')
        
        return private_key, public_key
    
    def public_key_to_string(self, public_key):
        """Convert public key to string for storage"""
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode()
    
    def string_to_public_key(self, key_str):
        """Convert string to public key object"""
        return serialization.load_pem_public_key(
            key_str.encode(),
            backend=default_backend()
        )
    
#====================================================================================
#                           TRANSACTION FUNCTIONS
#====================================================================================
    def sign_transaction(self, tx):
        """Sign a transaction with private key (ECDSA)"""
        signature = self.private_key.sign(
            tx.get_signing_data(),
            ec.ECDSA(hashes.SHA256())
        )
        tx.signature = signature.hex()
        return tx
    
    def verify_transaction(self, tx):
        """Verify transaction signature and validity (ECDSA)"""
        # Skip verification for coinbase transactions
        if tx.sender_pubkey == "COINBASE":
            return True
        if not tx.signature:
            return False

        try:
            public_key = self.string_to_public_key(tx.sender_pubkey)
            public_key.verify(
                bytes.fromhex(tx.signature),
                tx.get_signing_data(),
                ec.ECDSA(hashes.SHA256())
            )

            # Verify sender has sufficient balance
            balance = self.blockchain.get_balance_with_mempool(tx.sender_pubkey, self.mempool)
            if balance < tx.amount + tx.fee:
                print(f"[{self.name}] Transaction {tx.tx_id[:8]} rejected: insufficient balance ({balance} < {tx.amount + tx.fee})")
                return False
            return True

        except (InvalidSignature, Exception) as e:
            print(f"[{self.name}] Transaction verification failed: {e}")
            return False

    
    def create_and_sign_transaction(self, receiver_pubkey, amount, fee=0):
        """Create and sign a transaction"""
        # Check balance
        balance = self.blockchain.get_balance_with_mempool(self.public_key_str, self.mempool)
        if balance < amount + fee:
            print(f"[{self.name}] Insufficient balance: {balance} < {amount + fee}")
            return None
        
        tx = Transaction(
            sender_pubkey=self.public_key_str,
            receiver_pubkey=receiver_pubkey,
            amount=amount,
            fee=fee
        )
        
        tx = self.sign_transaction(tx)
        return tx
    
    def add_transaction(self, tx):
        """Adds a validated transaction to the mempool and gossips it"""
        # Check if already in blockchain, node can get mined txn in form of a block and appends to it blockchain 
        # before it gets the same txn via gossip, we prevent duplicate like that
        chain_copy = self.blockchain.get_chain_copy()
        for block in chain_copy:
            for btx in block.transactions:
                if isinstance(btx, Transaction) and isinstance(tx, Transaction):
                    if btx.tx_id == tx.tx_id:
                        return False
        
        # Verify transaction
        if not self.verify_transaction(tx):
            return False
        
        # Add to mempool
        with self.lock:
            if tx not in self.mempool:
                self.mempool.append(tx)
                print(f"[{self.name}] Added transaction {tx.tx_id[:8]} to mempool")
                
                # Gossip to peers
                self.gossip_transaction(tx)
                return True
        return False
    
    def gossip_transaction(self, tx):
        """Send transaction to all peers"""
        msg = {
            'type': 'transaction',
            'data': tx.to_dict()
        }
        self.broadcast_to_peers(msg)
    
#====================================================================================
#                           BLOCK FUNCTIONS
#====================================================================================
    def receive_block(self, block):
        """Process a received block"""
        # if not block.hash.startswith("0" * Blockchain.difficulty):
        #     return False

        # if block.generate_hash() != block.hash:
        #     return False

        # add_block checks both above conditions already
        appended = self.blockchain.add_block(block, block.hash)
        if appended:
            # Remove included txns from own mempool
            with self.lock:
                for tx in block.transactions:
                    if isinstance(tx, Transaction) and tx in self.mempool:
                        self.mempool.remove(tx)

            print(f"[{self.name}] Accepted block #{block.index}")

            # Persist updated chain on *all* nodes
            self.save_blockchain()

            # Broadcast to peers
            self.gossip_block(block)
            return True
        
        # Block did not append – possible fork so try to sync from peers
        # This is lightweight and runs rarely.
        self.request_chain_from_peers()
        return False

    def gossip_block(self, block):
        """Send block to all peers"""
        msg = {
            'type': 'block',
            'data': block.to_dict()
        }
        self.broadcast_to_peers(msg)

#====================================================================================
#                           UTILITY FUNCTIONS                                       
#====================================================================================
    def start_server(self):
        """Start listening for incoming connections"""
        def server_thread():
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('localhost', self.port))
            self.socket.listen(1)
            print(f"[{self.name}] Listening on port {self.port}")
            
            while True:
                try:
                    conn, addr = self.socket.accept()
                    threading.Thread(target=self.handle_connection, args=(conn,), daemon=True).start()
                except:
                    break
        
        threading.Thread(target=server_thread, daemon=True).start()
        time.sleep(0.1)
    
    def handle_connection(self, conn):
        """Handle incoming connection"""
        try:
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            
            if data:
                msg = json.loads(data.decode())
                
                if msg['type'] == 'transaction':
                    tx = Transaction.from_dict(msg['data'])
                    self.add_transaction(tx)
                elif msg['type'] == 'block':
                    block = Block.from_dict(msg['data'])
                    self.receive_block(block)
                elif msg['type'] == 'create_transaction':
                    # Node creates, signs, and broadcasts transaction
                    tx = self.create_and_sign_transaction(
                        msg['receiver_pubkey'],
                        msg['amount'],
                        msg.get('fee', 0)
                    )
                    if tx:
                        self.add_transaction(tx)
                elif msg['type'] == 'get_chain':
                    # Peer is asking for our current chain
                    self.send_chain(conn)
        except Exception as e:
            print(f"[{self.name}] Error handling connection: {e}")
        finally:
            conn.close()
    
    def broadcast_to_peers(self, msg):
        """Send message to all peers"""
        for peer_host, peer_port in self.peers:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                s.connect((peer_host, peer_port))
                s.sendall(json.dumps(msg).encode())
                s.close()
            except:
                pass  # Silently ignore failed peer connections
    
    def add_peer(self, host, port):
        """Add a peer to this node's peer list"""
        if (host, port) not in self.peers and port != self.port:
            self.peers.append((host, port))

#====================================================================================
#                   FORK RESOLUTION AND CHAIN SYNCHRONIZATION
#====================================================================================

    def send_chain(self, conn):
        """Send this node's blockchain over an existing connection."""
        try:
            chain_copy = self.blockchain.get_chain_copy()
            chain_data = [block.to_dict() for block in chain_copy]
            response = {
                'type': 'chain',
                'data': chain_data
            }
            conn.sendall(json.dumps(response).encode())
        except Exception as e:
            print(f"[{self.name}] Error sending chain: {e}")

    def handle_chain_response(self, chain_data):
        """Try to replace local chain with a received one (longest-chain rule + orphan tx re-injection)."""
        try:
            # Wo chain jiski copy aayi hai dusre node se
            new_chain = [Block.from_dict(b) for b in chain_data]

            # Snapshot old chain *before* replacement (Current state of blockchain of this node)
            old_chain = self.blockchain.get_chain_copy()

            # Build tx_id -> Transaction maps for old and new chains (skip genesis)
            old_tx_map = {}
            for block in old_chain[1:]:
                for tx in block.transactions:
                    if isinstance(tx, Transaction):
                        old_tx_map[tx.tx_id] = tx

            new_tx_ids = set()
            for block in new_chain[1:]:
                for tx in block.transactions:
                    if isinstance(tx, Transaction):
                        new_tx_ids.add(tx.tx_id)

            # Try to replace chain
            replaced = self.blockchain.replace_chain(new_chain)
            
            if replaced:
                print(f"[{self.name}] Replaced local chain with longer received chain ({len(new_chain)} blocks)")

                # 1) Clean mempool: remove txs that are *now* in the adopted chain
                with self.lock:
                    self.mempool = [
                        tx for tx in self.mempool
                        if not (isinstance(tx, Transaction) and tx.tx_id in new_tx_ids)
                    ]

                    # 2) Re-inject orphan-only transactions from the old chain:
                    #    those that were in old_chain but are NOT in new_chain.
                    orphan_only_ids = set(old_tx_map.keys()) - new_tx_ids
                    for tx_id in orphan_only_ids:
                        tx = old_tx_map[tx_id]

                        # Optionally re-validate under the new chain's balances
                        if not self.verify_transaction(tx):
                            continue

                        if tx not in self.mempool:
                            self.mempool.append(tx)

                # Persist updated chain
                self.save_blockchain()

        except Exception as e:
            print(f"[{self.name}] Error handling chain response: {e}")

    def request_chain_from_peers(self):
        """Ask all peers for their chain; Blockchain.replace_chain decides whether to adopt."""
        # print(f"[{self.name}] Starting chain sync from peers")
        for peer_host, peer_port in self.peers:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(10)
                s.connect((peer_host, peer_port))
                msg = {'type': 'get_chain'}
                s.sendall(json.dumps(msg).encode())

                # IMPORTANT: tell server we're done sending
                s.shutdown(socket.SHUT_WR)

                data = b''
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    
                if data:
                    resp = json.loads(data.decode())
                    if resp.get('type') == 'chain':
                        # print(f"[{self.name}] Received chain data and handling it")
                        self.handle_chain_response(resp['data'])
                s.close()
            except Exception as e:
                print(f"[{self.name}] Sync with peer port:{peer_port} was reset by peer, will try to sync again in next cycle")

    def periodic_chain_sync(self):
        """Periodically synchronize chain with peers (longest-chain wins)."""
        while True:
            time.sleep(3 + random.uniform(0,2))
            self.request_chain_from_peers()

#====================================================================================
#                               MINER LOGIC
#====================================================================================

    def mine(self):
        """Mine a new block (only for miners)"""
        if not self.is_miner:
            return None
        
        if not self.mempool:
            return None
        
        txs_to_mine = self.pick_transactions(Blockchain.BLOCK_SIZE_LIMIT - 1)
        if not txs_to_mine:
            return None
        
        # Calculate total fees
        total_fees = sum(tx.fee for tx in txs_to_mine if isinstance(tx, Transaction))
        
        # Create reward transaction
        reward_tx = create_reward_transaction(self.public_key_str, Blockchain.MINING_REWARD, total_fees)
        
        # Add reward transaction first
        all_txs = [reward_tx] + txs_to_mine
        
        last_block = self.blockchain.last_block()
        new_block = Block(last_block.index + 1, all_txs, last_block.hash)
        block_hash = self.blockchain.proof_of_work(new_block)
        new_block.hash = block_hash
        
        appended = self.blockchain.add_block(new_block, block_hash)
        if appended:
            print(f"[{self.name}] ⛏️  Mined Block #{new_block.index} with {len(txs_to_mine)} txns, reward={Blockchain.MINING_REWARD + total_fees}")
            
            # Remove included txns from own mempool
            with self.lock:
                for tx in txs_to_mine:
                    if tx in self.mempool:
                        self.mempool.remove(tx)
            
            # Save blockchain (update/commit block to own ledger first)
            self.save_blockchain()
            
            # Broadcast block
            self.gossip_block(new_block)
            # return new_block  <= no use of returning this 
        return None

    def pick_transactions(self, limit):
        """Select transactions from mempool for mining"""
        with self.lock:
            # Sort by fee (highest first)
            sorted_txs = sorted(self.mempool, key=lambda tx: tx.fee if isinstance(tx, Transaction) else 0, reverse=True)
            return sorted_txs[:limit]

#====================================================================================
#                           BLOCKCHAIN FUNCTIONS
#====================================================================================
    def save_blockchain(self):
        """Save blockchain to JSON file"""
        chain_data = [block.to_dict() for block in self.blockchain.get_chain_copy()]
        blockchain_path = os.path.join(self.node_dir, 'blockchain.json')
        with open(blockchain_path, 'w') as f:
            json.dump(chain_data, f, indent=2)
    
    def ensure_blockchain_file(self):
        """Ensure blockchain.json exists (initialized with the current chain, including genesis)."""
        blockchain_path = os.path.join(self.node_dir, 'blockchain.json')
        if not os.path.exists(blockchain_path):
            self.save_blockchain()
            print(f"[{self.name}] Initialized new blockchain.json with genesis block")

    def load_blockchain(self):
        """Load blockchain from JSON file"""
        blockchain_path = os.path.join(self.node_dir, 'blockchain.json')
        if os.path.exists(blockchain_path):
            try:
                with open(blockchain_path, 'r') as f:
                    chain_data = json.load(f)
                    new_chain = [Block.from_dict(block_data) for block_data in chain_data]
                    if self.blockchain.is_valid_chain(new_chain):
                        with self.blockchain.lock:
                            self.blockchain.chain = new_chain
                        print(f"[{self.name}] Loaded blockchain with {len(new_chain)} blocks")
            except Exception as e:
                print(f"[{self.name}] Error loading blockchain: {e}")

#====================================================================================
#                           FUCKASS FUNCTIONS
#====================================================================================
    def get_balance(self):
        """Get this node's balance"""
        return self.blockchain.get_balance(self.public_key_str)
    
    def __repr__(self):
        return f"Node(name='{self.name}', port={self.port}, is_miner={self.is_miner})"
     