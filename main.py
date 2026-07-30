"""Visualize Italian general-election polling data as PNG charts.

Reads italian_polls.csv (one row per poll, party shares in percent) and
renders individual polls as faint dots with a 21-day rolling-average trend
line per party, in each party's conventional color.

Usage: uv run main.py [--csv PATH] [--out PATH]
"""

import argparse

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

# Conventional party colors, adjusted for contrast on a light surface and
# color-vision-deficiency separation (M5S yellow darkened; FdI navy vs. FI
# azure kept far apart in hue). Order = label order by recent support.
PARTIES = {
    "FdI": "#0B2E59",
    "PD": "#E4032E",
    "M5S": "#D4A017",
    "FI": "#1E90CE",
    "AVS": "#8E44AD",
    "Lega": "#1D7A46",
    "Az-IV": "#00A99D",
    "+E": "#E4007C",
    "NM": "#F39C12",
    "Others": "#75797E",
}

PARTY_LABELS = {"Az-IV": "Azione–IV"}

ELECTIONS = {
    "2022-09-25": "Elezioni 2022",
    "2024-06-09": "Elezioni europee 2024",
}

INK = "#33302e"
MUTED = "#77716c"
SURFACE = "#fcfcfb"
ROLLING_WINDOW = "21D"
THRESHOLD = 3  # national single-list electoral threshold


def load_polls(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, parse_dates=["date"])
    return df.sort_values("date").set_index("date")


def spread_labels(positions: list[float], min_gap: float, lo: float, hi: float) -> list[float]:
    """Nudge label y-positions apart until no pair is closer than min_gap."""
    order = sorted(range(len(positions)), key=lambda i: positions[i])
    ys = [positions[i] for i in order]
    for _ in range(100):
        moved = False
        for a in range(len(ys) - 1):
            overlap = min_gap - (ys[a + 1] - ys[a])
            if overlap > 0:
                ys[a] -= overlap / 2
                ys[a + 1] += overlap / 2
                moved = True
        ys[0] = max(ys[0], lo)
        ys[-1] = min(ys[-1], hi)
        if not moved:
            break
    out = positions[:]
    for rank, i in enumerate(order):
        out[i] = ys[rank]
    return out


def latest_averages(df: pd.DataFrame) -> dict[str, float]:
    """Latest rolling-average share per party, from the most recent polls."""
    return {
        party: float(df[party].dropna().rolling(ROLLING_WINDOW).mean().iloc[-1])
        for party in PARTIES
        if df[party].notna().any()
    }


