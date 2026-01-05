#!/bin/bash
echo "Stopping blockchain network..."

for port in 5001 5002 5003 5004 5005; do
    lsof -ti:$port | xargs kill 2>/dev/null
done

echo "Network stopped!"
