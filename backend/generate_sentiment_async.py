# generate_sentiment_async.py
from db.store_review import supabase
from llm.openai_wrapper import analyze_sentiment
import asyncio

async def process_sentiment(record):
    sentiment = analyze_sentiment(record["blog_title"], record["subtext"])
    supabase.table("reviews").update({"sentiment": sentiment}).eq("id", record["id"]).execute()

async def main():
    records = supabase.table("reviews").select("*").is_("sentiment", "null").execute().data
    await asyncio.gather(*(process_sentiment(r) for r in records))

if __name__ == "__main__":
    asyncio.run(main())
