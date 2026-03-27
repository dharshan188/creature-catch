from __future__ import annotations

from datetime import datetime
import time
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

LOCATION = {
    "name": "Nelambur",
    "lat": 11.0168,
    "lon": 76.9558,
}

NEARBY_PLACES = [
    "Coimbatore",
    "Peelamedu",
]

KEYWORDS = [
    "elephant",
    "theft",
]

FILTER_KEYWORDS = [
    "elephant",
    "tiger",
    "leopard",
    "animal",
    "wild",
    "intrusion",
    "attack",
    "theft",
    "robbery",
]

# TEMP DEBUG
# Set to True to verify the full pipeline without discarding any articles.
TEMP_DEBUG_NO_FILTER = True


def _normalize_news_link(href: str | None) -> str:
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("./"):
        return f"https://news.google.com{href[1:]}"
    if href.startswith("/"):
        return f"https://news.google.com{href}"
    return f"https://news.google.com/{href}"


def fetch_news(city: str, nearby_keywords: list[str] | None = None, hours: int = 24) -> list[dict[str, str]]:
    _ = (nearby_keywords, hours)

    city_clean = (city or "").strip() or LOCATION["name"]
    nearby_places = [city_clean, *NEARBY_PLACES]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    articles: list[dict[str, str]] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start = time.time()

    for place in nearby_places:
        for keyword in KEYWORDS:
            if time.time() - start > 3:
                unique_articles = {article["title"]: article for article in articles}
                timed_articles = list(unique_articles.values())
                if not timed_articles:
                    timed_articles = [
                        {
                            "city": city_clean,
                            "title": "No recent intrusion news found",
                            "link": "#",
                            "location": LOCATION["name"],
                            "time": now,
                            "published_time": "",
                        }
                    ]
                print("⏱ Timeout reached, stopping search")
                print("📰 Articles found:", len(timed_articles))
                return timed_articles

            query = f"{place} {keyword}"
            url = f"https://news.google.com/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"

            try:
                response = requests.get(url, headers=headers, timeout=2)
                response.raise_for_status()
            except requests.RequestException:
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            for item in soup.select("article")[:2]:
                title_tag = item.select_one("h3 a") or item.find("a")
                title = title_tag.get_text(" ", strip=True) if title_tag else item.get_text(" ", strip=True)
                link = _normalize_news_link(title_tag.get("href") if title_tag else None)

                if not title or not link:
                    continue

                print("🧠 FILTER CHECK:", title)

                # Allow broader matching with city fallback.
                # TEMP DEBUG mode disables filtering to verify end-to-end display.
                if not TEMP_DEBUG_NO_FILTER:
                    lowered_title = title.lower()
                    if not any(k in lowered_title for k in FILTER_KEYWORDS):
                        if city_clean.lower() not in lowered_title:
                            continue

                articles.append(
                    {
                        "city": city_clean,
                        "title": title,
                        "link": link,
                        "location": place,
                        "time": now,
                        "published_time": "",
                    }
                )

    unique_articles = {article["title"]: article for article in articles}
    deduped_articles = list(unique_articles.values())

    if not deduped_articles:
        deduped_articles = [
            {
                "city": city_clean,
                "title": "No recent intrusion news found",
                "link": "#",
                "location": LOCATION["name"],
                "time": now,
                "published_time": "",
            }
        ]

    print("📰 Articles found:", len(deduped_articles))
    return deduped_articles
