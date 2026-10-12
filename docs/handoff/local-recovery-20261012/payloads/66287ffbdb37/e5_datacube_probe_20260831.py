# -*- coding: utf-8 -*-
import numpy as np, glob, os
from pathlib import Path

roots = [
 ("sub-adc-test/ses-0812", r"D:/Project/厚粲杯/11_数据/sub-adc-test/ses-0812/mmwave", "sub-adc-test_ses-0812_mmwave_datacube*.npz"),
 ("sub-1d-test/ses-0812",  r"D:/Project/厚粲杯/11_数据/sub-1d-test/ses-0812/mmwave",  "sub-1d-test_ses-0812_mmwave_datacube*.npz"),
 ("sub-adc-test2/ses-0812",r"D:/Project/厚粲杯/11_数据/sub-adc-test2/ses-0812/mmwave","sub-adc-test2_ses-0812_mmwave_datacube*.npz"),
]
for name, d, pat in roots:
    fs = sorted(glob.glob(os.path.join(d, pat)))
    print("="*70)
    print(name, "files=", len(fs))
    if not fs: continue
    z = np.load(fs[0])
    print("  keys:", z.files[:20], "..." if len(z.files)>20 else "")
    txkeys = sorted([k for k in z.files if k.startswith("tx")])
    print("  tx keys:", txkeys)
    a0 = np.asarray(z[txkeys[0]])
    print("  tx0 shape:", a0.shape, a0.dtype)
    # metadata?
    for k in z.files:
        if not k.startswith("tx"):
            v = z[k]
            try:
                vv = v.item() if getattr(v,'shape',None)==() else v
                print("  meta", k, "=", str(vv)[:300])
            except Exception as e:
                print("  meta", k, "err", e)
    break