def dodge(values: list[float], gap: float = 0.5, step: float = 0.16) -> list[float]:
    """Vertical offsets that spread out dots whose x-values nearly coincide."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    offsets = [0.0] * len(values)
    cluster = [order[0]]
    for i in order[1:] + [None]:
        if i is not None and values[i] - values[cluster[-1]] < gap:
            cluster.append(i)
            continue
        for k, idx in enumerate(cluster):
            offsets[idx] = (k - (len(cluster) - 1) / 2) * step
        cluster = [i] if i is not None else []
    return offsets


def plot_institutes(df: pd.DataFrame, out_path: str) -> None:
    cutoff = df.index.max() - pd.Timedelta(days=90)
    latest = df[df.index >= cutoff].reset_index().groupby("institute").last()
    latest = latest.sort_values("date")

    avg = latest_averages(df)
    rows = [(f"{inst}  ({row['date']:%d/%m})", row) for inst, row in latest.iterrows()]
    rows.append(("Media mobile 21 giorni", pd.Series(avg)))

    fig, ax = plt.subplots(figsize=(14, 0.62 * len(rows) + 2.6), dpi=200)
    fig.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    xmax = 0.0
    for y, (label, values) in enumerate(rows):
        present = [p for p in PARTIES if p in values and pd.notna(values[p])]
        vals = [float(values[p]) for p in present]
        offsets = dodge(vals)
        for party, v, dy in zip(present, vals, offsets):
            ax.scatter(v, y + dy, s=90, color=PARTIES[party], zorder=3,
                       edgecolor=SURFACE, linewidth=1.5)
        xmax = max(xmax, max(vals))

    ax.axvline(THRESHOLD, color=MUTED, linewidth=0.8, linestyle=(0, (1, 3)), alpha=0.8, zorder=1)
    ax.annotate(
        f"Soglia {THRESHOLD}%", (THRESHOLD, -0.5), ha="center", va="bottom", fontsize=8.5, color=MUTED,
    )
    ax.axhline(len(rows) - 1.5, color="#d5d1cd", linewidth=0.8)

    handles = [
        plt.Line2D([], [], marker="o", linestyle="", markersize=9,
                   markerfacecolor=color, markeredgecolor=SURFACE, label=PARTY_LABELS.get(party, party))
        for party, color in PARTIES.items()
    ]
    ax.legend(
        handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.0),
        ncol=len(PARTIES), frameon=False, fontsize=9.5, labelcolor=INK,
        handletextpad=0.1, columnspacing=0.9, borderaxespad=0.2,
    )

    ax.set_xlim(0, xmax + 2)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_yticks(range(len(rows)), [label for label, _ in rows], fontsize=10)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(axis="x", color="#e6e3e0", linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#d5d1cd")
    ax.tick_params(colors=MUTED, length=0)
    for tick in ax.get_yticklabels():
        tick.set_color(INK)
    ax.get_yticklabels()[-1].set_fontweight("bold")

    fig.text(
        0.03, 0.955, "Sondaggi recenti per istituto",
        fontsize=16, color=INK, fontweight="bold", va="top",
    )
    fig.text(
        0.03, 0.905,
        f"Ultimo sondaggio degli ultimi 90 giorni per istituto (al {df.index.max():%d/%m/%Y}), "
        "ordinato per data del sondaggio · Media = media mobile 21 giorni di tutti gli istituti",
        fontsize=10, color=MUTED, va="top",
    )
    fig.text(
        0.99, 0.02,
        "Fonte: italian_polls.csv (SWG, Tecnè, Termometro Politico, EMG, Ipsos, ecc.)",
        ha="right", fontsize=8.5, color=MUTED,
    )

    fig.subplots_adjust(left=0.19, right=0.97, top=0.79, bottom=0.10)
    fig.savefig(out_path, facecolor=SURFACE)
    print(f"Wrote {out_path}")


def plot(df: pd.DataFrame, out_path: str, title: str) -> None:
    fig, ax = plt.subplots(figsize=(14, 8), dpi=200)
    fig.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    label_targets = {}
    for party, color in PARTIES.items():
        series = df[party].dropna()
        if series.empty:
            continue
        ax.scatter(series.index, series.values, s=5, color=color, alpha=0.12, linewidths=0)
        smoothed = series.rolling(ROLLING_WINDOW).mean()
        ax.plot(smoothed.index, smoothed.values, color=color, linewidth=2, solid_capstyle="round")
        label_targets[party] = float(smoothed.iloc[-1])

    for date, name in ELECTIONS.items():
        ts = pd.Timestamp(date)
        if not (df.index.min() < ts < df.index.max()):
            continue
        ax.axvline(ts, color=MUTED, linewidth=0.8, linestyle=(0, (4, 4)), alpha=0.6)
        ax.annotate(
            name, (ts, 0.995), xycoords=("data", "axes fraction"),
            xytext=(0, -2), textcoords="offset points",
            ha="center", va="top", fontsize=8.5, color=MUTED,
        )

    ax.axhline(THRESHOLD, color=MUTED, linewidth=0.8, linestyle=(0, (1, 3)), alpha=0.8)
    ax.annotate(
        f"Soglia {THRESHOLD}%", (0.001, THRESHOLD), xycoords=("axes fraction", "data"),
        xytext=(2, 3), textcoords="offset points", fontsize=8.5, color=MUTED,
    )

    # Direct labels at the right edge: party name + latest smoothed value,
    # in ink (not series color) with a colored dash tying label to line.
    parties = list(label_targets)
    ymax = df[[p for p in PARTIES if p in df.columns]].max().max() + 2
    labeled_ys = spread_labels(
        [label_targets[p] for p in parties], ymax * 0.04, ymax * 0.01, ymax * 0.99
    )
    x_end = df.index.max()
    for party, y_label in zip(parties, labeled_ys):
        ax.annotate(
            "", (x_end, label_targets[party]),
            xytext=(14, 0), textcoords="offset points",
            arrowprops=dict(arrowstyle="-", color=PARTIES[party], linewidth=2,
                            shrinkA=0, shrinkB=3),
            annotation_clip=False,
        )
        ax.annotate(
            f"{PARTY_LABELS.get(party, party)}  {label_targets[party]:.0f}", (x_end, y_label),
            xytext=(18, 0), textcoords="offset points",
            va="center", fontsize=10, color=INK,
            annotation_clip=False,
        )

    ax.set_ylim(0, ymax)
    ax.set_xlim(df.index.min(), x_end)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    if (df.index.max() - df.index.min()).days > 3 * 365:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    else:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.grid(axis="y", color="#e6e3e0", linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#d5d1cd")
    ax.tick_params(colors=MUTED, labelsize=10, length=0)

    n_polls = len(df)
    ax.set_title(title, fontsize=16, color=INK, loc="left", pad=28, fontweight="bold")
    ax.text(
        0, 1.025,
        f"{n_polls} sondaggi, {df.index.min():%b %Y} – {df.index.max():%b %Y} · "
        f"Punti: singoli sondaggi · Linee: media mobile 21 giorni",
        transform=ax.transAxes, fontsize=10.5, color=MUTED,
    )
    fig.text(
        0.99, 0.01,
        "Fonte: italian_polls.csv (SWG, Tecnè, Termometro Politico, EMG, Ipsos, ecc.)",
        ha="right", fontsize=8.5, color=MUTED,
    )

    fig.subplots_adjust(left=0.045, right=0.885, top=0.895, bottom=0.07)
    fig.savefig(out_path, facecolor=SURFACE)
    print(f"Wrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="italian_polls.csv")
    parser.add_argument("--out", default="italian_polls.png")
    parser.add_argument("--out-recent", default="italian_polls_recent.png")
    parser.add_argument("--out-institutes", default="italian_polls_institutes.png")
    args = parser.parse_args()
    df = load_polls(args.csv)
    plot(df, args.out, "Sondaggi elettorali italiani: intenzioni di voto")
    plot(
        df[df.index > df.index.max() - pd.Timedelta(days=365)],
        args.out_recent,
        "Sondaggi elettorali italiani: ultimi 12 mesi",
    )
    plot_institutes(df, args.out_institutes)


if __name__ == "__main__":
    main()
