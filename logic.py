import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
from collections import deque
import pandas as pd
import json
import streamlit as st
from definitions import incentive, actual_bonus_payments, prefectures_reverse, num_of_bonuses, workstyle, relocation, positions, commission_earned_at, night_time_shift, overtime, job_categories
from ai_matching import call_api

# APIのエンドポイント
api_login_url = st.secrets["api_url"]["session"]
api_job_serach_url = st.secrets["api_url"]["job_search"]
api_logout_url = st.secrets["api_url"]["delete_session"]
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
    print("login Status Code:", response.status_code)

    # JSONデータを取得
    if response.status_code == 200 or response.status_code == 201:
        data = response.json()
        token = data.get("token")
        return token
    else:
        print("ログインに失敗しました。Error:", response.text)
        exit(1) # Stop execution on login failure

class RateLimiter:
    """
    1秒あたりの最大リクエスト数(rps)とバースト(burst)を制御する簡易レートリミッタ。
    マルチスレッド対応。
    """
    def __init__(self, rps: int, burst: int | None = None):
        self.rps = max(1, int(rps))
        self.burst = int(burst) if burst is not None else self.rps
        self.timestamps = deque()
        self._lock = threading.Lock()

    def acquire(self):
        while True:
            now = time.monotonic()
            with self._lock:
                # 1秒より古いタイムスタンプを捨てる
                while self.timestamps and now - self.timestamps[0] > 1.0:
                    self.timestamps.popleft()
                if len(self.timestamps) < self.burst:
                    self.timestamps.append(now)
                    return
                wait = 1.0 - (now - self.timestamps[0])
            if wait > 0:
                time.sleep(wait)

def _get_rate_config():
    try:
        cfg = st.secrets.get("rate_limit", {})
        rps = int(cfg.get("rps", 4))
        burst = int(cfg.get("burst", rps))
        return rps, burst
    except Exception:
        return 4, 4

