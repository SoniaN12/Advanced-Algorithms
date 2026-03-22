from pathlib import Path

import pandas as pd

from data_loader import load_city_bbox, load_hospitals, load_road_data, attach_hospitals_to_graph
from graph_builder import build_graph_from_overpass
from helpers import build_scenarios, ensure_directories, scenario_to_node
from dijkstra_algorithm import multi_target_dijkstra
from astar_algorithm import nearest_hospital_astar
from evaluation import compare_with_baseline, measure, save_results
from visualization import save_route_map

CITY = "Potsdam, Germany"
WEIGHT = "length"

OUTPUT_DIR = Path("output")
MAPS_DIR = OUTPUT_DIR / "maps"
TABLES_DIR = OUTPUT_DIR / "tables"


def normalize_graph_node_coordinates(G):
    """
    Ensure every graph node has 'lat' and 'lon' attributes.

    Common possibilities:
    - lat/lon
    - y/x
    - latitude/longitude
    """
    fixed = 0
    missing = 0

    for node, data in G.nodes(data=True):
        if "lat" in data and "lon" in data:
            continue

        if "y" in data and "x" in data:
            data["lat"] = data["y"]
            data["lon"] = data["x"]
            fixed += 1
        elif "latitude" in data and "longitude" in data:
            data["lat"] = data["latitude"]
            data["lon"] = data["longitude"]
            fixed += 1
        else:
            missing += 1

    if missing > 0:
        raise ValueError(
            f"{missing} graph nodes are missing usable coordinates. "
            f"Expected node attributes like ('lat','lon') or ('y','x')."
        )

    return fixed


def main():
    ensure_directories([OUTPUT_DIR, MAPS_DIR, TABLES_DIR])

    print("Loading city bounding box...")
    bbox = load_city_bbox(CITY)

    print("Downloading road network from OpenStreetMap Overpass API...")
    road_data = load_road_data(bbox)

    print("Building graph...")
    G = build_graph_from_overpass(road_data)

    print("Normalizing graph node coordinates...")
    fixed_nodes = normalize_graph_node_coordinates(G)
    print(f"Coordinate normalization complete. Fixed {fixed_nodes} nodes.")

    print("Downloading hospitals...")
    hospitals_df = load_hospitals(bbox)

    print("Attaching hospitals to graph...")
    hospitals_df = attach_hospitals_to_graph(G, hospitals_df)

    if hospitals_df.empty:
        raise ValueError("No hospitals could be attached to the graph.")

    hospital_nodes = hospitals_df["node"].tolist()
    hospital_lookup = dict(zip(hospitals_df["node"], hospitals_df["hospital_name"]))

    print("Building scenarios...")
    scenarios = build_scenarios()

    rows = []

    for scenario in scenarios:
        print(f"Running scenario: {scenario.name}")

        try:
            source_node = scenario_to_node(G, scenario)

            baseline_distance, baseline_path = compare_with_baseline(
                G, hospital_nodes, source_node, weight=WEIGHT
            )

            (dij_path, dij_target, dij_dist, dij_expanded), dij_time, dij_mem = measure(
                multi_target_dijkstra, G, source_node, hospital_nodes, WEIGHT
            )

            rows.append(
                {
                    "algorithm": "Dijkstra",
                    "scenario": scenario.name,
                    "source_node": source_node,
                    "nearest_hospital_node": dij_target,
                    "nearest_hospital_name": hospital_lookup.get(dij_target, "Unknown hospital"),
                    "distance_m": round(dij_dist, 3),
                    "runtime_ms": round(dij_time, 3),
                    "memory_kb": round(dij_mem, 3),
                    "expanded_nodes": dij_expanded,
                    "matches_baseline": abs(dij_dist - baseline_distance) < 1e-6,
                }
            )

            save_route_map(
                G,
                dij_path,
                MAPS_DIR / f"{scenario.name.replace(',', '').replace(' ', '_')}_dijkstra.png",
            )

            (astar_path, astar_target, astar_dist, astar_expanded), astar_time, astar_mem = measure(
                nearest_hospital_astar, G, source_node, hospital_nodes, WEIGHT
            )

            rows.append(
                {
                    "algorithm": "A*",
                    "scenario": scenario.name,
                    "source_node": source_node,
                    "nearest_hospital_node": astar_target,
                    "nearest_hospital_name": hospital_lookup.get(astar_target, "Unknown hospital"),
                    "distance_m": round(astar_dist, 3),
                    "runtime_ms": round(astar_time, 3),
                    "memory_kb": round(astar_mem, 3),
                    "expanded_nodes": astar_expanded,
                    "matches_baseline": abs(astar_dist - baseline_distance) < 1e-6,
                }
            )

            save_route_map(
                G,
                astar_path,
                MAPS_DIR / f"{scenario.name.replace(',', '').replace(' ', '_')}_astar.png",
            )

        except Exception as e:
            print(f"Skipping scenario '{scenario.name}' بسبب error: {e}")
            continue

    if not rows:
        raise RuntimeError("No scenario completed successfully. Check graph/node attributes and routing functions.")

    results_df = pd.DataFrame(rows)
    save_results(results_df, TABLES_DIR / "experiment_results.csv")
    hospitals_df.to_csv(TABLES_DIR / "hospitals.csv", index=False)

    print("\nResults:\n")
    print(results_df.to_string(index=False))

    summary_df = (
        results_df.groupby("algorithm")
        .agg(
            avg_distance_m=("distance_m", "mean"),
            avg_runtime_ms=("runtime_ms", "mean"),
            avg_memory_kb=("memory_kb", "mean"),
            avg_expanded_nodes=("expanded_nodes", "mean"),
            all_match_baseline=("matches_baseline", "all"),
        )
        .round(3)
    )

    print("\nSummary:\n")
    print(summary_df.to_string())

    print(f"\nSaved tables to: {TABLES_DIR}")
    print(f"Saved maps to: {MAPS_DIR}")


if __name__ == "__main__":
    main()