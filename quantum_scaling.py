"""
quantum_scaling.py — Scaling diagram: Classical O(N) vs Grover O(√N)

Standalone:
    python quantum_scaling.py

Called from testQuantumVsClassical.py with real measured values:
    python quantum_scaling.py --classical_ns 850 --qpu_seconds 0.003 --real_qbits 10
"""

import argparse
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# =============================================================================
# CLI args
# =============================================================================
parser = argparse.ArgumentParser()
parser.add_argument('--classical_ns', type=float, default=850.0)
parser.add_argument('--qpu_seconds',  type=float, default=0.003)
parser.add_argument('--real_qbits',   type=int,   default=10)
args = parser.parse_args()

REAL_QBITS   = args.real_qbits
CLASSICAL_NS = args.classical_ns
QPU_SECONDS  = args.qpu_seconds

# =============================================================================
# Scaling — anchor both curves to the real 10-qubit measurement
# =============================================================================
N_real            = 2 ** REAL_QBITS
grover_iters_real = math.floor(math.pi / 4 * math.sqrt(float(N_real)))

classical_ns_per_op = CLASSICAL_NS / N_real
qpu_ns_per_iter     = (QPU_SECONDS * 1e9) / grover_iters_real if QPU_SECONDS > 0 else 1e5

def classical_ns(n):
    return classical_ns_per_op * (2.0 ** n)

def grover_ns(n):
    iters = max(1, math.floor(math.pi / 4 * math.sqrt(2.0 ** n)))
    return qpu_ns_per_iter * iters

qbits = np.arange(1, 301)
c_arr = np.array([classical_ns(n) for n in qbits])
g_arr = np.array([grover_ns(n)    for n in qbits])

# Crossover
crossover_q = None
for i in range(1, len(qbits)):
    if g_arr[i] < c_arr[i] and g_arr[i-1] >= c_arr[i-1]:
        crossover_q = int(qbits[i])
        break

# =============================================================================
# Time reference lines  (in nanoseconds)
# =============================================================================
NS   = 1.0
US   = 1e3
MS   = 1e6
SEC  = 1e9
MIN  = 60   * SEC
HOUR = 3600 * SEC
DAY  = 24   * HOUR
YEAR = 365.25 * DAY
AGE  = 13.8e9 * YEAR          # age of universe in ns  ≈ 4.35e26

time_refs = [
    (NS,   "1 ns"),
    (US,   "1 µs"),
    (MS,   "1 ms"),
    (SEC,  "1 second"),
    (MIN,  "1 minute"),
    (HOUR, "1 hour"),
    (DAY,  "1 day"),
    (YEAR, "1 year"),
    (100*YEAR, "100 years"),
    (AGE,  "Age of Universe"),
]

# =============================================================================
# Roadmap milestones  (x = qubit count, just for vertical lines)
# =============================================================================
milestones = [
    (10,  "2024\n10 qubits\nNISQ real results"),
    (50,  "2025–26\nIBM Flamingo\n~50 logical qubits"),
    (100, "2027–28\nIBM Crossbill\n~100 logical qubits"),
    (200, "2030–32\nEarly fault-tolerant\nQEC threshold"),
    (300, "2033+\nIBM roadmap 300+\nlogical qubits\n(AES-128 threatened)"),
]

# =============================================================================
# Figure layout
# =============================================================================
fig = plt.figure(figsize=(15, 10), facecolor='#0d1117')
gs  = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.38,
                       left=0.07, right=0.82, top=0.93, bottom=0.07)
ax_main  = fig.add_subplot(gs[0])
ax_ratio = fig.add_subplot(gs[1])

DARK   = '#0d1117'
RED    = '#ff5555'
CYAN   = '#00ccff'
YELLOW = '#ffd700'
AMBER  = '#ffaa44'
GREY   = '#888888'

