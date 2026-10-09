# -*- coding: utf-8 -*-
"""
读取因子设计结果 (factorial_geoms/*/seed*/result.json), 生成:
  - 4x4 σ_y / UTS 矩阵 (均值), 含逐单元标准差 (用于误差棒)
  - 偏导拟合: σ_y_mean = a + b*vm + c*dm_df  ->  b=∂σ_y/∂vm, c=∂σ_y/∂dm_df
  - Fig 5: σ_y vs vm (按 dm/df 分线, ±1 std 误差棒) + 响应面
  - Table 8/9 风格的 LaTeX 矩阵
支持多 seed: 同一 (vm, dm/df) 下多个 seed 取均值与标准差.

用法:
  python build_factorial_tables.py
结果写入 ./factorial_out/
"""
import os, json, glob
import numpy as np

BASE = os.path.abspath("./factorial_geoms")
OUT = os.path.abspath("./factorial_out")
os.makedirs(OUT, exist_ok=True)

VMS = [0.20, 0.30, 0.40, 0.50]
DFS = [0.3, 0.5, 0.7, 1.0]


def load():
    rows = []
    for p in glob.glob(os.path.join(BASE, "*", "*", "result.json")):
        with open(p) as f:
            d = json.load(f)
        if d.get("status") != "OK":
            continue
        rows.append({
            "vm": d["vm_target"], "df": d["dm_df_target"],
            "vm_a": d.get("vm_actual"), "df_a": d.get("dm_df_actual"),
            "seed": d.get("seed"),
            "sy": d["sigma_y_MPa"], "uts": d["UTS_MPa"], "E": d.get("E_MPa"),
        })
    return rows


def cell_stats(rows):
    """对每 (vm,df) 单元聚合多 seed -> mean/std."""
    cells = {}
    for r in rows:
        key = (r["vm"], r["df"])
        cells.setdefault(key, []).append(r)
    stat = {}
    for key, rs in cells.items():
        sy = np.array([x["sy"] for x in rs])
        uts = np.array([x["uts"] for x in rs])
        stat[key] = {
            "n": len(rs), "seeds": [x["seed"] for x in rs],
            "sy_mean": float(sy.mean()), "sy_std": float(sy.std(ddof=0)),
            "uts_mean": float(uts.mean()), "uts_std": float(uts.std(ddof=0)),
            "vm_a": float(np.mean([x["vm_a"] for x in rs])),
            "df_a": float(np.mean([x["df_a"] for x in rs])),
        }
    return stat


def matrices(stat):
    syM = np.full((len(VMS), len(DFS)), np.nan)
    syS = np.full((len(VMS), len(DFS)), np.nan)
    utsM = np.full((len(VMS), len(DFS)), np.nan)
    utsS = np.full((len(VMS), len(DFS)), np.nan)
    for (vm, df), s in stat.items():
        i = VMS.index(vm); j = DFS.index(df)
        syM[i, j] = s["sy_mean"]; syS[i, j] = s["sy_std"]
        utsM[i, j] = s["uts_mean"]; utsS[i, j] = s["uts_std"]
    return syM, syS, utsM, utsS


def fit_plane(stat):
    """在逐单元均值上拟合 σ_y = a + b*vm + c*dm_df."""
    X, y = [], []
    for (vm, df), s in stat.items():
        X.append([1.0, vm, df]); y.append(s["sy_mean"])
    X = np.array(X); y = np.array(y)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coef


def fmt(v, nd=1):
    return f"{v:.{nd}f}" if (v == v and v is not None) else "---"


def latex_matrix(M, S, title, label):
    lines = [r"\begin{table}[t]", r"  \centering",
             f"  \\caption{{{title}}}", f"  \\label{{{label}}}",
             r"  \begin{tabular}{l|" + "c" * len(DFS) + "}",
             r"    \toprule",
             "    $v_m$ $\\backslash$ $d_m/d_f$ & " +
             " & ".join(f"{d:.1f}" for d in DFS) + r" \\",
             r"    \midrule"]
    for i, vm in enumerate(VMS):
        cells = []
        for j in range(len(DFS)):
            if M[i, j] == M[i, j]:
                if S[i, j] == S[i, j] and S[i, j] > 0:
                    cells.append(f"{M[i,j]:.1f}$\\pm${S[i,j]:.1f}")
                else:
                    cells.append(f"{M[i,j]:.1f}")
            else:
                cells.append("---")
        lines.append(f"    {vm:.2f} & " + " & ".join(cells) + r" \\")
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
    return "\n".join(lines)


