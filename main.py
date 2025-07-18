from util.construct_email import send_email
from arxiv_daily import ArxivDaily
import os
import json

def load_config():
    """Loads config_private.json if it exists, otherwise loads config.json."""
    config_path = None
    if os.path.exists("config_private.json"):
        config_path = "config_private.json"
    elif os.path.exists("config.json"):
        config_path = "config.json"

    if config_path:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise FileNotFoundError(
            "Configuration file not found. Please create 'config.json' or 'config_private.json'."
        )
def get_config_value(config, tool_section, key, default=None, required=False):
    if tool_section and key == "provider":
        value = config.get(tool_section, {}).get(key)
    else:
        value = config.get(tool_section, {}).get(key) or config.get("common", {}).get(key) or config.get(key)
    if required and value is None:
        raise ValueError(f"Missing required parameter: {key}")
    return value if value is not None else default

def run_arxiv_daily(tool_section=None):
    config = load_config()

    # Common parameters
    categories = get_config_value(config, None, "categories", required=True)
    max_paper_num = get_config_value(config, None, "max_paper_num", default=60)
    max_entries = get_config_value(config, None, "max_entries", default=100)
    save = get_config_value(config, None, "save", default=False)
    save_dir = get_config_value(config, None, "save_dir", default="./arxiv_history")
    description_path = get_config_value(config, None, "description", default="description.txt")

    # Tool-specific parameters, with fallback to common and default
    provider = get_config_value(config, tool_section, "provider", required=True)
    model = get_config_value(config, tool_section, "model")
    base_url = get_config_value(config, tool_section, "base_url")
    api_key = get_config_value(config, tool_section, "api_key")
    smtp_server = get_config_value(config, tool_section, "smtp_server", required=True)
    smtp_port = get_config_value(config, tool_section, "smtp_port", required=True)
    sender = get_config_value(config, tool_section, "sender", required=True)
    receiver = get_config_value(config, tool_section, "receiver", required=True)
    sender_password = get_config_value(config, tool_section, "sender_password", required=True)
    num_workers = get_config_value(config, tool_section, "num_workers", default=4)
    temperature = get_config_value(config, tool_section, "temperature", default=0.7)
    title = get_config_value(config, tool_section, "title", default="Daily arXiv")
    server_chan_key = get_config_value(config, tool_section, "Server_chan_KEY", default="")

    arxiv_daily = ArxivDaily(
        categories,
        max_entries,
        max_paper_num,
        provider,
        model,
        base_url,
        api_key,
        open(description_path, "r").read(),
        num_workers,
        temperature,
        save_dir=save_dir if save else None,
        server_chan_key=server_chan_key,
    )

    arxiv_daily.send_email(
        sender,
        receiver,
        sender_password,
        smtp_server,
        smtp_port,
        title,
    )

if __name__ == "__main__":
    import sys
# "main_silicon_flow.sh", "main_gpt.sh", "main_ollama.sh" are the entry points for different tools
    tool = "main_silicon_flow"  # Default to common settings
    if len(sys.argv) > 1:
        tool = sys.argv[1]  # Use the first command-line argument as the tool section

    # Remove .sh suffix if present for backwards compatibility
    if tool.endswith(".sh"):
        tool = tool[:-3]

    run_arxiv_daily(tool_section=tool)
