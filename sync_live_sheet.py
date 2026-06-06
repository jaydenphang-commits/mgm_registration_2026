import os
import re
import json
import gspread
import qrcode
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# Setup local folders
output_json = "attendees_db.json"
qr_folder = "generated_qrs"
os.makedirs(qr_folder, exist_ok=True)

# 1. Connect securely to Google Sheets API using your credentials key
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", scope)
client = gspread.authorize(creds)

# 2. Open your live Google Sheet (Change this to match your EXACT sheet title)
sheet_title = "MGM 2026 Sign Up Form (Responses)"
try:
    spreadsheet = client.open(sheet_title)
    sheet = spreadsheet.get_all_records() # Pulls live data rows instantly
except Exception as e:
    print(f"❌ Error linking to Google Sheet: {e}")
    print("Double check that you shared the sheet with your service account email!")
    exit()

# Convert the live Google row array data into a clean Pandas DataFrame
df = pd.DataFrame(sheet)
df.columns = df.columns.str.strip()

# 3. Handle Deduplication and Data Cleaning
df = df.drop_duplicates(subset=["Name:", "Email:", "Phone Number:", "Workshops: RM30 per session"])

attendees = []
seen_identities = set()
guest_id_counter = 1001

def is_valid_individual_name(name_str):
    if re.search(r'\d+\s*(pax|group|singers|people)', name_str, re.IGNORECASE):
        return False
    if len(name_str.strip()) < 2:
        return False
    return True

print("--- Starting LIVE Sync & Data Verification ---")

for index, row in df.iterrows():
    raw_name = str(row.get("Name:", "")).strip()
    raw_phone = str(row.get("Phone Number:", "")).strip()
    workshop = str(row.get("Workshops: RM30 per session", "None of the above")).strip()
    concert_status = str(row.get("Join the FREE Concert from 2pm to 4pm!!!", "No")).strip()

    if not raw_name or raw_name.lower() == "nan" or raw_name == "":
        continue

    if not is_valid_individual_name(raw_name):
        print(f"⚠️ Flagged Group Entry at Row {index+2}: '{raw_name}'")
        display_name = f"⚠️ [CHECK GROUP] {raw_name}"
    else:
        display_name = raw_name

    identity_key = (display_name.lower(), raw_phone.replace("-", "").replace(" ", ""))

    if identity_key in seen_identities:
        continue
        
    seen_identities.add(identity_key)
    concert_access = True if "yes" in concert_status.lower() else False
    guest_id = f"MGM2026_{guest_id_counter}"
    guest_id_counter += 1

    attendees.append({
        "id": guest_id,
        "name": display_name,
        "phone": raw_phone,
        "workshop": workshop,
        "concert": concert_access,
        "checkedIn": False
    })

    # Optional: Generate QR code only if it doesn't already exist locally
    # This avoids generating 182 pictures over and over again on every sync!
    safe_filename = "".join([c if c.isalnum() else "_" for c in display_name])
    qr_path = f"{qr_folder}/{guest_id}_{safe_filename}.png"
    
    if not os.path.exists(qr_path):
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(guest_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_path)

# 4. Save the updated database locally
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(attendees, f, indent=4, ensure_ascii=False)

print(f"\n✅ Live Sync Complete! Caught {len(attendees)} active individual entries.")