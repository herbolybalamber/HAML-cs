import argparse
from pathlib import Path

import pandas as pd


def build_summary(df: pd.DataFrame) -> dict:
    total_duels = len(df)
    smoke_duels = int(df["smoke_between_players"].sum()) if "smoke_between_players" in df.columns else 0
    headshots = int(df["headshot"].sum()) if "headshot" in df.columns else 0

    return {
        "total_duels": total_duels,
        "mean_distance_3d": float(df["distance_3d"].mean()),
        "median_distance_3d": float(df["distance_3d"].median()),
        "mean_attacker_view_error_deg": float(df["attacker_view_error_deg"].mean()),
        "mean_victim_view_error_deg": float(df["victim_view_error_deg"].mean()),
        "headshot_rate": float(headshots / total_duels) if total_duels else 0.0,
        "smoke_between_rate": float(smoke_duels / total_duels) if total_duels else 0.0,
    }


def print_summary(summary: dict) -> None:
    print("=== DUEL SUMMARY ===")
    print(f"Total duels: {summary['total_duels']}")
    print(f"Mean distance (3D): {summary['mean_distance_3d']:.2f}")
    print(f"Median distance (3D): {summary['median_distance_3d']:.2f}")
    print(f"Mean attacker view error: {summary['mean_attacker_view_error_deg']:.2f} deg")
    print(f"Mean victim view error: {summary['mean_victim_view_error_deg']:.2f} deg")
    print(f"Headshot rate: {summary['headshot_rate']:.2%}")
    print(f"Smoke-between rate: {summary['smoke_between_rate']:.2%}")


def build_weapon_stats(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby("weapon", dropna=False)
        .agg(
            duel_count=("duel_id", "count"),
            mean_distance_3d=("distance_3d", "mean"),
            median_distance_3d=("distance_3d", "median"),
            headshot_rate=("headshot", "mean"),
            mean_attacker_view_error_deg=("attacker_view_error_deg", "mean"),
            smoke_between_rate=("smoke_between_players", "mean"),
        )
        .sort_values("duel_count", ascending=False)
        .reset_index()
    )
    return grouped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Statisztika készítése a kinyert párbajokból")
    parser.add_argument("--input", type=str, default="extracted_duels.csv", help="Input CSV")
    parser.add_argument("--out-weapon", type=str, default="duel_stats_by_weapon.csv", help="Fegyver szerinti statisztika CSV")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Nincs ilyen input fájl: {input_path}")

    df = pd.read_csv(input_path)
    if df.empty:
        raise ValueError("Az input CSV üres.")

    required = [
        "duel_id",
        "weapon",
        "distance_3d",
        "headshot",
        "attacker_view_error_deg",
        "victim_view_error_deg",
        "smoke_between_players",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Hiányzó oszlop(ok): {missing}")

    summary = build_summary(df)
    print_summary(summary)

    weapon_stats = build_weapon_stats(df)
    weapon_stats.to_csv(args.out_weapon, index=False)
    print(f"\nMentve: {args.out_weapon}")


if __name__ == "__main__":
    main()