for ax in (ax_main, ax_ratio):
    ax.set_facecolor(DARK)
    for sp in ax.spines.values():
        sp.set_edgecolor('#444')
    ax.tick_params(colors='#aaa', labelsize=9)

# =============================================================================
# Y-axis limits: 0.1 ns  →  10× age of universe
# Anything that goes off the top just hits the edge — that IS the point.
# =============================================================================
Y_MIN = 0.1          # 0.1 ns
Y_MAX = AGE * 10     # 10× age of universe  ≈ 4.35e27 ns

# ── MAIN CHART ───────────────────────────────────────────────────────────────
ax = ax_main

# NISQ shading
ax.axvspan(1, 15, alpha=0.07, color='cyan', zorder=0)
ax.text(8, Y_MAX * 0.3, "NISQ\nregion\ntoday",
        color='#4dd', fontsize=8, ha='center', va='center')

# Curves — clip so they don't exceed Y_MAX visually
c_plot = np.clip(c_arr, Y_MIN, Y_MAX * 2)
g_plot = np.clip(g_arr, Y_MIN, Y_MAX * 2)

ax.semilogy(qbits, c_plot, color=RED,  linewidth=2.5, clip_on=True,
            label='Classical brute-force  O(2ⁿ)')
ax.semilogy(qbits[:10], g_plot[:10], color=CYAN, linewidth=2.5, clip_on=True,
            label='Grover — real hardware today  O(√2ⁿ)')
ax.semilogy(qbits[9:],  g_plot[9:],  color=CYAN, linewidth=2.5, linestyle='--', clip_on=True,
            label='Grover — extrapolated (future fault-tolerant hardware)')

# Real measured points
ax.scatter([REAL_QBITS], [CLASSICAL_NS],
           color=RED, s=140, zorder=6, marker='D',
           label=f'Measured: CPU brute-force  {CLASSICAL_NS:.0f} ns')
if QPU_SECONDS > 0:
    ax.scatter([REAL_QBITS], [QPU_SECONDS * 1e9],
               color=CYAN, s=140, zorder=6, marker='D',
               label=f'Measured: QPU gate time  {QPU_SECONDS*1000:.1f} ms')

# Crossover annotation
if crossover_q:
    cy = grover_ns(crossover_q)
    cy_clipped = min(cy, Y_MAX * 0.5)
    ax.scatter([crossover_q], [cy_clipped], color=YELLOW, s=160, zorder=7, marker='*')
    ax.annotate(f'Crossover ≈ {crossover_q} qubits\nGrover faster from here',
                xy=(crossover_q, cy_clipped),
                xytext=(crossover_q + 25, cy_clipped * 1e-3),
                color=YELLOW, fontsize=9,
                arrowprops=dict(arrowstyle='->', color=YELLOW, lw=1.5),
                bbox=dict(boxstyle='round,pad=0.3', fc='#111', ec=YELLOW, alpha=0.9))

# Time reference lines — right-hand side labels
for val, label in time_refs:
    if Y_MIN <= val <= Y_MAX:
        ax.axhline(val, color='#3a3a3a', linewidth=0.8, linestyle=':', zorder=1)
        ax.text(303, val, f' {label}', color='#777', fontsize=8,
                va='center', clip_on=False)

# Milestone vertical lines + top labels
for q, desc in milestones:
    ax.axvline(q, color='#6644aa', linewidth=0.9, linestyle='--', alpha=0.8, zorder=2)
    ax.text(q, Y_MAX * 1.5, desc,
            color=AMBER, fontsize=7.2, ha='center', va='bottom',
            rotation=0, clip_on=False,
            bbox=dict(boxstyle='round,pad=0.25', fc='#1a1020', ec='#6644aa', alpha=0.9))

