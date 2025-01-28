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

# def get_available_minutes(payload):
#     """
#     Делает POST-запрос на /salons/availability/ с JSON=payload.
#     payload — словарь типа:
#     {
#       "salon_id": 68,
#       "date": "2025-01-22",
#       "hours": [9,10,11],
#       "booking_details": [...],
#       "total_service_duration": 30
#       ...
#     }
#     """
#     url = f"{API_BASE_URL}/salons/availability/"
#     r = requests.post(url, json=payload)
#     r.raise_for_status()
#     return r.json()

# import requests

def get_available_minutes(payload):
    url = f"{API_BASE_URL}/salons/availability/"

    # url = "https://reservon.am/api/salons/availability/"
    # Обязательно json=..., чтобы requests сам добавил Content-Type: application/json
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()  # выбросит requests.HTTPError для 4xx/5xx
    return r.json()