def main():
    rows = load()
    print(f"可用 OK 结果: {len(rows)} 个")
    if not rows:
        print("尚无结果, 后台因子设计仍在运行。")
        return
    stat = cell_stats(rows)
    n_cells = len(stat)
    print(f"覆盖单元 (vm,dm/df): {n_cells} 个; 平均 seed/单元: "
          f"{np.mean([s['n'] for s in stat.values()]):.2f}")
    syM, syS, utsM, utsS = matrices(stat)
    coef = fit_plane(stat)
    a, b, c = coef
    print("\n=== σ_y 矩阵 (均值, MPa) ===")
    print("vm\\df ", DFS)
    for i, vm in enumerate(VMS):
        print(f"  {vm:.2f}", [fmt(syM[i, j]) + (f"±{syS[i,j]:.1f}" if syS[i,j]>0 else "")
                             for j in range(len(DFS))])
    print("\n=== UTS 矩阵 (均值, MPa) ===")
    for i, vm in enumerate(VMS):
        print(f"  {vm:.2f}", [fmt(utsM[i, j]) for j in range(len(DFS))])
    print(f"\n偏导拟合 σ_y = {a:.1f} + {b:.1f}·v_m + {c:.1f}·(d_m/d_f)  "
          f"[按 {n_cells} 单元均值, n_seed={int(np.mean([s['n'] for s in stat.values()]))}]")
    print(f"  ∂σ_y/∂v_m        = {b:.1f} MPa/单位v_m")
    print(f"  ∂σ_y/∂(d_m/d_f)  = {c:.1f} MPa/单位dm/df")

    np.savetxt(os.path.join(OUT, "sy_matrix.csv"), syM, delimiter=",")
    np.savetxt(os.path.join(OUT, "sy_std.csv"), syS, delimiter=",")
    np.savetxt(os.path.join(OUT, "uts_matrix.csv"), utsM, delimiter=",")
    with open(os.path.join(OUT, "fit.txt"), "w") as f:
        f.write(f"a={a:.3f}\nb={b:.3f}\nc={c:.3f}\nn_cells={n_cells}\n"
                f"n_rows={len(rows)}\n")
    with open(os.path.join(OUT, "tab_matrix_sy.tex"), "w") as f:
        nseed = int(np.mean([s['n'] for s in stat.values()]))
        f.write(latex_matrix(syM, syS,
              f"Yield stress $\\sigma_y$ (MPa, mean$\\pm$std over seeds) from "
              f"full-factorial DAMASK spectral simulations. Rows: martensite "
              f"volume fraction $v_m$; columns: martensite-to-ferrite "
              f"grain-size ratio $d_m/d_f$. Each cell averages {nseed} RVE "
              f"realizations.", "tab:fac-sy"))
    with open(os.path.join(OUT, "tab_matrix_uts.tex"), "w") as f:
        f.write(latex_matrix(utsM, utsS,
              "Ultimate tensile strength (MPa, mean$\\pm$std over seeds) from "
              "full-factorial DAMASK simulations (same layout as "
              "Table~\\ref{tab:fac-sy}).", "tab:fac-uts"))

    # Fig 5: σ_y vs vm, lines per dm/df, ±std 误差棒
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6.5, 4.5))
        for j, df in enumerate(DFS):
            xs, ys, es = [], [], []
            for i, vm in enumerate(VMS):
                if syM[i, j] == syM[i, j]:
                    xs.append(vm); ys.append(syM[i, j])
                    es.append(syS[i, j] if syS[i, j] == syS[i, j] else 0.0)
            if xs:
                ax.errorbar(xs, ys, yerr=es, fmt="o-", capsize=4,
                            label=f"$d_m/d_f$={df:.1f}")
        ax.set_xlabel("Martensite volume fraction $v_m$")
        ax.set_ylabel("Yield stress $\\sigma_y$ (MPa)")
        ax.set_title("DAMASK full-field: $\\sigma_y$ vs $v_m$ (factorial)")
        ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "fig5_pred.png"), dpi=150)
        fig.savefig(os.path.join(OUT, "fig5_pred.pdf"))
        print("\nFig 5 已保存:", os.path.join(OUT, "fig5_pred.png"))
    except Exception as e:
        print("绘图跳过:", e)

    snippet = (
        f"% 修正叙述 (替换原 185 MPa 手写值):\n"
        f"% 真实 DAMASK 因子设计 ({n_cells} 单元, 多 seed 均值±std) 给出\n"
        f"%   ∂σ_y/∂v_m = {b:.1f} MPa/单位v_m,\n"
        f"%   ∂σ_y/∂(d_m/d_f) = {c:.1f} MPa/单位dm/df.\n"
    )
    with open(os.path.join(OUT, "narrative_snippet.txt"), "w") as f:
        f.write(snippet)
    print("\n已写出 LaTeX 表 / 矩阵 / 拟合到 ./factorial_out/")


if __name__ == "__main__":
    main()
