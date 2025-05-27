#!/bin/bash

# Start the number server in the background
echo "Starting number server..."
python3 number_server.py > server_log.txt 2>&1 &
SERVER_PID=$!

# Wait for server to initialize
sleep 2

# Start two instances of the app
echo "Starting first instance..."
python3 main.py &
INSTANCE1_PID=$!

echo "Starting second instance..."
python3 main.py &
INSTANCE2_PID=$!

echo "Both instances started. Press Enter to stop all processes."
read

# Kill all processes
kill $INSTANCE1_PID
kill $INSTANCE2_PID
kill $SERVER_PID

echo "All processes stopped."