import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# 1. 讀取你剛剛下載的檔案
ds = xr.open_dataset('taiwan_test_data.nc')

# 2. 建立地圖畫布
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

# 3. 畫出風速大小 (Wind Speed) - 選擇第一個時間點
wind_speed = (ds.u10[0]**2 + ds.v10[0]**2)**0.5
wind_speed.plot(ax=ax, transform=ccrs.PlateCarree(), cmap='Spectral_r', add_colorbar=True)

# 4. 畫出風向箭頭 (Quiver)
# 每隔 2 個點畫一個箭頭，不然會太擠
skip = (slice(None, None, 2), slice(None, None, 2))
ax.quiver(ds.longitude[skip[1]].values, ds.latitude[skip[0]].values, 
          ds.u10[0][skip].values, ds.v10[0][skip].values, 
          transform=ccrs.PlateCarree())

# 5. 設定地圖範圍（台灣周邊）
ax.set_xlim(119, 123)
ax.set_ylim(21, 26)
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')

plt.title("ERA5 Ground Truth: Wind Field (2024-07-24 12:00)")
plt.savefig('wind_field_taiwan.png', dpi=100, bbox_inches='tight')
print("✅ 圖表已儲存為 wind_field_taiwan.png")
plt.close()