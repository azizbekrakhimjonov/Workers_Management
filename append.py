import pytz
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime
from pprint import pprint

SERVICE_ACCOUNT_FILE = 'keys.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

creds = None
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

SAMPLE_SPREADSHEET_ID = '1u0tXdHh-umD92RPgaM-bOz8tVgjDoeJ-wM5vn8Zfk3E'

service = build('sheets', 'v4', credentials=creds)

sheet = service.spreadsheets()


# column =  ["ИД", "Имя и Фамилию", "На работе", "Ушел с работы", 'местоположение', 'Отпроситься', 'На объекте'],

def add_gs(id, fullname, become, reason, inobject, location, belose):
    resource = {
        # "majorDimension": "ROWS",
        "values": [
            [id, fullname, become, reason, inobject, location, belose],
        ]
    }

    request = service.spreadsheets().values().append(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                                     range="Grace!A2", valueInputOption="USER_ENTERED",
                                                     body=resource)
    response = request.execute()
    print('Successfuly')


def register_gs(id, fullname):
    timezone = pytz.timezone('Asia/Tashkent')
    current_time = datetime.now(timezone)
    date = current_time.strftime("%d-%m-%Y")
    resource = {
        "values": [
            [id, date, fullname],
        ]
    }
    request = service.spreadsheets().values().append(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                                     range="Houz!A2", valueInputOption="USER_ENTERED",
                                                     body=resource)
    response = request.execute()
    print('Successfuly')


def working_time(user_id):
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range="Houz!A1:D25").execute()
    values = result.get('values', [])
    for row in values[1:]:
        if row[0] == str(user_id):
            if len(row) > 3:
                return row[3]
            else:
                return None
    return None


