# -*- coding: utf-8 -*-
"""普查：哪些会话的距离剖面上同时存在近距人体峰与 bin146 杂散峰（只读，不写数据）"""
import numpy as np, glob, os, re
from scipy import signal

CAND = [
 "D:/Project/厚粲杯/11_数据/sub-adc-test/ses-0812/mmwave",
 "D:/Project/厚粲杯/11_数据/sub-1d-test/ses-0812/mmwave",
 "D:/Project/厚粲杯/11_数据/sub-adc-test2/ses-0812/mmwave",
 "D:/Project/厚粲杯/11_数据/sub-deep-breath",
 "D:/Project/厚粲杯/11_数据/sub-rest_3min_",
 "D:/Project/厚粲杯/11_数据/radar_collector/data_v1",
 "D:/Project/厚粲杯/11_数据/radar_collector/data_v2",
 "D:/Project/厚粲杯/11_数据/radar_collector/data_v3",
 "D:/Project/厚粲杯/11_数据/calib_data",
 "J:/Data/sub-056_/mmwave",
 "J:/Data/sub-075_/mmwave",
 "J:/Data/sub-090_/mmwave",
]
BIN_M = 0.037

def txkeys(z): return sorted([k for k in z.files if re.match(r"^tx\d+_rx\d+$", k)])

for d in CAND:
    if not os.path.isdir(d):
        print(f"[skip] {d}  (目录不存在)"); continue
    fs = sorted(glob.glob(os.path.join(d, "*datacube*.npz")))
    if not fs:
        # 递归一层
        fs = sorted(glob.glob(os.path.join(d, "**", "*datacube*.npz"), recursive=True))
    if not fs:
        print(f"[skip] {d}  (无 datacube npz)"); continue
    try:
        z = np.load(fs[0])
        ks = txkeys(z)
        if not ks:
            print(f"[skip] {d}  (无 tx*_rx* 键, keys={z.files[:6]})"); continue
        a = np.asarray(z[ks[0]], dtype=np.complex64)
        n, nb = a.shape[0], a.shape[1]
        cube = np.stack([np.asarray(z[k])[:min(n,400)] for k in ks], axis=-1).astype(np.complex64)
        prof = (np.abs(cube)**2).mean(axis=(0,2))   # 帧维+通道维均值
        rng = prof.max()-prof.min()
        pk,_ = signal.find_peaks(prof, prominence=0.005*rng)
        order = np.argsort(prof[pk])[::-1][:8]
        tops = [(int(pk[i]), float(prof[pk[i]])) for i in order]
        # bin146 附近
        w = prof[131:162]
        b146 = int(131+int(np.argmax(w)))
        print(f"[ ok ] {d}")
        print(f"       files={len(fs)}  shape=({n},{nb})  n_ch={len(ks)}  首文件大小={os.path.getsize(fs[0])/1e6:.1f}MB")
        print(f"       top8 峰: " + ", ".join(f"bin{b}({b*BIN_M:.2f}m,{p:.4g})" for b,p in tops))
        print(f"       bin146 窗口[131..161] 局部峰 bin{b146} power={prof[b146]:.6g}  "
              f"倍率(相对全剖面中位数)={prof[b146]/np.median(prof):.1f}x")
        print(f"       近距窗[1..60] 峰 bin{int(1+np.argmax(prof[1:61]))} power={prof[1:61].max():.6g}  "
              f"倍率={prof[1:61].max()/np.median(prof):.1f}x")
    except Exception as e:
        print(f"[err ] {d}: {type(e).__name__}: {e}")
    print("-"*76)
