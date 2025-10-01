import streamlit as st
from st_ant_tree import st_ant_tree
from definitions import keyword_category_map, keyword_option_map, prefectures, job_categories_tree, holidays, work_environment, job_ex_categories_tree
from logic import login_to_api, job_search, job_count, format_job_df, flatten_json, sort
from import_csv import import_to_spreadsheet
import pandas as pd

def show_search_console():
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
  st.markdown(
      "<span style='font-size:0.9rem; color:black'>希望年収</span>",
      unsafe_allow_html=True
  )
  col1, col2 = st.columns(2)
  with col1:
      min_salary = st.text_input("下限")
  with col2:
      max_salary = st.text_input("上限")
  # 希望勤務地（プルダウンで都道府県を選択）
  desired_locations = st.multiselect('希望勤務地', list(prefectures.keys()))
  location_values = [prefectures[loc] for loc in desired_locations]
  # 希望職種
  st.markdown(
      "<span style='font-size:0.9rem; color:black'>希望職種</span>",
      unsafe_allow_html=True
  )
  selected_categories = st_ant_tree(
      treeData=job_categories_tree,
      treeCheckable=True,
      allowClear=True,
      key="desired"
  )
  # 休日
  selected_holidays = st.multiselect('休日', list(holidays.keys()))
  holiday_values = [holidays[loc] for loc in selected_holidays]

  # 労働環境
  selected_works = st.multiselect('労働環境', list(work_environment.keys()))
  work_values = [work_environment[loc] for loc in selected_works]

  # 経験職種
  st.markdown(
      "<span style='font-size:0.9rem; color:black'>経験職種</span>",
      unsafe_allow_html=True
  )
  selected_ex_categories = st_ant_tree(
      treeData=job_ex_categories_tree,
      treeCheckable=True,
      allowClear=True,
      key="experience"
  )

  # ---- 職種ごとの年数入力 ----
  job_years = {}

  if selected_ex_categories is not None:
      for job in selected_ex_categories:
          col1, col2 = st.columns([2,1])
          with col1:
              st.markdown(f"**{job}**")
          with col2:
              years = st.number_input(
                  "経験年数",
                  min_value=0, max_value=30, step=1,
                  key=f"{job}_years"
              )
          job_years[job] = years

  
  token = login_to_api()
  if token:
      try:
          count = job_count(token, keyword, keyword_category, keyword_option, min_salary, max_salary, location_values, selected_categories, holiday_values, work_values)
          st.write(f"検索結果数: {count}件")
      except Exception as e:
          st.write("検索結果数の取得に失敗しました。")
          # Optionally log the error: print(f"Error getting job count: {e}")
  # 検索ボタン
  if st.button('求人を検索'):
      if token:
          job_data = job_search(token, keyword, keyword_category, keyword_option, min_salary, max_salary, location_values, selected_categories, holiday_values, work_values)
          if job_data:
                st.write("求人データ取得成功！")
                flat_data = [flatten_json(d) for d in job_data]
                df = pd.DataFrame(flat_data)
                df_sorted = sort(job_years, df)
                df_formatted = format_job_df(df_sorted)
                st.write("求人データをスプレッドシートに転記中。。。")
                spreadsheet_url = import_to_spreadsheet(df_formatted)
                st.write(f"作成したシート：{spreadsheet_url}")
          elif len(job_data) < 1:
                st.write("検索結果が0件でした")
          else:
                st.write("求人データの取得に失敗しました。")
      else:
          st.write("ログインに失敗しました。")