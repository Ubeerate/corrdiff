# 超分辨率風場分析工具使用指南

## 功能簡介

`super_resolution_wind.py` 是一個支持可調控分辨率參數的風場超分辨率分析工具。

**主要功能：**
- 🔄 空間插值超分辨率 (1x~4x 倍數)
- 💨 詳細風場可視化
- 📊 風速、風向、U/V 風量多維度分析
- 🔍 原始 vs 超分辨率對比展示

---

## 快速開始

### 基本用法

```bash
# 2倍超分辨率
python CorrDiff/super_resolution_wind.py --sr-factor 2

# 4倍超分辨率 + 對比圖
python CorrDiff/super_resolution_wind.py --sr-factor 4 --compare

# 自訂輸入文件
python CorrDiff/super_resolution_wind.py --sr-factor 2 --input custom_data.nc
```

### 命令行參數

| 參數 | 說明 | 預設值 | 選項 |
|------|------|--------|------|
| `--sr-factor` | 超分辨率倍數 | 2 | 1, 2, 3, 4 |
| `--compare` | 顯示原始 vs SR 對比圖 | False | - |
| `--input` | 輸入 NetCDF 文件 | taiwan_test_data.nc | 文件路徑 |

---

## 輸出文件說明

### 1. 詳細風場圖 (`wind_detail_srNx.png`)

**包含 4 個子圖：**

#### 子圖 1: 風速場 + 風向向量
- **等高線**：風速分布 (m/s)
- **箭頭**：風向和大小
- **色系**：紅-黃-藍表示高-中-低風速

#### 子圖 2: U 風量 (東西向)
- **正值**：東風（向東）
- **負值**：西風（向西）
- 紅-藍表示西-東

#### 子圖 3: V 風量 (南北向)
- **正值**：南風（向北）
- **負值**：北風（向南）
- 紅-藍表示南-北

#### 子圖 4: 風向場
- **色環**：360° 風向
  - 0°: North (紅)
  - 90°: East (綠)
  - 180°: South (藍)
  - 270°: West (紫)

### 2. 對比圖 (`wind_comparison_Nx.png`)

**左圖：原始分辨率**
- 21 × 17 格點

**右圖：超分辨率**
- 41 × 33 格點 (2x) 或其他倍數
- 更細緻的風場結構

---

## 數據輸入要求

輸入 NetCDF 文件需要包含：

```
必需變數:
- u10: 10米東西向風速 (dimensions: time, latitude, longitude)
- v10: 10米南北向風速 (dimensions: time, latitude, longitude)

推薦變數:
- t2m: 2米溫度 (可選)
- sp: 海平面氣壓 (可選)

座標:
- latitude: 緯度
- longitude: 經度
- valid_time (or time): 時間戳
```

**支持格式：**
- ERA5 再分析數據 ✅
- GFS 預報數據 ✅
- MERRA-2 數據 ✅
- CDS API 下載的數據 ✅

---

## 使用案例

### 案例 1: 台灣 2024 年凱米颱風分析

```bash
# 下載 ERA5 數據 (2024-07-24)
python CorrDiff/Test_xarray.py

# 執行 2 倍超分辨率 + 對比
python CorrDiff/super_resolution_wind.py --sr-factor 2 --compare

# 生成文件:
# - wind_detail_sr2x.png      (詳細分析圖)
# - wind_comparison_2x.png     (對比圖)
```

### 案例 2: 高分辨率極端風場研究

```bash
# 4 倍超分辨率用於局地風速極值分析
python CorrDiff/super_resolution_wind.py --sr-factor 4

# 統計輸出:
# 風速最大值、最小值、平均值、標準差等信息
```

---

## 統計輸出說明

執行完成後會輸出風場統計信息：

```
============================================================
📊 風場統計信息
============================================================
分辨率倍數: 2x

風速統計:
  最大值: 24.52 m/s    <- 最強風速
  最小值: 0.57 m/s     <- 最弱風速
  平均值: 15.34 m/s    <- 平均風速
  標準差: 5.67 m/s     <- 風速變異性

U 風量統計:
  最大值: 19.03 m/s    <- 最強東風
  最小值: -19.64 m/s   <- 最強西風
  平均值: 3.61 m/s

V 風量統計:
  最大值: 23.01 m/s    <- 最強南風
  最小值: -18.96 m/s   <- 最強北風
  平均值: 1.56 m/s
```

