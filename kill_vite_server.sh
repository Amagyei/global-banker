#!/bin/bash
# Kill Vite server processes without using lsof

echo "Finding Vite/Node processes..."

# Method 1: Find by process name
VITE_PIDS=$(ps aux | grep -E "vite|node.*dev|npm.*dev" | grep -v grep | awk '{print $2}')

if [ -z "$VITE_PIDS" ]; then
    echo "No Vite processes found"
else
    echo "Found processes: $VITE_PIDS"
    for pid in $VITE_PIDS; do
        echo "Killing process $pid"
        kill -9 $pid 2>/dev/null
    done
    echo "Killed all Vite processes"
fi

# Method 2: Try to find processes on common ports using netstat or ss
if command -v netstat &> /dev/null; then
    echo "Checking ports with netstat..."
    for port in 8080 8081 8082 5173 3000; do
        PID=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | head -1)
        if [ ! -z "$PID" ]; then
            echo "Killing process $PID on port $port"
            kill -9 $PID 2>/dev/null
        fi
    done
elif command -v ss &> /dev/null; then
    echo "Checking ports with ss..."
    for port in 8080 8081 8082 5173 3000; do
        PID=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | head -1)
        if [ ! -z "$PID" ]; then
            echo "Killing process $PID on port $port"
            kill -9 $PID 2>/dev/null
        fi
    done
fi

# Method 3: Use pkill if available
if command -v pkill &> /dev/null; then
    echo "Using pkill to kill vite processes..."
    pkill -9 -f vite 2>/dev/null
    pkill -9 -f "npm.*dev" 2>/dev/null
fi

echo "Done. Verifying..."
sleep 1
REMAINING=$(ps aux | grep -E "vite|node.*dev|npm.*dev" | grep -v grep | wc -l)
if [ "$REMAINING" -eq 0 ]; then
    echo "✅ All Vite processes killed"
else
    echo "⚠️  Some processes may still be running"
    ps aux | grep -E "vite|node.*dev|npm.*dev" | grep -v grep
fi

