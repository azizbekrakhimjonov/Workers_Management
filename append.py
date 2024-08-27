from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime

SERVICE_ACCOUNT_FILE = 'keys.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

creds = None
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# The ID spreadsheet.
SAMPLE_SPREADSHEET_ID = '1eE6fNUw2DRCEivBEGs-EfAF5lbHDJVzQhLODGZWZc6U'

service = build('sheets', 'v4', credentials=creds)

# Call the Sheets API
sheet = service.spreadsheets()

#column =  ["ИД", "Имя и Фамилию", "На работе", "Ушел с работы", 'местоположение', 'Отпроситься', 'На объекте'],
    
def add_gs(id, fullname, become, reason, inobject, location, belose):
    resource = {
      # "majorDimension": "ROWS",
      "values": [
        [id, fullname, become, reason, inobject, location, belose],
      ]
    }
    
    request = service.spreadsheets().values().append(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                                     range="lose!A2", valueInputOption="USER_ENTERED",
                                                      body=resource)
    response = request.execute()
    print('Successfuly')
    


def register_gs(id, fullname):
    resource = {
        "values": [
            [id, datetime.now().strftime("%d-%m-%Y"), fullname],
        ]
    }

    request = service.spreadsheets().values().append(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                                     range="workers!A2", valueInputOption="USER_ENTERED",
                                                     body=resource)
    response = request.execute()
    print('Successfuly')