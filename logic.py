import requests
import pandas as pd
import json
import streamlit as st
from definitions import incentive, actual_bonus_payments, prefectures_reverse, num_of_bonuses, workstyle, relocation, positions, commission_earned_at, night_time_shift, overtime, job_categories

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

def job_search(token, keyword, keyword_category, keyword_option, min_salary, max_salary, desired_locations, categories, holidays, works):
    """
    Searches for jobs using the API and returns all job data across all pages.
    """

    headers = {
        "x-circus-authentication-token": token
    }

    qjson = {"option": keyword_category, "keyword": keyword, "logicType": keyword_option}

    jobs = []
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
            ("annualSalary.min", min_salary),
            ("commissionFeePercentage", 3),
        ]

        for loc in desired_locations:
            params.append(("prefectures", loc),)

        for loc in holidays:
            params.append(("holidays", loc),)

        for loc in works:
            params.append(("workEnvironments", loc),)

        if categories:
            for cat in categories:
                params.append(("occupations", cat),)

        # 件数確認
        cnt_res = requests.get(api_job_serach_url, headers=headers, params=params)
        if cnt_res.status_code != 200 and cnt_res.status_code != 201:
            print("求人件数取得に失敗しました。Error:", cnt_res.text)
            exit(1) # Stop execution on job search failure
        cnt = cnt_res.json()["total"]

        # 20件は担保する
        if cnt < 20:
            # 辞書に変換
            params_dict = dict(params)
            # 書き換え
            params_dict["commissionFeePercentage"] = 2
            # 最後に再度リスト形式に戻す
            params = list(params_dict.items())

        # リクエスト送信
        response = requests.get(api_job_serach_url, headers=headers, params=params)

        # ステータスコード確認
        print("Status Code:", response.status_code)

        if response.status_code != 200 and response.status_code != 201:
            print("求人取得に失敗しました。Error:", response.text)
            exit(1) # Stop execution on job search failure

        # JSONデータを取得
        data = response.json()["jobs"]
        if not data:
            break  # データがもうない場合はループを終了
        jobs.extend(data)
        offset += limit

    job_details = []
    # リクエスト送信(詳細情報など)
    for job in jobs:
        job_id = job["id"]
        response = requests.get(api_job_serach_url, headers=headers, params=[("id", job_id)])

        if response.status_code != 200 and response.status_code != 201:
            print(f"求人取得に失敗しました。求人ID: {job_id}, Error:{response.text}")
            continue
        job_details.append(response.json())

    return job_details

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

    df["職種"] = df["occupations.main"].map(job_categories)
    df["想定年収"] = df.apply(lambda row: f"{row["expectedAnnualSalary.min"]}万円~{row["expectedAnnualSalary.max"]}万円", axis=1)
    df["月給"] = df.apply(lambda row: f"{row["expectedMonthlySalary.min"]}万円~{row["expectedMonthlySalary.max"]}万円", axis=1)

    df["勤務地"] = df.apply(lambda row: collect_values(row, "addresses", prefectures_reverse, "prefecture"), axis=1)
    df["職位"] = df.apply(lambda row: collect_values(row, "positions", positions), axis=1)

    df["賞与回数"] = df["frequencyOfBonusPayments"].map(num_of_bonuses)
    df["昨年度賞与実績"] = df["actualBonusPaymentsLastYear"].map(actual_bonus_payments)
    df["インセンティブ"] = df["incentive"].map(incentive)

    df["勤務形態"] = df.apply(lambda row: collect_values(row, "workStyles", workstyle), axis=1)

    df["転勤の可能性"] = df["relocationProbability"].map(relocation)
    df["勤務時間"] = df.apply(lambda row: f"{row["workHours.start"]}~{row["workHours.end"]}", axis=1)
    df["夜間勤務"] = df["nightTimeShift"].map(night_time_shift)
    df["月刊平均残業時間"] = df["averageOvertime"].map(overtime)
    df['成果報酬金額'] = df.apply(format_commission, axis=1)
    df["成果地点"] = df["commissionEarnedAt"].map(commission_earned_at)

    # 抽出項目を絞り込み
    df = df[["id", "name", "company.name", "職種", "職位", "想定年収", "月給", "勤務地", "minimumQualification", "jobDescriptions", "賞与回数", "昨年度賞与実績", "インセンティブ", "annualSalaryExample", "salaryComments", "addressDetail", "勤務形態", "転勤の可能性", "勤務時間", "夜間勤務", "月刊平均残業時間", "locationComments", "成果報酬金額", "成果地点"]]

    # 項目名を変更
    df = df.rename(columns={
        "id": "求人ID",
        "name": "求人名",
        "company.name": "募集企業名",
        "minimumQualification": "応募必須条件",
        "jobDescriptions": "仕事内容",
        "annualSalaryExample": "年収例",
        "salaryComments": "給与・年収例 補足情報",
        "addressDetail": "勤務地詳細",
        "locationComments": "勤務地・勤務時間 補足情報",
    })

    return df

def job_count(token, keyword, keyword_category, keyword_option, min_salary, max_salary, desired_locations, categories, holidays, works):
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
        ("commissionFeePercentage", 2),
    ]

    for loc in desired_locations:
        params.append(("prefectures", loc),)

    for loc in holidays:
        params.append(("holidays", loc),)

    for loc in works:
        params.append(("workEnvironments", loc),)

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
        print("求人件数取得に失敗しました。Error:", response.text)
        exit(1) # Stop execution on job search failure


def collect_values(row, prefix: str, mapping: dict, suffix: str = "", sep: str = "、"):
    """
    row: df.apply で渡される1行
    prefix: 列名のプレフィックス (例: 'addresses.')
    suffix: 列名のサフィックス (例: '.prefecture')
    mapping: 対応辞書 (例: prefectures_reverse)
    sep: 結合時の区切り文字
    """
    results = []
    i = 0
    while True:
        parts = [prefix, str(i)]
        if suffix:
            parts.append(suffix)
        col = ".".join(parts)

        if col not in row:
            break
        val = row[col]
        if pd.notna(val):
            results.append(mapping.get(val, "不明"))
        i += 1
    return sep.join(results)

def format_commission(row):
    try:
        fee = row['commissionFee.fee']
        cid = row['commissionFee.id']
    except KeyError:
        return None
    if cid == 1:
        return f"理論年収×{fee}%"
    else:
        return f"{fee:,}円"