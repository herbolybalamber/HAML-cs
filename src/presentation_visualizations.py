import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


THRESHOLDS = [600, 900, 1000]


def resolve_path(path_value: str, base_dir: Path) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    if candidate.exists():
        return candidate.resolve()
    return (base_dir / candidate).resolve()


def load_inputs(distances_path: Path, summary_path: Path) -> tuple[pd.DataFrame, dict]:
    distances = pd.read_csv(distances_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return distances, summary


def plot_threshold_shares(distances: pd.DataFrame, output_dir: Path) -> None:
    total = len(distances)
    rows = []
    for threshold in THRESHOLDS:
        under = (distances["distance_3d"] <= threshold).sum()
        rows.append({"threshold": threshold, "share": under / total * 100, "count": int(under)})

    data = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=data, x="threshold", y="share", ax=ax, color="#2a9d8f")
    ax.set_title("Kill arány küszöbtávolság alatt")
    ax.set_xlabel("Küszöb (unit)")
    ax.set_ylabel("Arány (%)")
    for i, row in enumerate(data.to_dict(orient="records")):
        share = float(row["share"])
        count = int(row["count"])
        ax.text(float(i), share + 0.8, f"{share:.1f}%\n({count} db)", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    fig.savefig(output_dir / "threshold_share_bar.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_distance_ecdf(distances: pd.DataFrame, summary: dict, output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.ecdfplot(data=distances, x="distance_3d", ax=ax, color="#1d3557")
    radius = summary["duel_radius_used"]
    ax.axvline(radius, linestyle="--", color="#e63946", label=f"Aktív r = {radius:.1f}")
    ax.axvline(1000, linestyle=":", color="#6d597a", label="1000 unit")
    ax.set_title("Kumulatív távolságeloszlás (ECDF)")
    ax.set_xlabel("3D távolság (unit)")
    ax.set_ylabel("Kumulatív arány")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "distance_ecdf.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_weapon_boxplot(distances: pd.DataFrame, output_dir: Path) -> None:
    top_weapons = distances["weapon"].value_counts().head(8).index.tolist()
    subset = distances[distances["weapon"].isin(top_weapons)].copy()

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(data=subset, x="weapon", y="distance_3d", ax=ax, color="#457b9d")
    ax.set_title("Távolság eloszlás top-8 fegyverenként")
    ax.set_xlabel("Fegyver")
    ax.set_ylabel("3D távolság (unit)")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(output_dir / "weapon_distance_boxplot_top8.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_kill_type_donut(summary: dict, output_dir: Path) -> None:
    labels = ["Lőfegyveres player kill", "Egyéb kill"]
    values = [summary["shot_kills"], summary["non_shot_or_non_player_kills"]]
    colors = ["#2a9d8f", "#e76f51"]

    fig, ax = plt.subplots(figsize=(6, 6))
    pie_result = ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        colors=colors,
        wedgeprops={"width": 0.42},
    )
    autotexts = pie_result[2] if len(pie_result) == 3 else []
    for t in autotexts:
        t.set_fontsize(10)
    ax.set_title("Kill típusok aránya")
    fig.tight_layout()
    fig.savefig(output_dir / "kill_type_donut.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prezentációs ábrák generálása")
    parser.add_argument("--distances", type=str, default="../data/processed/shot_kill_distances.csv")
    parser.add_argument("--summary", type=str, default="../data/processed/shot_kill_summary.json")
    parser.add_argument("--out-dir", type=str, default="../outputs/plots/presentation")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent

    distances_path = resolve_path(args.distances, script_dir)
    summary_path = resolve_path(args.summary, script_dir)
    out_dir = resolve_path(args.out_dir, script_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    distances, summary = load_inputs(distances_path, summary_path)
    sns.set_theme(style="whitegrid")

    plot_threshold_shares(distances, out_dir)
    plot_distance_ecdf(distances, summary, out_dir)
    plot_weapon_boxplot(distances, out_dir)
    plot_kill_type_donut(summary, out_dir)

    print(f"Prezentacios abrak mentve ide: {out_dir}")


if __name__ == "__main__":
    main()