### 解讀風場統計：
- **風速大:** 標準差高 → 地形/氣象影響強
- **U/V 正負差大:** 風向變化快速
- **平均風向:** 判斷主要氣流方向

---

## 高級應用

### 超分辨率倍數選擇

| 倍數 | 分辨率增長 | 使用場景 | 計算時間 |
|------|----------|---------|---------|
| 1x | 原始 (21×17) | 基準對比 | <1 秒 |
| 2x | 41×33 | **推薦一般用途** | ~2 秒 |
| 3x | 61×49 | 區域細節分析 | ~4 秒 |
| 4x | 81×65 | 極值點位置分析 | ~6 秒 |

### 插值方法選擇

目前使用 **三次樣條插值 (cubic spline)**：
- ✅ 光滑連續
- ✅ 保持物理意義
- ✅ 平衡精度與穩定性

未來可擴展：
- Kriging 地理統計
- 神經網絡超分辨率 (與 CorrDiff 集成)
- 物理約束插值

---

## 常見問題 (FAQ)

### Q1: 圖表顯示中文亂碼？
**A:** 腳本已配置中文字體支持。如仍有問題：
```python
# 手動設定字體
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
```

### Q2: 插值會改變數據物理意義嗎？
**A:** 少量改變。超分辨率適合視覺化和模式分析，不適合進行嚴格統計檢驗。建議：
- 統計分析：用原始分辨率
- 視覺化/基本分析：用超分辨率

### Q3: 如何集成真正的 CorrDiff 模型？
**A:** 需要安裝 `physicsnemo` 依賴：
```bash
# 從 NVIDIA 官網下載並安裝
# 然後修改 CorrDiff.py 的導入部分
from earth2studio.models.dx import CorrDiff
model = CorrDiff.load_model()
```

### Q4: 可以處理全球數據嗎？
**A:** 可以，但效率會降低。建議：
- 裁切感興趣區域
- 或使用 GPU 加速
- 或降低超分辨率倍數

---

## 性能優化建議

### 內存優化
```bash
# 處理超大文件時：先進行空間裁切
# (修改 super_resolution_wind.py 的 load_data 方法)
ds = xr.open_dataset(file).sel(
    latitude=slice(20, 27),
    longitude=slice(118, 124)
)
```

### 速度優化
```bash
# 降低超分辨率倍數
python super_resolution_wind.py --sr-factor 1  # 快速預覽
python super_resolution_wind.py --sr-factor 4  # 詳細分析
```

---

## 輸出文件位置

所有生成的文件保存在執行目錄：
```
/Users/tpf-wifi/Desktop/vscode/
├── wind_detail_sr2x.png        (2倍超分辨率詳細圖)
├── wind_detail_sr4x.png        (4倍超分辨率詳細圖)
├── wind_comparison_2x.png      (2倍對比圖)
├── wind_comparison_4x.png      (4倍對比圖)
└── ...
```

---

## 相關文件

| 文件 | 功能 |
|------|------|
| `Test_xarray.py` | ERA5 數據下載 |
| `plot_taiwan.py` | 基礎風場繪圖 |
| `CorrDiff.py` | 簡易誤差修正示例 |
| `super_resolution_wind.py` | **超分辨率分析工具** ← 本文件 |

---

## 引用與參考

風場超分辨率方程式：

**風速：** $WS = \sqrt{u^2 + v^2}$

**風向：** $\theta = \text{atan2}(u, v) \mod 360°$

相關論文：
- CorrDiff: https://arxiv.org/html/2309.15214v
- Earth2Studio: https://nvidia.github.io/earth2studio/

---

## 許可證 & 支持

本工具為 Taiwan Typhoon Research 項目的一部分。

有問題或建議，請提出 Issue。

**最後更新：2026年5月21日**
