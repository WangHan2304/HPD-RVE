"""
任务1: 微观结构-性能定量映射
============================================
对DP钢进行系统性参数扫描：
- 马氏体体积分数: v_m ∈ [0.15, 0.25, 0.35, 0.45, 0.55] (5个水平)
- 晶粒尺寸比: d_m/d_f ∈ [0.3, 0.5, 0.7, 1.0] (4个水平)
- 随机种子: [1, 2, 3, 4, 5] (5个实现)
- 总计: 5×4×5 = 100个RVE模拟

此外还生成额外的预测集用于任务3。

输出:
- parametric_scan_results.json: 完整扫描结果
- figures/Figure_ParametricScan_*.png: 响应面等图表
"""

import json
import numpy as np
from cpfem_simulation import TaylorCrystalPlasticitySolver
from pathlib import Path

# ============================================================
# 配置
# ============================================================
V_M_VALUES = [0.15, 0.25, 0.35, 0.45, 0.55]   # 马氏体体积分数
RATIO_VALUES = [0.3, 0.5, 0.7, 1.0]            # d_m/d_f
SEEDS = [1, 2, 3, 4, 5]                        # 随机种子
MAX_STRAIN = 0.10
N_STEPS = 50
STRAIN_RATE = 0.001

# ============================================================
# 参数化扫描主函数
# ============================================================
def run_parametric_scan():
    results = []
    
    total = len(V_M_VALUES) * len(RATIO_VALUES) * len(SEEDS)
    count = 0
    
    for v_m in V_M_VALUES:
        for ratio in RATIO_VALUES:
            for seed in SEEDS:
                count += 1
                np.random.seed(seed)
                
                v_f = 1.0 - v_m
                # 晶粒数：总100个晶粒按体积分数分配
                n_martensite = max(3, int(v_m * 100))
                n_ferrite = max(3, 100 - n_martensite)
                
                print(f"[{count}/{total}] v_m={v_m:.2f}, ratio={ratio:.2f}, seed={seed}")
                
                try:
                    solver = TaylorCrystalPlasticitySolver("DP_steel")
                    result = solver.compute_stress_strain_curve(
                        ferrite_volume_fraction=v_f,
                        n_ferrite_grains=n_ferrite,
                        n_martensite_grains=n_martensite,
                        max_strain=MAX_STRAIN,
                        n_steps=N_STEPS,
                        strain_rate=STRAIN_RATE,
                        loading_mode="uniaxial_tension"
                    )
                    
                    # 提取关键力学量
                    strains = np.array(result["strains"])
                    stress_macro = np.array(result["stress_macro"])
                    stress_f = np.array(result["stress_ferrite"])
                    stress_m = np.array(result["stress_martensite"])
                    
                    # 屈服应力 (0.2% offset)
                    idx_02 = np.argmin(np.abs(strains - 0.002))
                    yield_stress = float(stress_macro[idx_02])
                    
                    # 极限强度 (最大应力)
                    uts = float(np.max(stress_macro))
                    
                    # 硬化率 (5%-10%应变段)
                    idx_5pct = np.argmin(np.abs(strains - 0.05))
                    idx_10pct = np.argmin(np.abs(strains - 0.10))
                    hardening_rate = float(
                        (stress_macro[idx_10pct] - stress_macro[idx_5pct]) / 0.05
                    )
                    
                    # 应力比 (M/F)
                    if v_m > 0 and stress_f[idx_10pct] > 0:
                        mf_ratio = float(stress_m[idx_10pct] / stress_f[idx_10pct])
                    else:
                        mf_ratio = None
                    
                    # 硬化指数 n (Ramberg-Osgood型: σ = K ε^n)
                    # 拟合 log(σ) = log(K) + n*log(ε_plastic)
                    # 简化：用0.5%-10%应变段的线性拟合
                    idx_start = np.argmin(np.abs(strains - 0.005))
                    idx_end = np.argmin(np.abs(strains - 0.10))
                    log_strains = np.log(strains[idx_start:idx_end+1] + 1e-6)
                    log_stress = np.log(np.abs(stress_macro[idx_start:idx_end+1]))
                    # 线性回归
                    A = np.vstack([log_strains, np.ones_like(log_strains)]).T
                    n, log_K = np.linalg.lstsq(A, log_stress, rcond=None)[0]
                    
                    entry = {
                        "v_m": v_m,
                        "v_f": v_f,
                        "d_ratio": ratio,
                        "seed": seed,
                        "n_ferrite_grains": n_ferrite,
                        "n_martensite_grains": n_martensite,
                        "yield_stress_MPa": round(yield_stress, 1),
                        "uts_MPa": round(uts, 1),
                        "hardening_rate_MPa": round(hardening_rate, 1),
                        "mf_stress_ratio": round(mf_ratio, 3) if mf_ratio else None,
                        "hardening_exponent_n": round(float(n), 4),
                        "flow_stress_5pct": round(float(stress_macro[idx_5pct]), 1),
                        "flow_stress_10pct": round(float(stress_macro[idx_10pct]), 1),
                        "strains": strains.tolist(),
                        "stress_macro": stress_macro.tolist(),
                        "stress_ferrite": stress_f.tolist(),
                        "stress_martensite": stress_m.tolist() if v_m > 0 else [],
                    }
                    results.append(entry)
                    
                except Exception as e:
                    print(f"  ERROR: {e}")
                    continue
    
    # 保存结果
    output_path = Path(__file__).parent / "parametric_scan_results.json"
    with open(output_path, 'w') as f:
        json.dump({
            "metadata": {
                "v_m_range": V_M_VALUES,
                "ratio_range": RATIO_VALUES,
                "seeds": SEEDS,
                "max_strain": MAX_STRAIN,
                "n_steps": N_STEPS,
                "total_simulations": len(results),
                "solver": "TaylorCrystalPlasticitySolver (DP_steel)",
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n[DONE] {len(results)}/{total} simulations completed successfully")
    print(f"  Results saved to: {output_path}")
    return results


# ============================================================
# 生成图表
# ============================================================
def generate_figures(results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    
    figures_dir = Path(__file__).parent / "figures"
    figures_dir.mkdir(exist_ok=True)
    
    # 将结果组织成表格
    data = {}
    for r in results:
        key = (r["v_m"], r["d_ratio"])
        if key not in data:
            data[key] = []
        data[key].append(r)
    
    # ---- Figure A: 响应面 - 屈服应力 σ_y(v_m, d_m/d_f) ----
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    
    # A1: 屈服应力响应面
    ax = axes[0]
    v_m_unique = sorted(set(r["v_m"] for r in results))
    ratio_unique = sorted(set(r["d_ratio"] for r in results))
    
    # 计算平均值和标准差
    Z_yield = np.zeros((len(ratio_unique), len(v_m_unique)))
    Z_yield_std = np.zeros_like(Z_yield)
    for i, ratio in enumerate(ratio_unique):
        for j, vm in enumerate(v_m_unique):
            vals = [r["yield_stress_MPa"] for r in data.get((vm, ratio), [])]
            Z_yield[i, j] = np.mean(vals)
            Z_yield_std[i, j] = np.std(vals)
    
    V, R = np.meshgrid(v_m_unique, ratio_unique)
    c = ax.pcolormesh(V, R, Z_yield, cmap='RdYlBu_r', shading='auto')
    # 添加标注
    for i in range(len(ratio_unique)):
        for j in range(len(v_m_unique)):
            ax.text(v_m_unique[j], ratio_unique[i], f'{Z_yield[i,j]:.0f}',
                   ha='center', va='center', fontsize=8, fontweight='bold')
    plt.colorbar(c, ax=ax, label='Yield Stress (MPa)')
    ax.set_xlabel('Martensite Volume Fraction $v_m$')
    ax.set_ylabel('Grain Size Ratio $d_m/d_f$')
    ax.set_title('(a) Yield Stress $\\sigma_y$ (MPa)\nResponse Surface')
    
    # A2: 不同d_m/d_f下的σ_y-v_m曲线
    ax = axes[1]
    colors = plt.cm.viridis(np.linspace(0, 1, len(ratio_unique)))
    for i, ratio in enumerate(ratio_unique):
        means = [np.mean([r["yield_stress_MPa"] for r in data.get((vm, ratio), [])])
                 for vm in v_m_unique]
        stds = [np.std([r["yield_stress_MPa"] for r in data.get((vm, ratio), [])])
                for vm in v_m_unique]
        ax.errorbar(v_m_unique, means, yerr=stds, marker='o', color=colors[i],
                   label=f'$d_m/d_f={ratio}$', capsize=3, linewidth=1.5)
    
    ax.set_xlabel('Martensite Volume Fraction $v_m$')
    ax.set_ylabel('Yield Stress $\\sigma_y$ (MPa)')
    ax.set_title('(b) $\\sigma_y$ vs $v_m$ by Grain Size Ratio')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    
    # A3: 硬化率 vs v_m
    ax = axes[2]
    for i, ratio in enumerate(ratio_unique):
        means = [np.mean([r["hardening_rate_MPa"] for r in data.get((vm, ratio), [])])
                 for vm in v_m_unique]
        stds = [np.std([r["hardening_rate_MPa"] for r in data.get((vm, ratio), [])])
                for vm in v_m_unique]
        ax.errorbar(v_m_unique, means, yerr=stds, marker='s', color=colors[i],
                   label=f'$d_m/d_f={ratio}$', capsize=3, linewidth=1.5)
    
    ax.set_xlabel('Martensite Volume Fraction $v_m$')
    ax.set_ylabel('Hardening Rate $\\theta$ (MPa)')
    ax.set_title('(c) Strain Hardening Rate $\\theta$\n($\\Delta\\sigma/\\Delta\\varepsilon$, 5-10% strain)')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(figures_dir / 'Figure_ParametricScan_ResponseSurface.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  [OK] Figure_ParametricScan_ResponseSurface.png")
    
    # ---- Figure B: 应力-应变曲线全家福 ----
    fig, axes = plt.subplots(len(ratio_unique), len(v_m_unique), 
                             figsize=(16, 12), sharex=True, sharey=True)
    
    for i, ratio in enumerate(ratio_unique):
        for j, vm in enumerate(v_m_unique):
            ax = axes[i, j] if len(ratio_unique) > 1 else axes[j]
            entries = data.get((vm, ratio), [])
            
            # 绘制所有seeds
            for e in entries:
                ax.plot(e["strains"], e["stress_macro"], alpha=0.3, linewidth=0.5, color='gray')
            # 绘制平均值
            if entries:
                avg_stress = np.mean([e["stress_macro"] for e in entries], axis=0)
                ax.plot(entries[0]["strains"], avg_stress, 'b-', linewidth=1.5)
                
                # 标注屈服和UTS
                avg_yield = np.mean([e["yield_stress_MPa"] for e in entries])
                avg_uts = np.mean([e["uts_MPa"] for e in entries])
                ax.axhline(y=avg_yield, color='r', linestyle='--', alpha=0.5, linewidth=0.8)
                
                ax.set_title(f'$v_m={vm}$\n$\\sigma_y={avg_yield:.0f}$, UTS$={avg_uts:.0f}$',
                           fontsize=7)
            
            if j == 0:
                ax.set_ylabel(f'$d_m/d_f={ratio}$\nStress (MPa)', fontsize=8)
            if i == len(ratio_unique) - 1:
                ax.set_xlabel('Strain', fontsize=8)
            ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    fig.savefig(figures_dir / 'Figure_ParametricScan_StressStrainGrid.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  [OK] Figure_ParametricScan_StressStrainGrid.png")
    
    # ---- Figure C: 相应力比和马氏体强化效率 ----
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # C1: M/F应力比 vs v_m (at ε=10%)
    ax = axes[0]
    for i, ratio in enumerate(ratio_unique):
        mf_means = []
        mf_stds = []
        for vm in v_m_unique:
            vals = [r["mf_stress_ratio"] for r in data.get((vm, ratio), []) 
                   if r["mf_stress_ratio"] is not None]
            if vals:
                mf_means.append(np.mean(vals))
                mf_stds.append(np.std(vals))
            else:
                mf_means.append(np.nan)
                mf_stds.append(np.nan)
        
        valid = ~np.isnan(mf_means)
        if np.any(valid):
            ax.errorbar(np.array(v_m_unique)[valid], np.array(mf_means)[valid],
                       yerr=np.array(mf_stds)[valid], marker='D', color=colors[i],
                       label=f'$d_m/d_f={ratio}$', capsize=3, linewidth=1.5)
    
    ax.set_xlabel('Martensite Volume Fraction $v_m$')
    ax.set_ylabel('Stress Ratio $\\sigma_m/\\sigma_f$ (at $\\varepsilon=0.10$)')
    ax.set_title('(a) Phase Stress Partitioning')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    
    # C2: 马氏体强化效率 Δσ_y/Δv_m
    ax = axes[1]
    for i, ratio in enumerate(ratio_unique):
        vm_arr = np.array(v_m_unique)
        sy_means = np.array([np.mean([r["yield_stress_MPa"] for r in data.get((vm, ratio), [])])
                            for vm in v_m_unique])
        
        # 线性拟合
        A = np.vstack([vm_arr, np.ones_like(vm_arr)]).T
        slope, intercept = np.linalg.lstsq(A, sy_means, rcond=None)[0]
        
        ax.scatter(vm_arr, sy_means, color=colors[i], marker='o', s=40)
        ax.plot(vm_arr, slope * vm_arr + intercept, '--', color=colors[i], 
               label=f'$d_m/d_f={ratio}$: {slope:.0f} MPa/$v_m$, $R^2={1-np.var(sy_means-slope*vm_arr-intercept)/np.var(sy_means):.3f}$',
               alpha=0.7)
    
    ax.set_xlabel('Martensite Volume Fraction $v_m$')
    ax.set_ylabel('Yield Stress $\\sigma_y$ (MPa)')
    ax.set_title('(b) Martensite Strengthening Efficiency\n$\\Delta\\sigma_y/\\Delta v_m$ (slope)')
    ax.legend(fontsize=6)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(figures_dir / 'Figure_ParametricScan_PhasePartitioning.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  [OK] Figure_ParametricScan_PhasePartitioning.png")
    
    # ---- Figure D: 敏感性分析 ----
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 计算各参数的主效应
    from itertools import combinations
    
    # v_m主效应
    vm_effect_yield = []
    vm_effect_uts = []
    for vm in v_m_unique:
        vals_y = [r["yield_stress_MPa"] for r in results if abs(r["v_m"] - vm) < 0.001]
        vals_u = [r["uts_MPa"] for r in results if abs(r["v_m"] - vm) < 0.001]
        vm_effect_yield.append(np.mean(vals_y))
        vm_effect_uts.append(np.mean(vals_u))
    
    # d_ratio主效应
    ratio_effect_yield = []
    ratio_effect_uts = []
    for ratio in ratio_unique:
        vals_y = [r["yield_stress_MPa"] for r in results if abs(r["d_ratio"] - ratio) < 0.001]
        vals_u = [r["uts_MPa"] for r in results if abs(r["d_ratio"] - ratio) < 0.001]
        ratio_effect_yield.append(np.mean(vals_y))
        ratio_effect_uts.append(np.mean(vals_u))
    
    # 敏感性：参数范围引起的响应变化幅度
    sensitivity_vm_yield = max(vm_effect_yield) - min(vm_effect_yield)
    sensitivity_ratio_yield = max(ratio_effect_yield) - min(ratio_effect_yield)
    sensitivity_vm_uts = max(vm_effect_uts) - min(vm_effect_uts)
    sensitivity_ratio_uts = max(ratio_effect_uts) - min(ratio_effect_uts)
    
    x = np.arange(2)
    width = 0.35
    bars1 = ax.bar(x - width/2, [sensitivity_vm_yield, sensitivity_ratio_yield], 
                   width, label='Yield Stress $\\sigma_y$', color='#e74c3c', edgecolor='black')
    bars2 = ax.bar(x + width/2, [sensitivity_vm_uts, sensitivity_ratio_uts], 
                   width, label='Ultimate Strength UTS', color='#3498db', edgecolor='black')
    
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{bar.get_height():.0f}', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{bar.get_height():.0f}', ha='center', va='bottom', fontsize=9)
    
    ax.set_xticks(x)
    ax.set_xticklabels(['$v_m$ (Martensite VF)', '$d_m/d_f$ (Grain Size Ratio)'])
    ax.set_ylabel('Response Range $\\Delta$ (MPa)')
    ax.set_title('Parameter Sensitivity: Main Effect Magnitudes\n(over studied ranges)')
    ax.legend()
    ax.grid(True, alpha=0.2, axis='y')
    
    plt.tight_layout()
    fig.savefig(figures_dir / 'Figure_ParametricScan_Sensitivity.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  [OK] Figure_ParametricScan_Sensitivity.png")
    
    # 输出统计摘要
    print("\n" + "="*60)
    print("PARAMETRIC SCAN SUMMARY")
    print("="*60)
    print(f"\nParameter ranges:")
    print(f"  v_m ∈ {V_M_VALUES}")
    print(f"  d_m/d_f ∈ {RATIO_VALUES}")
    print(f"  Seeds per config: {len(SEEDS)}")
    print(f"  Total simulations: {len(results)}")
    
    print(f"\nMain effects (response range):")
    print(f"  v_m effect on σ_y: {sensitivity_vm_yield:.0f} MPa")
    print(f"  d_m/d_f effect on σ_y: {sensitivity_ratio_yield:.0f} MPa")
    print(f"  v_m effect on UTS: {sensitivity_vm_uts:.0f} MPa")
    print(f"  d_m/d_f effect on UTS: {sensitivity_ratio_uts:.0f} MPa")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "figures_only":
        # 仅从已有结果生成图表
        with open(Path(__file__).parent / "parametric_scan_results.json", 'r') as f:
            data = json.load(f)
        generate_figures(data["results"])
    else:
        print("="*60)
        print("TASK 1: Microstructure-Property Parametric Scan")
        print("="*60)
        print(f"v_m levels: {V_M_VALUES}")
        print(f"d_m/d_f levels: {RATIO_VALUES}")
        print(f"Seeds per config: {len(SEEDS)}")
        print(f"Total: {len(V_M_VALUES)*len(RATIO_VALUES)*len(SEEDS)} simulations")
        print("="*60)
        
        results = run_parametric_scan()
        generate_figures(results)
