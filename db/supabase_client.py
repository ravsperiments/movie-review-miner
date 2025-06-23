import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()  # load your SUPABASE_URL and SUPABASE_KEY from .env

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
