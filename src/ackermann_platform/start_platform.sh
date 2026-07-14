#!/bin/bash
# Start the Ackermann Algorithm Test Platform
# Usage: ./start_platform.sh [--no-gazebo]
#
# Starts three components:
#   1. Gazebo + racebot (via racebot.launch.py, which includes bridge_node)
#   2. FastAPI backend (port 8000) — activates default path on startup
#   3. Vite frontend dev server (port 5173)
#
# Note on bridge_node: racebot.launch.py starts bridge_node which publishes
# zeros to /ackermann_cmd.  The platform backend only publishes to
# /ackermann_cmd when the user explicitly starts an algorithm, so there is
# no conflict during normal operation.  When an algorithm IS started, the
# platform's publications override bridge_node.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLATFORM_DIR="$SCRIPT_DIR"
SRC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

NO_GAZEBO=false
if [ "$1" = "--no-gazebo" ]; then
    NO_GAZEBO=true
fi

cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

echo -e "${GREEN}=== Ackermann Algorithm Test Platform ===${NC}"

# 1. Check ROS2 environment
if ! command -v ros2 &>/dev/null; then
    echo -e "${RED}Error: ros2 not found. Source your ROS2 setup.bash first.${NC}"
    exit 1
fi

# 2. Launch Gazebo + racebot (unless --no-gazebo)
if [ "$NO_GAZEBO" = false ]; then
    echo -e "${YELLOW}[1/3] Starting Gazebo + racebot...${NC}"
    ros2 launch racebot_control racebot.launch.py &
    GAZEBO_PID=$!
    echo "Waiting for Gazebo to initialize (15s)..."
    sleep 15
else
    echo -e "${YELLOW}[1/3] Skipping Gazebo (--no-gazebo)${NC}"
fi

# 3. Start FastAPI backend
# PYTHONPATH must point to src/ so that "ackermann_platform.backend.main" resolves.
echo -e "${YELLOW}[2/3] Starting FastAPI backend...${NC}"
cd "$PROJECT_DIR"
PYTHONPATH="$SRC_DIR:$PYTHONPATH" python3 -m uvicorn ackermann_platform.backend.main:app \
    --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 2

# Activate default path
curl -s -X POST http://localhost:8000/api/paths/activate \
    -H 'Content-Type: application/json' \
    -d '{"filename": "default"}' > /dev/null || true

# 4. Start frontend dev server
echo -e "${YELLOW}[3/3] Starting frontend dev server...${NC}"
cd "$PLATFORM_DIR/frontend"
npx vite --host &
FRONTEND_PID=$!

echo -e "\n${GREEN}Platform running!${NC}"
echo -e "  Frontend: ${GREEN}http://localhost:5173${NC}"
echo -e "  Backend:  ${GREEN}http://localhost:8000${NC}"
echo -e "  API docs: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "\nPress Ctrl+C to stop all processes.\n"

wait
