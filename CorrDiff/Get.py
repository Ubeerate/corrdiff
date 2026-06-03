import cdsapi
import xarray as xr

c = cdsapi.Client()

# 定義抓取的範圍 (台灣周邊)
# North, West, South, East
area = [26, 119, 21, 123] 

def fetch_era5_sample():
    print("🚀 開始從 CDS 下載 ERA5 數據...")
    c.retrieve(
        'reanalysis-era5-single-levels',
        {
            'product_type': 'reanalysis',
            'format': 'netcdf', # CorrDiff 喜歡的格式
            'variable': [
                '10m_u_component_of_wind', 
                '10m_v_component_of_wind',
                '2m_temperature', 
                'surface_pressure'
            ],
            'year': '2024',
            'month': '07', # 我們抓 2024 年 7 月（凱米颱風期間）
            'day': '24',
            'time': '12:00',
            'area': area,
        },
        'taiwan_test_data.nc' # 儲存檔名
    )
    print("✅ 下載完成！檔案已存為 taiwan_test_data.nc")

def verify_data():
    # 使用 xarray 檢查下載的內容
    ds = xr.open_dataset('taiwan_test_data.nc')
    print("\n--- 數據內容檢查 ---")
    print(ds)
    # 畫個簡單的圖確認沒抓錯地方
    ds.t2m.plot() 
    print("📊 已產生簡易溫度圖，請確認範圍是否為台灣。")

if __name__ == "__main__":
    fetch_era5_sample()
    verify_data()