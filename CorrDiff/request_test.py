import requests
import time

# 1. 提交任務 (POST)
# 重點：你必須把回應存起來，因為「號碼牌」藏在 Header 裡面！
response = requests.post(invoke_url, json=payload, headers=headers)

# 2. 領取號碼牌 (ID)
# NVIDIA 的系統通常把號碼牌放在這個 key：'nvcf-reqid'
request_id = response.headers.get("nvcf-reqid")
print(f"成功提交！任務 ID: {request_id}")

# 3. 查詢任務狀態 (GET)
# 重點：查詢的網址通常跟提交的網址「不一樣」！
# 提交是發給模型，查詢是發給「狀態中心 (Status API)」
status_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{request_id}"

for i in range(10):
    time.sleep(10)
    
    # 這裡的 GET 不需要帶 payload 了（因為資料已經在雲端算了）
    # 只需要帶 headers (裡面有你的 API Key)
    status_response = requests.get(status_url, headers=headers)
    
    if status_response.status_code == 200:
        print(f"任務完成！結果已下載。")
        # 這裡處理 status_response.json()
        break
    elif status_response.status_code == 202:
        print(f"第 {i+1} 次查詢：運算中，請稍候...")
    else:
        print(f"查詢失敗，狀態碼：{status_response.status_code}")
        break