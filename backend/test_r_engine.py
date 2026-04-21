import requests

try:
    print(requests.get('http://127.0.0.1:8010/health').status_code)
except Exception as e:
    print(f"Error: {e}")
