import streamlit_authenticator as stauth

# ログインユーザーのパスワードをハッシュ化するためのファイルです
passwords = "パスワードを入力!"

# パスワードをハッシュ化
hashed_passwords = stauth.Hasher().hash(passwords)
print(hashed_passwords)