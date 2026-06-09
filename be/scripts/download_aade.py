"""
Two-step scraper for AADE circulars (egkyklioi-kai-apofaseis).

Step 1: Scrape the listing page (paginated) to collect detail page URLs.
Step 2: Visit each detail page and find the PDF download link.
Step 3: Download the PDF.

Usage (inside container):
    docker-compose exec api bash
    python scripts/download_aade.py
    python scripts/download_aade.py --output ./docs/aade --since 2022 --concurrency 3
"""
import httpx, asyncio, re, argparse
from pathlib import Path
from bs4 import BeautifulSoup

BASE_URL = "https://www.aade.gr"
LISTING_PATH = "/egkyklioi-kai-apofaseis"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="./docs/aade", help="Output dir (relative to /app inside container)")
    parser.add_argument("--since", type=int, default=2022, help="Skip circulars older than this year")
    parser.add_argument("--concurrency", type=int, default=3, help="Parallel detail page fetches")
    return parser.parse_args()


def extract_year(slug: str) -> int | None:
    """Extract year from URL slug like '1073-20-03-2026'."""
    match = re.search(r"(\d{4})$", slug)
    return int(match.group(1)) if match else None


async def fetch(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    try:
        r = await client.get(url, timeout=20)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  ✗ fetch error {url}: {e}")
        return None


async def scrape_listing_page(client: httpx.AsyncClient, page: int, since: int) -> tuple[list[str], bool]:
    """
    Returns (detail_urls, has_more).
    Stops early if all items on the page are older than `since`.
    """
    url = f"{BASE_URL}{LISTING_PATH}?page={page}"
    r = await fetch(client, url)
    if not r:
        return [], False

    soup = BeautifulSoup(r.text, "html.parser")

    # Circular links match /egkyklioi-kai-apofaseis/SLUG (not the root listing itself)
    pattern = re.compile(rf"^{LISTING_PATH}/[^/]+$")
    links = soup.find_all("a", href=pattern)

    if not links:
        return [], False  # no more pages

    detail_urls = []
    found_old = False

    for a in links:
        href = a["href"]
        slug = href.rsplit("/", 1)[-1]
        year = extract_year(slug)

        if year and year < since:
            found_old = True
            continue

        detail_urls.append(BASE_URL + href)

    # Stop paginating once we've hit items older than `since`
    has_more = not found_old
    return detail_urls, has_more


async def scrape_detail_page(client: httpx.AsyncClient, url: str) -> dict | None:
    """Visit a circular detail page and return the PDF URL + suggested filename."""
    r = await fetch(client, url)
    if not r:
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # Find PDF link — AADE marks it with type="application/pdf"
    pdf_link = soup.find("a", type="application/pdf")
    if not pdf_link:
        # Fallback: any link ending in .pdf under /sites/default/files/
        pdf_link = soup.find("a", href=re.compile(r"/sites/default/files/.*\.pdf$"))

    if not pdf_link:
        print(f"  ✗ no PDF found on {url}")
        return None

    pdf_href = pdf_link["href"]
    pdf_url = pdf_href if pdf_href.startswith("http") else BASE_URL + pdf_href

    # Use the PDF filename from the URL (e.g. a1073fek.pdf)
    filename = Path(pdf_href).name

    return {"pdf_url": pdf_url, "filename": filename, "detail_url": url}


async def download_pdf(client: httpx.AsyncClient, item: dict, output_dir: Path):
    dest = output_dir / item["filename"]
    if dest.exists():
        print(f"  skip (exists): {item['filename']}")
        return

    r = await fetch(client, item["pdf_url"])
    if not r:
        return

    if r.content[:4] != b"%PDF":
        print(f"  ✗ response is not a PDF: {item['pdf_url']}")
        return

    dest.write_bytes(r.content)
    print(f"  ✓ {item['filename']} ({len(r.content) // 1024}KB)")


async def main():
    args = parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:

        # Step 1 — collect all detail page URLs from paginated listing
        print(f"Collecting circular URLs from listing (since {args.since})...")
        all_detail_urls: list[str] = []
        page = 0

        while True:
            detail_urls, has_more = await scrape_listing_page(client, page, args.since)
            all_detail_urls.extend(detail_urls)
            print(f"  page {page}: {len(detail_urls)} circulars")

            if not has_more:
                break
            page += 1

        print(f"\nFound {len(all_detail_urls)} circulars total")

        # Step 2 — visit each detail page to get the PDF URL
        print(f"\nFetching PDF links (concurrency={args.concurrency})...")
        sem = asyncio.Semaphore(args.concurrency)

        async def get_pdf_info(url: str) -> dict | None:
            async with sem:
                return await scrape_detail_page(client, url)

        results = await asyncio.gather(*[get_pdf_info(u) for u in all_detail_urls])
        items = [r for r in results if r is not None]
        print(f"  {len(items)} PDFs located")

        # Step 3 — download
        print(f"\nDownloading {len(items)} PDFs to {output_dir}/...")

        async def guarded_download(item: dict):
            async with sem:
                await download_pdf(client, item, output_dir)

        await asyncio.gather(*[guarded_download(i) for i in items])

    total = len(list(output_dir.glob("*.pdf")))
    print(f"\nDone — {total} PDFs in {output_dir}/")
    print("Next step: python be/scripts/check_pdfs.py --dir ./docs/")


asyncio.run(main())
