import gspread
from google.oauth2.service_account import Credentials
import os
import json

# Scopes required for Google Sheets and Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def sync_to_sheets(review_data: dict, sheet_name: str = "Peer Review Data"):
    """
    Appends a single review record to the Google Sheet.
    review_data should contain: project, reviewer, rated_person, scores, remarks, etc.
    """
    json_path = "service_account.json"
    
    if not os.path.exists(json_path):
        print(f"Warning: {json_path} not found. Skipping Google Sheets sync.")
        return False

    try:
        credentials = Credentials.from_service_account_file(json_path, scopes=SCOPES)
        client = gspread.authorize(credentials)
        
        # Open the sheet by name
        try:
            sheet = client.open(sheet_name).get_worksheet(0)
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"Error: Spreadsheet '{sheet_name}' not found. Please share the sheet with the service account email.")
            return False

        # Prepare the row
        # Order: Date, Project, Reviewer, Reviewer Role, Rated Person, Rated Role, S1, S2, S3, POC Score, Remarks, Delay Reason
        row = [
            review_data.get("date", ""),
            review_data.get("project_name", ""),
            review_data.get("reviewer_name", ""),
            review_data.get("reviewer_role", ""),
            review_data.get("rated_person", ""),
            review_data.get("rated_role", ""),
            review_data.get("score_1", 0),
            review_data.get("score_2", 0),
            review_data.get("score_3", 0),
            review_data.get("score_poc", "N/A"),
            review_data.get("remarks", ""),
            review_data.get("delay_reason", "")
        ]
        
        sheet.append_row(row)
        print(f"Successfully synced review for {review_data.get('rated_person')} to Google Sheets.")
        return True
        
    except Exception as e:
        print(f"Failed to sync to Google Sheets: {str(e)}")
        return False

def initialize_sheet(sheet_name: str = "Peer Review Data"):
    """
    Sets up the headers if the sheet is empty.
    """
    json_path = "service_account.json"
    if not os.path.exists(json_path): return

    try:
        credentials = Credentials.from_service_account_file(json_path, scopes=SCOPES)
        client = gspread.authorize(credentials)
        sheet = client.open(sheet_name).get_worksheet(0)
        
        if not sheet.get_all_values():
            headers = ["Date", "Project", "Reviewer", "Reviewer Role", "Rated Person", "Rated Role", "Score 1", "Score 2", "Score 3", "POC Score", "Remarks", "Delay Reason"]
            sheet.append_row(headers)
    except Exception as e:
        print(f"Google Sheets init failed: {e}")
