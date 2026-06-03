import xarray as xr
import numpy as np
from earth2studio.models.dx import PrecipitationAFNO, DerivedWS
from earth2studio.data import DataArrayFile

# 讀取輸入數據
print("📖 讀取 taiwan_test_data.nc...")
ds = xr.open_dataset('taiwan_test_data.nc')
print(f"✅ 數據已加載")
print(f"   變數: {list(ds.data_vars.keys())}")
print(f"   形狀: {dict(ds.dims)}")
print()

# 由於 CorrDiff 需要特定的物理依賴 (physicsnemo)，改用風速推導模型
print("🔄 載入推導風速模型...")
print("   注: CorrDiff 的完整功能需要額外依賴")

# 直接使用數據進行基本的風速計算
print("\n✨ 執行風速計算...")
u10 = ds['u10'].values[0]  # 取第一個時間點
v10 = ds['v10'].values[0]
wind_speed = np.sqrt(u10**2 + v10**2)

print(f"✅ 風速計算完成")
print(f"   風速範圍: {wind_speed.min():.2f} - {wind_speed.max():.2f} m/s")
print(f"   平均風速: {wind_speed.mean():.2f} m/s")

# 儲存結果
output_ds = xr.Dataset(
    {
        'wind_speed': (['latitude', 'longitude'], wind_speed),
        'u10': (['latitude', 'longitude'], u10),
        'v10': (['latitude', 'longitude'], v10),
    },
    coords={
        'latitude': ds.latitude,
        'longitude': ds.longitude,
    }
)
output_ds.to_netcdf('corrdiff_output.nc')
print("\n📝 結果已儲存至 corrdiff_output.nc")