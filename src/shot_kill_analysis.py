import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from demoparser2 import DemoParser


FIREARM_WEAPONS = {
    "ak47",
    "awp",
    "deagle",
    "elite",
    "galilar",
    "glock",
    "m4a1",
    "m4a1_silencer",
    "mac10",
    "mp9",
    "p250",
    "tec9",
    "usp_silencer",
}


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}

    content = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        raise ValueError("A config fájl gyökéreleme objektum kell legyen.")
    return content


def resolve_path(path_value: str, base_dir: Path) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    if candidate.exists():
        return candidate.resolve()
    return (base_dir / candidate).resolve()


def as_event_frame(parsed_events, event_name: str) -> pd.DataFrame:
    if isinstance(parsed_events, pd.DataFrame):
        return parsed_events
    if isinstance(parsed_events, dict):
        return parsed_events.get(event_name, pd.DataFrame())
    if isinstance(parsed_events, list):
        for item in parsed_events:
            if isinstance(item, tuple) and len(item) == 2 and item[0] == event_name:
                return item[1]
    return pd.DataFrame()


def load_or_build_duel_distances(demo_path: Path, extracted_csv: Path) -> pd.DataFrame:
    if extracted_csv.exists():
        return pd.read_csv(extracted_csv)

    from extract_duels import extract_duels

    return extract_duels(demo_path=demo_path, output_csv=extracted_csv)


def build_analysis_frame(demo_path: Path, extracted_csv: Path, radius: float | None = None) -> tuple[pd.DataFrame, dict]:
    parser = DemoParser(str(demo_path))
    death_df = as_event_frame(parser.parse_events(["player_death"]), "player_death")
    if death_df.empty:
        raise RuntimeError("Nem található player_death esemény a demóban.")

    death_df = death_df.copy()
    death_df["attacker_steamid"] = death_df["attacker_steamid"].astype("string")
    death_df["user_steamid"] = death_df["user_steamid"].astype("string")
    death_df["tick"] = death_df["tick"].astype(int)

    duel_df = load_or_build_duel_distances(demo_path, extracted_csv).copy()
    if duel_df.empty:
        raise RuntimeError("Az extracted_duels CSV üres, nem számolható távolság.")

    duel_df["attacker_steamid"] = duel_df["attacker_steamid"].astype("string")
    duel_df["victim_steamid"] = duel_df["victim_steamid"].astype("string")
    duel_df["tick"] = duel_df["tick"].astype(int)

    player_vs_player = death_df[
        death_df["attacker_steamid"].notna()
        & death_df["user_steamid"].notna()
        & (death_df["attacker_steamid"] != death_df["user_steamid"])
    ].copy()

    shot_kills = player_vs_player[player_vs_player["weapon"].isin(FIREARM_WEAPONS)].copy()

    merged = shot_kills.merge(
        duel_df[
            [
                "tick",
                "attacker_steamid",
                "victim_steamid",
                "weapon",
                "distance_3d",
                "attacker_name",
                "victim_name",
            ]
        ],
        left_on=["tick", "attacker_steamid", "user_steamid", "weapon"],
        right_on=["tick", "attacker_steamid", "victim_steamid", "weapon"],
        how="left",
        suffixes=("_event", "_duel"),
    )

    analyzed = merged.dropna(subset=["distance_3d"]).copy()
    if analyzed.empty:
        raise RuntimeError("Egyetlen lőfegyveres killhez sem sikerült távolságot rendelni.")

    mean_distance = float(analyzed["distance_3d"].mean())
    duel_radius = mean_distance if radius is None else float(radius)
    analyzed["is_duel_by_radius"] = analyzed["distance_3d"] <= duel_radius

    summary = {
        "total_kills": int(len(death_df)),
        "player_vs_player_kills": int(len(player_vs_player)),
        "shot_kills": int(len(shot_kills)),
        "shot_kill_share_of_all": float(len(shot_kills) / len(death_df)),
        "distance_rows_matched": int(len(analyzed)),
        "distance_rows_missing": int(len(shot_kills) - len(analyzed)),
        "mean_duel_radius": mean_distance,
        "duel_radius_used": duel_radius,
        "radius_source": "mean_distance_default" if radius is None else "manual_parameter",
        "median_shot_kill_distance": float(analyzed["distance_3d"].median()),
        "min_shot_kill_distance": float(analyzed["distance_3d"].min()),
        "max_shot_kill_distance": float(analyzed["distance_3d"].max()),
        "duels_within_radius": int(analyzed["is_duel_by_radius"].sum()),
        "non_duels_outside_radius": int((~analyzed["is_duel_by_radius"]).sum()),
        "duel_share_within_radius": float(analyzed["is_duel_by_radius"].mean()),
        "non_shot_or_non_player_kills": int(len(death_df) - len(shot_kills)),
    }

    return analyzed, summary


