import os
import gspread
from google.oauth2.service_account import Credentials
from core.database import get_all_leads

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
SHEET_NAME = "Viber Outreach Sync"

def sync_leads_to_sheets():
    if not os.path.exists(CREDENTIALS_FILE):
        return False, "credentials.json not found in the root folder.\n\nPlease follow instructions provided to generate and place it in the same folder as main.py."
        
    try:
        credentials = Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        
        try:
            sh = gc.open(SHEET_NAME)
        except gspread.exceptions.SpreadsheetNotFound:
            return False, f"Google Sheet named '{SHEET_NAME}' not found.\n\nPlease create a blank Google Sheet natively in your Drive and name it exactly '{SHEET_NAME}', then click 'Share' and share it with this service account email:\n{credentials.service_account_email}"
        
        worksheet = sh.sheet1
        leads = get_all_leads()
        
        headers = [
            "ID", "Name", "Phone Number", "City", "SIM Assignment", 
            "Contacted Status", "Pipeline Status", "Template Used", 
            "Contact Timestamp", "Reply Notes", "Action Link"
        ]
        rows = [headers]
        
        for lead in leads:
            phone = lead['phone_number']
            phone_clean = phone.replace(" ", "")
            if phone_clean.startswith("+"):
                phone_link = phone_clean.replace("+", "%2B")
            else:
                phone_link = phone_clean
                
            action_link = f'=HYPERLINK("viber://chat?number={phone_link}", "Message on Viber")'
            
            row = [
                lead['id'],
                lead['name'],
                phone,
                lead['city'] or "",
                lead['sim_assignment'],
                "True" if lead['is_contacted'] else "False",
                lead.get('lead_status', 'Uncontacted'),
                lead['template_used'] or "",
                lead['contact_timestamp'] or "",
                lead.get('reply_notes', ""),
                action_link
            ]
            rows.append(row)
            
        worksheet.clear()
        
        # Support both gspread <6.0 and >=6.0 syntax
        try:
            worksheet.update(values=rows, range_name='A1', value_input_option='USER_ENTERED')
        except TypeError:
            worksheet.update('A1', rows, value_input_option='USER_ENTERED')
            
        return True, "Data successfully synced to your Google Sheet!"
        
    except Exception as e:
        return False, str(e)
