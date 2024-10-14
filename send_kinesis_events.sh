#!/bin/bash

EVENTS_FILE=$1
KINESIS_STREAM_NAME=$2

# Read all events into an array
mapfile -t events < <(jq -c '.[]' "$EVENTS_FILE")

# Function to send event
send_event() {
    local event=$1
    echo "Sending event to Kinesis stream $KINESIS_STREAM_NAME..."
    echo "Event data: $event"
    aws kinesis put-record \
        --stream-name "$KINESIS_STREAM_NAME" \
        --partition-key 3389 \
        --data "$event" \
        --cli-binary-format raw-in-base64-out || { echo "Failed to send event"; return 1; }
    echo "Event sent successfully."
}

# Main loop
for event in "${events[@]}"; do
    while true; do
      read -n 1 -s -r -p "Press any key (not Space or Enter) to send the next event, or 'q' to quit: " key
        echo
        if [[ $key == "q" ]]; then
            echo "Exiting loop."
            exit 0
        elif [[ -n $key ]]; then
            if send_event "$event"; then
                break
            fi
        fi
    done
done

echo "All events processed."
