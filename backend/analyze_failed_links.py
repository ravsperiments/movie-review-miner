# analyze_failed_links.py

import os

from utils.logger import get_logger

FAILED_LINKS_FILE = "failed_links.txt"

def main():
    logger = get_logger(__name__)
    if not os.path.exists(FAILED_LINKS_FILE):
        logger.info("No failed_links.txt file found.")
        return

    with open(FAILED_LINKS_FILE, "r") as f:
        links = [line.strip() for line in f if line.strip()]

    total = len(links)
    unique_links = set(links)

    logger.info("\nFailed Links Analysis")
    logger.info("------------------------")
    logger.info("Total failures recorded: %s", total)
    logger.info("Unique failed links:     %s", len(unique_links))

    if total > len(unique_links):
        logger.warning("Some links failed multiple times.")

    logger.info("\nSample failed links:")
    for link in list(unique_links)[:10]:
        logger.info(" - %s", link)

if __name__ == "__main__":
    main()
