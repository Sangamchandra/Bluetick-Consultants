import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from collections import deque
import phonenumbers
from phonenumbers import PhoneNumberMatcher

# -------- CONFIG --------
MAX_PAGES = 50   # prevent infinite crawling

SKIP_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".rar", ".mp4", ".mp3", ".avi",
    ".css", ".js", ".ico"
)

# -------- STORAGE --------
visited = set()
phone_numbers = {}

# -------- HELPERS --------
def normalize_url(url):
    url, _ = urldefrag(url)  # remove #fragment
    return url.rstrip("/")

def is_same_domain(base, url):
    return urlparse(base).netloc == urlparse(url).netloc

def is_valid_page(url):
    return not urlparse(url).path.lower().endswith(SKIP_EXTENSIONS)

def is_html(response):
    return "text/html" in response.headers.get("Content-Type", "")

def extract_numbers(text):
    nums = set()
    for match in PhoneNumberMatcher(text, "IN"):
        if phonenumbers.is_valid_number(match.number):
            nums.add(
                phonenumbers.format_number(
                    match.number,
                    phonenumbers.PhoneNumberFormat.E164
                )
            )
    return nums

# -------- MAIN CRAWLER --------
def crawl(start_url):
    session = requests.Session()  # ✅ faster requests
    queue = deque([start_url])

    while queue and len(visited) < MAX_PAGES:
        url = normalize_url(queue.popleft())

        if url in visited or not is_valid_page(url):
            continue

        print(f"🔍 Crawling: {url}")
        visited.add(url)

        try:
            res = session.get(url, timeout=5)
            if res.status_code != 200 or not is_html(res):
                continue
        except:
            continue

        soup = BeautifulSoup(res.text, "html.parser")

        # -------- FOOTER --------
        footer_nums = set()
        footer = soup.find("footer")
        if footer:
            footer_nums = extract_numbers(footer.get_text(" ", strip=True))

        # -------- FULL TEXT --------
        all_nums = extract_numbers(soup.get_text(" ", strip=True))
        main_nums = all_nums - footer_nums

        # -------- STORE --------

        # 1. Store footer numbers (highest priority)
        for num in footer_nums:
            if num not in phone_numbers:
                phone_numbers[num] = {"pages": set(), "type": "footer"}
            
            # Force it to always be footer
            phone_numbers[num]["type"] = "footer"
            phone_numbers[num]["pages"] = {"GLOBAL_FOOTER"}  # overwrite any page entries


        # 2. Store main content numbers ONLY if not already footer
        for num in main_nums:
            if num in phone_numbers and phone_numbers[num]["type"] == "footer":
                continue  # skip, already classified as footer
            
            phone_numbers.setdefault(num, {"pages": set(), "type": "page"})
            phone_numbers[num]["pages"].add(url)

        # -------- ADD LINKS --------
        for tag in soup.find_all("a", href=True):
            next_url = normalize_url(urljoin(start_url, tag["href"]))

            if is_same_domain(start_url, next_url) and next_url not in visited:
                queue.append(next_url)

    return {
        num: {
            "found_at": list(data["pages"]),
            "source": data["type"]
        }
        for num, data in phone_numbers.items()
    }

# -------- RUN --------
if __name__ == "__main__":
    start_url = input("Enter website URL to crawl: ").strip()

    # Basic validation
    if not start_url.startswith("http"):
        start_url = "https://" + start_url

    result = crawl(start_url)

    print("\n📞 Phone Numbers:\n")
    for num, info in result.items():
        print(f"{num} ({info['source']})")
        for loc in info["found_at"]:
            print(f"  -> {loc}")
        print()
