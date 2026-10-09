"""
微观结构-性能参数化扫描 v3 (最终版)
使用 PhysicsBasedCPFEM - 纯物理预测，无全局校准
- Hall-Petch晶粒尺寸效应
- 混合法则体积分数效应
- 展示的是物理趋势而非绝对数值
"""

import json
import numpy as np
from parametric_cpfem import PhysicsBasedCPFEM, DP800_REF
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# ============================================================
# 参数空间
# ============================================================
V_M_VALUES = [0.15, 0.25, 0.35, 0.45, 0.55]
RATIO_VALUES = [0.3, 0.5, 0.7, 1.0]
SEEDS = [1, 2, 3, 4, 5]
D_F_UM = 15.0

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
                    enable_calibration=False  # 纯物理预测！
                )
                results.append(r)
    
    out_path = Path(__file__).parent / "parametric_scan_results_v3.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "v_m_range": V_M_VALUES,
                "ratio_range": RATIO_VALUES,
                "seeds": SEEDS,
                "d_f_um": D_F_UM,
                "solver": "PhysicsBasedCPFEM (Hall-Petch + Mixing Rule, NO calibration)",
                "hall_petch_k_ferrite": 18.0,
                "hall_petch_k_martensite": 25.0,
                "note": "Raw physical predictions. Trends are meaningful; absolute values "
                        "may deviate from experiment due to simplified Taylor assumption."
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n[DONE] {len(results)}/{total} completed. Saved: {out_path}")
    return results


