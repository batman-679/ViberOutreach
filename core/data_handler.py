import pandas as pd
import os
from .database import add_lead

def import_leads_from_csv(file_path):
    """
    Reads a CSV file using pandas and inserts new leads into the database.
    Expected columns: Name, Phone Number, City (case-insensitive, handles various combinations)
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return 0
        
    try:
        df = pd.read_csv(file_path, dtype=str) # Read as string to preserve phone number formatting
        
        # Standardize column names to lowercase for easier matching
        df.columns = df.columns.astype(str).str.lower().str.strip()
        
        # Map expected columns
        name_col = next((col for col in df.columns if 'name' in col), None)
        phone_col = next((col for col in df.columns if 'phone' in col or 'number' in col), None)
        city_col = next((col for col in df.columns if 'city' in col or 'location' in col), None)
        
        if not name_col or not phone_col:
            print("Error: CSV must contain 'Name' and 'Phone Number' columns.")
            return 0
            
        imported_count = 0
        
        # Iterate over rows and add to database
        for _, row in df.iterrows():
            name = str(row[name_col]).strip() if pd.notna(row[name_col]) else "Unknown"
            phone = str(row[phone_col]).strip() if pd.notna(row[phone_col]) else ""
            city = str(row[city_col]).strip() if city_col and pd.notna(row[city_col]) else ""
            
            if phone:  # Only add if phone number is present
                add_lead(name, phone, city)
                imported_count += 1
                
        return imported_count
        
    except Exception as e:
        print(f"Failed to import CSV: {e}")
        return 0
