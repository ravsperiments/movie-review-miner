"""Initialise a Supabase client using credentials from the environment."""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

from utils.logger import get_logger

# Load credentials defined in the .env file
load_dotenv()  # load your SUPABASE_URL and SUPABASE_KEY from .env

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Logger to track client creation
logger = get_logger(__name__)

try:
    # Create the client at import time so other modules can use it
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logger.error("Failed to create Supabase client: %s", e)
    raise
