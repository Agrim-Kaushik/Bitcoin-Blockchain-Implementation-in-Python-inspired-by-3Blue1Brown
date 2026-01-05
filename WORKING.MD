# How The Simulation Works

Each node runs as one OS process with several threads inside it that handle mining, networking, and sync in parallel.

---
## Big picture per node

```
OS process: python run_node.py --name ... --port ...

  ├── Main thread (from run_node.py)
  │    ├─ Creates Node(...)
  │    ├─ Prints status every 5 seconds
  │    └─ Keeps process alive (sleep loop)
  │
  ├── Server thread (Node.start_server)
  │    └─ Accept loop: accepts incoming TCP connections
  │
  ├── N handler threads (one per connection)
  |    └─ Handles Incoming messages
  │    └─ handle_connection(conn): read 1 JSON message, act on it
  │
  ├── Sync thread (Node.periodic_chain_sync)
  │    └─ Every few seconds: request_chain_from_peers()
  │
  └── [Miners only] Mining thread (mining_loop in run_node.py)
       └─ Repeatedly calls node.mine()

```
---

## System Architecture

### Main thread

1. This is the thread that runs main() in run_node.py.
2. Creates the Node instance, which internally sets up blockchain, keys, server, and sync thread.
3. Adds peers from --peers.
4. Every 5 seconds prints: balance, mempool size, chain length.

### Server thread

1. Listens on the node’s port.
2. For each incoming TCP connection, it spawns a new handler thread and immediately goes back to accept().

### Handler thread (per connection) 
1. Reads all bytes until the remote side closes its write end (EOF).

2. Parses a single JSON message from that data.

3. Dispatches based on msg['type']:
    - "transaction" → add to mempool and gossip
    - "block" → try to commit block.
    - "create_transaction" → locally create + sign tx, then add/gossip.
    - "get_chain" → sends full chain back over the same connection.

4. Finally closes conn.

### Sync thread (chain synchronization)
1. Every few seconds it requests chain from peers and tries to sync if a longer chain is found.

### Mining thread (miners only)
1. Picks txns from mempool and does PoW.
2. If successful, appends it, saves blockchain, and gossips the block.
---

