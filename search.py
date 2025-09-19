import streamlit as st
from st_ant_tree import st_ant_tree
from definitions import keyword_category_map, keyword_option_map, prefectures, job_categories_tree
from logic import login_to_api, job_search, job_count, create_job_df
from import_csv import import_to_spreadsheet

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
  st.markdown(
      "<span style='font-size:0.9rem; color:black'>希望職種</span>",
      unsafe_allow_html=True
  )
  selected_categories = st_ant_tree(
      treeData=job_categories_tree,
      treeCheckable=True,
      allowClear=True
  )
  
  token = login_to_api()
  if token:
      try:
          count = job_count(token, keyword, keyword_category, keyword_option, min_salary, max_salary, location_values, selected_categories)
          st.write(f"検索結果数: {count}件")
      except Exception as e:
          st.write("検索結果数の取得に失敗しました。")
          # Optionally log the error: print(f"Error getting job count: {e}")
  # 検索ボタン
  if st.button('求人を検索'):
      if token:
          job_data = job_search(token, keyword, keyword_category, keyword_option, min_salary, max_salary, location_values, selected_categories)
          if job_data:
              st.write("求人データ取得成功！")
              df = create_job_df(job_data)
              spreadsheet_url = import_to_spreadsheet(df)
              st.write(f"作成したシート：{spreadsheet_url}")
          elif len(job_data) < 1:
              st.write("検索結果が0件でした")
          else:
              st.write("求人データの取得に失敗しました。")
      else:
          st.write("ログインに失敗しました。")