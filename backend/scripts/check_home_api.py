import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


URLS = [
    "http://127.0.0.1:5000/api/categories",
    "http://127.0.0.1:5000/api/sites/hot?limit=8",
    "http://127.0.0.1:5000/api/sites/latest?limit=8",
    "http://127.0.0.1:5000/api/sites/recommend?limit=8",
]


def unwrap_count(payload):
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("items", "list", "rows"):
            value = data.get(key)
            if isinstance(value, list):
                return len(value)
    return 0


def check_url(url):
    try:
        with urlopen(url, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = {}
            print(f"{url}")
            print(f"  HTTP {response.status}")
            print(f"  count: {unwrap_count(payload)}")
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        print(f"{url}")
        print(f"  HTTP {error.code}")
        print(f"  error: {body[:300]}")
    except URLError as error:
        print(f"{url}")
        print("  HTTP request failed")
        print(f"  error: {str(error)[:300]}")


def main():
    for url in URLS:
        check_url(url)


if __name__ == "__main__":
    main()
