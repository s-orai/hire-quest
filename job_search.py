from sqlite3 import paramstyle
import requests
import os
from dotenv import load_dotenv
import pandas as pd
import json


load_dotenv()

# APIのエンドポイント
api_login_url = os.getenv("API_SESSION_URL")
api_job_serach_url = os.getenv("API_JOB_SEARCH_URL")
login_email = os.getenv("LOGIN_EMAIL")
login_password = os.getenv("LOGIN_PASSWORD")

def login_to_api(login_email, login_password):
    """
    Logs in to the API and returns the authentication token and response data.
    """
    # パラメータ（クエリ文字列）
    payload = {
        "email": login_email,
        "password": login_password
    }

    # リクエスト送信
    response = requests.post(api_login_url, json=payload)

    # ステータスコード確認
    print("Status Code:", response.status_code)

    # JSONデータを取得
    if response.status_code == 200 or response.status_code == 201:
        data = response.json()
        token = data.get("token")
        return token
    else:
        print("ログインに失敗しました。Error:", response.text)
        exit(1) # Stop execution on login failure

def job_search(token):
    """
    Searches for jobs using the API and returns the job data.
    """

    headers = {
        "x-circus-authentication-token": token
    }

    #  qJson を複数回指定するために list of tuple を使用
    params = [
        ("limit", 25),
        ("offset", 0),
        ("order", "desc"),
        ("orderBy", "recommendScore"),
        ("page", 1),
        ("qJson", json.dumps({"option": 7, "keyword": "188718, 73202", "logicType": "or"})),
        ("qJson", json.dumps({"option": 1, "keyword": "", "logicType": "or"})),
        ("qJson", json.dumps({"option": 1, "keyword": "", "logicType": "excludeAnd"})),
        ("qJson", json.dumps({"option": 1, "keyword": "", "logicType": "excludeOr"})),
        ("selectionDaysIncludingDuringMeasurement", "true"),
    ]

    # リクエスト送信
    response = requests.get(api_job_serach_url, headers=headers, params=params)

    # ステータスコード確認
    print("Status Code:", response.status_code)

        # JSONデータを取得
    if response.status_code == 200 or response.status_code == 201:
        data = response.json()["jobs"]
        print(data)
        return data
    else:
        print("求人取得に失敗しました。Error:", response.text)
        exit(1) # Stop execution on job search failure

# 再帰的にフラット化する関数
def flatten_json(y, prefix=''):
    out = {}
    if isinstance(y, dict):
        for k, v in y.items():
            out.update(flatten_json(v, prefix + k + '.'))
    elif isinstance(y, list):
        for i, v in enumerate(y):
            out.update(flatten_json(v, prefix + str(i) + '.'))
    else:
        out[prefix[:-1]] = y  # 最後のドットを除去
    return out


def create_job_list(json_data):
    """
    Creates a job list from the JSON data.
    """
    if not json_data:
        print("Error: No job data to process. Exiting.")
        exit(1)
    # JSONリストをフラット化
    flat_data = [flatten_json(d) for d in json_data]
    df = pd.DataFrame(flat_data)

    # CSV に書き出す
    df.to_csv("output.csv", index=False, encoding="utf-8")

    print("output.csv に出力しました")


if __name__ == "__main__":
    token = login_to_api(login_email, login_password)

    if token is None:
        print("Error: Token is None. Exiting.")
        exit(1)

    json_data = job_search(token)

    if json_data is None:
        print("Error: Job search data is None. Exiting.")
        exit(1)

    create_job_list(json_data)

