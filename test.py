import requests

API_KEY = "83e37052c9c640cb97681b2b04a1d939"

KEYWORDS = [
    "elephant",
    "leopard",
    "tiger",
    "animal",
    "wildlife",
    "intrusion",
    "attack",
    "entered",
    "village",
    "theft",
    "robbery"
]

def fetch_news(city):
    print(f"\n🔍 Searching news for: {city}\n")

    url = f"https://newsapi.org/v2/everything?q={city}&apiKey={API_KEY}"

    try:
        response = requests.get(url)
        print("STATUS CODE:", response.status_code)

        data = response.json()

        if data.get("status") != "ok":
            print("\n❌ API ERROR:", data.get("message"))
            return []

        articles = data.get("articles", [])

        print(f"\n📦 TOTAL ARTICLES: {len(articles)}")

        # 🔥 FILTER LOGIC
        filtered = []

        for a in articles:
            title = a["title"].lower()

            if any(k in title for k in KEYWORDS):
                filtered.append(a)

        print(f"\n🎯 FILTERED ARTICLES: {len(filtered)}\n")

        # 🔥 DISPLAY FILTERED
        if filtered:
            for i, a in enumerate(filtered[:5], 1):
                print(f"{i}. {a['title']}")
                print(f"   🔗 {a['url']}\n")
        else:
            # 🔥 FALLBACK (VERY IMPORTANT FOR DEMO)
            print("⚠️ No intrusion news today, showing general news\n")

            for i, a in enumerate(articles[:3], 1):
                print(f"{i}. {a['title']}")
                print(f"   🔗 {a['url']}\n")

        return filtered if filtered else articles[:3]

    except Exception as e:
        print("❌ ERROR:", e)
        return []


if __name__ == "__main__":
    city = input("Enter city: ")
    fetch_news(city)