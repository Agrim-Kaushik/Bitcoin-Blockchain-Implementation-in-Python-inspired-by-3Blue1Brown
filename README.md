# Bitcoin Blockchain Implementation in Python inspired by [3Blue1Brown](https://youtu.be/bBC-nXj3Ng4?si=9bvOCZlV6NtbyOGl) video

A toy simulation of Bitcoin-like blockchain system inspired by this video from **([3Blue1Brown](https://youtu.be/bBC-nXj3Ng4?si=9bvOCZlV6NtbyOGl))**. It supports multiple nodes(non-miners) carrying out transactions, multiple mining nodes competing to miner those transactions , gossip-based propagation like real blockchain protocol used in bitcoin, rewards for miners (Coinbase Transactions) for mining, chain synchronization every few seconds, each node with it's own local ledger and public, private(secret) keys and a lot more.

## Features

- ✅ **Account-based balance model** (initial balance: 100 per node just like in video)
- ✅ **Cryptographically signed transactions** using ECDSA
- ✅ **Unique transaction IDs**
- ✅ **Mempool-aware** (orphaned txns are added back to mempool if they're not in winning chain and not already pending)
- ✅ **Gossip protocol** for transaction and block propagation
- ✅ **Mining rewards and transaction fees**
- ✅ **Multi-process architecture** (each node runs independently)
- ✅ **Persistent storage** (.env files for keys, blockchain.json for chain state)
- ✅ **External transaction simulation** with configurable timing and concurrency

---

## System Architecture

### Components

1. **Transaction.py** - Transaction structure 
2. **Block.py** - Block structure
3. **Blockchain.py** - Blockchain logic 
4. **Node.py** - Node (miner or non-miner) implementation 
5. **run_node.py** - Script to run individual nodes
6. **simulate_transactions.py** - Transaction simulator

### Node Types

- **Regular Nodes**: Maintain blockchain, validate transactions, participate in network
- **Miners**: All of the above + mine blocks and earn rewards (Miner is just a non-miner node with a mining flag enabled)

---

## Installation

### Requirements

```bash
pip install cryptography
```

### Files Structure

```
blockchain-system/
├── Transaction.py
├── Block.py
├── Blockchain.py
├── Node.py
├── run_node.py
├── simulate_transactions.py
├── start_network.sh
├── stop_network.sh
├── example_transactions.json
├── logs/
└── node_*/  (created automatically for each node)
    ├── .env  (public/private keys)
    └── blockchain.json  (local blockchain ledger copy)
```

---

## Quick Start

### Option 1: Automated Network Startup (lazy and better approach)

```bash
# Start a 5-node network (2 miners + 3 non-miner nodes)
chmod +x start_network.sh (make it executable)
./start_network.sh 

# View logs in separate terminals
tail -f logs/node_5001.log  # Miner 1
tail -f logs/node_5002.log  # Miner 2
tail -f logs/node_5003.log  # Node 3
tail -f logs/node_5004.log  # Node 4
tail -f logs/node_5005.log  # Node 5

# Simulate transactions
python3 simulate_transactions.py --config example_transactions.json

# Stop the network
./stop_network.sh
```

### Option 2: Manual Node Startup

#### Terminal 1 - Miner 1
```bash
python3 run_node.py --name "Miner1" --port 5001 --dir "node_5001" --miner --peers 5002 5003
```

#### Terminal 2 - Miner 2
```bash
python3 run_node.py --name "Miner2" --port 5002 --dir "node_5002" --miner --peers 5001 5003
```

#### Terminal 3 - Regular Node
```bash
python3 run_node.py --name "Node3" --port 5003 --dir "node_5003" --peers 5001 5002
```

---

## Transaction Simulation

### Configuration Format

Create a JSON file (e.g., `transactions.json`):

```json
{
  "transactions": [
    {
      "sender_port": 5001,
      "receiver_port": 5002,
      "amount": 10,
      "fee": 1,
      "delay": 0,
      "parallel": false
    },
    {
      "sender_port": 5002,
      "receiver_port": 5003,
      "amount": 5,
      "fee": 0.5,
      "delay": 2,
      "parallel": false
    }
  ]
}
```

### Configuration Parameters

- **sender_port**: Port of the sending node
- **receiver_port**: Port of the receiving node
- **amount**: Transaction amount
- **fee**: Transaction fee (paid to miner)
- **delay**: After how much time you want to perform this transaction (preferably for sequential transactions)
- **parallel**: Those which are true, are processed concurrently in background (This was to simulate simultaneous transactions)

### Run Simulations

```bash
python3 simulate_transactions.py --config tsx1.json
```

---

## Transaction Flow

1. **External script** sends the transaction parameters to sender node
2. **Sender node**:
   - Validates sufficient balance ( blockchain(confirmed txns)+mempool(pending txns) )
   - Generates unique transaction ID
   - Signs transaction with private key
   - Adds to its mempool
   - **Gossips transaction** to all peers
3. **Receiving nodes**:
   - Verify signature
   - Validate balance
   - Add to their mempools
   - Propagate to their peers
4. **Miners**:
   - Select transactions from mempool sorted by fee
   - Mine block with transactions + they get their reward and fee
   - Broadcast mined block
   - Balances are updated

---

## Key Features Explained

### 1. Account-Based Balances

- Every node starts with **100** units just like in video
- Balances calculated from blockchain state
- Transactions validated against available balance

### 2. Signed Transactions

- Each transaction signed with sender's **ECDSA private key**
- Signature verified by all nodes before acceptance
- Invalid signatures rejected immediately

### 3. Mempool-Aware

Before accepting a transaction, nodes check:
- Net balance = blockchain balance - pending outgoing transactions
- Orphaned transactions(txns in losing fork chain) are added back to mempool if they're not in winning chain and not already pending

### 4. Mining Rewards

- Block reward: **10 units**
- Plus sum of all transaction fees in the block
- Paid via special COINBASE transaction

### 5. Gossip Protocol

- Transactions propagate peer-to-peer
- Each node forwards to all its peers

### 6. Chain Synchronization 

- Each node requests chain from it's peers every few seconds (4s - 6s) to remain synchronized  

---

## Flexible - Create Your Own Network !

### Add Custom Nodes

```bash
python3 run_node.py \
  --name "MyNode" \
  --port 6000 \
  --dir "node_6000" \
  --peers 5001 5002 5003
```

### Add Custom Miner

```bash
python3 run_node.py \
  --name "MyMiner" \
  --port 6001 \
  --dir "node_6001" \
  --miner \
  --peers 5001 5002 5003
```

### Configuring Mining Difficulty

Edit `Blockchain.py`:
```python
class Blockchain:
    difficulty = 4  # Number of leading zeros required
    BLOCK_SIZE_LIMIT = 3  # Max transactions each block can possess
    MINING_REWARD = 10  # Block reward
```

---

## Monitoring

### View Node Status

Each node prints periodic status updates:
```
[Miner1] Status - Balance: 120, Mempool: 2, Chain: 15 blocks
```

### Check Blockchain

View blockchain file (blockchain.json) or:
```bash
cat miner_node_5001/blockchain.json 
```

### Check Keys

View public key (in your node's .env) or:
```bash
grep -A 10 "PUBLIC_KEY_START" miner_node_5001/.env
```

---

## Testing Scenarios

### Scenario 1: Simple Transfer
```json
{
  "transactions": [
    {"sender_port": 5001, "receiver_port": 5002, "amount": 10, "fee": 1, "delay": 0}
  ]
}
```

### Scenario 2: Concurrent Transactions - see tx1.json

### Scenario 3: Sequential Transfers - see tx2.json

---

## Troubleshooting

### Port Already in Use 
Kill processes on specific port
```bash
lsof -ti:5001 | xargs kill -9
```
or restart network with
```bash
./start_network.sh
```


### Node Can't Connect to Peers
- Ensure all peer nodes are running
- Check firewall settings
- Verify port numbers in --peers argument

### Transaction Rejected
- Check sender has sufficient balance
- Verify transaction is properly formatted
- Check node logs for error messages

### Blockchain Not Syncing
- Ensure nodes are connected (check peers list)
- Verify blockchain.json is valid JSON
- Try deleting blockchain.json and restarting

---

## System Constraints / Scope for Future Improvements 

- Account-based (not UTXO) but we're following the video so okay
- Mining difficulty does not auto-adjust 

---

## License

This is a demonstration blockchain system for educational purposes.

---

## Support

For issues or questions, reach out at agrimkaushik25@gmail.com
