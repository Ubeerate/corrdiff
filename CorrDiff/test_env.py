try:
    import earth2studio
    import torch
    import numpy as np
    
    print("✅ Earth2Studio 版本:", earth2studio.__version__)
    print("✅ PyTorch 版本:", torch.__version__)
    print("✅ Numpy 版本:", np.__version__)
    
    # 檢查是否有抓到 GPU (雖然你在 Mac 安裝，但未來在 3060 上這行很重要)
    print("🚀 是否可用 GPU (CUDA):", torch.cuda.is_available())
    print("🚀 是否可用 Apple Silicon (MPS):", torch.backends.mps.is_available())
    
    print("\n🎉 環境測試完全成功！你可以開始寫 CorrDiff 的實作了。")

except ImportError as e:
    print(f"❌ 模組載入失敗: {e}")