import random
from Block import Block
from Transaction import Transaction
import threading
from copy import deepcopy

class Blockchain:
    difficulty = 4
    BLOCK_SIZE_LIMIT = 3
    MINING_REWARD = 10

    def __init__(self):
        self.chain = []
        self.lock = threading.Lock()
        self.create_genesis_block()

    def create_genesis_block(self):
        # Use fixed, deterministic values so all nodes share the same genesis
        genesis = Block(
            index=0,
            transactions=[{"type": "genesis", "message": "Genesis Block"}],
            prev_hash="0",
            timestamp=0,   # fixed timestamp
            nonce=0        # fixed nonce
        )
        # Hash is now deterministic across all nodes
        genesis.hash = genesis.generate_hash()
        self.chain.append(genesis)

    def last_block(self):
        with self.lock:
            return self.chain[-1]

    def add_block(self, block, block_hash):
        """Try to append block to this chain if valid (prev_hash matches and hash is valid)."""
        with self.lock:
            prev_hash = self.chain[-1].hash
            if prev_hash != block.prev_hash:
                return False
            if not self.is_valid_block(block, block_hash):
                return False
            block.hash = block_hash
            self.chain.append(block)
            return True

    def is_valid_block(self, block, block_hash):
        """Validate block's hash and difficulty."""
        if not block_hash.startswith("0" * Blockchain.difficulty):
            return False
        return block.generate_hash() == block_hash

    def is_valid_chain(self, chain):
        """Validate an entire chain object (list of Blocks)."""
        if not chain:
            return False

        # genesis
        if chain[0].prev_hash != "0":
            return False

        for i in range(1, len(chain)):
            curr = chain[i]
            prev = chain[i - 1]

            if curr.prev_hash != prev.hash:
                return False
            if not curr.hash.startswith("0" * Blockchain.difficulty):
                return False
            if curr.generate_hash() != curr.hash:
                return False

        return True

    def replace_chain(self, new_chain):
        """Replace local chain with new_chain if longer and valid."""
        with self.lock:
            if len(new_chain) > len(self.chain) and self.is_valid_chain(new_chain):
                self.chain = deepcopy(new_chain)
                return True
        return False

    def get_chain_copy(self):
        with self.lock:
            return deepcopy(self.chain)

    def proof_of_work(self, block):
        block.nonce = 0
        h = block.generate_hash()
        while not h.startswith("0" * Blockchain.difficulty):
            block.nonce += 1
            h = block.generate_hash()
        return h

    def get_balance(self, pubkey):
        """Calculate balance for a public key from the blockchain (blockchain history = currency acc to video)"""
        balance = 100  # Initial balance for all accounts

        with self.lock:
            for block in self.chain[1:]:  # Skip genesis
                for tx in block.transactions:
                    if isinstance(tx, Transaction):
                        if tx.sender_pubkey == pubkey:
                            balance -= (tx.amount + tx.fee)
                        if tx.receiver_pubkey == pubkey:
                            balance += tx.amount

        return balance

    # This is also known as pending transaction
    def get_balance_with_mempool(self, pubkey, mempool):
        """Calculate balance considering both blockchain and mempool"""
        balance = self.get_balance(pubkey)

        # Subtract pending outgoing transactions from balance
        for tx in mempool:
            if isinstance(tx, Transaction) and tx.sender_pubkey == pubkey:
                balance -= (tx.amount + tx.fee)

        return balance
