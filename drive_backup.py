# drive_backup.py
import os
import zipfile
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import subprocess

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate():
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def zip_git_tracked_files():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f'kuber_git_backup_{timestamp}.zip'

    result = subprocess.run(['git', 'ls-files'], stdout=subprocess.PIPE)
    files = result.stdout.decode().splitlines()

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            if os.path.isfile(file):
                zipf.write(file)
    print(f"Zipped: {zip_filename}")
    return zip_filename

def upload_to_drive(file_path):
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {'name': os.path.basename(file_path)}
    media = MediaFileUpload(file_path, resumable=True)
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    print(f"Uploaded to Drive: File ID = {uploaded_file.get('id')}")
    return uploaded_file.get('id')

def main():
    zip_file = zip_git_tracked_files()
    upload_to_drive(zip_file)
    os.remove(zip_file)

if __name__ == '__main__':
    main()
