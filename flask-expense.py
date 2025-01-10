from flask import Flask, render_template, request, redirect, jsonify
import pandas as pd
import os
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

app = Flask(__name__)

# Authenticate with Google Sheets
def authenticate_google_sheets():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    # Load Google OAuth credentials from an environment variable
    client_secrets_str = os.getenv("GOOGLE_CREDENTIALS_JSON")  # Environment variable containing JSON
    if not client_secrets_str:
        raise ValueError("Environment variable GOOGLE_CREDENTIALS_JSON not set")
        
    client_config = json.loads(client_secrets_str)
    
    # Create OAuth flow using in-memory config
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)  # This will open the local server for login
    service = build('sheets', 'v4', credentials=creds)
    return service

# Write data to a Google Sheet
def write_to_google_sheet(spreadsheet_id, data_frame):
    service = authenticate_google_sheets()
    sheet = service.spreadsheets()
    
    values = [data_frame.columns.tolist()] + data_frame.fillna("").values.tolist()  # Convert to list of lists
    body = {'values': values}
    output_range_name = "sheets-proto!A1:D"

    result = sheet.values().update(
        spreadsheetId=spreadsheet_id,
        range=output_range_name,
        valueInputOption="RAW",
        body=body
    ).execute()

# Analyze spending
def analyze_spending(data, spending_threshold=500):
    data['Amount'] = pd.to_numeric(data['Amount'], errors='coerce').fillna(0)

    work_expenses = data[data['Category'] == 'Work']
    personal_expenses = data[data['Category'] == 'Personal']

    work_summary = work_expenses.groupby('Description')['Amount'].sum().to_dict()
    personal_summary = personal_expenses.groupby('Description')['Amount'].sum().to_dict()

    total_work = work_expenses['Amount'].sum()
    total_personal = personal_expenses['Amount'].sum()

    labeled_summary = {
        'Work Expenses': work_summary,
        'Personal Expenses': personal_summary,
        'Total Work': total_work,
        'Total Personal': total_personal
    }

    return labeled_summary

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        file = request.files['file']
        spreadsheet_id = request.form['spreadsheet_id']

        if file and spreadsheet_id:
            amex_data = pd.read_csv(file)
            if all(col in amex_data.columns for col in ['Description', 'Category', 'Amount']):
                write_to_google_sheet(spreadsheet_id, amex_data)
                summary = analyze_spending(amex_data)
                return render_template("summary.html", summary=summary)
            else:
                return "Error: CSV is missing required columns."
        else:
            return "Error: Missing spreadsheet ID or file."
    return render_template("index.html")

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
