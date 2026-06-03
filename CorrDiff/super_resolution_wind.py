import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.interpolate import griddata
import argparse

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Heiti TC', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ==================== 超分辨率與風場視覺化 ====================

class SuperResolutionWind:
    """控制分辨率參數與風場細節的超分辨率風速預報"""
    
    def __init__(self, input_file='taiwan_test_data.nc', sr_factor=2):
        """
        初始化超分辨率風場處理器
        
        Parameters
        ----------
        input_file : str
            輸入的 NetCDF 檔案
        sr_factor : int
            超分辨率倍數 (1, 2, 3, 4)
        """
        self.sr_factor = sr_factor
        self.input_file = input_file
        self.ds = None
        self.sr_ds = None
        self.load_data()
    
    def load_data(self):
        """載入原始氣象數據"""
        print(f"📖 讀取 {self.input_file}...")
        self.ds = xr.open_dataset(self.input_file)

        if self.ds['u10'].ndim == 3:
            self.has_time = True
            time_dim = self.ds['u10'].dims[0]
            print(f"✅ 原始分辨率：{len(self.ds.latitude)} × {len(self.ds.longitude)} (時間維度: {time_dim}={len(self.ds[time_dim])})")
        else:
            self.has_time = False
            print(f"✅ 原始分辨率：{len(self.ds.latitude)} × {len(self.ds.longitude)}")
    
    def super_resolve(self):
        """
        執行空間超分辨率插值
        (模擬 CorrDiff 的超分辨率功能)
        """
        print(f"\n🔄 執行 {self.sr_factor}x 超分辨率處理...")
        
        # 原始網格
        lat = self.ds.latitude.values
        lon = self.ds.longitude.values
        if self.ds['u10'].ndim == 3:
            u10 = self.ds.u10[0].values  # 取第一個時間點
            v10 = self.ds.v10[0].values
        else:
            u10 = self.ds.u10.values
            v10 = self.ds.v10.values
        
        # 建立高分辨率網格
        sr_lat = np.linspace(lat.min(), lat.max(), len(lat) * self.sr_factor - (self.sr_factor - 1))
        sr_lon = np.linspace(lon.min(), lon.max(), len(lon) * self.sr_factor - (self.sr_factor - 1))
        sr_lat_grid, sr_lon_grid = np.meshgrid(sr_lat, sr_lon, indexing='ij')
        
        # 原始網格
        lat_grid, lon_grid = np.meshgrid(lat, lon, indexing='ij')
        
        # 插值 (三次樣條插值)
        points = np.column_stack([lat_grid.ravel(), lon_grid.ravel()])
        u10_sr = griddata(points, u10.ravel(), 
                         (sr_lat_grid, sr_lon_grid), method='cubic')
        v10_sr = griddata(points, v10.ravel(), 
                         (sr_lat_grid, sr_lon_grid), method='cubic')
        
        # 建立高分辨率 Dataset
        self.sr_ds = xr.Dataset(
            {
                'u10': (['latitude', 'longitude'], u10_sr),
                'v10': (['latitude', 'longitude'], v10_sr),
            },
            coords={
                'latitude': sr_lat,
                'longitude': sr_lon,
            }
        )
        
        print(f"✅ 新分辨率：{len(sr_lat)} × {len(sr_lon)}")
        return self.sr_ds
    
    def get_wind_speed_and_direction(self, ds=None):
        """計算風速和風向"""
        if ds is None:
            ds = self.sr_ds if self.sr_ds is not None else self.ds
        
        u10 = ds['u10'].values
        v10 = ds['v10'].values
        
        wind_speed = np.sqrt(u10**2 + v10**2)
        # 風向: 從北方順時針 (0-360)
        wind_direction = np.degrees(np.arctan2(u10, v10)) % 360
        
        return wind_speed, wind_direction, u10, v10
    
    def plot_wind_detail(self, output_file='wind_detail_sr.png'):
        """
        繪製風場細節圖
        包含: 風速、風向箭頭、等高線
        """
        if self.sr_ds is None:
            print("⚠️  請先執行 super_resolve()")
            return
        
        wind_speed, wind_direction, u10, v10 = self.get_wind_speed_and_direction()
        
        # 建立圖表
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'台灣風場分析 (分辨率: {self.sr_factor}x 超分辨率)', 
                     fontsize=16, fontweight='bold')
        
        lat = self.sr_ds.latitude.values
        lon = self.sr_ds.longitude.values
        
        # ========== 子圖 1: 風速場 + 風向箭頭 ==========
        ax = axes[0, 0]
        
        # 繪製風速等高線
        cf = ax.contourf(lon, lat, wind_speed, levels=20, cmap='RdYlBu_r')
        contour = ax.contour(lon, lat, wind_speed, levels=10, colors='black', 
                            alpha=0.3, linewidths=0.5)
        ax.clabel(contour, inline=True, fontsize=8)
        
        # 添加風向箭頭 (稀疏顯示)
        skip = max(1, self.sr_factor)
        ax.quiver(lon[::skip], lat[::skip], u10[::skip, ::skip], v10[::skip, ::skip],
                 alpha=0.6, scale=200, width=0.003)
        
        cbar = plt.colorbar(cf, ax=ax)
        cbar.set_label('風速 (m/s)')
        ax.set_xlabel('經度 (°E)')
        ax.set_ylabel('緯度 (°N)')
        ax.set_title('風速場 + 風向向量')
        ax.grid(True, alpha=0.3)
        
        # ========== 子圖 2: U 風量 ==========
        ax = axes[0, 1]
        cf = ax.contourf(lon, lat, u10, levels=20, cmap='RdBu_r', 
                        vmin=-np.abs(u10).max(), vmax=np.abs(u10).max())
        contour = ax.contour(lon, lat, u10, levels=10, colors='black', 
                            alpha=0.3, linewidths=0.5)
        cbar = plt.colorbar(cf, ax=ax)
        cbar.set_label('U 風量 (m/s)')
        ax.set_xlabel('經度 (°E)')
        ax.set_ylabel('緯度 (°N)')
        ax.set_title('東西向風量 (U10)')
        ax.grid(True, alpha=0.3)
        
        # ========== 子圖 3: V 風量 ==========
        ax = axes[1, 0]
        cf = ax.contourf(lon, lat, v10, levels=20, cmap='RdBu_r',
                        vmin=-np.abs(v10).max(), vmax=np.abs(v10).max())
        contour = ax.contour(lon, lat, v10, levels=10, colors='black', 
                            alpha=0.3, linewidths=0.5)
        cbar = plt.colorbar(cf, ax=ax)
        cbar.set_label('V 風量 (m/s)')
        ax.set_xlabel('經度 (°E)')
        ax.set_ylabel('緯度 (°N)')
        ax.set_title('南北向風量 (V10)')
        ax.grid(True, alpha=0.3)
        
        # ========== 子圖 4: 風向 ==========
        ax = axes[1, 1]
        
        # 使用極坐標風向顏色
        cf = ax.contourf(lon, lat, wind_direction, levels=16, 
                        cmap=plt.cm.hsv, vmin=0, vmax=360)
        contour = ax.contour(lon, lat, wind_direction, levels=8, colors='black', 
                            alpha=0.3, linewidths=0.5)
        
        cbar = plt.colorbar(cf, ax=ax, ticks=[0, 45, 90, 135, 180, 225, 270, 315, 360])
        cbar.set_label('風向 (度) [N=0, E=90, S=180, W=270]')
        ax.set_xlabel('經度 (°E)')
        ax.set_ylabel('緯度 (°N)')
        ax.set_title('風向場')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"\n✅ 詳細風場圖已儲存: {output_file}")
        plt.close()
    
    def plot_comparison(self, output_file='wind_comparison.png'):
        """
        對比原始分辨率 vs 超分辨率
        """
        # 計算原始分辨率風速
        if self.ds['u10'].ndim == 3:
            u10_orig = self.ds['u10'][0].values
            v10_orig = self.ds['v10'][0].values
        else:
            u10_orig = self.ds['u10'].values
            v10_orig = self.ds['v10'].values
        wind_speed_orig = np.sqrt(u10_orig**2 + v10_orig**2)
        
        wind_speed_sr, _, u10_sr, v10_sr = self.get_wind_speed_and_direction()
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle('Resolution Comparison: Original vs Super-Resolution', 
                    fontsize=14, fontweight='bold')
        
        # 原始分辨率
        lat_orig = self.ds.latitude.values
        lon_orig = self.ds.longitude.values
        ax = axes[0]
        cf = ax.contourf(lon_orig, lat_orig, wind_speed_orig, levels=20, cmap='RdYlBu_r')
        ax.quiver(lon_orig, lat_orig, u10_orig, v10_orig, alpha=0.6, scale=200)
        plt.colorbar(cf, ax=ax, label='Wind Speed (m/s)')
        ax.set_title(f'Original: {len(lat_orig)} x {len(lon_orig)}')
        ax.set_xlabel('Longitude (°E)')
        ax.set_ylabel('Latitude (°N)')
        
        # 超分辨率
        lat_sr = self.sr_ds.latitude.values
        lon_sr = self.sr_ds.longitude.values
        ax = axes[1]
        skip = max(1, self.sr_factor)
        cf = ax.contourf(lon_sr, lat_sr, wind_speed_sr, levels=20, cmap='RdYlBu_r')
        ax.quiver(lon_sr[::skip], lat_sr[::skip], u10_sr[::skip, ::skip], 
                 v10_sr[::skip, ::skip], alpha=0.6, scale=200, width=0.003)
        plt.colorbar(cf, ax=ax, label='Wind Speed (m/s)')
        ax.set_title(f'Super-Resolution: {len(lat_sr)} x {len(lon_sr)} ({self.sr_factor}x)')
        ax.set_xlabel('Longitude (°E)')
        ax.set_ylabel('Latitude (°N)')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"✅ Comparison plot saved: {output_file}")
        plt.close()
        plt.close()
    
    def print_statistics(self):
        """輸出風場統計信息"""
        wind_speed, wind_direction, u10, v10 = self.get_wind_speed_and_direction()
        
        print("\n" + "="*60)
        print("📊 風場統計信息")
        print("="*60)
        print(f"分辨率倍數: {self.sr_factor}x")
        print(f"\n風速統計:")
        print(f"  最大值: {wind_speed.max():.2f} m/s")
        print(f"  最小值: {wind_speed.min():.2f} m/s")
        print(f"  平均值: {wind_speed.mean():.2f} m/s")
        print(f"  標準差: {wind_speed.std():.2f} m/s")
        
        print(f"\nU 風量統計:")
        print(f"  最大值: {u10.max():.2f} m/s")
        print(f"  最小值: {u10.min():.2f} m/s")
        print(f"  平均值: {u10.mean():.2f} m/s")
        
        print(f"\nV 風量統計:")
        print(f"  最大值: {v10.max():.2f} m/s")
        print(f"  最小值: {v10.min():.2f} m/s")
        print(f"  平均值: {v10.mean():.2f} m/s")
        print("="*60)


def main():
    """主程序"""
    parser = argparse.ArgumentParser(
        description='超分辨率風場分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python super_resolution_wind.py --sr-factor 2
  python super_resolution_wind.py --sr-factor 4 --compare
        """
    )
    parser.add_argument('--sr-factor', type=int, default=2,
                       choices=[1, 2, 3, 4],
                       help='超分辨率倍數 (預設: 2)')
    parser.add_argument('--compare', action='store_true',
                       help='顯示原始 vs 超分辨率對比圖')
    parser.add_argument('--input', type=str, default='taiwan_test_data.nc',
                       help='輸入檔案 (預設: taiwan_test_data.nc)')
    
    args = parser.parse_args()
    
    # 初始化
    sr = SuperResolutionWind(input_file=args.input, sr_factor=args.sr_factor)
    
    # 執行超分辨率
    sr.super_resolve()
    
    # 繪製詳細風場圖
    sr.plot_wind_detail(f'wind_detail_sr{args.sr_factor}x.png')
    
    # 對比圖
    if args.compare:
        sr.plot_comparison(f'wind_comparison_{args.sr_factor}x.png')
    
    # 統計信息
    sr.print_statistics()


if __name__ == '__main__':
    main()
