簡短使用說明 — CorrDiff super-resolution 風場輸出

這個專案包含一支安全的風場超解析與輸出腳本 `CorrDiff/super_resolution_wind.py`。
README 提供從 0 開始在 Windows + conda 上重現輸出的最短流程（包含避開 Cartopy 在某些 Windows 環境導致的崩潰）。

快速要點
- 建議用 `conda` 建環（使用 conda-forge）以得到穩定的 Cartopy/依賴。
- 預設輸出採用 Matplotlib colormap -> PIL 合成（不走 Matplotlib 畫圖路徑），在有些 Windows 環境更穩定。
- 若要在影像上加海岸線，使用 `--coastline-overlay`（安全；shapereader 只讀 geometry，使用 PIL 畫線）。

1) 建立 conda 環境（建議）
```powershell
conda create -n corrdiff-cartopy -c conda-forge python=3.13 -y
conda activate corrdiff-cartopy
```

2) 安裝必要套件
```powershell
conda install -c conda-forge xarray numpy scipy matplotlib pillow cartopy -y
# 或若不使用 cartopy：
pip install xarray numpy scipy matplotlib pillow
```

3) 取得專案（如果還沒）
```powershell
git clone https://github.com/Ubeerate/corrdiff.git
cd corrdiff\corrdiff-main
```

4) 執行（安全：PIL-based 輸出）
```powershell
python CorrDiff\super_resolution_wind.py --sr-factor 2 --input CorrDiff\corrdiff_output.nc --compare --out-dir CorrDiff\outputs
```

5) 執行並加海岸線（安全覆蓋）
```powershell
python CorrDiff\super_resolution_wind.py --sr-factor 2 --input CorrDiff\corrdiff_output.nc --compare --out-dir CorrDiff\outputs --coastline-overlay
```
說明：第一次執行時，Cartopy 的 shapereader 會自動下載 Natural Earth coastline data（需網路）。

6) （風險較高：直接用 Cartopy 繪圖）
```powershell
python CorrDiff\super_resolution_wind.py --sr-factor 2 --input CorrDiff\corrdiff_output.nc --compare --out-dir CorrDiff\outputs --use-cartopy
```
警告：在某些 Windows 環境這個選項會觸發 Matplotlib/Cartopy 的 C-level fatal exception（0xc06d007f），會直接終止 Python process。若你不確定環境穩定，請不要使用。

7) 查看輸出
```powershell
dir CorrDiff\outputs
start "" CorrDiff\outputs\wind_detail_sr2x.png
```

8) Commit & push（如需加入 repo）
```powershell
git add CorrDiff/super_resolution_wind.py CorrDiff/outputs/*.png README.md
git commit -m "Add README with run instructions and generated outputs"
git push
```

常見問題（短）
- 如果 `--use-cartopy` 崩潰：改用 `--coastline-overlay`。後者會用 shapereader 讀 geometry，並以 PIL 在像素座標上畫線，不走 Matplotlib 繪圖流程。
- shapereader 無法下載：確認有網路或改用手動下載 Natural Earth coastlines。
- OneDrive 同步影響檔案可見性：用 PowerShell 的 `dir` 或 `Get-ChildItem` 確認檔案存在。

短版 meeting 口白（可背稿）
"我在 conda 環境裡執行 `CorrDiff/super_resolution_wind.py`，預設用 PIL 合成輸出到 `CorrDiff/outputs`。要顯示海岸線只加 `--coastline-overlay`；不建議用 `--use-cartopy`，因為在某些 Windows 配置會造成崩潰。我已經把 README 放在專案根目錄，裡面有快速指令可直接複製貼上執行。"

如果你要我直接幫你 commit & push `README.md`，或把 README 放在 `CorrDiff/README.md`（子目錄），告訴我你的偏好。
