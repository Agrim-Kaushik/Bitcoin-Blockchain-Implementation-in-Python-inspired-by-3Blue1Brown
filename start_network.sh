#!/bin/bash
# Startup script for running a 5-node blockchain network
# 2 miners + 3 regular nodes

echo "Starting Blockchain Network..."
echo "================================"

# Kill any existing processes on these ports
for port in 5001 5002 5003 5004 5005; do
    lsof -ti:$port | xargs kill -9 2>/dev/null
done

# Clean up old data (optional - comment out to keep existing blockchain)
rm -rf node_* miner_node_*

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Starting nodes..."

# Start Node 1 (Miner)
python3 -u run_node.py --name "Miner1" --port 5001 --dir "miner_node_5001" --miner --peers 5002 5003 5004 5005 > logs/miner_node_5001.log 2>&1 &
sleep 1

# Start Node 2 (Miner)
python3 -u run_node.py --name "Miner2" --port 5002 --dir "miner_node_5002" --miner --peers 5001 5003 5004 5005 > logs/miner_node_5002.log 2>&1 &
sleep 1

# Start Node 3 (Regular)
python3 -u run_node.py --name "Node3" --port 5003 --dir "node_5003" --peers 5001 5002 5004 5005 > logs/node_5003.log 2>&1 &
sleep 1

# Start Node 4 (Regular)
python3 -u run_node.py --name "Node4" --port 5004 --dir "node_5004" --peers 5001 5002 5003 5005 > logs/node_5004.log 2>&1 &
sleep 1

# Start Node 5 (Regular)
python3 -u run_node.py --name "Node5" --port 5005 --dir "node_5005" --peers 5001 5002 5003 5004 > logs/node_5005.log 2>&1 &
sleep 1

echo ""
echo "All nodes started!"
echo ""
echo "To view logs:"
echo "  Miner1:  tail -f logs/miner_node_5001.log"
echo "  Miner2:  tail -f logs/miner_node_5002.log"
echo "  Node3:   tail -f logs/node_5003.log"
echo "  Node4:   tail -f logs/node_5004.log"
echo "  Node5:   tail -f logs/node_5005.log"
echo ""
echo "To stop all nodes: ./stop_network.sh"
echo "To run transactions: python3 simulate_transactions.py --config txs1.json"