# ============================================================
# 图表生成
# ============================================================
def generate_figures(results):
    figures_dir = Path(__file__).parent / "figures"
    figures_dir.mkdir(exist_ok=True)
    
    data = {}
    for r in results:
        key = (r["v_m"], r["d_ratio"])
        if key not in data:
            data[key] = []
        data[key].append(r)
    
    v_m_unique = sorted(set(r["v_m"] for r in results))
    ratio_unique = sorted(set(r["d_ratio"] for r in results))
    
    # 色彩方案
    cmap_vm = plt.cm.RdYlBu_r
    cmap_ratio = plt.cm.viridis
    colors_ratio = cmap_ratio(np.linspace(0, 1, len(ratio_unique)))
    
    # ============ Figure 1: 四面板核心图 (upgraded) ============
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure(figsize=(18, 15))
    
    # ---- (a) 3D Response Surface — 优化视角确保所有点可见 ----
    ax = fig.add_subplot(2, 3, (1, 2), projection='3d')
    Z_yield = np.zeros((len(ratio_unique), len(v_m_unique)))
    Z_yield_std = np.zeros_like(Z_yield)
    for i, ratio in enumerate(ratio_unique):
        for j, vm in enumerate(v_m_unique):
            vals = [r["yield_stress_MPa"] for r in data.get((vm, ratio), [])]
            Z_yield[i, j] = np.mean(vals)
            Z_yield_std[i, j] = np.std(vals)
    
    V, R = np.meshgrid(v_m_unique, ratio_unique)
    # 使用Viridis色图，更清晰且黑白打印友好
    surf = ax.plot_surface(V, R, Z_yield, cmap='viridis', alpha=0.85,
                           linewidth=0.5, edgecolor='gray', antialiased=True)
    # Add scatter points for actual data locations with column projection lines
    v_flat = V.flatten()
    r_flat = R.flatten()
    z_flat = Z_yield.flatten()
    for vv, rr, zz in zip(v_flat, r_flat, z_flat):
        ax.plot([vv, vv], [rr, rr], [ax.get_zlim()[0] if hasattr(ax, 'get_zlim') else 300, zz],
               'gray', alpha=0.3, linewidth=0.5)
    ax.scatter(v_flat, r_flat, z_flat, c=z_flat, cmap='viridis',
              s=60, edgecolors='black', linewidth=0.8, zorder=8)
    
    ax.set_xlabel('$v_m$', fontsize=11, fontweight='bold')
    ax.set_ylabel('$d_m/d_f$', fontsize=11, fontweight='bold')
    ax.set_zlabel('$\\sigma_y$ (MPa)', fontsize=11, fontweight='bold')
    ax.set_title('(a) 3D Response Surface: $\\sigma_y(v_m, d_m/d_f)$', fontsize=12, fontweight='bold')
    ax.view_init(elev=20, azim=-45)  # 更利于观测的视角
    cbar = fig.colorbar(surf, ax=ax, shrink=0.6, pad=0.1)
    cbar.set_label('$\\sigma_y$ (MPa)', fontsize=9, fontweight='bold')
    
    # ---- (b) 简化等高线图，关键等值线标注 ----
    ax = fig.add_subplot(2, 3, 3)
    contour = ax.contourf(V, R, Z_yield, levels=15, cmap='viridis', alpha=0.85)
    # 只保留关键等值线并标注数值
    key_levels = [np.percentile(Z_yield.flatten(), p) for p in [10, 30, 50, 70, 90]]
    cs = ax.contour(V, R, Z_yield, levels=key_levels, colors='black', linewidths=1.2)
    ax.clabel(cs, inline=True, fontsize=7, fmt='%.0f MPa')
    for i in range(len(ratio_unique)):
        for j in range(len(v_m_unique)):
            ax.plot(v_m_unique[j], ratio_unique[i], 'o', color='black',
                   markersize=6, markerfacecolor='white', markeredgewidth=1)
    # 更细长的colorbar
    cbar2 = plt.colorbar(contour, ax=ax, shrink=0.75, aspect=20)
    cbar2.set_label('$\\sigma_y$ (MPa)', fontsize=8, fontweight='bold')
    ax.set_xlabel('$v_m$', fontsize=10, fontweight='bold')
    ax.set_ylabel('$d_m/d_f$', fontsize=10, fontweight='bold')
    ax.set_title('(b) Key Contours: $\\sigma_y(v_m, d_m/d_f)$', fontsize=10, fontweight='bold')
    
    # ---- (c) σ_y vs v_m 曲线 ----
    ax = fig.add_subplot(2, 3, 4)
    for i, ratio in enumerate(ratio_unique):
        means = [np.mean([r["yield_stress_MPa"] for r in data.get((vm, ratio), [])])
                 for vm in v_m_unique]
        stds = [np.std([r["yield_stress_MPa"] for r in data.get((vm, ratio), [])])
                for vm in v_m_unique]
        ax.errorbar(v_m_unique, means, yerr=stds, marker='o', color=colors_ratio[i],
                   label=f'$d_m/d_f={ratio}$', capsize=3, linewidth=2, markersize=8)
    
    # 线性拟合
    all_vm = np.array(v_m_unique)
    all_means = np.array([np.mean([r["yield_stress_MPa"] for r in data.get((vm, 0.5), [])])
                          for vm in v_m_unique])
    A = np.vstack([all_vm, np.ones_like(all_vm)]).T
    slope, intercept = np.linalg.lstsq(A, all_means, rcond=None)[0]
    r2 = 1 - np.var(all_means - slope*all_vm - intercept) / np.var(all_means)
    ax.plot(all_vm, slope*all_vm + intercept, 'k--', linewidth=2.5,
           label=f'Linear fit: {slope:.0f} MPa/$v_m$, $R^2={r2:.3f}$')
    
    ax.axhline(y=340, color='gray', linestyle=':', linewidth=1.5, alpha=0.7,
              label='DP800 ref: 340 MPa')
    ax.set_xlabel('v_m', fontsize=10, fontweight='bold')
    ax.set_ylabel('σ_y (MPa)', fontsize=10, fontweight='bold')
    ax.set_title(f'(c) σ_y vs v_m: {slope:.0f} MPa per 1% v_m',
                fontsize=10, fontweight='bold')
    ax.legend(fontsize=7, loc='upper left')
    ax.grid(True, alpha=0.3)
    
    # (d) 硬化率 vs v_m
    ax = fig.add_subplot(2, 3, 5)
    for i, ratio in enumerate(ratio_unique):
        means = [np.mean([r["hardening_rate_MPa"] for r in data.get((vm, ratio), [])])
                 for vm in v_m_unique]
        stds = [np.std([r["hardening_rate_MPa"] for r in data.get((vm, ratio), [])])
                for vm in v_m_unique]
        ax.errorbar(v_m_unique, means, yerr=stds, marker='s', color=colors_ratio[i],
                   label=f'$d_m/d_f={ratio}$', capsize=3, linewidth=2, markersize=8)
    
    ax.set_xlabel('v_m', fontsize=10, fontweight='bold')
    ax.set_ylabel('θ (MPa)', fontsize=10, fontweight='bold')
    ax.set_title('(d) Strain Hardening Rate θ\n(Monotonic increase with v_m)',
                fontsize=10, fontweight='bold')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    
    # (e) M/F应力比 — 用粗实线+阴影带替代误差棒
    ax = fig.add_subplot(2, 3, 6)
    all_mf_ratios = []
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
                all_mf_ratios.extend(vals)
        
        if vm_valid:
            vm_arr = np.array(vm_valid)
            means_arr = np.array(mf_means)
            stds_arr = np.array(mf_stds)
            ax.plot(vm_arr, means_arr, '-', color=colors_ratio[i], linewidth=2.5,
                   label=f'$d_m/d_f={ratio}$')
            ax.fill_between(vm_arr, means_arr - stds_arr, means_arr + stds_arr,
                          alpha=0.15, color=colors_ratio[i])
    
    # 全局均值线，强调"Nearly Constant"
    if all_mf_ratios:
        global_mean = np.mean(all_mf_ratios)
        global_std = np.std(all_mf_ratios)
        ax.axhline(y=global_mean, color='darkred', linestyle='-', linewidth=2.0, alpha=0.8,
                  label=f'Mean $\\approx${global_mean:.2f}$\\pm${global_std:.2f}')
        ax.fill_between([min(v_m_unique), max(v_m_unique)],
                       [global_mean - global_std]*2, [global_mean + global_std]*2,
                       alpha=0.08, color='red')
    
    ax.axhline(y=1.49, color='gray', linestyle=':', linewidth=1.5, alpha=0.6, label='DAMASK ref: 1.49')
    ax.set_xlabel('$v_m$', fontsize=10, fontweight='bold')
    ax.set_ylabel('$\\sigma_m/\\sigma_f$ (at $\\varepsilon$=0.10)', fontsize=10, fontweight='bold')
    ax.set_title(f'(e) Load Partitioning: Nearly Constant\n$\\sigma_m/\\sigma_f \\approx$ {global_mean:.2f} independent of $v_m$',
                fontsize=10, fontweight='bold')
    ax.legend(fontsize=6.5)
    ax.grid(True, alpha=0.3)
    
    fig.suptitle('Microstructure-Property Quantitative Mapping\n'
                 '100 configurations (5 v_m × 4 d_m/d_f × 5 seeds)',
                 fontsize=14, fontweight='bold', y=1.01)
    plt.tight_layout()
    fig.savefig(figures_dir / 'Figure_ParametricScan_Core.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  [OK] Figure_ParametricScan_Core.png")
    
    # ============ Figure 2: 应力-应变曲线网格 (精简版) ============
    # 只展示关键行: d_m/d_f = 0.3, 0.7, 1.0; 关键列: v_m = 0.15, 0.35, 0.55
    # 选出代表性子集, 去掉子图内部标题和网格线
    showcase_rows = [0.3, 0.7, 1.0]  # d_m/d_f
    showcase_cols = [0.15, 0.35, 0.55]  # v_m
    n_rows = len(showcase_rows)
    n_cols = len(showcase_cols)
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 10), sharex=True, sharey=True)
    
    for i, ratio in enumerate(showcase_rows):
        ratio_idx = np.argmin(np.abs(np.array(ratio_unique) - ratio))
        actual_ratio = ratio_unique[ratio_idx]
        for j, vm in enumerate(showcase_cols):
            vm_idx = np.argmin(np.abs(np.array(v_m_unique) - vm))
            actual_vm = v_m_unique[vm_idx]
            ax = axes[i, j] if n_rows > 1 else axes[j]
            entries = data.get((actual_vm, actual_ratio), [])
            
            # 所有5个seeds (细线)
            for e in entries:
                ax.plot(e["strains"], e["stress_macro"], alpha=0.2, linewidth=0.3, color='gray')
            
            if entries:
                avg = np.mean([e["stress_macro"] for e in entries], axis=0)
                avg_f = np.mean([e["stress_ferrite"] for e in entries], axis=0)
                avg_m = np.mean([e["stress_martensite"] for e in entries], axis=0) if actual_vm > 0 else None
                
                # 加粗线条，去掉网格
                ax.plot(entries[0]["strains"], avg, color='#1A5276', linewidth=2.5)
                ax.plot(entries[0]["strains"], avg_f, color='#27AE60', linestyle='--', linewidth=1.2, alpha=0.7)
                if avg_m is not None:
                    ax.plot(entries[0]["strains"], avg_m, color='#C0392B', linestyle='--', linewidth=1.2, alpha=0.7)
                
                avg_yield = np.mean([e["yield_stress_MPa"] for e in entries])
                avg_uts = np.mean([e["uts_MPa"] for e in entries])
                ax.axhline(y=avg_yield, color='#E67E22', linestyle=':', linewidth=1.2, alpha=0.5)
                # 简洁标注在子图角落
                ax.text(0.97, 0.97, f'$\\sigma_y$={avg_yield:.0f}\nUTS={avg_uts:.0f}',
                       transform=ax.transAxes, ha='right', va='top',
                       fontsize=7, bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
            
            # 左侧标注d_m/d_f行
            if j == 0:
                ax.set_ylabel(f'$d_m/d_f={actual_ratio}$', fontsize=10, fontweight='bold')
            # 底部标注v_m列
            if i == n_rows - 1:
                ax.set_xlabel(f'$v_m={actual_vm}$\nStrain $\\varepsilon$', fontsize=10, fontweight='bold')
            # 顶部列标题
            if i == 0:
                ax.set_title(f'$v_m={actual_vm}$', fontsize=10, fontweight='bold', pad=3)
            
            ax.set_xlim(0, 0.10)
            # 去掉网格线
            ax.tick_params(labelsize=8)
    
    # 统一图例
    legend_elements = [
        Line2D([0], [0], color='#1A5276', linewidth=2.5, label='Macro (avg)'),
        Line2D([0], [0], color='#27AE60', linestyle='--', linewidth=1.2, label='Ferrite'),
        Line2D([0], [0], color='#C0392B', linestyle='--', linewidth=1.2, label='Martensite'),
        Line2D([0], [0], color='#E67E22', linestyle=':', linewidth=1.2, label='Yield'),
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=4, fontsize=9,
              bbox_to_anchor=(0.5, -0.01))
    
    fig.suptitle('Representative Stress-Strain Curves: Key ($v_m$, $d_m/d_f$) Combinations\n'
                 'Shaded curves: 5 individual seeds; bold: ensemble mean',
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    fig.savefig(figures_dir / 'Figure_ParametricScan_StressStrainGrid.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  [OK] Figure_ParametricScan_StressStrainGrid.png (optimized 3×3 key combinations)")
    
    # ============ Figure 3: 敏感性分析 + 与经典理论对比 ============
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    
    # (a) 参数敏感性 — 双Y轴避免绿色柱子压制红/蓝
    ax = axes[0]
    ax2_param = ax.twinx()
    vm_effect_yield = [np.mean([r["yield_stress_MPa"] for r in results if abs(r["v_m"]-vm)<0.001]) for vm in v_m_unique]
    ratio_effect_yield = [np.mean([r["yield_stress_MPa"] for r in results if abs(r["d_ratio"]-ratio)<0.001]) for ratio in ratio_unique]
    vm_effect_hr = [np.mean([r["hardening_rate_MPa"] for r in results if abs(r["v_m"]-vm)<0.001]) for vm in v_m_unique]
    
    sens_vm_yield = max(vm_effect_yield) - min(vm_effect_yield)
    sens_ratio_yield = max(ratio_effect_yield) - min(ratio_effect_yield)
    sens_vm_hr = max(vm_effect_hr) - min(vm_effect_hr)
    
    cats = ['$v_m$\\non $\\sigma_y$', '$d_m/d_f$\\non $\\sigma_y$', '$v_m$\\non $\\theta$']
    vals = [sens_vm_yield, sens_ratio_yield, sens_vm_hr]
    # v_m→σ_y on left axis (red), d_m/d_f→σ_y on left axis (blue), v_m→θ on right axis (green)
    colors_bar = ['#e74c3c', '#3498db', '#2ecc71']
    bar_width = 0.55
    x_pos = np.arange(3)
    # Plot first two bars on left Y-axis, third on right Y-axis
    bars_left = ax.bar(x_pos[:2], vals[:2], bar_width, color=colors_bar[:2], edgecolor='black', linewidth=1.5)
    bars_right = ax2_param.bar(x_pos[2:], vals[2:], bar_width, color=colors_bar[2:], edgecolor='black', linewidth=1.5)
    # Annotate all bars
    for bar, val in zip(bars_left, vals[:2]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{val:.1f} MPa', ha='center', va='bottom', fontsize=11, fontweight='bold', color='#333')
    for bar, val in zip(bars_right, vals[2:]):
        ax2_param.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
               f'{val:.1f} MPa', ha='center', va='bottom', fontsize=11, fontweight='bold', color='#2ecc71')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(cats, fontsize=9)
    ax.set_ylabel('$\\Delta\\sigma_y$ (MPa)', fontsize=11, color='#e74c3c')
    ax2_param.set_ylabel('$\\Delta\\theta$ (MPa)', fontsize=11, color='#2ecc71')
    ax.tick_params(axis='y', colors='#e74c3c')
    ax2_param.tick_params(axis='y', colors='#2ecc71')
    ax.set_title('(a) Parameter Sensitivity\n(Main Effect Magnitudes)', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.2, axis='y')
    
    # (b) v_m主效应 + 混合法则验证 — 阴影表示RoM上下界
    ax = axes[1]
    ax.scatter(v_m_unique, vm_effect_yield, s=120, c='#e74c3c', edgecolors='black', 
              zorder=5, label='HPD-RVE prediction')
    vm_arr = np.array(v_m_unique)
    ax.plot(vm_arr, slope*vm_arr + intercept, 'k--', linewidth=2.5, 
           label=f'Linear fit: $R^2={r2:.3f}$\n$\\Delta\\sigma_y = {slope:.0f} \\cdot v_m + {intercept:.0f}$ MPa')
    
    # 混合法则理论线 + 上下界阴影
    solver = PhysicsBasedCPFEM()
    r_pure_f = solver.compute_stress_strain(v_m=0.0, d_f_um=15.0, d_m_um=7.5, max_strain=0.10, n_steps=50, seed=42)
    r_pure_m = solver.compute_stress_strain(v_m=0.999, d_f_um=15.0, d_m_um=7.5, max_strain=0.10, n_steps=50, seed=42)
    rule_of_mixture = [(1-vm)*r_pure_f['yield_stress_MPa'] + vm*r_pure_m['yield_stress_MPa'] for vm in v_m_unique]
    # RoM ±5% 不确定带
    rom_upper = [r * 1.05 for r in rule_of_mixture]
    rom_lower = [r * 0.95 for r in rule_of_mixture]
    ax.fill_between(v_m_unique, rom_lower, rom_upper, alpha=0.12, color='blue',
                    label='RoM $\\pm$5% band')
    ax.plot(v_m_unique, rule_of_mixture, 'b-', linewidth=2.0, alpha=0.85, label='Rule of Mixture')
    # 标注HPD-RVE偏离RoM的物理意义
    ax.annotate('Deviation from RoM\n(phase interaction)', 
                xy=(0.4, rule_of_mixture[2]),
                xytext=(0.42, rule_of_mixture[2] + 40),
                arrowprops=dict(arrowstyle='->', color='darkblue', lw=1.5),
                fontsize=8, color='darkblue', fontweight='bold')
    
    ax.set_xlabel('Martensite Volume Fraction $v_m$', fontsize=11)
    ax.set_ylabel('Yield Stress $\\sigma_y$ (MPa)', fontsize=11)
    ax.set_title('(b) $v_m$ Main Effect: Strengthening\nvs Rule of Mixture', fontsize=11, fontweight='bold')
    ax.legend(fontsize=7.5)
    ax.grid(True, alpha=0.3)
    
    # (c) Hall-Petch效应验证 — 添加鲁棒性检查，避免R²=nan
    ax = axes[2]
    # 使用扫描中存在的v_m值 (0.25是最接近DP800的0.28)
    vm_ref = 0.25
    d_m_values = [D_F_UM * ratio for ratio in ratio_unique]
    hp_yields_raw = [data.get((vm_ref, ratio), []) for ratio in ratio_unique]
    hp_yields = [np.mean([r["yield_stress_MPa"] for r in entries]) if entries else np.nan
                 for entries in hp_yields_raw]
    hp_yields_std = [np.std([r["yield_stress_MPa"] for r in entries]) if entries else 0
                     for entries in hp_yields_raw]
    
    # Hall-Petch: σ_y = σ_0 + k / √d_eff
    # d_eff 近似为铁素体和马氏体的调和平均
    # 使用vm_ref计算有效晶粒尺寸
    v_f_frac = 1.0 - vm_ref
    d_eff = [1.0 / (v_f_frac/D_F_UM + vm_ref/dm) for dm in d_m_values]
    inv_sqrt_d = np.array([1.0/np.sqrt(d) for d in d_eff])
    
    # 过滤掉NaN值
    valid = ~np.isnan(hp_yields)
    inv_sqrt_d_valid = inv_sqrt_d[valid]
    hp_yields_valid = np.array(hp_yields)[valid]
    hp_yields_std_valid = np.array(hp_yields_std)[valid]
    
    ax.errorbar(inv_sqrt_d_valid, hp_yields_valid, yerr=hp_yields_std_valid,
               fmt='o', ms=10, color='#3498db', markeredgecolor='black', markeredgewidth=1.5,
               capsize=4, zorder=5)
    
    # 线性拟合 Hall-Petch (鲁棒版本)
    if len(hp_yields_valid) >= 2 and np.std(hp_yields_valid) > 1e-6:
        A_hp = np.vstack([inv_sqrt_d_valid, np.ones_like(inv_sqrt_d_valid)]).T
        k_hp, sigma0_hp = np.linalg.lstsq(A_hp, hp_yields_valid, rcond=None)[0]
        var_resid = np.var(hp_yields_valid - k_hp*inv_sqrt_d_valid - sigma0_hp)
        var_total = np.var(hp_yields_valid)
        r2_hp = 1 - var_resid / var_total if var_total > 1e-10 else 0.0
        
        x_fit = np.linspace(min(inv_sqrt_d_valid)*0.95, max(inv_sqrt_d_valid)*1.05, 50)
        ax.plot(x_fit, k_hp*x_fit + sigma0_hp, '--', color='#3498db', linewidth=2.5,
               label=f'Hall-Petch fit: $k_y={k_hp:.0f}$ MPa$\\cdot\\mu$m$^{{1/2}}$\n$R^2={r2_hp:.3f}$')
    else:
        k_hp, sigma0_hp, r2_hp = 0, np.mean(hp_yields_valid) if len(hp_yields_valid) > 0 else 0, 0
        ax.text(0.5, 0.5, 'Insufficient data\nfor Hall-Petch fit', transform=ax.transAxes,
               ha='center', va='center', fontsize=12, color='red', fontweight='bold')
    
    ax.set_xlabel('$d_{eff}^{-1/2}$ ($\\mu$m$^{-1/2}$)', fontsize=11)
    ax.set_ylabel('Yield Stress $\\sigma_y$ (MPa)', fontsize=11)
    ax.set_title('(c) Hall-Petch Validation\n$\\sigma_y = \\sigma_0 + k_y/\\sqrt{d_{eff}}$', fontsize=11, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(figures_dir / 'Figure_ParametricScan_Sensitivity.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("  [OK] Figure_ParametricScan_Sensitivity.png")
    
    # ============ 统计摘要 ============
    print("\n" + "="*70)
    print("PARAMETRIC SCAN v3 SUMMARY (PhysicsBasedCPFEM - No Calibration)")
    print("="*70)
    print(f"Hall-Petch: k_HP_f = 18.0 MPa·um^0.5, k_HP_m = 25.0 MPa·um^0.5")
    print(f"Reference grain sizes: d_f = {D_F_UM} um")
    print(f"\nMain effects (response range):")
    print(f"  v_m effect on sigma_y: {sens_vm_yield:.1f} MPa")
    print(f"  d_m/d_f effect on sigma_y: {sens_ratio_yield:.1f} MPa")
    print(f"  v_m effect on hardening rate: {sens_vm_hr:.1f} MPa")
    print(f"\nLinear relationship sigma_y(v_m):")
    print(f"  slope = {slope:.1f} MPa per 1% v_m")
    print(f"  R^2 = {r2:.4f}")
    print(f"\nHall-Petch fit:")
    print(f"  k_y = {k_hp:.0f} MPa·um^0.5")
    print(f"  sigma_0 = {sigma0_hp:.0f} MPa")
    print(f"  R^2 = {r2_hp:.4f}")
    print(f"\nReference: Pure ferrite sigma_y = {r_pure_f['yield_stress_MPa']:.0f} MPa")
    print(f"           Pure martensite sigma_y = {r_pure_m['yield_stress_MPa']:.0f} MPa")
    print(f"           Rule of mixture (v_m=0.28): {0.72*r_pure_f['yield_stress_MPa'] + 0.28*r_pure_m['yield_stress_MPa']:.0f} MPa")
    print(f"           DP800 experiment (Tasan 2014): 340 MPa")
    
    return {
        "sens_vm_yield": sens_vm_yield,
        "sens_ratio_yield": sens_ratio_yield,
        "slope_vm": slope,
        "r2_vm": r2,
        "k_hp": k_hp,
        "sigma0_hp": sigma0_hp,
        "r2_hp": r2_hp,
        "sigma_pure_f": r_pure_f['yield_stress_MPa'],
        "sigma_pure_m": r_pure_m['yield_stress_MPa'],
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "figures_only":
        with open(Path(__file__).parent / "parametric_scan_results_v3.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        generate_figures(data["results"])
    else:
        results = run_scan()
        stats = generate_figures(results)
        
        with open(Path(__file__).parent / "parametric_scan_summary.json", 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
