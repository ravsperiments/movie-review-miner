# analyze_failed_links.py

import os

FAILED_LINKS_FILE = "failed_links.txt"

def main():
    if not os.path.exists(FAILED_LINKS_FILE):
        print("No failed_links.txt file found.")
        return

    with open(FAILED_LINKS_FILE, "r") as f:
        links = [line.strip() for line in f if line.strip()]

    total = len(links)
    unique_links = set(links)

    print(f"\n🔍 Failed Links Analysis")
    print(f"------------------------")
    print(f"Total failures recorded: {total}")
    print(f"Unique failed links:     {len(unique_links)}")

    if total > len(unique_links):
        print("⚠️ Some links failed multiple times.")

    print("\nSample failed links:")
    for link in list(unique_links)[:10]:
        print(f" - {link}")

if __name__ == "__main__":
    main()
