{
  "nbformat": 4,
  "nbformat_minor": 5,
  "metadata": {
    "kernelspec": {
      "name": "python3",
      "display_name": "Python 3"
    },
    "language_info": {
      "name": "python"
    }
  },
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "# CorrDiff Pipeline 範例\n",
        "這個 Notebook 示範如何使用專案內的 `CorrDiff/pipeline.py` 執行一個完整的推論 Pipeline（目前以插值模擬下尺度），並繪製放大前後的對比圖以供簡報展示。\n",
        "\n",
        "說明：\n",
        "- 輸入：`corrdiff_output.nc`（粗解析度）\n",
        "- 放大：插值（cubic）模擬 CorrDiff 行為（可替換為實體模型）\n",
        "- 輸出：`corrdiff_pipeline_out.nc`（高解析度 NetCDF4）\n",
        "- 評估：MAE / RMSE 指標計算\n"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 0) 環境初始化"
      ]
    },
    {
      "cell_type": "code",
      "metadata": {},
      "source": [
        "# 在 Windows 上避免 HOME 相關錯誤\n",
        "import os\n",
        "os.environ['HOME'] = os.environ.get('USERPROFILE', '')\n",
        "\n",
        "# 常用套件與 pipeline 模組\n",
        "import xarray as xr\n",
        "import numpy as np\n",
        "import pandas as pd\n",
        "import matplotlib.pyplot as plt\n",
        "from pathlib import Path\n",
        "import CorrDiff.pipeline as pipeline\n",
        "\n",
        "# 顯示圖表內嵌於 notebook\n",
        "%matplotlib inline\n",
        "\n",
        "print('✅ 環境初始化完成')"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 1) 執行 Pipeline（會在工作資料夾產生輸出檔案）\n",
        "你可以修改 `sr_factor` 或 `--weights` 參數（權重為保留介面，目前為 placeholder）。"
      ]
    },
    {
      "cell_type": "code",
      "metadata": {},
      "source": [
        "# pipeline 執行範例（若已執行過可跳過這格）\n",
        "input_path = 'corrdiff_output.nc'\n",
        "output_path = 'corrdiff_pipeline_out.nc'\n",
        "sr_factor = 2\n",
        "\n",
        "# 若要指定本地模型權重或 package 路徑，可填 weights 參數\n",
        "weights = None  # e.g. 'path/to/corrdiff_package'\n",
        "\n",
        "# 呼叫 pipeline.run_pipeline：會產生輸出 NetCDF 檔案\n",
        "pipeline.run_pipeline(input_path, output_path, sr_factor=sr_factor, weights=weights)"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 2) 載入放大前 / 放大後資料並繪圖對比\n",
        "以下會載入原始檔（可能有或沒有 time 維度）以及 pipeline 產出的高解析度檔，計算評估指標，並繪製風速等高線與風向箭頭的比較圖。"
      ]
    },
    {
      "cell_type": "code",
      "metadata": {},
      "source": [
        "# 讀取資料集\n",
        "ds_orig = xr.open_dataset(input_path)\n",
        "ds_up = xr.open_dataset(output_path)\n",
        "\n",
        "# 處理可能的 time 維度（若有就取第一個時間點）\n",
        "def _get_uv(ds):\n",
        "    if 'u10' not in ds or 'v10' not in ds:\n",
        "        raise ValueError('Dataset 必須包含 u10 與 v10 變數')\n",
        "    if ds['u10'].ndim == 3:\n",
        "        u = ds['u10'][0].values\n",
        "        v = ds['v10'][0].values\n",
        "    else:\n",
        "        u = ds['u10'].values\n",
        "        v = ds['v10'].values\n",
        "    return u, v\n",
        "\n",
        "u0, v0 = _get_uv(ds_orig)\n",
        "u1, v1 = _get_uv(ds_up)\n",
        "\n",
        "# 取得經緯度座標\n",
        "lat0 = ds_orig['latitude'].values\n",
        "lon0 = ds_orig['longitude'].values\n",
        "lat1 = ds_up['latitude'].values\n",
        "lon1 = ds_up['longitude'].values\n",
        "\n",
        "# 計算風速\n",
        "ws0 = np.sqrt(u0**2 + v0**2)\n",
        "ws1 = np.sqrt(u1**2 + v1**2)\n",
        "\n",
        "print(f'原始資料形狀: {u0.shape}')\n",
        "print(f'放大後資料形狀: {u1.shape}')"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 3) 計算評估指標 (MAE / RMSE)\n",
        "透過插值原始資料到高解析度網格，計算與放大結果的差異。"
      ]
    },
    {
      "cell_type": "code",
      "metadata": {},
      "source": [
        "from scipy.interpolate import griddata\n",
        "\n",
        "# 將原始低解析度資料插值到高解析度網格\n",
        "lat_grid0, lon_grid0 = np.meshgrid(lat0, lon0, indexing='ij')\n",
        "lat_grid1, lon_grid1 = np.meshgrid(lat1, lon1, indexing='ij')\n",
        "\n",
        "points = np.column_stack([lat_grid0.ravel(), lon_grid0.ravel()])\n",
        "\n",
        "# 線性插值原始 u10, v10, ws 到高解析度網格（作為 Ground Truth）\n",
        "u0_interp = griddata(points, u0.ravel(), (lat_grid1, lon_grid1), method='linear')\n",
        "v0_interp = griddata(points, v0.ravel(), (lat_grid1, lon_grid1), method='linear')\n",
        "ws0_interp = np.sqrt(u0_interp**2 + v0_interp**2)\n",
        "\n",
        "# 計算誤差（只在有效的格點上計算）\n",
        "valid_mask = ~np.isnan(u0_interp) & ~np.isnan(u1)\n",
        "\n",
        "u_mae = np.mean(np.abs(u1[valid_mask] - u0_interp[valid_mask]))\n",
        "v_mae = np.mean(np.abs(v1[valid_mask] - v0_interp[valid_mask]))\n",
        "ws_mae = np.mean(np.abs(ws1[valid_mask] - ws0_interp[valid_mask]))\n",
        "\n",
        "u_rmse = np.sqrt(np.mean((u1[valid_mask] - u0_interp[valid_mask])**2))\n",
        "v_rmse = np.sqrt(np.mean((v1[valid_mask] - v0_interp[valid_mask])**2))\n",
        "ws_rmse = np.sqrt(np.mean((ws1[valid_mask] - ws0_interp[valid_mask])**2))\n",
        "\n",
        "# 建立評估指標 DataFrame\n",
        "evaluation_data = {\n",
        "    '變數': ['U10 (東西風)', 'V10 (南北風)', '風速 (WS)'],\n",
        "    'MAE (m/s)': [f'{u_mae:.4f}', f'{v_mae:.4f}', f'{ws_mae:.4f}'],\n",
        "    'RMSE (m/s)': [f'{u_rmse:.4f}', f'{v_rmse:.4f}', f'{ws_rmse:.4f}']\n",
        "}\n",
        "\n",
        "df_eval = pd.DataFrame(evaluation_data)\n",
        "\n",
        "print('\\n' + '='*60)\n",
        "print('📊 評估指標 (與內插 Ground Truth 比較)')\n",
        "print('='*60)\n",
        "print(df_eval.to_string(index=False))\n",
        "print('='*60)\n",
        "print(f'有效格點數: {np.sum(valid_mask)} / {u1.size}')\n",
        "print('='*60)"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 4) 繪製對比圖（含評估指標標籤）"
      ]
    },
    {
      "cell_type": "code",
      "metadata": {},
      "source": [
        "# 繪圖設定\n",
        "fig, axes = plt.subplots(1, 2, figsize=(16, 6), constrained_layout=True)\n",
        "fig.suptitle(f'風場放大對比圖 (sr_factor={sr_factor}x)', fontsize=16, fontweight='bold')\n",
        "\n",
        "# 原始分辨率圖\n",
        "ax = axes[0]\n",
        "cf = ax.contourf(lon0, lat0, ws0, levels=20, cmap='RdYlBu_r')\n",
        "ax.quiver(lon0, lat0, u0, v0, scale=200, width=0.003, alpha=0.7)\n",
        "ax.set_title(f'Original: {len(lat0)} × {len(lon0)} 格點', fontsize=12, fontweight='bold')\n",
        "ax.set_xlabel('Longitude (°E)', fontsize=11)\n",
        "ax.set_ylabel('Latitude (°N)', fontsize=11)\n",
        "cbar0 = plt.colorbar(cf, ax=ax, orientation='vertical')\n",
        "cbar0.set_label('Wind Speed (m/s)', fontsize=10)\n",
        "ax.grid(True, alpha=0.3, linestyle='--')\n",
        "\n",
        "# 放大後圖\n",
        "ax = axes[1]\n",
        "skip = max(1, int(len(lat1)/15))\n",
        "cf = ax.contourf(lon1, lat1, ws1, levels=20, cmap='RdYlBu_r')\n",
        "ax.quiver(lon1[::skip], lat1[::skip], u1[::skip, ::skip], v1[::skip, ::skip], \n",
        "          scale=200, width=0.003, alpha=0.7)\n",
        "ax.set_title(f'Upscaled: {len(lat1)} × {len(lon1)} 格點', fontsize=12, fontweight='bold')\n",
        "ax.set_xlabel('Longitude (°E)', fontsize=11)\n",
        "ax.set_ylabel('Latitude (°N)', fontsize=11)\n",
        "cbar1 = plt.colorbar(cf, ax=ax, orientation='vertical')\n",
        "cbar1.set_label('Wind Speed (m/s)', fontsize=10)\n",
        "ax.grid(True, alpha=0.3, linestyle='--')\n",
        "\n",
        "# 在右圖角落添加評估指標文字框\n",
        "textstr = f'評估指標 (vs 內插基準)\\n'\\\n",
        "          f'U MAE: {u_mae:.4f} m/s\\n'\\\n",
        "          f'V MAE: {v_mae:.4f} m/s\\n'\\\n",
        "          f'WS MAE: {ws_mae:.4f} m/s\\n'\\\n",
        "          f'---\\n'\\\n",
        "          f'U RMSE: {u_rmse:.4f} m/s\\n'\\\n",
        "          f'V RMSE: {v_rmse:.4f} m/s\\n'\\\n",
        "          f'WS RMSE: {ws_rmse:.4f} m/s'\n",
        "\n",
        "props = dict(boxstyle='round', facecolor='wheat', alpha=0.85)\n",
        "ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,\n",
        "        verticalalignment='top', bbox=props, family='monospace')\n",
        "\n",
        "# 儲存比較圖供簡報使用\n",
        "out_fig = 'pipeline_comparison_with_metrics.png'\n",
        "fig.savefig(out_fig, dpi=150, bbox_inches='tight')\n",
        "print(f'✅ 已儲存對比圖: {out_fig}')\n",
        "plt.show()"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 5) 誤差分佈視覺化\n",
        "可視化風速誤差的空間分佈。"
      ]
    },
    {
      "cell_type": "code",
      "metadata": {},
      "source": [
        "# 計算風速誤差\n",
        "ws_error = ws1 - ws0_interp\n",
        "\n",
        "fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)\n",
        "fig.suptitle('風速誤差分析', fontsize=14, fontweight='bold')\n",
        "\n",
        "# 誤差分佈圖\n",
        "ax = axes[0]\n",
        "cf = ax.contourf(lon1, lat1, ws_error, levels=20, cmap='RdBu_r', \n",
        "                  vmin=-np.abs(ws_error).max(), vmax=np.abs(ws_error).max())\n",
        "ax.set_title('風速誤差 (Upscaled - Ground Truth)', fontsize=12)\n",
        "ax.set_xlabel('Longitude (°E)')\n",
        "ax.set_ylabel('Latitude (°N)')\n",
        "cbar = plt.colorbar(cf, ax=ax, label='Error (m/s)')\n",
        "ax.grid(True, alpha=0.3, linestyle='--')\n",
        "\n",
        "# 誤差直方圖\n",
        "ax = axes[1]\n",
        "error_flat = ws_error[valid_mask].flatten()\n",
        "ax.hist(error_flat, bins=30, edgecolor='black', alpha=0.7, color='skyblue')\n",
        "ax.axvline(0, color='red', linestyle='--', linewidth=2, label='Zero Error')\n",
        "ax.axvline(np.mean(error_flat), color='green', linestyle='--', linewidth=2, label=f'Mean: {np.mean(error_flat):.4f}')\n",
        "ax.set_xlabel('Wind Speed Error (m/s)')\n",
        "ax.set_ylabel('Frequency')\n",
        "ax.set_title('誤差分佈直方圖')\n",
        "ax.legend()\n",
        "ax.grid(True, alpha=0.3, axis='y')\n",
        "\n",
        "fig.savefig('pipeline_error_analysis.png', dpi=150, bbox_inches='tight')\n",
        "print(f'✅ 已儲存誤差分析圖: pipeline_error_analysis.png')\n",
        "plt.show()"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 6) 權重替換介面說明（給未來 CorrDiff 實體模型）\n",
        "- 在 `CorrDiff/pipeline.py` 中，`ModelWrapper.load_weights(path)` 是未來接入模型的入口。\n",
        "- 當你有 CorrDiff 的 package 或 checkpoint，可以在 `load_weights` 實作：\n",
        "  ```python\n",
        "  from earth2studio.models.auto.package import Package\n",
        "  from earth2studio.models.dx import CorrDiff\n",
        "  pkg = Package(path_to_package_root)\n",
        "  model = CorrDiff.load_model(pkg, device='cuda:0')\n",
        "  self._model = model\n",
        "  ```\n",
        "- `ModelWrapper.predict()` 目前會呼叫插值函式；未來可改為呼叫 `self._model(...)` 並轉換輸入/輸出格式。"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "---\n",
        "## ✅ 完成\n",
        "你現在可以在報告中直接展示：\n",
        "1. **pipeline_comparison_with_metrics.png** — 放大前後對比圖 + 評估指標框\n",
        "2. **pipeline_error_analysis.png** — 誤差分佈與直方圖\n",
        "3. **df_eval DataFrame** — MAE/RMSE 詳細表格\n",
        "\n",
        "打開本 Notebook 並從上至下執行每個 cell 即可重現完整流程與成果。"
      ]
    }
  ]
}