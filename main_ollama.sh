#!/bin/bash

# Define the configuration file, prioritizing config_private.json
if [ -f "config_private.json" ]; then
    # Activate the conda environment and get the Python interpreter path
    eval "$(conda shell.bash hook)"
    conda activate arXiv
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

# Modified to read from common or top-level for shared keys
read_value() {
    local key="$1"
    read_json_value "main_ollama" "$key" || read_json_value "common" "$key" || read_json_value "" "$key"
}

# Construct the command
COMMAND=$(read_value "script_path")
COMMAND="$COMMAND --categories $(read_value "categories" | tr -d '[],' | sed 's/"//g')"

# Add common parameters
for key in max_paper_num max_entries num_workers; do
  value=$(read_json_value "common" "$key")
  if [[ "$value" != "null" ]]; then
    COMMAND="$COMMAND --$key $value"
  fi
done
# Loop through the keys and add them to the command if they exist in the config file
for key in provider model smtp_server smtp_port sender receiver sender_password save; do
  value=$(read_value "$key")
  if [[ "$value" != "null" ]]; then
    COMMAND="$COMMAND --$key $value"
  fi
done

# Print the command to the screen for verification
echo "--------------------------------------------------"
echo "Executing Command:"
echo "$COMMAND"
echo "--------------------------------------------------"
# Execute the command
eval "$COMMAND"