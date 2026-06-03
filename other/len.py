import base64

# 把你的那串亂碼放進去
s = "cGljb0NURntwdXp6bDNkX20zdGFkYXRhX2YwdW5kIV9mOT"

# 自動補足缺失的等號 (Padding)
missing_padding = len(s) % 4
if missing_padding:
    s += '=' * (4 - missing_padding)

try:
    decoded = base64.b64decode(s).decode('utf-8')
    print(f"解碼結果: {decoded}")
except Exception as e:
    print(f"解碼失敗: {e}")