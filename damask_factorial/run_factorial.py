# -*- coding: utf-8 -*-
"""
HPD-RVE 完整因子设计驱动 (vm x dm/df) — 真实 DAMASK 计算每个组合.
流程: 生成几何 -> DAMASK_grid -> 解析屈服/UTS -> 聚合结果.
支持断点续跑: 若 outdir/result.json 已存在则跳过.

用法:
  python run_factorial.py            # 跑全部 4x4 (单 seed)
  python run_factorial.py --seeds 1 2 3   # 多 seed 取均值/方差
"""
import argparse
import os
import json
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from factorial_rve_gen import gen_geometry
from parse_damask import parse

DAMASK_BIN = "/usr/bin/DAMASK_grid"
LOAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "load_factorial.yaml")
BASE = os.path.abspath("./factorial_geoms")

VMS = [0.20, 0.30, 0.40, 0.50]
DFS = [0.3, 0.5, 0.7, 1.0]
N = 32
G = 70


def run_one(vm, df, seed, timeout=1800):
    od = os.path.join(BASE, f"vm{vm:.2f}_df{df:.2f}", f"seed{seed}")
    os.makedirs(od, exist_ok=True)
    res_path = os.path.join(od, "result.json")
    if os.path.exists(res_path):
        with open(res_path) as f:
            return json.load(f)  # 续跑跳过
    # 1) 几何
    vti, yaml, meta = gen_geometry(vm, df, seed=seed, N=N, G=G, outdir=od)
    # 2) DAMASK
    h5 = os.path.join(od, "t1.hdf5")
    t0 = time.time()
    with open(os.path.join(od, "run.log"), "w") as log:
        p = subprocess.run(
            [DAMASK_BIN, "-g", vti, "-l", LOAD, "-m", yaml, "-w", od, "-j", "t1"],
            stdout=log, stderr=subprocess.STDOUT, cwd=od, timeout=timeout)
    if p.returncode != 0 or not os.path.exists(h5):
        meta.update({"status": "FAILED", "returncode": p.returncode,
                     "time_s": round(time.time() - t0, 1)})
        with open(res_path, "w") as f:
            json.dump(meta, f, indent=2)
        return meta
    # 3) 解析
    r = parse(h5)
    meta.update({"status": "OK", "time_s": round(time.time() - t0, 1),
                 "sigma_y_MPa": r["sigma_y_MPa"], "UTS_MPa": r["UTS_MPa"],
                 "E_MPa": r["E_MPa"]})
    with open(res_path, "w") as f:
        json.dump(meta, f, indent=2)
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1])
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args()
    results = []
    total = len(VMS) * len(DFS) * len(a.seeds)
    done = 0
    for vm in VMS:
        for df in DFS:
            for seed in a.seeds:
                done += 1
                print(f"[{done}/{total}] vm={vm} dm/df={df} seed={seed} ...", flush=True)
                try:
                    m = run_one(vm, df, seed, timeout=a.timeout)
                    print(f"    -> {m.get('status')} sigma_y={m.get('sigma_y_MPa')} "
                          f"UTS={m.get('UTS_MPa')} (vm_act={m.get('vm_actual'):.3f}, "
                          f"df_act={m.get('dm_df_actual'):.3f})", flush=True)
                    results.append(m)
                except Exception as e:
                    print(f"    -> EXCEPTION {e}", flush=True)
                    results.append({"vm_target": vm, "dm_df_target": df, "seed": seed,
                                    "status": "EXCEPTION", "error": str(e)})
    # 聚合
    agg = os.path.join(BASE, "all_results.json")
    with open(agg, "w") as f:
        json.dump(results, f, indent=2)
    # 打印表格
    print("\n=== 因子设计结果 (真实 DAMASK) ===")
    print(f"{'vm':>5} {'dm/df':>6} {'seed':>4} {'vm_act':>7} {'df_act':>7} "
          f"{'sigma_y':>9} {'UTS':>9} {'E':>9}")
    for m in results:
        print(f"{m.get('vm_target'):>5.2f} {m.get('dm_df_target'):>6.2f} "
              f"{m.get('seed','-'):>4} {m.get('vm_actual',0):>7.3f} "
              f"{m.get('dm_df_actual',0):>7.3f} {m.get('sigma_y_MPa',0):>9.1f} "
              f"{m.get('UTS_MPa',0):>9.1f} {m.get('E_MPa',0):>9.0f}")
    print(f"\n聚合已写入: {agg}")


if __name__ == "__main__":
    main()
