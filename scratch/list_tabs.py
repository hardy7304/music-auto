import requests
r = requests.get("http://127.0.0.1:9222/json/list")
for t in r.json():
    if t.get("type") == "page":
        print(f"  {t['url'][:100]}")