ax.set_xlim(1, 300)
ax.set_ylim(Y_MIN, Y_MAX)
ax.set_xlabel('Key size  (number of qubits)', color='#ccc', fontsize=11)
ax.set_ylabel('Time  (nanoseconds, log scale)', color='#ccc', fontsize=11)
ax.set_title(
    'Classical Brute-Force  vs  Grover\'s Quantum Search  ·  1 → 300 qubits\n'
    '◆ = real IBM hardware measurement at 10 qubits  |  dashed = extrapolated future hardware',
    color='white', fontsize=12, pad=10
)
ax.legend(loc='lower right', facecolor='#111', edgecolor='#444',
          labelcolor='white', fontsize=8.5, framealpha=0.95)

# Custom y-axis tick labels
def ns_formatter(val, _):
    if   val >= AGE:         return f'{val/AGE:.0f}× Universe age'
    elif val >= YEAR:        return f'{val/YEAR:.0g} yr'
    elif val >= DAY:         return f'{val/DAY:.0g} day'
    elif val >= HOUR:        return f'{val/HOUR:.0g} hr'
    elif val >= MIN:         return f'{val/MIN:.0g} min'
    elif val >= SEC:         return f'{val/SEC:.0g} s'
    elif val >= MS:          return f'{val/MS:.0g} ms'
    elif val >= US:          return f'{val/US:.0g} µs'
    else:                    return f'{val:.0g} ns'

ax.yaxis.set_major_formatter(ticker.FuncFormatter(ns_formatter))

# ── RATIO CHART ──────────────────────────────────────────────────────────────
ax2 = ax_ratio

ratio = np.where(g_arr > 0, c_arr / g_arr, np.nan)
ratio_clipped = np.clip(ratio, 1e-3, 1e30)

ax2.semilogy(qbits, ratio_clipped, color='#88ff88', linewidth=2.2, clip_on=True)
ax2.axhline(1, color=GREY, linewidth=0.8, linestyle='--')
ax2.text(303, 1, '  equal', color=GREY, fontsize=8, va='center', clip_on=False)

if QPU_SECONDS > 0:
    real_ratio = CLASSICAL_NS / (QPU_SECONDS * 1e9)
    ax2.scatter([REAL_QBITS], [real_ratio], color=YELLOW, s=100, zorder=5, marker='D',
                label=f'Real ratio at {REAL_QBITS} qubits: CPU is {real_ratio:.1f}× faster than QPU')
    ax2.legend(loc='upper left', facecolor='#111', edgecolor='#444',
               labelcolor='white', fontsize=8.5)

for q, _ in milestones:
    ax2.axvline(q, color='#6644aa', linewidth=0.9, linestyle='--', alpha=0.5)

ax2.set_xlim(1, 300)
ax2.set_ylim(1e-3, 1e30)
ax2.set_xlabel('Key size  (number of qubits)', color='#ccc', fontsize=11)
ax2.set_ylabel('Speedup ratio', color='#ccc', fontsize=11)
ax2.set_title('Speedup Ratio: Classical time ÷ QPU gate time',
              color='white', fontsize=10)

def ratio_formatter(val, _):
    if   val >= 1e24: return f'10^{int(round(math.log10(val)))}× (cryptography broken)'
    elif val >= 1e12: return f'10^{int(round(math.log10(val)))}×'
    elif val >= 1e6:  return f'{val:.0e}×'
    elif val >= 1:    return f'{val:.0f}×'
    else:             return f'1/{1/val:.0f}×'

ax2.yaxis.set_major_formatter(ticker.FuncFormatter(ratio_formatter))

# =============================================================================
# Footer
# =============================================================================
fig.text(
    0.44, 0.005,
    'Extrapolation assumes fault-tolerant QPU with ~100 µs/iteration. '
    'Real NISQ hardware degrades sharply with depth beyond ~15 qubits. '
    'IBM roadmap: 2025 Flamingo ~50 logical qubits · 2027 ~100 · 2033 300+.',
    ha='center', color='#555', fontsize=7.5
)

plt.savefig('quantum_scaling.png', dpi=150, bbox_inches='tight',
            facecolor=DARK, format='png')
plt.close()
print("quantum_scaling.png saved.")
