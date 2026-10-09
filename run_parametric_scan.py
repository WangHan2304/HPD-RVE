"""
微观结构-性能参数化扫描 v2
使用 PhysicsBasedCPFEM (含Hall-Petch + 混合法则)
"""

import json
import numpy as np
from parametric_cpfem import PhysicsBasedCPFEM, DP800_REF
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ============================================================
# 参数空间
# ============================================================
V_M_VALUES = [0.15, 0.25, 0.35, 0.45, 0.55]    # 马氏体体积分数
RATIO_VALUES = [0.3, 0.5, 0.7, 1.0]             # d_m/d_f
SEEDS = [1, 2, 3, 4, 5]
D_F_UM = 15.0  # 铁素体参考晶粒尺寸 (µm)

# 额外预测集 (未实验组合)
PREDICTION_CONFIGS = [
    {"v_m": 0.40, "d_ratio": 0.4, "label": "v_m=0.40, d_m/d_f=0.4"},
    {"v_m": 0.50, "d_ratio": 0.6, "label": "v_m=0.50, d_m/d_f=0.6"},
    {"v_m": 0.30, "d_ratio": 0.8, "label": "v_m=0.30, d_m/d_f=0.8"},
    {"v_m": 0.20, "d_ratio": 0.9, "label": "v_m=0.20, d_m/d_f=0.9"},
]

# ============================================================
# 运行扫描
# ============================================================
def run_scan():
    solver = PhysicsBasedCPFEM()
    results = []
    
    total = len(V_M_VALUES) * len(RATIO_VALUES) * len(SEEDS)
    count = 0
    
    for v_m in V_M_VALUES:
        for ratio in RATIO_VALUES:
            for seed in SEEDS:
                count += 1
                d_f = D_F_UM
                d_m = d_f * ratio
                
                n_m = max(3, int(v_m * 100))
                n_f = max(3, 100 - n_m)
                
                print(f"[{count}/{total}] v_m={v_m:.2f}, d_ratio={ratio:.2f}, seed={seed}")
                
                r = solver.compute_stress_strain(
                    v_m=v_m, d_f_um=d_f, d_m_um=d_m,
                    n_ferrite_grains=n_f, n_martensite_grains=n_m,
                    max_strain=0.10, n_steps=50, seed=seed,
                    enable_calibration=True  # 用DP800参考数据校准形状
                )
                results.append(r)
    
    # 保存
    out_path = Path(__file__).parent / "parametric_scan_results_v2.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "v_m_range": V_M_VALUES,
                "ratio_range": RATIO_VALUES,
                "seeds": SEEDS,
                "d_f_um": D_F_UM,
                "solver": "PhysicsBasedCPFEM (Hall-Petch + Mixing Rule)",
                "hall_petch_k_ferrite": 18.0,
                "hall_petch_k_martensite": 25.0,
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n[DONE] {len(results)}/{total} simulations completed")
    print(f"  Saved: {out_path}")
    return results


def run_predictions():
    """运行预测集 (未实验的微观结构)"""
    solver = PhysicsBasedCPFEM()
    preds = []
    
    for config in PREDICTION_CONFIGS:
        d_f = D_F_UM
        d_m = d_f * config["d_ratio"]
        n_m = max(3, int(config["v_m"] * 100))
        n_f = max(3, 100 - n_m)
        
        print(f"Prediction: {config['label']}")
        
        # 5个seeds取平均
        seed_results = []
        for seed in [1, 2, 3, 4, 5]:
            r = solver.compute_stress_strain(
                v_m=config["v_m"], d_f_um=d_f, d_m_um=d_m,
                n_ferrite_grains=n_f, n_martensite_grains=n_m,
                max_strain=0.10, n_steps=50, seed=seed,
                enable_calibration=True
            )
            seed_results.append(r)
        
        # 平均
        avg = {
            "v_m": config["v_m"],
            "d_ratio": config["d_ratio"],
            "label": config["label"],
            "yield_stress_MPa": round(np.mean([r["yield_stress_MPa"] for r in seed_results]), 1),
            "uts_MPa": round(np.mean([r["uts_MPa"] for r in seed_results]), 1),
            "hardening_rate_MPa": round(np.mean([r["hardening_rate_MPa"] for r in seed_results]), 1),
            "mf_stress_ratio": round(np.mean([r["mf_stress_ratio"] for r in seed_results if r["mf_stress_ratio"]]), 3),
            "strains": seed_results[0]["strains"],
            "stress_macro_avg": np.mean([r["stress_macro"] for r in seed_results], axis=0).tolist(),
            "stress_macro_std": np.std([r["stress_macro"] for r in seed_results], axis=0).tolist(),
            "seeds_detail": seed_results,
        }
        preds.append(avg)
    
    out_path = Path(__file__).parent / "predictions_results.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({"predictions": preds}, f, indent=2)
    
    print(f"\n[DONE] {len(preds)} predictions completed")
    print(f"  Saved: {out_path}")
    return preds


