# utils/api.py
import requests
from config import API_BASE_URL

def get_salons():
    r = requests.get(f"{API_BASE_URL}/salons")
    r.raise_for_status()
    return r.json()

def get_salon_details(salon_id):
    r = requests.get(f"{API_BASE_URL}/salons/{salon_id}")
    r.raise_for_status()
    return r.json()

def get_available_minutes(payload):
    url = f"{API_BASE_URL}/salons/availability/"
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()
    return r 

