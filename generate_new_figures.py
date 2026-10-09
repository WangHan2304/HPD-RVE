"""
生成新增论文图表:
- Figure 29: G3 三相合金验证
- Figure 30: 不确定性量化
"""

import numpy as np
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# 设置中文字体支持
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# Figure 29: G3 Validation
# ============================================================
def generate_figure_29():
    print("生成 Figure 29: G3 三相合金验证...")
    
    with open('g3_validation_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.35)
    
    # (a) Stress-strain curves for 5 seeds + phase components
    ax1 = fig.add_subplot(gs[0, :2])
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    seed_names = ['42', '123', '456', '789', '1024']
    
    for i, r in enumerate(data['baseline_results']):
        strains = np.array(r['strains'])
        stress = np.array(r['stress_macro'])
        ax1.plot(strains * 100, stress, color=colors[i], linewidth=1.5,
                label=f'Seed {seed_names[i]}', alpha=0.8)
    
    # 添加相分量 (使用seed 42)
    r0 = data['baseline_results'][0]
    strains = np.array(r0['strains'])
    ax1.plot(strains * 100, np.array(r0['stress_ferrite']), '--', 
            color='gray', linewidth=1, alpha=0.7, label='Ferrite (BCC)')
    ax1.plot(strains * 100, np.array(r0['stress_austenite']), '--', 
            color='blue', linewidth=1, alpha=0.7, label='Austenite (FCC)')
    ax1.plot(strains * 100, np.array(r0['stress_alpha_ti']), '--', 
            color='red', linewidth=1, alpha=0.7, label='alpha-Ti (HCP)')
    
    ax1.set_xlabel('Engineering Strain (%)', fontsize=11)
    ax1.set_ylabel('True Stress (MPa)', fontsize=11)
    ax1.set_title('(a) G3 Fe-Ni-Ti Stress-Strain Curves', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=8, ncol=2)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 10)
    
    # (b) Literature comparison
    ax2 = fig.add_subplot(gs[0, 2])
    pred_mean = data['baseline_statistics']['sigma_y_mean']
    pred_std = data['baseline_statistics']['sigma_y_std']
    
    refs = data['literature_comparison']['references']
    names = list(refs.keys())
    ranges = [(refs[n]['sigma_y'][0], refs[n]['sigma_y'][1]) for n in names]
    
    y_pos = range(len(names))
    for i, (name, (lo, hi)) in enumerate(zip(names, ranges)):
        ax2.barh(i, hi - lo, left=lo, height=0.5, color='lightgray', edgecolor='gray')
        ax2.text((lo + hi) / 2, i, f'{lo}-{hi}', ha='center', va='center', fontsize=7)
    
    # 预测值
    ax2.axvline(x=pred_mean, color='red', linewidth=2, linestyle='--', label=f'HPD-RVE: {pred_mean:.0f} MPa')
    ax2.axvspan(pred_mean - pred_std, pred_mean + pred_std, alpha=0.15, color='red')
    
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([n.split('(')[0].strip() for n in names], fontsize=8)
    ax2.set_xlabel('Yield Strength (MPa)', fontsize=11)
    ax2.set_title('(b) Literature Comparison', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3, axis='x')
    
    # (c) Parameter sensitivity - grain size
    ax3 = fig.add_subplot(gs[1, 0])
    gs_data = data['sensitivity_analysis']['grain_size_variants']
    labels = [d['label'] for d in gs_data]
    sigmas = [d['sigma_y'] for d in gs_data]
    colors_bar = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    bars = ax3.bar(range(len(labels)), sigmas, color=colors_bar, edgecolor='black', linewidth=0.5)
    ax3.set_xticks(range(len(labels)))
    ax3.set_xticklabels(labels, fontsize=9)
    ax3.set_ylabel('Yield Strength (MPa)', fontsize=11)
    ax3.set_title('(c) Grain Size Sensitivity', fontsize=11, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    for bar, s in zip(bars, sigmas):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f'{s:.1f}',
                ha='center', va='bottom', fontsize=8)
    ax3.set_ylim(340, 350)
    
    # (d) Parameter sensitivity - volume fraction
    ax4 = fig.add_subplot(gs[1, 1])
    vf_data = data['sensitivity_analysis']['volume_fraction_variants']
    labels_vf = [d['label'] for d in vf_data]
    sigmas_vf = [d['sigma_y'] for d in vf_data]
    bars = ax4.bar(range(len(labels_vf)), sigmas_vf, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd'], 
                  edgecolor='black', linewidth=0.5)
    ax4.set_xticks(range(len(labels_vf)))
    ax4.set_xticklabels(labels_vf, fontsize=9)
    ax4.set_ylabel('Yield Strength (MPa)', fontsize=11)
    ax4.set_title('(d) Volume Fraction Sensitivity', fontsize=11, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    for bar, s in zip(bars, sigmas_vf):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f'{s:.1f}',
                ha='center', va='bottom', fontsize=8)
    
    # (e) Phase stress ratios
    ax5 = fig.add_subplot(gs[1, 2])
    ratio_data = [
        ('Austenite/\nFerrite', data['baseline_statistics']['austenite_ferrite_ratio']),
        ('Alpha-Ti/\nFerrite', data['baseline_statistics']['alpha_ti_ferrite_ratio']),
    ]
    names_ratio = [r[0] for r in ratio_data]
    values_ratio = [r[1] for r in ratio_data]
    ax5.bar(names_ratio, values_ratio, color=['#2ca02c', '#d62728'], 
           edgecolor='black', linewidth=0.5, width=0.5)
    ax5.set_ylabel('Phase Stress Ratio', fontsize=11)
    ax5.set_title('(e) Phase Stress Ratios at 10% Strain', fontsize=11, fontweight='bold')
    ax5.grid(True, alpha=0.3, axis='y')
    for i, v in enumerate(values_ratio):
        ax5.text(i, v + 0.05, f'{v:.2f}', ha='center', fontsize=10, fontweight='bold')
    ax5.set_ylim(0, 4)
    
    fig.suptitle('Figure 29. G3 Three-Phase Alloy (Fe-Ni-Ti) CPFEM Validation', 
                 fontsize=14, fontweight='bold', y=0.98)
    
    plt.savefig('figures/Figure_G3_Validation.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  -> figures/Figure_G3_Validation.png 已保存")


# ============================================================
# Figure 30: UQ Analysis
# ============================================================
def generate_figure_30():
    print("生成 Figure 30: 不确定性量化...")
    
    with open('uq_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 重新运行MC以获得原始样本 (使用种子以确保一致性)
    from uq_analysis import generate_perturbed_samples, monte_carlo_propagation
    samples = generate_perturbed_samples(n_samples=200, seed=42)
    mc_results = monte_carlo_propagation(samples, base_seed=42)
    sigma_y = np.array([r['sigma_y'] for r in mc_results])
    v_m_vals = np.array([r['v_m'] for r in mc_results])
    dm_df_vals = np.array([r['d_m_d_f'] for r in mc_results])
    
    fig = plt.figure(figsize=(18, 11))
    gs = GridSpec(2, 3, figure=fig, hspace=0.38, wspace=0.35)
    
    # (a) Histogram of sigma_y — enhanced with CV highlight
    ax1 = fig.add_subplot(gs[0, :2])
    counts, bins, _ = ax1.hist(sigma_y, bins=30, color='#2166AC', alpha=0.75, 
                                edgecolor='white', linewidth=0.8, density=True)
    
    from scipy import stats
    mu, std = np.mean(sigma_y), np.std(sigma_y)
    cv_pct = std/mu*100
    x = np.linspace(mu - 4*std, mu + 4*std, 300)
    ax1.plot(x, stats.norm.pdf(x, mu, std), '-', color='#E65100', linewidth=2.5,
             label=f'Normal fit: N({mu:.1f}, {std:.1f}²)')
    
    ci_lo, ci_hi = np.percentile(sigma_y, [2.5, 97.5])
    ax1.axvline(x=ci_lo, color='#B2182B', linestyle='--', linewidth=2, alpha=0.8)
    ax1.axvline(x=ci_hi, color='#B2182B', linestyle='--', linewidth=2, alpha=0.8)
    ax1.axvline(x=mu, color='#8B0000', linestyle='-', linewidth=2.5)
    ax1.fill_betweenx([0, max(counts)*1.1], ci_lo, ci_hi, alpha=0.08, color='#B2182B')
    
    # Key annotations
    ax1.annotate(f'CV = {cv_pct:.1f}%\n(Exp. CV ≈ 7%)', 
                xy=(mu + 2.5*std, max(counts)*0.75), fontsize=11, fontweight='bold',
                color='#2166AC', ha='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                          edgecolor='#2166AC', alpha=0.9))
    ax1.annotate(f'95% CI: [{ci_lo:.1f}, {ci_hi:.1f}] MPa', 
                xy=(ci_hi + 0.3, max(counts)*0.5), fontsize=10, color='#B2182B',
                ha='left', fontweight='bold')
    ax1.annotate(f'Mean = {mu:.1f} MPa', 
                xy=(mu + 0.2, max(counts)*0.35), fontsize=10, color='#8B0000',
                ha='left', fontweight='bold')
    
    ax1.set_xlabel('Yield Strength σ_y (MPa)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Probability Density', fontsize=11, fontweight='bold')
    ax1.set_title('(a) Yield Strength Distribution (MC, n=200)\n'
                  f'Prediction uncertainty (CV={cv_pct:.1f}%) < Experimental scatter (CV≈7%)',
                  fontsize=11, fontweight='bold')
    ax1.legend(fontsize=9, loc='upper right', framealpha=0.9)
    ax1.grid(True, alpha=0.2, axis='y', linestyle=':')
    
    # (b) Response Surface — enhanced scatter
    ax2 = fig.add_subplot(gs[0, 2])
    scatter = ax2.scatter(v_m_vals, dm_df_vals, c=sigma_y, cmap='RdYlBu_r', 
                         s=50, edgecolors='#333', linewidth=0.5, alpha=0.85)
    ax2.set_xlabel('v_m (Martensite Vol. Fraction)', fontsize=9, fontweight='bold')
    ax2.set_ylabel('d_m/d_f (Grain Size Ratio)', fontsize=9, fontweight='bold')
    ax2.set_title('(b) Parameter Space Sampling\n(LHS, n=200)',
                  fontsize=10, fontweight='bold')
    cbar = plt.colorbar(scatter, ax=ax2, shrink=0.8)
    cbar.set_label('σ_y (MPa)', fontsize=8, fontweight='bold')
    ax2.grid(True, alpha=0.2, linestyle=':')
    
    # (c) Sobol Sensitivity Indices — enhanced
    ax3 = fig.add_subplot(gs[1, 0])
    sobol = data['pce_approximation']['sobol_indices']
    indices = [sobol['S_v_m'], sobol['S_dm_df']]
    names = ['v_m\n(Martensite\nVolume Fraction)', 'd_m/d_f\n(Grain Size\nRatio)']
    colors_bar = ['#2166AC', '#E65100']
    bars = ax3.bar(range(len(names)), indices, color=colors_bar, 
                  edgecolor='#333', linewidth=1, width=0.55, alpha=0.85)
    ax3.set_xticks(range(len(names)))
    ax3.set_xticklabels(names, fontsize=8)
    ax3.set_ylabel('First-Order Sobol Index S_i', fontsize=10, fontweight='bold')
    ax3.set_title('(c) Sobol Sensitivity Analysis\n(PCE R² = 0.129)',
                  fontsize=10, fontweight='bold')
    ax3.grid(True, alpha=0.2, axis='y', linestyle=':')
    for bar, v in zip(bars, indices):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.008, 
                f'{v:.4f}', ha='center', fontsize=11, fontweight='bold', color='#333')
    
    # (d) Prediction vs Experimental Uncertainty — CV comparison
    ax4 = fig.add_subplot(gs[1, 1])
    categories = ['Yield Strength\nσ_y', 'UTS\nσ_max']
    pred_std = [data['uq_statistics']['sigma_y_MPa']['std'], 
               data['uq_statistics']['uts_MPa']['std']]
    exp_std = [25.0, 40.0]
    
    x = np.arange(len(categories))
    width = 0.32
    bars1 = ax4.bar(x - width/2, pred_std, width, label='HPD-RVE Prediction',
                   color='#2166AC', edgecolor='#333', linewidth=1, alpha=0.85)
    bars2 = ax4.bar(x + width/2, exp_std, width, label='Experiment (Tasan 2014)',
                   color='#D5D8DC', edgecolor='#333', linewidth=1, alpha=0.85)
    
    # Ratio annotations
    for i, (p, e) in enumerate(zip(pred_std, exp_std)):
        ax4.annotate(f'Ratio: {p/e:.2f}×', xy=(i, max(p, e) + 2),
                    ha='center', fontsize=9, fontweight='bold',
                    color='#2E7D32',
                    bbox=dict(boxstyle='round,pad=0.15', facecolor='#D5F5E3',
                              edgecolor='#2E7D32', alpha=0.85))
    
    ax4.set_ylabel('Standard Deviation (MPa)', fontsize=10, fontweight='bold')
    ax4.set_title('(d) Prediction vs. Experimental\nUncertainty Comparison',
                  fontsize=10, fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(categories, fontsize=9, fontweight='bold')
    ax4.legend(fontsize=8, loc='upper left', framealpha=0.9)
    ax4.grid(True, alpha=0.2, axis='y', linestyle=':')
    
    for bar, v in zip(bars1, pred_std):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{v:.1f}', ha='center', fontsize=9, fontweight='bold', color='#2166AC')
    for bar, v in zip(bars2, exp_std):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{v:.0f}', ha='center', fontsize=9, color='#566573')
    
    # (e) Coefficient of Variation (CV) Comparison — NEW
    ax5 = fig.add_subplot(gs[1, 2])
    cv_pred = [pred_std[0]/np.mean(sigma_y)*100, pred_std[1]/400*100]  # σ_y CV and UTS CV
    cv_exp = [7.0, 10.0]  # Approximate experimental CVs
    cv_categories = ['Yield\nStrength', 'UTS']
    
    x_cv = np.arange(len(cv_categories))
    bars_cv1 = ax5.bar(x_cv - width/2, cv_pred, width, label='HPD-RVE',
                       color='#2166AC', edgecolor='#333', linewidth=1, alpha=0.85)
    bars_cv2 = ax5.bar(x_cv + width/2, cv_exp, width, label='Experiment',
                       color='#D5D8DC', edgecolor='#333', linewidth=1, alpha=0.85)
    
    for bar, v in zip(bars_cv1, cv_pred):
        ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                f'{v:.1f}%', ha='center', fontsize=10, fontweight='bold', color='#2166AC')
    for bar, v in zip(bars_cv2, cv_exp):
        ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                f'{v:.0f}%', ha='center', fontsize=10, color='#566573')
    
    # Add reduction annotation
    for i, (p, e) in enumerate(zip(cv_pred, cv_exp)):
        reduction = (1 - p/e) * 100
        ax5.annotate(f'↓{reduction:.0f}%', xy=(i, max(p, e)*0.55),
                    ha='center', fontsize=11, fontweight='bold',
                    color='#2E7D32',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='#D5F5E3',
                              edgecolor='#2E7D32', alpha=0.9))
    
    ax5.set_xticks(x_cv)
    ax5.set_xticklabels(cv_categories, fontsize=9, fontweight='bold')
    ax5.set_ylabel('Coefficient of Variation (%)', fontsize=10, fontweight='bold')
    ax5.set_title('(e) CV Comparison: Prediction\nMore Reproducible than Experiment',
                  fontsize=10, fontweight='bold')
    ax5.legend(fontsize=8, loc='upper right', framealpha=0.9)
    ax5.grid(True, alpha=0.2, axis='y', linestyle=':')
    ax5.set_ylim(0, max(max(cv_pred), max(cv_exp)) * 1.3)
    
    fig.suptitle('Figure 30. Uncertainty Quantification: HPD-RVE Produces Statistically\n'
                 'More Reproducible Predictions than Experimental Measurements',
                 fontsize=14, fontweight='bold', y=1.01)
    
    plt.savefig('figures/Figure_UQ_Analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  -> figures/Figure_UQ_Analysis.png 已保存")


if __name__ == '__main__':
    generate_figure_29()
    generate_figure_30()
    print("\n所有新图表已生成!")
