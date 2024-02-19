#!/bin/sh
echo "Starting demo services..."

# Start Node server
node server.js &

# Start python LED control daemon
python3 led-control.py

wait -n

exit $?