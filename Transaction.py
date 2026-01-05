import time
import json
import hashlib
import uuid
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

class Transaction:
    def __init__(self, sender_pubkey, receiver_pubkey, amount, fee=0, tx_id=None, signature=None, timestamp=None):
        self.tx_id = tx_id if tx_id else str(uuid.uuid4())
        self.sender_pubkey = sender_pubkey
        self.receiver_pubkey = receiver_pubkey
        self.amount = amount
        self.fee = fee
        self.timestamp = timestamp if timestamp else time.time()
        self.signature = signature

    def to_dict(self):
        return {
            'tx_id': self.tx_id,
            'sender_pubkey': self.sender_pubkey,
            'receiver_pubkey': self.receiver_pubkey,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp,
            'signature': self.signature
        }

    def get_signing_data(self):
        """Returns the data that should be signed (without signature)"""
        data = {
            'tx_id': self.tx_id,
            'sender_pubkey': self.sender_pubkey,
            'receiver_pubkey': self.receiver_pubkey,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp
        }
        return json.dumps(data, sort_keys=True).encode()

    @staticmethod
    def from_dict(data):
        return Transaction(
            sender_pubkey=data['sender_pubkey'],
            receiver_pubkey=data['receiver_pubkey'],
            amount=data['amount'],
            fee=data.get('fee', 0),
            tx_id=data['tx_id'],
            signature=data.get('signature'),
            timestamp=data.get('timestamp')
        )

    def __eq__(self, other):
        if isinstance(other, Transaction):
            return self.tx_id == other.tx_id
        return False

    def __hash__(self):
        return hash(self.tx_id)

    def __repr__(self):
        return f"Tx({self.tx_id[:8]}... {self.amount} from {self.sender_pubkey[:8]}... to {self.receiver_pubkey[:8]}...)"

def create_reward_transaction(miner_pubkey, amount, fee_sum):
    """Create a mining reward transaction"""
    tx = Transaction(
        sender_pubkey="COINBASE",
        receiver_pubkey=miner_pubkey,
        amount=amount + fee_sum,
        fee=0,
        tx_id=str(uuid.uuid4())
    )
    tx.signature = "COINBASE"
    return tx
