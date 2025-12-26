import requests
import base64
import os

# Placeholder keys - User should update these in their environment or settings
# For now, we default to empty strings or placeholders if env vars are missing
PAYMONGO_PUBLIC_KEY = os.environ.get('PAYMONGO_PUBLIC_KEY', 'pk_test_placeholder')
PAYMONGO_SECRET_KEY = os.environ.get('PAYMONGO_SECRET_KEY', 'sk_test_placeholder')

API_URL = "https://api.paymongo.com/v1"

def get_headers(secret_key=True):
    key = PAYMONGO_SECRET_KEY if secret_key else PAYMONGO_PUBLIC_KEY
    # Basic Auth with key as username and empty password
    encoded_key = base64.b64encode(f"{key}:".encode()).decode()
    return {
        "Authorization": f"Basic {encoded_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def create_gcash_source(amount, redirect_success, redirect_failed):
    """
    Creates a PayMongo Source for GCash.
    amount: float or int (in PESOS)
    """
    url = f"{API_URL}/sources"
    
    # PayMongo expects amount in centavos
    amount_in_cents = int(amount * 100)
    
    payload = {
        "data": {
            "attributes": {
                "amount": amount_in_cents,
                "redirect": {
                    "success": redirect_success,
                    "failed": redirect_failed
                },
                "type": "gcash",
                "currency": "PHP"
            }
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=get_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"PayMongo Error: {e}")
        if 'response' in locals() and response is not None:
            print(f"Response: {response.text}")
        return None

def retrieve_source(source_id):
    url = f"{API_URL}/sources/{source_id}"
    try:
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"PayMongo Error: {e}")
        return None

def create_payment(source_id, amount, description="Subscription Payment"):
    """
    Finalize the payment after the source is chargeable.
    """
    url = f"{API_URL}/payments"
    amount_in_cents = int(amount * 100)
    
    payload = {
        "data": {
            "attributes": {
                "amount": amount_in_cents,
                "source": {
                    "id": source_id,
                    "type": "source"
                },
                "currency": "PHP",
                "description": description
            }
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=get_headers())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"PayMongo Error: {e}")
        return None
