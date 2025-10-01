from openai import OpenAI
import streamlit as st
import json
from pprint import pprint

api_key = st.secrets["open_ai"]["api_key"]
client = OpenAI(api_key=api_key)
model = "gpt-4o-mini"

def call_api(candidate_dict, jobs_df):

    candidate_text = json.dumps(candidate_dict, ensure_ascii=False)
    # JSONに変換する
    json_data = jobs_df[["id", "minimumQualification"]].to_dict(orient="records")

    # 日本語そのまま保持
    jobs_text = json.dumps(json_data, ensure_ascii=False, indent=2)

    print("aiにこれから話しかけます")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role":"developer","content":f"""あなたはプロの人材エージェントです。

            これから、
            ・求職者のこれまでの経験職種と対応する年数
            ・idと応募必須要件(minimumQualification)がペアになった求人情報
            を渡します。

            以下の条件に従ってください。

            <最重要ルール>
            ・同じ求人idは必ず一度だけ出力してください。重複は禁止です。
            ・もし複数の通過率に属する可能性がある場合は、最も高い通過率のグループにのみ含めてください。
            ・出力直前に、idが重複していないか必ず検証してください。

            <その他条件>
            ・求職者の経験職種・年数と求人の応募必須要件(minimumQualification)を照らし合わせて書類通過率を出してください。
            ・すべてのidに対して必ず判定してください。
            ・同じ書類通過率は一つのグループにまとめてください。
            ・書類通過率の高い順にソートしてください。

            ・出力は JSON 形式で、書類通過率(%:rate)とidのjsonリストのみを返してください。
            <出力形式>
            JSONリストのみを返してください。
            例：
            [
              {{
                "rate": 100,
                "ids": [111111, 222222]
              }},
              {{
                "rate": 80,
                "ids": [333333, 444444]
              }}
            ]
                """},
            {"role":"user","content":f"""
            求職者の職種・年数:
            {candidate_text}

            求人の応募必須要件：
            {jobs_text}
            """},
        ],
        store=True,
        temperature=0
    )
    res = response.choices[0].message.content
    try:
        # # 余分な文字列を削除
        cleaned_res = res.replace('```json', '').replace('```', '').strip()
        parsed_json = json.loads(cleaned_res)
        pprint(parsed_json)
        return parsed_json
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {str(e)}")
        print("Invalid JSON content:", res)
        raise


import pandas as pd

def example():
    data = {
        "job_id": [1, 2, 3, 4],
        "title": ["エンジニア", "デザイナー", "営業", "営業2"],
        "requirements": [
            "Pythonの経験3年以上",
            "Figmaを用いたUI設計経験",
            "法人営業経験5年以上",
            "法人営業経験5年以上"
        ]
    }
    df = pd.DataFrame(data)
    candidate_dict = {"エンジニア": 3, "営業": 5, "デザイナー": 2}

    candidate_text = json.dumps(candidate_dict, ensure_ascii=False)
    print(f"candidate_text: {candidate_text}")
    # JSONに変換する（job_idをキーにすると便利）
    json_data = df[["job_id", "requirements"]].to_dict(orient="records")
    # 日本語そのまま保持
    jobs_text = json.dumps(json_data, ensure_ascii=False, indent=2)
    print(f"jobs_text: {jobs_text}")
    scores = []
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role":"developer","content":f"""あなたはプロの人材エージェントです。
            求職者の職種・年数と求人の応募必須要件を照らし合わせて、合格率の高い順に求人をソートしてください。
            出力は JSON 形式で、書類通過率と求人ID のjsonリストのみを返してください。
            同じ書類通過率の場合は、まとめてください。
            """},
            {"role":"user","content":f"""
            求職者の職種・年数:
            {candidate_text}
            求人の応募必須要件：
            {jobs_text}
            """}
        ],
        store=True,
        temperature=0
    )
    res = response.choices[0].message.content
    try:
        # # 余分な文字列を削除
        cleaned_res = res.replace('```json', '').replace('```', '').strip()
        parsed_json = json.loads(cleaned_res)
        pprint(parsed_json)
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {str(e)}")
        print("Invalid JSON content:", res)
        raise


