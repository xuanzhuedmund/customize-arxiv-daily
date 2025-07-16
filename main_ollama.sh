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
  # Use jq to extract the value from the JSON file and remove quotes
  jq ".$config_key | .[\"$json_key\"]" "$CONFIG_FILE" | tr -d '"'
}

# Construct the command
COMMAND=$(read_json_value "main_ollama" "script_path")
# Add categories to the command, remove brackets, commas, and quotes
COMMAND="$COMMAND --categories $(read_json_value "main_ollama" "categories" | tr -d '[],' | sed 's/"//g')"
# Loop through the keys and add them to the command if they exist in the config file
for key in provider model smtp_server smtp_port sender receiver sender_password save; do
  value=$(read_json_value "main_ollama" "$key")
  if [[ "$value" != "null" ]]; then
    # Append the key-value pair as an argument to the command
    COMMAND="$COMMAND --$key $value"
  fi
done

# Execute the command
eval "$COMMAND"