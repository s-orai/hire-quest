import streamlit as st
from definitions import keyword_category_map, keyword_option_map, prefectures, job_categories

st.title('Job Search App')

# キーワード種別
displayed_category = st.selectbox('検索種別', list(keyword_category_map.keys()))
keyword_category = keyword_category_map[displayed_category]

# キーワード
keyword = st.text_input('キーワード')

# andかor
displayed_option = st.selectbox('検索条件', list(keyword_option_map.keys()))
keyword_option = keyword_option_map[displayed_option]

# 希望年収（下限と上限）
min_salary, max_salary = st.slider(
    '希望年収 (万円)',
    min_value=0,
    max_value=2000,
    value=(300, 800)
)

# 希望勤務地（プルダウンで都道府県を選択）
desired_location = st.selectbox('希望勤務地', list(prefectures.keys()))

st.markdown(
    "<span style='font-size:0.9rem; color:black'>希望職種</span>",
    unsafe_allow_html=True
)
# ステップ1: カテゴリ選択
selected_category = st.selectbox("① 職種カテゴリを選択してください", list(job_categories.keys()))

# session_state の初期化
for cat in job_categories:
    if cat not in st.session_state:
        st.session_state[cat] = []  # 空のリストで初期化
    if f"all_{cat}" not in st.session_state:
        st.session_state[f"all_{cat}"] = False  # 全選択チェック用

# ステップ2: 職種選択
if selected_category:
    st.markdown(f"""
    <span style='font-size:0.9rem; color:black'>② {selected_category} の職種を選択してください</span>
    """,
    unsafe_allow_html=True
)

    # 全て選択チェックボックス
    select_all = st.checkbox("全て選択", value=st.session_state[f"all_{selected_category}"], key=f"check_{selected_category}")
    
    if select_all:
        # 全部選択
        selected_jobs = job_categories[selected_category]
    else:
        # 過去の選択を復元
        selected_jobs = st.multiselect(
            "職種",
            job_categories[selected_category],
            default=st.session_state[selected_category],
            key=f"multiselect_{selected_category}"
        )
    
    # session_state に保存
    st.session_state[selected_category] = selected_jobs
    st.session_state[f"all_{selected_category}"] = select_all

# 結果まとめて表示
st.write("✅ 現在の全カテゴリでの選択状況:")
for cat, jobs in st.session_state.items():
    if not cat.startswith("all_") and jobs:
        st.write(f"- {cat}: {jobs}")

st.write('カテゴリー:', keyword_category)
st.write('キーワード:', keyword)
st.write('検索条件:', keyword_option)
st.write('希望年収:', f'{min_salary}万円 〜 {max_salary}万円')
st.write('希望勤務地:', desired_location)
