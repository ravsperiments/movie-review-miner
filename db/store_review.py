from db.supabase_client import supabase

def store_review(review: dict):
    try:# <-- Debug print
        print("\n📤 Inserting into Supabase:")
        for key, value in review.items():
            print(f"  {key}: {repr(value)[:200]}")  # Truncate long text

        response = supabase.table("reviews").insert(review).execute()
        print("✅ Insert successful:", response)
    except Exception as e:
        print("❌ DB Insert failed:", e)
        raise