def job_search(token, keyword, keyword_category, keyword_option, min_salary, max_salary, desired_locations, categories, holidays, works):
    """
    Searches for jobs using the API and returns all job data across all pages.
    """

    headers = {
        "x-circus-authentication-token": token
    }

    qjson = {"option": keyword_category, "keyword": keyword, "logicType": keyword_option}

    fixed_params = [
        ("qJson", json.dumps(qjson, ensure_ascii=False)),
        ("selectionDaysIncludingDuringMeasurement", "true"),
        ("annualSalary.max", max_salary),
        ("annualSalary.min", min_salary),
        ("commissionFeePercentage", 3),
    ]

    for loc in desired_locations:
        fixed_params.append(("prefectures", loc),)

    for loc in holidays:
        fixed_params.append(("holidays", loc),)

    for loc in works:
        fixed_params.append(("workEnvironments", loc),)

    if categories:
        for cat in categories:
            fixed_params.append(("occupations", cat),)

    # 件数確認
    cnt_res = requests.get(api_job_serach_url, headers=headers, params=fixed_params)
    if cnt_res.status_code != 200 and cnt_res.status_code != 201:
        print("求人件数取得に失敗しました。Error:", cnt_res.text)
        exit(1) # Stop execution on job search failure
    cnt = cnt_res.json()["total"]

    # 20件は担保する
    if cnt < 20:
        # 辞書に変換
        params_dict = dict(fixed_params)
        # 書き換え
        params_dict["commissionFeePercentage"] = 2
        # 最後に再度リスト形式に戻す
        fixed_params = list(params_dict.items())

    jobs = []
    limit = 25  # 1ページあたりの取得件数

    # ページ単位取得の並列化
    rps, burst = _get_rate_config()
    limiter = RateLimiter(rps, burst)

    def _fetch_page(off):
        params = [
            ("limit", limit),
            ("offset", off),
            ("page", (off // limit) + 1),
        ]
        params.extend(fixed_params)
        try:
            print(f"params: {params}")
            print(f"page: {(off // limit) + 1}")
            limiter.acquire()
            response = requests.get(api_job_serach_url, headers=headers, params=params, timeout=20)
            print("job_search Status Code:", response.status_code)
            if response.status_code == 200 or response.status_code == 201:
                return response.json().get("jobs", [])
            print("求人取得に失敗しました。Error:", response.text)
            exit(1)
        except Exception as e:
            print(f"求人一覧ページ取得中に例外が発生しました。offset={off}, Error:{e}")
            exit(1)

    offsets = list(range(0, cnt, limit))
    with ThreadPoolExecutor(max_workers=min(6, burst)) as executor:
        futures = [executor.submit(_fetch_page, off) for off in offsets]
        for future in as_completed(futures):
            data = future.result()
            if data:
                jobs.extend(data)

    job_details = []
    # リクエスト送信(詳細情報など) 並列化
    def _fetch_detail(job_id):
        try:
            limiter.acquire()
            response = requests.get(api_job_serach_url, headers=headers, params=[("id", job_id)], timeout=15)
            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            print(f"求人取得に失敗しました。求人ID: {job_id}, Error:{response.text}")
            return None
        except Exception as e:
            print(f"求人詳細取得中に例外が発生しました。求人ID: {job_id}, Error:{e}")
            return None

    with ThreadPoolExecutor(max_workers=min(8, burst)) as executor:
        futures = [executor.submit(_fetch_detail, job["id"]) for job in jobs]
        for future in as_completed(futures):
            detail = future.result()
            if detail:
                job_details.append(detail)

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

def format_job_df(df):
    """
    Format a job list from the JSON data.
    """

    df["職種"] = df["occupations.main"].map(job_categories)
    df["想定年収"] = df.apply(lambda row: f"{row["expectedAnnualSalary.min"]}万円~{row["expectedAnnualSalary.max"]}万円", axis=1)
    df["月給"] = df.apply(
        lambda row: "" if pd.isna(row["expectedMonthlySalary.min"]) and pd.isna(row["expectedMonthlySalary.max"]) else f"{row['expectedMonthlySalary.min']}万円~{row['expectedMonthlySalary.max']}万円",
        axis=1,
    )

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
    df["成果報酬金額"] = df.apply(format_commission, axis=1)
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

    # リクエスト送信
    res = requests.get(api_job_serach_url, headers=headers, params=params)
    # ステータスコード確認
    print("job_count Status Code:", res.status_code)
    if res.status_code != 200 and res.status_code != 201:
        print("求人件数取得に失敗しました。Error:", res.text)
        exit(1) # Stop execution on job search failure

    cnt = res.json()["total"]

    if cnt >= 20:
        return cnt

    # 20件は担保する
    # 辞書に変換
    params_dict = dict(params)
    # 書き換え
    params_dict["commissionFeePercentage"] = 2
    # 最後に再度リスト形式に戻す
    params = list(params_dict.items())

    res = requests.get(api_job_serach_url, headers=headers, params=params)

    # ステータスコード確認
    print("job_count Status Code:", res.status_code)

    # JSONデータを取得
    if res.status_code == 200 or res.status_code == 201:
        cnt = res.json()["total"]
        return cnt
    else:
        print("求人件数取得に失敗しました。Error:", res.text)
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

def logout(token):
    headers = {
        "x-circus-authentication-token": token
    }
    # リクエスト送信
    response = requests.get(api_logout_url, headers=headers)

    # ステータスコード確認
    if response.status_code != 200 and response.status_code != 201:
        print("ログアウトに失敗しました。Error:", response.text)
    else:
        print("ログアウトsuccess!!")

def sort(job_years, df):
    # 経験職種情報がない場合は、feeでのソートのみ
    if not job_years:
        sorted_ids = sort_fee(df)

        df_sorted = df.set_index("id").loc[sorted_ids].reset_index()
        return df_sorted

    # aiが書類通過率を判定
    matching_json = call_api(job_years, df)

    # ---- 重複除去&ソート処理 ----
    # 書類通過率が高い順に並んでいる前提（AI側でソートしている想定）
    seen = set() # 初めて出てきたIDを管理
    sorted_ids = []

    for group in matching_json:
        # 重複除去
        unique_ids = [] # rateごとのID保持する
        for _id in group["ids"]:
            if _id not in seen:  # 初めて出てきたIDなら採用
                seen.add(_id)
                unique_ids.append(_id)
            # すでに出たIDはスキップ（＝高いレートの方に残る）
        if unique_ids:
            # ソート（commissionFeeの降順）
            sub_ids = sort_fee(df, unique_ids)
            sorted_ids.extend(sub_ids)

    # --- AIに出てこなかった残りのIDを最後に追加 ---
    remaining_ids = df.loc[~df["id"].isin(sorted_ids), "id"].tolist()
    remaining_ids_sort = sort_fee(df, remaining_ids)
    sorted_ids.extend(remaining_ids_sort)

    df_sorted = df.set_index("id").loc[sorted_ids].reset_index()
    return df_sorted

def sort_fee(df, ids = []):
    if ids:
        df = df[df["id"].isin(ids)]
    ids_sort = df.sort_values("commissionFee.fee", ascending=False)["id"].tolist()
    return ids_sort
