import os
import pandas as pd
import qrcode

# 1. Load the spreadsheet (Adjust filename if necessary)
csv_file = "MGM 2026 Sign Up Form (Responses).xlsx"
df = pd.read_excel(csv_file)

# 2. Clean up column names to avoid typing mistakes
df.columns = df.columns.str.strip()

# Create a directory to store the generated QR codes
os.makedirs("generated_qrs", exist_ok=True)

# 3. Process each attendee
attendee_list_json = []

for index, row in df.iterrows():
    # Create a unique ID for every registration line
    guest_id = f"MGM2026_{1001 + index}"
    
    name = row["Name:"].strip()
    email = row["Email:"].strip()
    phone = str(row["Phone Number:"]).strip()
    workshop = row["Workshops: RM30 per session"].strip()
    concert_join = str(row["Join the FREE Concert from 2pm to 4pm!!!"]).strip()
    
    # Check if they get a concert wristband
    gets_concert_wristband = "Yes" in concert_join
    
    # Store clean information to be used by our scanner database
    attendee_list_json.append({
        "id": guest_id,
        "name": name,
        "email": email,
        "phone": phone,
        "workshop": workshop,
        "concert": gets_concert_wristband,
        "checkedIn": False # Initial status
    })
    
    # 4. Generate the QR Code containing ONLY the unique ID
    # (Keeping data inside the QR minimal ensures it's easy to scan even on old phones)
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(guest_id)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save the QR with a recognizable filename for distribution
    clean_name = "".join([c if c.isalnum() else "_" for c in name])
    filename = f"generated_qrs/{guest_id}_{clean_name}.png"
    img.save(filename)

# 5. Export our structured scanner database
import json
with open("attendees_db.json", "w", encoding="utf-8") as f:
    json.dump(attendee_list_json, f, indent=4, ensure_ascii=False)

print(f"Success! Generated {len(df)} QR codes in /generated_qrs/ and created attendees_db.json")