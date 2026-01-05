import time
import json
from hashlib import sha256
from Transaction import Transaction

class Block:
    def __init__(self, index, transactions, prev_hash, timestamp=None, nonce=0, hash_val=None):
        self.index = index
        self.timestamp = time.time() if timestamp is None else timestamp
        self.transactions = transactions  # List of Transaction objects
        self.prev_hash = prev_hash
        self.nonce = nonce
        self.hash = hash_val if hash_val is not None else self.generate_hash()

    def generate_hash(self):
        # Convert transactions to dictionaries for hashing
        tx_data = [tx.to_dict() if isinstance(tx, Transaction) else tx for tx in self.transactions]
        data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": tx_data,
            "prev_hash": self.prev_hash,
            "nonce": self.nonce,
        }
        block_string = json.dumps(data, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        tx_data = [tx.to_dict() if isinstance(tx, Transaction) else tx for tx in self.transactions]
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": tx_data,
            "prev_hash": self.prev_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }

    @staticmethod
    def from_dict(data):
        transactions = [Transaction.from_dict(tx) if isinstance(tx, dict) and 'tx_id' in tx else tx 
                       for tx in data['transactions']]
        return Block(
            index=data['index'],
            transactions=transactions,
            prev_hash=data['prev_hash'],
            timestamp=data.get('timestamp'),
            nonce=data.get('nonce', 0),
            hash_val=data.get('hash')
        )

    def __repr__(self):
        return f"Block(index={self.index}, txns={len(self.transactions)}, hash={self.hash[:10]}...)"
