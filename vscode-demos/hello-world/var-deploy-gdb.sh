#!/bin/bash
readonly TARGET_IP="$1"
readonly PROGRAM="$2"
readonly TARGET_DIR="/home/root"

# Must match startsPattern in tasks.json
echo "Deploying to target"

# kill gdbserver on target and delete old binary
ssh root@${TARGET_IP} "sh -c '/usr/bin/killall -q gdbserver; rm -rf ${TARGET_DIR}/${PROGRAM}  exit 0'"

# send the program to the target
scp ${PROGRAM} root@${TARGET_IP}:${TARGET_DIR}

# Must match endsPattern in tasks.json
echo "Starting GDB Server on Target"

# start gdbserver on target
ssh -t root@${TARGET_IP} "sh -c 'cd ${TARGET_DIR}; gdbserver localhost:3000 ${PROGRAM}'"
