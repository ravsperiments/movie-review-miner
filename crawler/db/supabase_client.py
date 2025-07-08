"""Initialise a Supabase client using credentials from the environment."""

import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Load credentials defined in the .env file
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")  # load your SUPABASE_URL and SUPABASE_KEY from .env

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    # Create the client at import time so other modules can use it
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logger.error("Failed to create Supabase client: %s", e)
    raise
