import requests

API_URL = "http://localhost:8000"

def login(username: str, password: str):
    response = requests.post(f"{API_URL}/auth/token", 
    data={"username": username, "password": password})
    if response.status_code == 200:
        return response.json()["access_token"]
    return None                        