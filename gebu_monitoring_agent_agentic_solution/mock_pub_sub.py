import base64
import json
import requests
import sys

def mock_pubsub_event(work_item_id: str, port: int = 8001):
    """Mocks a Google Cloud Pub/Sub Push notification to test the local FastAPI handler."""
    
    print(f"Mocking Pub/Sub event for Work Item: {work_item_id}")
    
    # 1. Create the payload your DB trigger would send
    data = json.dumps({"work_item_id": work_item_id})
    
    # 2. Base64 encode it (exactly how Pub/Sub does it)
    data_b64 = base64.b64encode(data.encode("utf-8")).decode("utf-8")
    
    # 3. Create the standard Pub/Sub Push JSON wrapper
    payload = {
        "message": {
            "data": data_b64,
            "messageId": "mock-id-1234",
            "publishTime": "2026-09-23T12:00:00.000Z"
        },
        "subscription": "projects/my-project/subscriptions/my-sub"
    }
    
    # 4. Send the POST request to your local FastAPI server
    url = f"http://127.0.0.1:{port}/cloudevent"
    print(f"Sending POST request to {url}...")
    
    try:
        response = requests.post(url, json=payload)
        print(f"\nStatus Code: {response.status_code}")
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except json.JSONDecodeError:
            print(f"Response (Raw): {response.text}")
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Could not connect to {url}.")
        print("Is your FastAPI/Uvicorn server running?")

if __name__ == "__main__":
    target_wi = sys.argv[1] if len(sys.argv) > 1 else "wi_12345"
    mock_pubsub_event(target_wi)