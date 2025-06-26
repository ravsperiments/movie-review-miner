"""Step 1: fetch blog post links from the source site."""
import asyncio
from crawler.fetch_links import get_post_links_async
from db.review_queries import get_latest_post_date, get_links_after_date
from utils.logger import StepLogger

async def fetch_links(start_page: int = 1, end_page: int = 279) -> list[str]:
    """Fetch new blog post links skipping ones already stored."""
    slog = StepLogger("step_1_fetch_links")
    slog.set_input_count(end_page - start_page + 1)
    try:
        log = slog.logger
        log.info("Fetching links from pages %s to %s", start_page, end_page)
        latest_date = get_latest_post_date()
        existing_links = (
            get_links_after_date(latest_date) if latest_date else set()
        )
        log.info("Loaded %s existing links", len(existing_links))

        links = await get_post_links_async(start_page, end_page)
        slog.processed(len(links))
        new_links = [link for _, _, link in links if link not in existing_links]
        slog.saved(len(new_links))
        log.info("Discovered %s new links", len(new_links))
        slog.note(f"Skipped {len(links) - len(new_links)} duplicates")
        return new_links
    except Exception as e:
        slog.failed()
        slog.logger.exception("Failed to fetch links: %s", e)
        return []
    finally:
        slog.finalize()


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    asyncio.run(fetch_links())
