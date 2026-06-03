# CorrDiff 集成示例（需要 physicsnemo）

import torch
import xarray as xr
from earth2studio.models.dx import CorrDiff

def super_resolve_with_corrdiff(ds, sr_factor=2):
    """
    使用真正的 CorrDiff 模型進行超分辨率
    (需要: pip install earth2studio[corrdiff])
    """
    
    try:
        # 1. 載入 CorrDiff 模型
        print("🔄 載入 CorrDiff 模型...")
        model = CorrDiff.load_model()
        model.eval()  # 設定為推論模式
        
        # 2. 準備輸入數據
        u10 = torch.from_numpy(ds.u10[0].values).float()
        v10 = torch.from_numpy(ds.v10[0].values).float()
        
        # 打包為 xarray Dataset (CorrDiff 期望的格式)
        input_data = xr.Dataset({
            'u10': (['latitude', 'longitude'], u10.numpy()),
            'v10': (['latitude', 'longitude'], v10.numpy()),
        })
        
        # 3. 執行推論
        print("🚀 執行 CorrDiff 推論...")
        with torch.no_grad():
            output = model(input_data)
        
        print("✅ CorrDiff 超分辨率完成！")
        return output
        
    except ImportError as e:
        print(f"❌ CorrDiff 依賴不可用: {e}")
        print("💡 請安裝: pip install earth2studio[corrdiff]")
        return None


# ============ CorrDiff vs 插值方法的對比 ============

comparison = """
┌─────────────────────────────────────────────────────────────┐
│           CorrDiff (機器學習)  vs  插值 (數學)               │
├─────────────────────────────────────────────────────────────┤
│ 特性              │    CorrDiff      │     三次樣條插值      │
├─────────────────────────────────────────────────────────────┤
│ 方法              │ 迴歸 + 擴散      │     平滑插值          │
│ 物理約束          │ ✅ 有            │ ❌ 無                 │
│ 學習能力          │ ✅ 有            │ ❌ 無                 │
│ 細節保留          │ ✅ 高保真        │ ⚠️  可能產生假象      │
│ 計算速度          │ ❌ 慢 (秒級)     │ ✅ 快 (毫秒級)        │
│ 依賴複雜度        │ ✅ 高 (需GPU)    │ ✅ 低 (純numpy)       │
│ 完全性            │ ✅ 多樣本支持    │ ⚠️  單一確定結果      │
│ 適用場景          │ 研究/高精度      │ 視覺化/快速預覽      │
└─────────────────────────────────────────────────────────────┘

CorrDiff 工作流程:
  低分辨率數據 → 迴歸模型 → 初步高分辨率
                    ↓
              擴散去噪步驟 (8-18步)
                    ↓
              生成高保真結果 (可多樣本)

插值工作流程:
  低分辨率數據 → 網格擴展 → 三次樣條插值 → 高分辨率數據
"""

print(comparison)
