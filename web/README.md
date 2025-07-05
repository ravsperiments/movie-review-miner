# Movie Review Miner — Web

This static web interface displays the latest curated movie reviews from your Supabase database.

## Setup

1. Copy your Supabase credentials into the `.env` file in this directory:
   ```
   EXPO_PUBLIC_SUPABASE_URL=https://<your-project>.supabase.co
   EXPO_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
   ```

2. Serve the files over HTTP (browsers cannot fetch `.env` via `file://`):
   ```bash
   cd web
   python3 -m http.server 8000
   ```

3. Open your browser at <http://localhost:8000> to view the reviews.

## Troubleshooting
- If you see "No reviews found", ensure you have run the backend pipeline (`run_pipeline.py`) to populate the `vw_flat_movie_reviews` view.
- Check the browser console for any initialization or query errors.