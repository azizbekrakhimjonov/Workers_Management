import datetime

from googleapiclient.discovery import build
from google.oauth2 import service_account

SERVICE_ACCOUNT_FILE = 'keys.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = None
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
SAMPLE_SPREADSHEET_ID = '1eE6fNUw2DRCEivBEGs-EfAF5lbHDJVzQhLODGZWZc6U'
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()
resource = {
    "values": [
        ["F.I.O", "Age", "Year", 'Address', 'Created_at'],
        ["Azizbek Rahimjonov", 22, 2002, 'Toshkent', datetime.datetime.now().strftime('%Y-%m-%d')],
        ["Jamshid Jabborov", 23, 2001, 'Toshkent', datetime.datetime.now().strftime('%Y-%m-%d')],
        [' ', '=MAX(B2:B3)']
    ]
}

request = service.spreadsheets().values().append(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                                 range="workers!A1", valueInputOption="USER_ENTERED",
                                                 body=resource)
response = request.execute()

print('Successfuly')