# ============================================================
# 图表生成
# ============================================================
def generate_figures(results):
    figures_dir = Path(__file__).parent / "figures"
    figures_dir.mkdir(exist_ok=True)
    
    # 组织数据
    data = {}
    for r in results:
        key = (r["v_m"], r["d_ratio"])
        if key not in data:
            data[key] = []
        data[key].append(r)
    
    v_m_unique = sorted(set(r["v_m"] for r in results))
    ratio_unique = sorted(set(r["d_ratio"] for r in results))
    colors = plt.cm.viridis(np.linspace(0, 1, len(ratio_unique)))
    
    # ============ Figure 1: 主响应面 (4面板) ============
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    # (a) 屈服应力响应面
    ax = axes[0, 0]
    Z = np.zeros((len(ratio_unique), len(v_m_unique)))
    for i, ratio in enumerate(ratio_unique):
        for j, vm in enumerate(v_m_unique):
            vals = [r["yield_stress_MPa"] for r in data.get((vm, ratio), [])]
            Z[i, j] = np.mean(vals)
    
    V, R = np.meshgrid(v_m_unique, ratio_unique)
    im = ax.pcolormesh(V, R, Z, cmap='RdYlBu_r', shading='auto')
    for i in range(len(ratio_unique)):
        for j in range(len(v_m_unique)):
            ax.text(v_m_unique[j], ratio_unique[i], f'{Z[i,j]:.0f}',
                   ha='center', va='center', fontsize=8, fontweight='bold',
                   color='white' if Z[i,j] > 450 else 'black')
    plt.colorbar(im, ax=ax, label='Yield Stress (MPa)')
    ax.set_xlabel('Martensite Volume Fraction $v_m$')
    ax.set_ylabel('Grain Size Ratio $d_m/d_f$')
    ax.set_title('(a) Yield Stress $\\sigma_{0.2\\%}$ (MPa)')
    
    # (b) 屈服应力 vs v_m (按d_ratio)
    ax = axes[0, 1]
    for i, ratio in enumerate(ratio_unique):
        means = [np.mean([r["yield_stress_MPa"] for r in data.get((vm, ratio), [])])
                 for vm in v_m_unique]
        stds = [np.std([r["yield_stress_MPa"] for r in data.get((vm, ratio), [])])
                for vm in v_m_unique]
        ax.errorbar(v_m_unique, means, yerr=stds, marker='o', color=colors[i],
                   label=f'$d_m/d_f={ratio}$', capsize=3, linewidth=1.8, markersize=7)
    
    # Hall-Petch参考线
    ax.axhline(y=340, color='gray', linestyle=':', alpha=0.5, label='DP800 ref (Tasan 2014)')
    ax.set_xlabel('Martensite Volume Fraction $v_m$')
    ax.set_ylabel('Yield Stress $\\sigma_{0.2\\%}$ (MPa)')
    ax.set_title('(b) $\\sigma_y$ vs $v_m$ (Hall-Petch + Mixing)')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    
    # (c) 硬化率 vs v_m
    ax = axes[1, 0]
    for i, ratio in enumerate(ratio_unique):
        means = [np.mean([r["hardening_rate_MPa"] for r in data.get((vm, ratio), [])])
                 for vm in v_m_unique]
        stds = [np.std([r["hardening_rate_MPa"] for r in data.get((vm, ratio), [])])
                for vm in v_m_unique]
        ax.errorbar(v_m_unique, means, yerr=stds, marker='s', color=colors[i],
                   label=f'$d_m/d_f={ratio}$', capsize=3, linewidth=1.8, markersize=7)
    
    ax.set_xlabel('Martensite Volume Fraction $v_m$')
    ax.set_ylabel('Hardening Rate $\\theta$ (MPa)')
    ax.set_title('(c) Strain Hardening Rate $\\theta = d\\sigma/d\\varepsilon|_{5-10\\%}$')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    
    # (d) M/F应力比
    ax = axes[1, 1]
    for i, ratio in enumerate(ratio_unique):
        mf_means = []
        mf_stds = []
        vm_valid = []
        for vm in v_m_unique:
            vals = [r["mf_stress_ratio"] for r in data.get((vm, ratio), [])
                   if r["mf_stress_ratio"] is not None]
            if vals:
                mf_means.append(np.mean(vals))
                mf_stds.append(np.std(vals))
                vm_valid.append(vm)
        
        if vm_valid:
            ax.errorbar(vm_valid, mf_means, yerr=mf_stds, marker='D', color=colors[i],
                       label=f'$d_m/d_f={ratio}$', capsize=3, linewidth=1.8, markersize=7)
    
    ax.axhline(y=1.36, color='gray', linestyle=':', alpha=0.5, label='Taylor CPFEM (1.36)')
    ax.axhline(y=1.49, color='red', linestyle='--', alpha=0.5, label='DAMASK (1.49)')
    ax.set_xlabel('Martensite Volume Fraction $v_m$')
    ax.set_ylabel('Phase Stress Ratio $\\sigma_m/\\sigma_f$')
    ax.set_title('(d) Load Partitioning: $\\sigma_m/\\sigma_f$ at $\\varepsilon=0.10$')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(figures_dir / 'Figure_ParametricScan_Main.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  [OK] Figure_ParametricScan_Main.png")
    
    # ============ Figure 2: 敏感性分析 ============
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    # 主效应计算
    vm_effect_yield = [np.mean([r["yield_stress_MPa"] for r in results if abs(r["v_m"]-vm)<0.001]) for vm in v_m_unique]
    ratio_effect_yield = [np.mean([r["yield_stress_MPa"] for r in results if abs(r["d_ratio"]-ratio)<0.001]) for ratio in ratio_unique]
    vm_effect_hr = [np.mean([r["hardening_rate_MPa"] for r in results if abs(r["v_m"]-vm)<0.001]) for vm in v_m_unique]
    
    # (a) 参数敏感性条形图
    ax = axes[0]
    sens_vm_yield = max(vm_effect_yield) - min(vm_effect_yield)
    sens_ratio_yield = max(ratio_effect_yield) - min(ratio_effect_yield)
    sens_vm_hr = max(vm_effect_hr) - min(vm_effect_hr)
    
    categories = ['$v_m$ on $\\sigma_y$', '$d_m/d_f$ on $\\sigma_y$', '$v_m$ on $\\theta$']
    values = [sens_vm_yield, sens_ratio_yield, sens_vm_hr]
    colors_bar = ['#e74c3c', '#3498db', '#2ecc71']
    bars = ax.bar(categories, values, color=colors_bar, edgecolor='black', linewidth=1.2)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
               f'{val:.1f} MPa', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Response Range (MPa)')
    ax.set_title('(a) Parameter Sensitivity\n(Main Effect Magnitudes)')
    ax.grid(True, alpha=0.2, axis='y')
    
    # (b) v_m主效应 (线性度)
    ax = axes[1]
    vm_arr = np.array(v_m_unique)
    A = np.vstack([vm_arr, np.ones_like(vm_arr)]).T
    slope, intercept = np.linalg.lstsq(A, vm_effect_yield, rcond=None)[0]
    r2 = 1 - np.var(np.array(vm_effect_yield) - slope*vm_arr - intercept) / np.var(vm_effect_yield)
    
    ax.scatter(vm_arr, vm_effect_yield, s=100, c='#e74c3c', edgecolors='black', zorder=5)
    ax.plot(vm_arr, slope*vm_arr + intercept, 'k--', linewidth=2, 
           label=f'Linear fit: $R^2={r2:.3f}$\nSlope = {slope:.0f} MPa/$v_m$')
    ax.set_xlabel('Martensite Volume Fraction $v_m$')
    ax.set_ylabel('Yield Stress $\\sigma_y$ (MPa)')
    ax.set_title('(b) $v_m$ Main Effect on $\\sigma_y$\n(Linear Strengthening)')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # (c) d_m/d_f主效应
    ax = axes[2]
    ax.plot(ratio_unique, ratio_effect_yield, 'o-', color='#3498db', linewidth=2, markersize=10)
    ax.set_xlabel('Grain Size Ratio $d_m/d_f$')
    ax.set_ylabel('Yield Stress $\\sigma_y$ (MPa)')
    ax.set_title('(c) $d_m/d_f$ Main Effect on $\\sigma_y$\n(Minor effect via Hall-Petch)')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(figures_dir / 'Figure_ParametricScan_SensitivityAnalysis.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  [OK] Figure_ParametricScan_SensitivityAnalysis.png")
    
    # ============ Figure 3: 代表性应力-应变曲线 ============
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    
    # 选择d_ratio=0.5的所有v_m
    ratio_show = 0.5
    for j, vm in enumerate(v_m_unique):
        ax = axes[0, j] if j < 3 else axes[1, j-3]
        entries = [r for r in data.get((vm, ratio_show), [])]
        
        # 5个seeds
        for e in entries:
            ax.plot(e["strains"], e["stress_macro"], alpha=0.3, linewidth=0.8, color='gray')
        
        # 平均
        if entries:
            avg = np.mean([e["stress_macro"] for e in entries], axis=0)
            ax.plot(entries[0]["strains"], avg, 'b-', linewidth=2.5, label='Macro')
            # 相分解
            if vm > 0.01:
                avg_f = np.mean([e["stress_ferrite"] for e in entries], axis=0)
                avg_m = np.mean([e["stress_martensite"] for e in entries], axis=0)
                ax.plot(entries[0]["strains"], avg_f, 'g--', linewidth=1.5, alpha=0.7, label='Ferrite')
                ax.plot(entries[0]["strains"], avg_m, 'r--', linewidth=1.5, alpha=0.7, label='Martensite')
            
            avg_yield = np.mean([e["yield_stress_MPa"] for e in entries])
            avg_uts = np.mean([e["uts_MPa"] for e in entries])
            ax.set_title(f'$v_m={vm:.2f}$ ($d_m/d_f={ratio_show}$)\n'
                        f'$\\sigma_y={avg_yield:.0f}$ MPa, UTS$={avg_uts:.0f}$ MPa',
                        fontsize=10)
        
        ax.set_xlabel('Strain $\\varepsilon$')
        if j == 0:
            ax.set_ylabel('Stress $\\sigma$ (MPa)')
            ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 0.10)
    
    plt.tight_layout()
    fig.savefig(figures_dir / 'Figure_ParametricScan_StressStrain.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  [OK] Figure_ParametricScan_StressStrain.png")
    
    # 打印摘要
    print("\n" + "="*60)
    print("PARAMETRIC SCAN SUMMARY (PhysicsBasedCPFEM)")
    print("="*60)
    print(f"Hall-Petch: k_HP_f = {18.0} MPa·um^0.5, k_HP_m = {25.0} MPa·um^0.5")
    print(f"Reference d_f = {D_F_UM} um")
    print(f"\nMain effects:")
    print(f"  v_m on sigma_y: {sens_vm_yield:.1f} MPa (slope = {slope:.0f} MPa/v_m, R^2 = {r2:.3f})")
    print(f"  d_m/d_f on sigma_y: {sens_ratio_yield:.1f} MPa")
    print(f"  v_m on hardening rate: {sens_vm_hr:.1f} MPa")
    
    print(f"\nYield stress by v_m (d_m/d_f={ratio_show}):")
    for vm in v_m_unique:
        vals = [r["yield_stress_MPa"] for r in data.get((vm, ratio_show), [])]
        print(f"  v_m={vm:.2f}: {np.mean(vals):.1f} +/- {np.std(vals):.1f} MPa")
    
    return {
        "sens_vm_yield": sens_vm_yield,
        "sens_ratio_yield": sens_ratio_yield,
        "slope_vm": slope,
        "r2_vm": r2,
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "figures_only":
        with open(Path(__file__).parent / "parametric_scan_results_v2.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        generate_figures(data["results"])
    elif len(sys.argv) > 1 and sys.argv[1] == "predict":
        run_predictions()
    else:
        print("="*60)
        print("TASK 1: Microstructure-Property Parametric Scan v2")
        print("PhysicsBasedCPFEM with Hall-Petch + Mixing Rule")
        print("="*60)
        
        results = run_scan()
        stats = generate_figures(results)
        
        # 运行预测
        print("\n--- Running prediction set ---")
        preds = run_predictions()
        
        # 保存摘要
        summary = {
            "scan_statistics": stats,
            "prediction_configs": PREDICTION_CONFIGS,
        }
        with open(Path(__file__).parent / "parametric_scan_summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
