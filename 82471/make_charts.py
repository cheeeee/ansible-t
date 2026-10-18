"""Render before/after charts for the WorkerQueue fix (light mode, reference palette)."""
import json
import os
import statistics

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

OUT = os.environ.get("OUT", "/charts")
DATA = os.path.join(OUT, "data")

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
AFTER = "#2a78d6"   # categorical slot 1: with the patch
BEFORE = "#eb6834"  # categorical slot 2: without the patch
LABEL_AFTER = "з патчем"
LABEL_BEFORE = "без патча"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2,
    "axes.titlecolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK2,
    "ytick.labelcolor": INK2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "grid.linestyle": "-",
    "axes.axisbelow": True,
    "legend.frameon": False,
    "legend.labelcolor": INK2,
})


def style(ax, ygrid_only=True):
    if ygrid_only:
        ax.grid(axis="x", visible=False)
    ax.tick_params(length=0)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(0.8)


def line(ax, xs, ys, color, label):
    ax.plot(xs, ys, color=color, linewidth=2, solid_capstyle="round", solid_joinstyle="round", label=label,
            marker="o", markersize=8, markerfacecolor=color, markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)


def rounded_bar(ax, x, height, width, color, radius_px=4):
    """Column with a 4px rounded data end and a square baseline."""
    if height <= 0:
        return
    fig = ax.figure
    fig.canvas.draw()
    # convert 4px into data units for both axes
    inv = ax.transData.inverted()
    (x0, y0), (x1, y1) = inv.transform([(0, 0), (radius_px, radius_px)])
    rx, ry = abs(x1 - x0), abs(y1 - y0)
    r_x = min(rx, width / 2)
    r_y = min(ry, height / 2)
    # square base: a plain rectangle up to just below the rounded cap, then the rounded cap drawn over the joint
    ax.add_patch(Rectangle((x - width / 2, 0), width, max(height - r_y, 0), linewidth=0, facecolor=color, zorder=3))
    cap_h = min(height, 3 * r_y)
    ax.add_patch(FancyBboxPatch((x - width / 2, height - cap_h), width, cap_h, boxstyle=f"round,pad=0,rounding_size={r_x}",
                                mutation_aspect=r_y / max(r_x, 1e-12), linewidth=0, facecolor=color, zorder=4))


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print("wrote", path)


# 1. Named semaphores held by the controller vs forks (measured on musl, Alpine 3.24)
def chart_semaphores():
    fig, ax = plt.subplots(figsize=(8, 4.4))
    before = [(10, 35), (40, 125), (74, 227), (80, 242)]
    after = [(10, 2), (40, 2), (85, 2), (120, 2), (200, 2), (500, 2), (1000, 2)]
    xs = [10 + i * 0.5 for i in range(int((84 - 10) / 0.5) + 1)]
    ax.plot(xs, [2 + 3 * x for x in xs], color=BEFORE, linewidth=2, solid_capstyle="round", zorder=2)
    ax.scatter(*zip(*before), s=64, color=BEFORE, edgecolors=SURFACE, linewidths=2, zorder=3)
    ax.plot([], [], color=BEFORE, linewidth=2, marker="o", markersize=8, markeredgecolor=SURFACE, markeredgewidth=2,
            label=LABEL_BEFORE + ": 2 + 3 × forks (точки — виміри)")
    line(ax, *zip(*after), AFTER, LABEL_AFTER + ": 2 (виміри)")
    ax.axhline(256, color=INK2, linewidth=1, zorder=2)
    ax.text(1000, 262, "ліміт musl: 256 на процес", ha="right", va="bottom", color=INK2, fontsize=9)
    ax.annotate("на 85-му форку таблиця заповнена:\nнові воркери не створюються", xy=(80, 242), xytext=(120, 175),
                color=INK2, fontsize=9, arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=1))
    ax.text(1000, 14, "2 за будь-якого forks", ha="right", va="bottom", color=INK2, fontsize=9)
    ax.set_xscale("log")
    ax.set_xticks([10, 20, 50, 100, 200, 500, 1000])
    ax.set_xticklabels(["10", "20", "50", "100", "200", "500", "1K"])
    ax.set_xlim(8, 1200)
    ax.set_ylim(0, 300)
    ax.set_xlabel("forks (лог. шкала)")
    ax.set_ylabel("іменованих семафорів у контролері")
    ax.set_title("Іменовані семафори в контролері: 2 + 3 × forks → 2", loc="left", fontsize=12, pad=12)
    ax.legend(loc="upper left")
    style(ax, ygrid_only=False)
    save(fig, "1-semaphores-vs-forks.png")


