import os
import re
import gspread
import yagmail
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# CONFIGURATION DETAILS FOR AUTOMATION EMAIL
# ==========================================
SENDER_EMAIL = "mgmkenny970@gmail.com"
SENDER_APP_PASSWORD = "pcwu ovrn cnbb tvkg"  # Your 16-character Gmail App Password

sheet_title = "MGM 2026 Sign Up Form (Responses)"
qr_folder = "test_QRS"
# ==========================================

# 1. Configure Google API Permissions
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if not os.path.exists("google_credentials.json"):
    print("❌ Error: 'google_credentials.json' missing from your project folder.")
    exit()

creds = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", scope)
client = gspread.authorize(creds)

print(f"🔄 Connecting to Google Cloud to fetch sheet: '{sheet_title}'...")

try:
    spreadsheet = client.open(sheet_title)
    worksheet = spreadsheet.get_worksheet(0)
    raw_data = worksheet.get_all_values()
    
    headers = [h.strip() for h in raw_data[0]]
    rows = raw_data[1:]
    
    # Locate column positions dynamically
    name_idx = headers.index("Name:")
    workshop_idx = headers.index("Workshops: RM30 per session")
    concert_idx = headers.index("Join the FREE Concert from 2pm to 4pm!!!")
    email_idx = headers.index("Email:") if "Email Address" in headers else headers.index("Email:")
    
    # Handle tracking for already sent emails dynamically
    if "Ticket Sent" not in headers:
        print("➕ Creating 'Ticket Sent' column in your Google Sheet to track delivery...")
        worksheet.update_cell(1, len(headers) + 1, "Ticket Sent")
        headers.append("Ticket Sent")
    
    ticket_sent_idx = headers.index("Ticket Sent")

    # Connect securely to Gmail via yagmail
    print("🔌 Starting secure automated email client connection...")
    yag = yagmail.SMTP(SENDER_EMAIL, SENDER_APP_PASSWORD)
    
    guest_id_counter = 1001
    emails_sent_this_run = 0

    # Loop through rows to send unsent tickets
    for i, row in enumerate(rows):
        # Row number in Google Sheet (1-indexed, skipping header)
        sheet_row_num = i + 2 
        
        if len(row) <= max(name_idx, email_idx) or not row[name_idx].strip():
            continue
            
        display_name = row[name_idx].strip()
        raw_email = row[email_idx].strip()
        
        workshop = row[workshop_idx].strip() if workshop_idx < len(row) else "None of the above"
        concert_status = row[concert_idx].strip() if concert_idx < len(row) else "No"
        concert_access = True if "yes" in concert_status.lower() else False
        
        # Determine tracking sequence ID matching generate_qr_codes.py
        guest_id = f"MGM2026_{guest_id_counter}"
        guest_id_counter += 1

        # Check if the ticket has already been recorded as sent in the Google Sheet
        if ticket_sent_idx < len(row) and row[ticket_sent_idx].strip().upper() == "SENT":
            print(f"⏩ Already sent to {display_name}. Skipping.")
            continue

        if not raw_email or "@" not in raw_email:
            print(f"⚠️ Invalid/Missing email for {display_name}. Skipping.")
            continue

        # Look for the generated QR code image file
        safe_filename = "".join([c if c.isalnum() else "_" for c in display_name])
        qr_path = f"{qr_folder}/{guest_id}_{safe_filename}.png"

        if not os.path.exists(qr_path):
            print(f"⚠️ QR code file missing for {display_name} ({qr_path}). Run your generator first!")
            continue

        # Compose and dispatch the HTML email ticket template
        try:
            subject = f"Your MGM 2026 Registration Ticket - {display_name}"
            
            # Polished & Highly Readable HTML Email Template (Optimized for Mobile viewports)
            body = f"""
            <html>
                <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f9; color: #2c3e50;-webkit-font-smoothing: antialiased;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px 15px;">
                        
                        <div style="background: #ffffff; border-radius: 12px; padding: 30px 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border: 1px solid #eef2f5;">
                            
                            <h2 style="margin-top: 0; margin-bottom: 15px; color: #1e293b; font-size: 22px; font-weight: 700; line-height: 1.3;">
                                Hi {display_name},
                            </h2>
                            
                            <p style="font-size: 16px; line-height: 1.6; color: #475569; margin-bottom: 25px;">
                                Thank you for registering for <strong>MGM 2026</strong>! We are excited to have you join us. Your registration details and unique entryway ticket are finalized.
                            </p>
                            
                            <div style="background-color: #f8fafc; border-left: 4px solid #2c3e50; border-radius: 6px; padding: 20px; margin: 25px 0;">
                                <h3 style="margin-top: 0; margin-bottom: 12px; color: #2c3e50; font-size: 16px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                                    📌 Event Entry Details
                                </h3>
                                
                                <table style="width: 100%; border-collapse: collapse; font-size: 16px; line-height: 1.5;">
                                    <tr>
                                        <td style="padding: 6px 0; color: #64748b; width: 40%; vertical-align: top;"><strong>Your Unique ID:</strong></td>
                                        <td style="padding: 6px 0; color: #0f172a; font-family: monospace; font-weight: bold; font-size: 17px;">{guest_id}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #64748b; vertical-align: top;"><strong>Workshop Name:</strong></td>
                                        <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{workshop}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #64748b; vertical-align: top;"><strong>Concert Pass:</strong></td>
                                        <td style="padding: 6px 0; color: #0f172a;">
                                            {"🎟️ Included (Full Access)" if concert_access else "❌ Workshop Only"}
                                        </td>
                                    </tr>
                                </table>
                            </div>
                            
                            <div style="border-top: 1px solid #e2e8f0; margin-top: 25px; padding-top: 20px;">
                                <p style="font-size: 15px; line-height: 1.6; color: #475569; margin-bottom: 15px;">
                                    ⚠️ <strong style="color: #dc2626;">Important Check-In Instructions:</strong>
                                </p>
                                <p style="font-size: 15px; line-height: 1.6; color: #64748b; margin-top: 0;">
                                    Attached to this email is your personal <strong>QR Ticket Image file</strong>. Please save this picture to your phone's photo library. 
                                </p>
                                <p style="font-size: 15px; line-height: 1.6; color: #64748b;">
                                    When you arrive at the venue, present the image file on your phone screen to our volunteers at the registration counters. They will scan it to provide you with your official session and concert entrance wristbands.
                                </p>
                            </div>
                            
                            <div style="margin-top: 35px; padding-top: 20px; border-top: 1px solid #f1f5f9; font-size: 14px; color: #94a3b8; line-height: 1.5;">
                                See you at the event!<br>
                                <strong style="color: #475569; font-size: 15px;">MGM 2026 Organizing Team</strong>
                            </div>
                            
                        </div>
                    </div>
                </body>
            </html>
            """
            
            print(f"✉️ Dispatching ticket to: {raw_email}...")
            yag.send(to=raw_email, subject=subject, contents=body, attachments=qr_path)
            
            # Immediately update the Google Sheet so this row is permanently marked safe
            worksheet.update_cell(sheet_row_num, ticket_sent_idx + 1, "SENT")
            emails_sent_this_run += 1
            
        except Exception as email_err:
            print(f"❌ Error sending to {display_name}: {str(email_err)}")

    print(f"\n✅ Finished! Successfully dispatched {emails_sent_this_run} new ticket emails.")

except Exception as global_err:
    print(f"🚨 A processing error occurred: {str(global_err)}")