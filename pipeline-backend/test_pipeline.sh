#!/bin/bash

# Configuration
API_URL="http://localhost:8000/api/v1/pipeline"
BROKER_INTERNAL="localhost:19092"
TOPIC_IN="complex-in-$RANDOM"
TOPIC_OUT="complex-out-$RANDOM"
CONTAINER_NAME="redpanda"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting Complex Chain Pipeline Test (Redpanda)...${NC}\n"

# Helper function
get_id() {
  RESPONSE="$1"
  KEY="$2"
  if [[ "$RESPONSE" == *"detail"* ]] || [[ "$RESPONSE" == *"error"* ]]; then
    echo -e "${RED}API Error:${NC}" >&2
    echo "$RESPONSE" >&2
    return 1
  fi
  VAL=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('$KEY', ''))" 2>/dev/null)
  if [ -z "$VAL" ]; then
    echo -e "${RED}Error: Could not find key '$KEY'. Response:${NC}" >&2
    echo "$RESPONSE" >&2
    return 1
  fi
  echo $VAL
}

run_step() {
  ID=$(get_id "$1" "$2")
  if [ $? -ne 0 ]; then exit 1; fi
  echo $ID
}

# --- PRE-CHECK: Create Topics Manually ---
# This prevents UNKNOWN_TOPIC_OR_PARTITION errors
echo "0. Pre-creating Redpanda topics..."
docker exec $CONTAINER_NAME rpk topic create $TOPIC_IN $TOPIC_OUT -r 1 -p 1
echo "   -> Topics created."

# 1. Create Pipeline
PIPELINE_NAME="Complex Chain $RANDOM"
echo "1. Creating Pipeline: '$PIPELINE_NAME'..."
RESP=$(curl -s -X POST "$API_URL" -H 'Content-Type: application/json' -d "{\"name\": \"$PIPELINE_NAME\"}")
PID=$(run_step "$RESP" "pipeline_id")
echo "   -> Pipeline ID: $PID"

# 2. Add Input
echo "2. Adding Input..."
RESP=$(curl -s -X POST "$API_URL/$PID/input" -H 'Content-Type: application/json' \
  -d "{\"name\": \"Start Node $RANDOM\", \"topic\": \"$TOPIC_IN\", \"schemas\": {}, \"broker_address\": \"$BROKER_INTERNAL\", \"description\": \"x\"}")
IID=$(run_step "$RESP" "input_id")
echo "   -> Input ID: $IID"

# 3. Add Output
echo "3. Adding Output..."
RESP=$(curl -s -X POST "$API_URL/$PID/output" -H 'Content-Type: application/json' \
  -d "{\"name\": \"End Node $RANDOM\", \"topic\": \"$TOPIC_OUT\", \"schema\": {}, \"broker_address\": \"$BROKER_INTERNAL\", \"description\": \"x\"}")
OID=$(run_step "$RESP" "output_id")
echo "   -> Output ID: $OID"

# 4. Add Transformation 1 (ADDER)
echo "4. Adding Transformation 1 (Adder +10)..."
SCRIPT_ADD="def transform(data):\\n    data['val'] = data.get('val', 0) + 10\\n    return data"
JSON_PAYLOAD="{\"name\": \"Adder $RANDOM\", \"description\": \"x\", \"python_script\": \"$SCRIPT_ADD\"}"
RESP=$(curl -s -X POST "$API_URL/$PID/transformation" -H 'Content-Type: application/json' -d "$JSON_PAYLOAD")
TID_1=$(run_step "$RESP" "transformation_id")
echo "   -> Trans 1 ID: $TID_1"

# 5. Add Transformation 2 (MULTIPLIER)
echo "5. Adding Transformation 2 (Multiplier x2)..."
SCRIPT_MULT="def transform(data):\\n    data['val'] = data.get('val', 0) * 2\\n    return data"
JSON_PAYLOAD="{\"name\": \"Multiplier $RANDOM\", \"description\": \"x\", \"python_script\": \"$SCRIPT_MULT\"}"
RESP=$(curl -s -X POST "$API_URL/$PID/transformation" -H 'Content-Type: application/json' -d "$JSON_PAYLOAD")
TID_2=$(run_step "$RESP" "transformation_id")
echo "   -> Trans 2 ID: $TID_2"

# 6. Link Flows
echo "6. Linking Flows..."
curl -s -X POST "$API_URL/$PID/flow" -H 'Content-Type: application/json' \
  -d "{\"start_node_type\": \"input\", \"start_node\": $IID, \"end_node_type\": \"transformation\", \"end_node\": $TID_1}" > /dev/null
curl -s -X POST "$API_URL/$PID/flow" -H 'Content-Type: application/json' \
  -d "{\"start_node_type\": \"transformation\", \"start_node\": $TID_1, \"end_node_type\": \"transformation\", \"end_node\": $TID_2}" > /dev/null
curl -s -X POST "$API_URL/$PID/flow" -H 'Content-Type: application/json' \
  -d "{\"start_node_type\": \"transformation\", \"start_node\": $TID_2, \"end_node_type\": \"output\", \"end_node\": $OID}" > /dev/null
echo "   -> Flows created."

# 7. Validate
echo "7. Validating..."
RESP=$(curl -s -X POST "$API_URL/$PID/validate" -H 'Content-Type: application/json')
STATUS=$(echo "$RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'error'))")

if [ "$STATUS" != "valid" ]; then
    echo -e "${RED}Validation Failed: $RESP${NC}"
    exit 1
fi
echo "   -> Pipeline Valid."

# 8. Start Pipeline
echo "8. Starting Pipeline..."
RESP=$(curl -s -X POST "$API_URL/$PID/start" -H 'Content-Type: application/json')
echo "   -> Started."

echo "   -> Waiting 5 seconds for Worker initialization..."
sleep 5

# 9. Produce Message
TEST_VAL=50
EXPECTED_VAL=120
echo "9. Producing message: {\"val\": $TEST_VAL}..."
echo "{\"val\": $TEST_VAL}" | docker exec -i $CONTAINER_NAME rpk topic produce $TOPIC_IN -f "%v"

# 10. Consume Message
echo "10. Consuming message..."
RESULT=$(docker exec $CONTAINER_NAME rpk topic consume $TOPIC_OUT -n 1 --format "%v")

if [ -z "$RESULT" ]; then
   echo -e "${RED}No data received from output topic.${NC}"
   exit 1
fi

echo "   -> Received: $RESULT"

# 11. Verify
if [[ $RESULT == *"\"val\": $EXPECTED_VAL"* ]] || [[ $RESULT == *"\"val\":$EXPECTED_VAL"* ]]; then
  echo -e "\n${GREEN}SUCCESS! Logic Chain (50 + 10) * 2 = $EXPECTED_VAL verified.${NC}"
  curl -s -X POST "$API_URL/$PID/stop" -H 'Content-Type: application/json' > /dev/null
else
  echo -e "\n${RED}FAILURE! Expected value $EXPECTED_VAL not found.${NC}"
  exit 1
fi