# 2. Share of hosts that completed the play vs forks (musl)
def chart_completion():
    fig, ax = plt.subplots(figsize=(8, 4.0))
    before = [(10, 100), (40, 100), (74, 100), (80, 100), (85, 0), (120, 0), (200, 0)]
    after = [(10, 100), (40, 100), (85, 100), (120, 100), (200, 100), (500, 100), (1000, 100)]
    line(ax, *zip(*before), BEFORE, LABEL_BEFORE)
    line(ax, *zip(*after), AFTER, LABEL_AFTER)
    ax.annotate("85 форків: 0 з 85 хостів,\nа ansible-playbook повернув rc=0", xy=(85, 0), xytext=(130, 30),
                color=INK2, fontsize=9, arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=1))
    ax.set_xscale("log")
    ax.set_xticks([10, 20, 50, 100, 200, 500, 1000])
    ax.set_xticklabels(["10", "20", "50", "100", "200", "500", "1K"])
    ax.set_xlim(8, 1200)
    ax.set_ylim(-5, 112)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("forks (лог. шкала)")
    ax.set_ylabel("хостів виконали всі таски")
    ax.set_title("Alpine (musl): скільки хостів справді виконали play", loc="left", fontsize=12, pad=12)
    ax.legend(loc="center left")
    style(ax, ygrid_only=False)
    save(fig, "2-hosts-completed-vs-forks.png")


# 3. Controller resources per worker
def chart_resources():
    panels = [
        ("іменовані семафори\nна воркер", 3, 0, "{:.0f}"),
        ("файлові дескриптори\nна воркер (виміряно)", 4, 4, "{:.0f}"),
        ("фонові потоки на воркер,\nякому відповідали на prompt", 1, 0, "{:.0f}"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.4))
    for ax, (title, b, a, fmt) in zip(axes, panels):
        ax.set_xlim(-0.8, 1.8)
        top = max(b, a, 1) * 1.35
        ax.set_ylim(0, top)
        rounded_bar(ax, 0, b, 0.24, BEFORE)
        rounded_bar(ax, 1, a, 0.24, AFTER)
        for x, v in ((0, b), (1, a)):
            ax.text(x, v + top * 0.03, fmt.format(v), ha="center", va="bottom", color=INK, fontsize=11)
        ax.set_xticks([0, 1])
        ax.set_xticklabels([LABEL_BEFORE, LABEL_AFTER])
        ax.set_yticks([])
        ax.set_title(title, fontsize=10, color=INK, pad=8)
        ax.grid(False)
        ax.spines["left"].set_visible(False)
        ax.tick_params(length=0)
    fig.suptitle("Скільки контролеру коштує один воркер", x=0.02, ha="left", fontsize=12, color=INK)
    fig.tight_layout()
    save(fig, "3-resources-per-worker.png")


