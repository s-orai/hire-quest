import pandas as pd
import json

# サンプル JSON（不定で複数の配列・ネストがある）
# Load data from sample.json
with open('sample.json', 'r', encoding='utf-8') as f:
    json_data = json.load(f)

data = json_data['jobs']

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

# JSONリストをフラット化
flat_data = [flatten_json(d) for d in data]

# DataFrameに変換
df = pd.DataFrame(flat_data)

# CSVに出力
df.to_csv("output.csv", index=False, encoding="utf-8")

print("不定の配列を含む JSON を CSV に出力しました")