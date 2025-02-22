import requests
import json
from typing import List, Dict, Any

def fetch_emails(base_url: str = "http://localhost:8000", batch_size: int = 100) -> List[Dict[Any, Any]]:
    """
    Fetch all emails from the API using pagination
    """
    all_emails = []
    offset = 0

    while True:
        # Make request to API
        response = requests.get(
            f"{base_url}/emails/",
            params={"skip": offset, "limit": batch_size}
        )

        # Check if request was successful
        if response.status_code != 200:
            print(f"Error fetching emails: {response.status_code}")
            break

        # Get emails from response
        emails = response.json()

        # If no more emails, break
        if not emails:
            break

        # Add emails to list
        all_emails.extend(emails)
        print(f"Fetched {len(emails)} emails")

        # Update offset for next batch
        offset += batch_size

    print(f"Total emails fetched: {len(all_emails)}")
    return all_emails

def save_emails(emails: List[Dict[Any, Any]], filename: str = "emails.json"):
    """
    Save emails to JSON file
    """
    with open(filename, 'w') as f:
        json.dump(emails, f, indent=2)
    print(f"Saved {len(emails)} emails to {filename}")

if __name__ == "__main__":
    # Fetch all emails
    emails = fetch_emails()

    # Save to file
    save_emails(emails)
