import streamlit as st
import streamlit_authenticator as stauth
import yaml
import search

# secrets.toml から取得
config = {
    "credentials": yaml.safe_load(st.secrets["auth"]["credentials"])["credentials"],
    "cookie": yaml.safe_load(st.secrets["auth"]["cookie"])["cookie"],
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)

authenticator.login()
if st.session_state["authentication_status"]:
    # 職種コンポーネントが正しく初期化されるように、ログイン成功したら一度リロードを挟む
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.session_state["logged_in"] = True
        st.rerun()
    # ログイン後に別ファイルを描画
    search.show_search_console()
elif st.session_state["authentication_status"] is False:
    st.error("ユーザー名またはパスワードが間違っています")
elif st.session_state["authentication_status"] is None:
    st.warning("ユーザー名とパスワードを入力してください")