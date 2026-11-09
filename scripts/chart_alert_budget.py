"""Draw the alert-budget chart for the README (light and dark versions).

Each bar is the share of calls a compliance rule would alert on if it ran live (at most one alert
per call), against a rule of thumb that a live alert should fire on fewer than 1 call in 10.

Usage: chart_alert_budget.py results/workflow_sim.json out_dir
"""
import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

src, out_dir = sys.argv[1:3]
B = json.load(open(src))["alert_budget"]
rows = [("No recording notice before the handoff", B["recording_notice"]["pct"]),
        ("Opener implies Medicare is calling", B["medicare_affiliation_claim"]["pct"]),
        ("Benefit before the disclaimer", B["tpmo_disclaimer"]["pct"]),
        ("Money-back promise", B["money_back_claim"]["pct"]),
        ("“No one will call you again”", B["no_more_calls_promise"]["pct"]),
        ("Stop-calling request", B["do_not_call_request"]["pct"])]
rows.reverse()  # largest at the top

THEMES = {"light": {"bg": "#ffffff", "ink": "#1f2328", "muted": "#59636e", "grid": "#d1d9e0", "bar": "#2a78d6"},
          "dark": {"bg": "#0d1117", "ink": "#e6edf3", "muted": "#9198a1", "grid": "#3d444d", "bar": "#3987e5"}}

for name, T in THEMES.items():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, ax = plt.subplots(figsize=(10, 4.4), dpi=200)
    fig.patch.set_facecolor(T["bg"]); ax.set_facecolor(T["bg"])
    labels = [r[0] for r in rows]; vals = [r[1] for r in rows]
    ax.barh(range(len(rows)), vals, height=0.56, color=T["bar"], zorder=3)
    for i, v in enumerate(vals):
        ax.text(v + 1.2, i, f"{v:.0f}%" if v >= 1 else f"{v:.1f}%", va="center", ha="left", color=T["ink"], fontsize=11, zorder=4,
                bbox=dict(facecolor=T["bg"], edgecolor="none", pad=1.5))
    ax.axvline(10, color=T["muted"], linestyle=(0, (4, 3)), linewidth=1.2, zorder=2)
    ax.text(11.2, len(rows) - 0.45, "Rule of thumb for a live alert: under 1 call in 10", color=T["muted"], fontsize=10, va="center", ha="left")
    ax.set_yticks(range(len(rows)), labels, color=T["ink"], fontsize=11)
    ax.set_xlim(0, 108)
    ax.set_xticks(range(0, 101, 20), [f"{x}%" for x in range(0, 101, 20)])
    ax.tick_params(axis="x", colors=T["muted"], labelsize=10, length=0)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.grid(axis="x", color=T["grid"], linewidth=0.8, zorder=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel("Share of calls the alert would fire on", color=T["muted"], fontsize=10, labelpad=8)
    fig.text(0.012, 0.95, "If each compliance rule alerted agents live", color=T["ink"], fontsize=14, fontweight="bold", ha="left")
    fig.text(0.012, 0.885, "3,750 Medicare sales calls recorded from the start, made before mid-2025", color=T["muted"], fontsize=10.5, ha="left")
    fig.subplots_adjust(left=0.33, right=0.97, top=0.82, bottom=0.14)
    fig.savefig(os.path.join(out_dir, f"alert-budget-{name}.png"), facecolor=T["bg"])
    plt.close(fig)
print("ok")
