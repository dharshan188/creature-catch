import requests
import xml.etree.ElementTree as ET

def fetch_news(city):
    print(f"\n🔍 Searching news for: {city}\n")

    url = f"https://news.google.com/rss/search?q={city}+wildlife+OR+elephant+OR+leopard+OR+tiger+OR+theft&hl=en-IN&gl=IN&ceid=IN:en"

    try:
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)

        items = root.findall(".//item")
        print(f"📦 TOTAL ARTICLES: {len(items)}\n")

        filtered = []

        for item in items:
            title = item.find("title").text
            link = item.find("link").text

            t = title.lower()

            # ❌ REMOVE UNWANTED (tech, govt, etc.)
            if any(word in t for word in [
                "ai", "system", "project", "inaugurated", "scheme",
                "policy", "research", "study", "plan"
            ]):
                continue

            # 🔥 STRICT INTRUSION FILTER
            if (
                ("elephant" in t or "leopard" in t or "tiger" in t)
                and ("village" in t or "road" in t or "area" in t or "near")
                and any(action in t for action in [
                    "entered", "spotted", "roaming", "strayed",
                    "attacked", "panic", "rescued"
                ])
            ):
                filtered.append((title, link))

        print(f"🎯 FILTERED ARTICLES: {len(filtered)}\n")

        # ✅ OUTPUT
        if filtered:
            print("🚨 Intrusion Alerts:\n")
            for i, (title, link) in enumerate(filtered[:5], 1):
                print(f"{i}. {title}")
                print(f"   🔗 {link}\n")
        else:
            print("⚠️ No intrusion news found.\n")
            print("✅ System is actively monitoring nearby regions.\n")

        return filtered

    except Exception as e:
        print("❌ ERROR:", e)
        return []


if __name__ == "__main__":
    city = input("Enter city: ").strip()
    fetch_news(city)