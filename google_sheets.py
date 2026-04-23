# Google Sheets sync is currently DISABLED.
# To re-enable: restore the original gspread implementation and add service_account.json

def sync_to_sheets(review_data: dict, sheet_name: str = "Peer Review Data"):
    """Google Sheets sync is disabled. No-op."""
    print("[Sheets] Sync disabled — skipping.")
    return False

def initialize_sheet(sheet_name: str = "Peer Review Data"):
    """Google Sheets init is disabled. No-op."""
    print("[Sheets] Init disabled — skipping.")
