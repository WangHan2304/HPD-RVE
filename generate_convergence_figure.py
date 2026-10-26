#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate N_models convergence figure for the paper.
"""
import numpy as np
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

with open('n_models_convergence_results.json') as f:
    data = json.load(f)

conv = data['convergence']
n_values = sorted([int(k) for k in conv.keys()])
means = [conv[str(n)]['mean'] for n in n_values]
cis = [conv[str(n)]['ci_95_half'] for n in n_values]
ci_pct = [conv[str(n)]['ci_width_pct'] for n in n_values]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw={'width_ratios': [1.2, 1]})

# Left: Mean σ_y with 95% CI error bars
ax1.errorbar(n_values, means, yerr=cis, fmt='o-', color='#2166ac', linewidth=2,
             markersize=8, capsize=5, capthick=1.5, elinewidth=1.5, zorder=5)
# Shade the N≥5 region
ax1.axvspan(5, 10.5, alpha=0.08, color='green', zorder=0)
ax1.annotate('N ≥ 5:\nCI < 0.5%', xy=(7, min(means) - 1), fontsize=9,
             color='green', ha='center', fontweight='bold')
# Reference line at N=10 mean
ax1.axhline(y=means[-1], color='gray', ls='--', lw=0.8, alpha=0.5)
ax1.set_xlabel('Number of RVE realizations (N)', fontsize=11)
ax1.set_ylabel('Mean Yield Stress σ_y (MPa)', fontsize=11)
ax1.set_title('(a) Convergence of mean yield stress', fontsize=11, fontweight='bold')
ax1.set_xticks(n_values)
ax1.xaxis.set_major_locator(MaxNLocator(integer=True))
ax1.grid(True, alpha=0.3)
ax1.set_ylim(min(means) - 4, max(means) + 4)

# Right: CI width % vs N
ax2.plot(n_values, ci_pct, 's-', color='#b2182b', linewidth=2, markersize=8, zorder=5)
ax2.axhline(y=2.0, color='gray', ls='--', lw=1, alpha=0.6, label='2% threshold')
ax2.axvspan(5, 10.5, alpha=0.08, color='green', zorder=0)
ax2.fill_between(n_values, ci_pct, alpha=0.15, color='#b2182b')
ax2.set_xlabel('Number of RVE realizations (N)', fontsize=11)
ax2.set_ylabel('95% CI Width (% of mean)', fontsize=11)
ax2.set_title('(b) Statistical uncertainty vs N', fontsize=11, fontweight='bold')
ax2.set_xticks(n_values)
ax2.xaxis.set_major_locator(MaxNLocator(integer=True))
ax2.legend(fontsize=9, loc='upper right')
ax2.grid(True, alpha=0.3)
ax2.set_ylim(-0.1, max(ci_pct) + 0.5)

plt.tight_layout()
fig.savefig('figures_paper_latest/n_models_convergence.png', dpi=300, bbox_inches='tight')
fig.savefig('figures_paper_latest/n_models_convergence.pdf', bbox_inches='tight')
print("Figure saved: figures_paper_latest/n_models_convergence.png/pdf")
plt.close()
