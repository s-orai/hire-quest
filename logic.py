import requests
import pandas as pd
import json
import streamlit as st

# APIのエンドポイント
api_login_url = st.secrets["api_url"]["session"]
api_job_serach_url = st.secrets["api_url"]["job_search"]
login_email = st.secrets["login_user"]["email"]
login_password = st.secrets["login_user"]["password"]

def login_to_api():
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

def job_search(token, keyword, keyword_category, keyword_option, min_salary, max_salary, desired_locations, categories):
    """
    Searches for jobs using the API and returns all job data across all pages.
    """

    headers = {
        "x-circus-authentication-token": token
    }

    qjson = {"option": keyword_category, "keyword": keyword, "logicType": keyword_option}

    all_jobs = []
    offset = 0
    limit = 25  # 1ページあたりの取得件数

    while True:
        params = [
          ("limit", limit),
          ("offset", offset),
          ("order", "desc"),
          ("orderBy", "recommendScore"),
          ("page", (offset // limit) + 1),
          ("qJson", json.dumps(qjson, ensure_ascii=False)),
          ("selectionDaysIncludingDuringMeasurement", "true"),
          ("annualSalary.max", max_salary),
          ("annualSalary.min", min_salary)
        ]

        for loc in desired_locations:
          params.append(("prefectures", loc),)

        if categories:
            for cat in categories:
              params.append(("occupations", cat),)

        # リクエスト送信
        response = requests.get(api_job_serach_url, headers=headers, params=params)

        # ステータスコード確認
        print("Status Code:", response.status_code)

        # JSONデータを取得
        if response.status_code == 200 or response.status_code == 201:
            data = response.json()["jobs"]
            if not data:
                break  # データがもうない場合はループを終了
            all_jobs.extend(data)
            offset += limit
        else:
            print("求人取得に失敗しました。Error:", response.text)
            exit(1) # Stop execution on job search failure
    return all_jobs

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

def create_job_df(json_data):
    """
    Creates a job list from the JSON data.
    """
    if not json_data:
        print("Error: No job data to process. Exiting.")
        exit(1)
    # JSONリストをフラット化
    flat_data = [flatten_json(d) for d in json_data]
    df = pd.DataFrame(flat_data)

    return df

def job_count(token, keyword, keyword_category, keyword_option, min_salary, max_salary, desired_locations, categories):
    """
    Searches for jobs using the API and returns the job count.
    """

    headers = {
        "x-circus-authentication-token": token
    }

    qjson = {"option": keyword_category, "keyword": keyword, "logicType": keyword_option}

    params = [
      ("qJson", json.dumps(qjson, ensure_ascii=False)),
      ("selectionDaysIncludingDuringMeasurement", "true"),
      ("annualSalary.max", max_salary),
      ("annualSalary.min", min_salary),
    ]

    for loc in desired_locations:
      params.append(("prefectures", loc),)

    if categories:
        for cat in categories:
          params.append(("occupations", cat),)

    # リクエスト送信
    response = requests.get(api_job_serach_url, headers=headers, params=params)

    # ステータスコード確認
    print("Status Code:", response.status_code)

        # JSONデータを取得
    if response.status_code == 200 or response.status_code == 201:
        data = response.json()["total"]
        return data
    else:
        print("求人取得に失敗しました。Error:", response.text)
        exit(1) # Stop execution on job search failure