def create_visualization(analyzed: pd.DataFrame, summary: dict, output_path: Path) -> None:
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    counts = pd.DataFrame(
        {
            "category": [
                "Osszes kill",
                "Lofegyveres\nplayer kill",
                "Nem lofegyveres\nvagy nem player kill",
            ],
            "count": [
                summary["total_kills"],
                summary["shot_kills"],
                summary["non_shot_or_non_player_kills"],
            ],
        }
    )

    sns.barplot(
        data=counts,
        x="category",
        y="count",
        hue="category",
        dodge=False,
        legend=False,
        ax=axes[0],
        palette=["#16324f", "#2a9d8f", "#e76f51"],
    )
    axes[0].set_title("Kill megoszlas a demo alapjan")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("Darab")
    for index, row in counts.iterrows():
        axes[0].text(index, row["count"] + 1, f"{int(row['count'])}", ha="center", va="bottom", fontsize=10)

    duel_radius = summary["duel_radius_used"]
    axes[1].axvspan(0, duel_radius, color="#2a9d8f", alpha=0.12, label="Parbaj zona")
    axes[1].axvspan(duel_radius, analyzed["distance_3d"].max(), color="#e76f51", alpha=0.10, label="Nem parbaj zona")
    sns.histplot(data=analyzed, x="distance_3d", bins=18, kde=True, ax=axes[1], color="#1d3557")
    axes[1].axvline(duel_radius, color="#e63946", linestyle="--", linewidth=2, label=f"Atlagos r = {duel_radius:.1f}")
    axes[1].set_title("Lofegyveres killek tavolsaga")
    axes[1].set_xlabel("3D tavolsag")
    axes[1].set_ylabel("Esetszam")
    axes[1].legend()

    fig.suptitle("Demo kill elemzes: lofegyveres olesek es parbaj sugar", fontsize=16)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_outputs(analyzed: pd.DataFrame, summary: dict, summary_path: Path, classified_kills_path: Path) -> None:
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    export_columns = [
        "tick",
        "attacker_name_event",
        "user_name",
        "weapon",
        "distance_3d",
        "is_duel_by_radius",
    ]
    renamed = analyzed[export_columns].rename(
        columns={
            "attacker_name_event": "attacker_name",
            "user_name": "victim_name",
        }
    )
    renamed.to_csv(classified_kills_path, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kill- es tavolsagalapu parbajelemzes CS demohoz")
    parser.add_argument("config_positional", nargs="?", default=None, help="Opcionális config JSON pozíciós paraméterként")
    parser.add_argument("--config", type=str, default="../config/shot_kill_config.json", help="Konfiguracios JSON fajl")
    parser.add_argument("--demo", type=str, default="../data/raw/heroic-vs-parivision-ancient.dem", help="Input .dem fajl")
    parser.add_argument("--extracted", type=str, default="../data/processed/extracted_duels.csv", help="Elore kinyert tavolsag CSV")
    parser.add_argument("--out-plot", type=str, default="../outputs/plots/shot_kill_analysis.png", help="Output abra PNG")
    parser.add_argument("--out-summary", type=str, default="../data/processed/shot_kill_summary.json", help="Output osszefoglalo JSON")
    parser.add_argument(
        "--out-classified",
        type=str,
        default="../data/processed/shot_kill_distances.csv",
        help="Output CSV a tavolsaggal es parbaj-besorolassal",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=None,
        help="Kezzel megadott parbaj-sugar. Ha nincs megadva, az atlagos kill-tavolsag lesz hasznalva.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent

    config_arg = args.config_positional if args.config_positional is not None else args.config
    config_path = resolve_path(config_arg, script_dir)
    config = load_config(config_path)

    config_radius = config.get("radius")
    if config_radius is not None:
        config_radius = float(config_radius)

    effective_radius = args.radius if args.radius is not None else config_radius

    demo_path = resolve_path(args.demo, script_dir)
    extracted_path = resolve_path(args.extracted, script_dir)
    analyzed, summary = build_analysis_frame(demo_path, extracted_path, radius=effective_radius)

    out_plot_path = resolve_path(args.out_plot, script_dir)
    out_summary_path = resolve_path(args.out_summary, script_dir)
    out_classified_path = resolve_path(args.out_classified, script_dir)

    create_visualization(analyzed, summary, out_plot_path)
    save_outputs(analyzed, summary, out_summary_path, out_classified_path)

    print("=== SHOT KILL ANALYSIS ===")
    print(f"Total kills: {summary['total_kills']}")
    print(f"Shot kills: {summary['shot_kills']} ({summary['shot_kill_share_of_all']:.2%})")
    print(f"Mean duel radius (default): {summary['mean_duel_radius']:.2f}")
    print(f"Duel radius used: {summary['duel_radius_used']:.2f} ({summary['radius_source']})")
    print(f"Median shot-kill distance: {summary['median_shot_kill_distance']:.2f}")
    print(f"Duels within radius: {summary['duels_within_radius']} ({summary['duel_share_within_radius']:.2%})")
    print(f"Non-duels outside radius: {summary['non_duels_outside_radius']}")


if __name__ == "__main__":
    main()