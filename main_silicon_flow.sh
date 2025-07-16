#!/bin/bash

# Define the configuration file, prioritizing config_private.json
if [ -f "config_private.json" ]; then
    # If the private config file exists, use it
    CONFIG_FILE="config_private.json"
else
    # Otherwise, use the default config file
    CONFIG_FILE="config.json"
fi

# Function to read JSON values
read_json_value() {
  local config_key="$1"
  local json_key="$2"
  jq ".$config_key | .[\"$json_key\"]" "$CONFIG_FILE" | tr -d '"'
}

# Change directory (you might not need this if paths in config are absolute)
# cd "$(read_json_value "main_silicon_flow" "working_directory")"

# Construct the command
COMMAND=$(read_json_value "main_silicon_flow" "script_path")
COMMAND="$COMMAND --categories $(read_json_value "main_silicon_flow" "categories" | tr -d '[],' | sed 's/"//g')"
for key in provider model base_url api_key smtp_server smtp_port sender receiver sender_password save; do
  value=$(read_json_value "main_silicon_flow" "$key")
  if [[ "$value" != "null" ]]; then
    COMMAND="$COMMAND --$key $value"
  fi
done

# Execute the command
eval "$COMMAND"