import os
import re
import json
import gspread
import qrcode
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# 1. Setup local output folders
output_json = "attendees_db.json"
qr_folder = "generated_qrs"
os.makedirs(qr_folder, exist_ok=True)

# 2. Configure Google API Permissions
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Ensure the credentials file exists before running
if not os.path.exists("google_credentials.json"):
    print("❌ Error: 'google_credentials.json' missing from your project folder.")
    print("Please place your downloaded Google Cloud secret key file here to continue.")
    exit()

creds = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", scope)
client = gspread.authorize(creds)

# 3. Open the Cloud Sheet
# CHANGE THIS STRING to match the exact name at the top of your Google Sheet browser window
sheet_title = "MGM 2026 Sign Up Form (Responses)"

print(f"🔄 Connecting to Google Cloud to fetch sheet: '{sheet_title}'...")

try:
    spreadsheet = client.open(sheet_title)
    worksheet = spreadsheet.get_worksheet(0)
    
    # FIX: Read raw values as a grid instead of records to bypass duplicate header crashes
    raw_rows = worksheet.get_all_values()
    
    # Separate the first row (headers) from the rest of the actual sign-up data rows
    headers = [h.strip() for h in raw_rows[0]]
    data_rows = raw_rows[1:]
    
except Exception as e:
    print(f"❌ Google API Error: {e}")
    print("Please verify your sheet title matches exactly and that you shared the sheet with your Service Account email.")
    exit()

# 4. Load data into a Pandas DataFrame using our extracted custom headers safely
df = pd.DataFrame(data_rows, columns=headers)

# Target your exact column names
name_col = "Name:"
phone_col = "Phone Number:"
workshop_col = "Workshops: RM30 per session"
concert_col = "Join the FREE Concert from 2pm to 4pm!!!"

# Verify vital columns exist in the downloaded sheet
missing_cols = [c for c in [name_col, phone_col, workshop_col, concert_col] if c not in df.columns]
if missing_cols:
    print(f"❌ Error: Could not find these exact columns in your sheet: {missing_cols}")
    print(f"Available columns found are: {headers[:5]}... (showing first 5)")
    exit()

# 5. Data Cleaning: Drop absolute identical rows (double form submissions)
df = df.drop_duplicates(subset=[name_col, phone_col, workshop_col])

attendees = []
seen_identities = set()
guest_id_counter = 1001

def is_valid_individual_name(name_str):
    """Flags group signups like '7 pax' or 'Singers'"""
    if re.search(r'\d+\s*(pax|group|singers|people)', name_str, re.IGNORECASE):
        return False
    if len(name_str.strip()) < 2:
        return False
    return True

print("--- Data Cleaning & QR Generation Started ---")

for index, row in df.iterrows():
    raw_name = str(row.get(name_col, "")).strip()
    raw_phone = str(row.get(phone_col, "")).strip()
    workshop = str(row.get(workshop_col, "None of the above")).strip()
    concert_status = str(row.get(concert_col, "No")).strip()

    # Skip empty or unformed rows safely
    if not raw_name or raw_name.lower() == "nan" or raw_name == "":
        continue

    # Evaluate name authenticity
    if not is_valid_individual_name(raw_name):
        print(f"⚠️ Row {index+2}: Flagged Group Entry -> '{raw_name}'")
        display_name = f"⚠️ [CHECK GROUP] {raw_name}"
    else:
        display_name = raw_name

    # Normalize name + phone combinations to filter hidden duplicate entries
    normalized_phone = raw_phone.replace("-", "").replace(" ", "")
    identity_key = (display_name.lower(), normalized_phone)

    if identity_key in seen_identities:
        print(f"⏩ Skipping identical name/phone duplicate entry: {display_name}")
        continue
        
    seen_identities.add(identity_key)
    concert_access = True if "yes" in concert_status.lower() else False
    
    # Generate Unique Tracking IDs
    guest_id = f"MGM2026_{guest_id_counter}"
    guest_id_counter += 1

    # Append data structural object
    attendees.append({
        "id": guest_id,
        "name": display_name,
        "phone": raw_phone,
        "workshop": workshop,
        "concert": concert_access,
        "checkedIn": False
    })

    # Generate visual QR code output
    safe_filename = "".join([c if c.isalnum() else "_" for c in display_name])
    qr_path = f"{qr_folder}/{guest_id}_{safe_filename}.png"
    
    # Only generate the QR code image if it doesn't already exist locally
    if not os.path.exists(qr_path):
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(guest_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_path)

# 6. Output clean JSON file database
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(attendees, f, indent=4, ensure_ascii=False)

print(f"\n✅ Database synced successfully! Compiled {len(attendees)} clean unique entries.")
print(f"📁 Local frontend source updated: '{output_json}'")