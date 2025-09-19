import csv
import datetime
import streamlit as st
import gspread
from gspread_dataframe import set_with_dataframe
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials


SCOPES = [
  "https://www.googleapis.com/auth/drive",
  "https://www.googleapis.com/auth/spreadsheets"
]

FOLDER_ID = st.secrets["google"]["folder_id"]

def import_to_spreadsheet(df):
    # サービスアカウント認証
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)

    # Drive API クライアント作成
    drive_service = build("drive", "v3", credentials=creds)

    # gspread 用クライアント
    gspread_client = gspread.authorize(creds)


    # 1. 新しいスプレッドシートを作成（共有ドライブのフォルダ内）
    title = "import_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "parents": [FOLDER_ID]
    }

    spreadsheet = drive_service.files().create(
        body=file_metadata,
        supportsAllDrives=True,
        fields="id"
    ).execute()

    spreadsheet_id = spreadsheet.get("id")
    print(f"✅ 新規スプレッドシート作成: {spreadsheet_id}")

    # 2. gspreadでシートを開く
    sheet = gspread_client.open_by_key(spreadsheet_id).sheet1

    # 3. dfをシートに書き込み
    set_with_dataframe(sheet, df)

    # URLを組み立てる
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

    print("✅ CSVをスプレッドシートにインポートしました！")
    return spreadsheet_url