# 4. Micro benchmarks (min of rounds), musl vs glibc
def chart_micro():
    path = os.path.join(DATA, "micro.jsonl")
    if not os.path.exists(path):
        print("skip micro: no data")
        return
    rows = [json.loads(line) for line in open(path) if line.startswith("{")]
    get = {(r["libc"], r["label"]): r for r in rows}
    libcs = [lc for lc in ("musl", "glibc") if (lc, "before") in get]
    panels = [("створення каналу\nна воркер, мкс", "create_us", "{:.1f}"),
              ("put + get туди-назад,\nмкс", "roundtrip_us", "{:.1f}"),
              ("fork + join за 50 живих\nканалів, мс", "fork_with_50_live_ms", "{:.2f}")]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.6))
    for ax, (title, key, fmt) in zip(axes, panels):
        vals = [get[(lc, t)][key] for lc in libcs for t in ("before", "after")]
        top = max(vals) * 1.3
        ax.set_ylim(0, top)
        ax.set_xlim(-0.7, len(libcs) - 0.3)
        for i, lc in enumerate(libcs):
            for off, t, color in ((-0.11, "before", BEFORE), (0.11, "after", AFTER)):
                v = get[(lc, t)][key]
                rounded_bar(ax, i + off, v, 0.16, color)
                ax.text(i + off, v + top * 0.03, fmt.format(v), ha="center", va="bottom", color=INK, fontsize=8.5)
        ax.set_xticks(range(len(libcs)))
        ax.set_xticklabels(libcs)
        ax.set_yticks([])
        ax.set_title(title, fontsize=10, color=INK, pad=8)
        ax.grid(False)
        ax.spines["left"].set_visible(False)
        ax.tick_params(length=0)
    handles = [Rectangle((0, 0), 1, 1, color=BEFORE), Rectangle((0, 0), 1, 1, color=AFTER)]
    fig.legend(handles, [LABEL_BEFORE, LABEL_AFTER], loc="upper right", ncol=2, frameon=False, labelcolor=INK2)
    fig.suptitle("Мікровиміри (найкраще з прогонів, arm64; менше — краще)", x=0.02, ha="left", fontsize=12, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, "4-micro-benchmarks.png")


# 5. End-to-end runs: every run as a dot, median as a tick
def chart_e2e():
    series = []
    for lc in ("musl", "glibc"):
        path = os.path.join(DATA, f"e2e-{lc}.times")
        if os.path.exists(path):
            d = {"before": [], "after": []}
            for line_ in open(path):
                t, v = line_.split()
                d[t].append(float(v))
            series.append((lc, d))
    if not series:
        print("skip e2e: no data")
        return
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for i, (lc, d) in enumerate(series):
        for off, t, color in ((-0.15, "before", BEFORE), (0.15, "after", AFTER)):
            vals = d[t]
            xs = [i + off + (k - (len(vals) - 1) / 2) * 0.018 for k in range(len(vals))]
            ax.scatter(xs, vals, s=40, color=color, edgecolors=SURFACE, linewidths=1.5, zorder=3,
                       label=(LABEL_BEFORE if t == "before" else LABEL_AFTER) if i == 0 else None)
            med = statistics.median(vals)
            ax.plot([i + off - 0.09, i + off + 0.09], [med, med], color=INK, linewidth=2, solid_capstyle="round", zorder=4)
            ax.text(i + off + 0.11, med, f"{med:.1f} с", va="center", ha="left", color=INK, fontsize=9)
        b, a = statistics.median(d["before"]), statistics.median(d["after"])
        ax.text(i, ax.get_ylim()[1] if False else max(max(d["before"]), max(d["after"])) * 1.04,
                f"медіана {((a - b) / b) * 100:+.1f}%".replace("-", "\u2212"), ha="center", va="bottom", color=INK2, fontsize=9)
    ax.set_xticks(range(len(series)))
    ax.set_xticklabels([lc for lc, _ in series])
    ax.set_xlim(-0.6, len(series) - 0.4)
    ax.set_ylabel("секунд на прогін")
    lo = min(min(d["before"] + d["after"]) for _, d in series)
    hi = max(max(d["before"] + d["after"]) for _, d in series)
    ax.set_ylim(lo * 0.9, hi * 1.12)
    ax.set_title("Наскрізний прогін: 100 хостів × 30 тасків, forks=50 (3000 воркерів)", loc="left", fontsize=12, pad=12)
    ax.legend(loc="upper right")
    style(ax)
    fig.text(0.01, -0.02, "Кожна точка — один прогін, почергово до/після; чорна риска — медіана. arm64, без емуляції.",
             color=MUTED, fontsize=8.5)
    save(fig, "5-end-to-end.png")


if __name__ == "__main__":
    chart_semaphores()
    chart_completion()
    chart_resources()
    chart_micro()
    chart_e2e()
