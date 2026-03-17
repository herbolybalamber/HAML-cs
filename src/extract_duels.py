import argparse
import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from demoparser2 import DemoParser


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


def pick_first_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def to_vec(yaw_deg: float, pitch_deg: float) -> np.ndarray:
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    x = math.cos(pitch) * math.cos(yaw)
    y = math.cos(pitch) * math.sin(yaw)
    z = -math.sin(pitch)
    return np.array([x, y, z], dtype=float)


def angle_error_degrees(observer_row: pd.Series, target_row: pd.Series) -> float:
    view = to_vec(float(observer_row["yaw"]), float(observer_row["pitch"]))
    delta = np.array(
        [
            float(target_row["X"]) - float(observer_row["X"]),
            float(target_row["Y"]) - float(observer_row["Y"]),
            float(target_row["Z"]) - float(observer_row["Z"]),
        ],
        dtype=float,
    )
    dist = np.linalg.norm(delta)
    if dist == 0:
        return 0.0
    direction = delta / dist
    dot = float(np.clip(np.dot(view, direction), -1.0, 1.0))
    return math.degrees(math.acos(dot))


def distance_3d(row_a: pd.Series, row_b: pd.Series) -> float:
    dx = float(row_a["X"]) - float(row_b["X"])
    dy = float(row_a["Y"]) - float(row_b["Y"])
    dz = float(row_a["Z"]) - float(row_b["Z"])
    return float(math.sqrt(dx * dx + dy * dy + dz * dz))


def nearest_state_at_tick(player_states: pd.DataFrame, player_id: str, tick: int) -> Optional[pd.Series]:
    p = player_states[player_states["steamid"] == player_id]
    if p.empty:
        return None
    idx = (p["tick"] - tick).abs().idxmin()
    return p.loc[idx]


