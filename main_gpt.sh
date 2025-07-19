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
  jq ".$config_key | .[\"$json_key\"]" "$CONFIG_FILE" | tr -d '"'
}

# Construct the command
COMMAND=$(read_json_value "common" "script_path" || read_json_value "" "script_path")  # Read common or top-level script_path
COMMAND="$COMMAND --categories $(read_json_value "common" "categories" || read_json_value "" "categories" | tr -d '[],' | sed 's/"//g')"  # Read common or top-level categories

# Add common parameters
for key in max_paper_num max_entries num_workers; do
  value=$(read_json_value "common" "$key")
  if [[ "$value" != "null" ]]; then
    COMMAND="$COMMAND --$key $value"
  fi
done
# Process tool-specific and common parameters
for key in provider model base_url api_key smtp_server smtp_port sender receiver sender_password num_workers temperature title description save; do
  # Prioritize tool-specific values, then fall back to common or top-level values
  if [[ "$key" == "provider" ]]; then
    value=$(read_json_value "main_gpt" "$key")
  else
    value=$(read_json_value "main_gpt" "$key" || read_json_value "common" "$key" || read_json_value "" "$key")
  fi

  # Add the parameter to the command if a value was found (and isn't "null")
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