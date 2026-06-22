import os
import sys
import traceback
from unittest.mock import MagicMock
from dotenv import load_dotenv
import google.auth

# Load environment variables (.env file)
load_dotenv()

# Mock google credentials to prevent ADC check issues
def mock_default(*args, **kwargs):
    mock_creds = MagicMock()
    mock_creds.universe_domain = "googleapis.com"
    mock_creds.token = "dummy-token"
    return mock_creds, "dummy-project"

google.auth.default = mock_default

# Mock google cloud storage client to prevent ValueError/type check issues
import google.cloud.storage
google.cloud.storage.Client = MagicMock()

# Mock google cloud bigquery client to prevent ValueError/type check issues
import google.cloud.bigquery
google.cloud.bigquery.Client = MagicMock()

# Patch vertexai.Client class to force Developer API (API Key) mode
import vertexai
original_client = vertexai.Client

def mock_client_init(
    self,
    *,
    api_key=None,
    credentials=None,
    project=None,
    location=None,
    debug_config=None,
    http_options=None,
):
    from google.genai import client as genai_client
    from google.genai import types

    self._debug_config = debug_config or genai_client.DebugConfig()
    if isinstance(http_options, dict):
        http_options = types.HttpOptions(**http_options)
    if http_options is None:
        http_options = types.HttpOptions()
    if http_options.headers is None:
        http_options.headers = {}

    # Initialize underlying client with vertexai=False
    self._api_client = genai_client.Client._get_api_client(
        vertexai=False,
        api_key=api_key,
        credentials=credentials,
        project=project,
        location=location,
        debug_config=self._debug_config,
        http_options=http_options,
    )
    self._aio = vertexai._genai.client.AsyncClient(self._api_client)
    self._evals = None
    self._prompt_optimizer = None
    self._agent_engines = None
    self._prompts = None
    self._datasets = None
    self._skills = None

vertexai.Client.__init__ = mock_client_init

# Import agents-cli entry point
from google.agents.cli.main import main

if __name__ == "__main__":
    try:
        # Call main with standalone_mode=False so exceptions bubble up
        main(standalone_mode=False)
    except Exception as e:
        print("\n--- Raw Exception Traceback ---")
        traceback.print_exc()
        sys.exit(1)
