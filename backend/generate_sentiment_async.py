import asyncio
from db.review_queries import get_reviews_missing_sentiment, update_sentiment_for_review
from llm.openai_wrapper import analyze_sentiment
from utils.logger import get_logger

logger = get_logger(__name__)

async def enrich_sentiment():
    reviews = get_reviews_missing_sentiment()
    logger.info(f"🔍 Found {len(reviews)} reviews without sentiment.")

    for review in reviews:
        try:
            title = review.get("blog_title") or ""
            subtext = review.get("short_review") or ""
            sentiment = analyze_sentiment(title, subtext)
            if sentiment:
                update_sentiment_for_review(review["id"], sentiment)
                logger.info(f"✅ Updated sentiment for: {title} -> {sentiment}")
            else:
                logger.warning(f"⚠️ No sentiment returned for: {title}")
        except Exception as e:
            logger.error(f"❌ Failed sentiment analysis for {title}: {e}")

if __name__ == "__main__":
    asyncio.run(enrich_sentiment())
