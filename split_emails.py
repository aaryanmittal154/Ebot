import json
import math
import os

def load_emails(filename="emails.json"):
    """Load emails from JSON file"""
    with open(filename, 'r') as f:
        return json.load(f)

def save_emails(emails, filename):
    """Save emails to JSON file"""
    with open(filename, 'w') as f:
        json.dump(emails, f, indent=2)

def split_emails(emails, num_parts=6):
    """Split emails into specified number of parts"""
    # Calculate size of each part
    part_size = math.ceil(len(emails) / num_parts)

    # Create parts directory if it doesn't exist
    if not os.path.exists('email_parts'):
        os.makedirs('email_parts')

    # Split and save parts
    for i in range(num_parts):
        start_idx = i * part_size
        end_idx = min((i + 1) * part_size, len(emails))
        part_emails = emails[start_idx:end_idx]

        # Save part to file
        filename = f'email_parts/emails_part_{i+1}.json'
        save_emails(part_emails, filename)
        print(f"Saved {len(part_emails)} emails to {filename}")

if __name__ == "__main__":
    # Load all emails
    print("Loading emails...")
    emails = load_emails()
    print(f"Loaded {len(emails)} emails")

    # Split into parts
    print("\nSplitting emails into 6 parts...")
    split_emails(emails)
    print("\nDone! Check the email_parts directory for the split files.")
