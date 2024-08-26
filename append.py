from googleapiclient.discovery import build
from google.oauth2 import service_account

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
    
def add(id, name, atwork, notwork, location, reason, inobject): 
    resource = {
      # "majorDimension": "ROWS",
      "values": [
        [id, name, atwork, notwork, location, reason, inobject],
      ]
    }
    
    request = service.spreadsheets().values().append(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                                     range="lose!A1", valueInputOption="USER_ENTERED",
                                                      body=resource)
    response = request.execute()
    
    print('Successfuly')
    
    
add(234234, 'Azizbek Rahimjonov', '14:00',  '16:30', 'It Park', 'fall', 'Yunusobod' )
add(234234, 'Ali Sharipov', '14:00',  '16:30', 'It Park', 'fall', 'Yunusobod' )