def point_segment_distance_2d(point: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    ab = b - a
    ab_len2 = float(np.dot(ab, ab))
    if ab_len2 == 0:
        return float(np.linalg.norm(point - a))
    t = float(np.clip(np.dot(point - a, ab) / ab_len2, 0.0, 1.0))
    projection = a + t * ab
    return float(np.linalg.norm(point - projection))


def active_smokes_from_events(smoke_df: pd.DataFrame, tick: int, smoke_duration_ticks: int) -> pd.DataFrame:
    if smoke_df.empty:
        return smoke_df
    low = tick - smoke_duration_ticks
    return smoke_df[(smoke_df["tick"] <= tick) & (smoke_df["tick"] >= low)]


def smoke_obstacle_features(
    smokes: pd.DataFrame,
    attacker_row: pd.Series,
    victim_row: pd.Series,
    smoke_radius: float,
    smoke_x_col: str,
    smoke_y_col: str,
) -> Tuple[bool, bool, bool]:
    if smokes.empty:
        return False, False, False

    a2 = np.array([float(attacker_row["X"]), float(attacker_row["Y"])], dtype=float)
    v2 = np.array([float(victim_row["X"]), float(victim_row["Y"])], dtype=float)

    attacker_in_smoke = False
    victim_in_smoke = False
    smoke_between_players = False

    for _, smoke in smokes.iterrows():
        s2 = np.array([float(smoke[smoke_x_col]), float(smoke[smoke_y_col])], dtype=float)
        if np.linalg.norm(a2 - s2) <= smoke_radius:
            attacker_in_smoke = True
        if np.linalg.norm(v2 - s2) <= smoke_radius:
            victim_in_smoke = True
        if point_segment_distance_2d(s2, a2, v2) <= smoke_radius:
            smoke_between_players = True
        if attacker_in_smoke and victim_in_smoke and smoke_between_players:
            break

    return attacker_in_smoke, victim_in_smoke, smoke_between_players


def extract_duels(demo_path: Path, output_csv: Path, tickrate: int = 64) -> pd.DataFrame:
    parser = DemoParser(str(demo_path))
    try:
        header = parser.parse_header()
        map_name = header.get("map_name", "unknown")
    except Exception:
        map_name = "unknown"

    death_raw = parser.parse_events(["player_death"])
    death_df = as_event_frame(death_raw, "player_death")
    if death_df.empty:
        raise RuntimeError("A player_death event lista üres, nem található kinyerhető párbaj.")

    death_df = death_df.dropna(subset=["attacker_steamid", "user_steamid", "tick"]).copy()
    death_df = death_df[death_df["attacker_steamid"] != death_df["user_steamid"]].copy()
    death_df["attacker_steamid"] = death_df["attacker_steamid"].astype(str)
    death_df["user_steamid"] = death_df["user_steamid"].astype(str)
    death_df["tick"] = death_df["tick"].astype(int)

    state_fields = ["tick", "steamid", "name", "team_name", "X", "Y", "Z", "pitch", "yaw", "health", "armor_value"]
    state_df = parser.parse_ticks(state_fields)
    state_df = state_df.dropna(subset=["tick", "steamid", "X", "Y", "Z", "pitch", "yaw"]).copy()
    state_df["steamid"] = state_df["steamid"].astype(str)
    state_df["tick"] = state_df["tick"].astype(int)

    smoke_raw = parser.parse_events(["smokegrenade_detonate"])
    smoke_df = as_event_frame(smoke_raw, "smokegrenade_detonate")
    smoke_x_col = "X"
    smoke_y_col = "Y"
    if not smoke_df.empty:
        smoke_x_col = pick_first_existing_column(smoke_df, ["X", "x"])
        smoke_y_col = pick_first_existing_column(smoke_df, ["Y", "y"])
        if smoke_x_col is None or smoke_y_col is None:
            smoke_df = pd.DataFrame()
        else:
            smoke_df = smoke_df.dropna(subset=["tick", smoke_x_col, smoke_y_col]).copy()
        smoke_df["tick"] = smoke_df["tick"].astype(int)

    smoke_duration_ticks = int(round(18.0 * tickrate))
    smoke_radius = 144.0
    records: List[Dict] = []

    for _, kill in death_df.iterrows():
        kill_tick = int(kill["tick"])
        attacker_id = str(kill["attacker_steamid"])
        victim_id = str(kill["user_steamid"])

        attacker_state = nearest_state_at_tick(state_df, attacker_id, kill_tick)
        victim_state = nearest_state_at_tick(state_df, victim_id, kill_tick)
        if attacker_state is None or victim_state is None:
            continue

        dist = distance_3d(attacker_state, victim_state)
        attacker_view_error = angle_error_degrees(attacker_state, victim_state)
        victim_view_error = angle_error_degrees(victim_state, attacker_state)

        active_smokes = active_smokes_from_events(smoke_df, kill_tick, smoke_duration_ticks)
        atk_smoke, vic_smoke, smoke_between = smoke_obstacle_features(
            active_smokes, attacker_state, victim_state, smoke_radius, smoke_x_col, smoke_y_col
        )

        records.append(
            {
                "duel_id": f"{attacker_id}_vs_{victim_id}_at_{kill_tick}",
                "map_name": map_name,
                "tick": kill_tick,
                "attacker_steamid": attacker_id,
                "attacker_name": attacker_state.get("name", ""),
                "attacker_team": attacker_state.get("team_name", ""),
                "victim_steamid": victim_id,
                "victim_name": victim_state.get("name", ""),
                "victim_team": victim_state.get("team_name", ""),
                "weapon": kill.get("weapon", "unknown"),
                "headshot": bool(kill.get("headshot", False)),
                "penetrated": int(kill.get("penetrated", 0) if pd.notna(kill.get("penetrated", 0)) else 0),
                "attacker_x": float(attacker_state["X"]),
                "attacker_y": float(attacker_state["Y"]),
                "attacker_z": float(attacker_state["Z"]),
                "victim_x": float(victim_state["X"]),
                "victim_y": float(victim_state["Y"]),
                "victim_z": float(victim_state["Z"]),
                "distance_3d": dist,
                "attacker_view_error_deg": attacker_view_error,
                "victim_view_error_deg": victim_view_error,
                "attacker_hp_at_kill": int(attacker_state.get("health", -1)),
                "victim_hp_at_kill": int(victim_state.get("health", -1)),
                "victim_died": True,
                "attacker_in_smoke": atk_smoke,
                "victim_in_smoke": vic_smoke,
                "smoke_between_players": smoke_between,
                "active_smoke_count": int(len(active_smokes)),
            }
        )

    result = pd.DataFrame.from_records(records)
    result.to_csv(output_csv, index=False)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CS:GO .dem párbajok kinyerése (distance, angle, weapon, obstacle, death)")
    parser.add_argument("--demo", type=str, default="heroic-vs-parivision-ancient.dem", help="Input .dem fájl")
    parser.add_argument("--out", type=str, default="extracted_duels.csv", help="Output CSV")
    parser.add_argument("--tickrate", type=int, default=64, help="Demó tickrate (alapértelmezett: 64)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    demo_path = Path(args.demo)
    if not demo_path.exists():
        raise FileNotFoundError(f"A demó fájl nem található: {demo_path}")

    output_path = Path(args.out)
    data = extract_duels(demo_path=demo_path, output_csv=output_path, tickrate=args.tickrate)
    print(f"Kész: {len(data)} párbaj mentve ide: {output_path}")


if __name__ == "__main__":
    main()