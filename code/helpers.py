import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import requests


HEADERS = {
    "User-Agent": "EmergencyPathfindingProject/1.0 (case study)"
}

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


@dataclass
class Scenario:
    name: str
    latitude: float
    longitude: float


class Counter:
    def __init__(self):
        self.count = 0


def ensure_directories(paths: Iterable[Path]):
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def geocode_place(place_name: str):
    candidates = [place_name]

    fallback_map = {
        "Dutch Quarter, Potsdam, Germany": [
            "Holländisches Viertel, Potsdam, Germany",
            "Hollaendisches Viertel, Potsdam, Germany",
        ],
        "Sanssouci Palace, Potsdam, Germany": [
            "Schloss Sanssouci, Potsdam, Germany",
        ],
    }

    candidates.extend(fallback_map.get(place_name, []))

    for candidate in candidates:
        params = {
            "q": candidate,
            "format": "jsonv2",
            "limit": 1,
        }
        response = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=60)
        response.raise_for_status()
        data = response.json()

        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])

    raise ValueError(f"Could not geocode place: {place_name}")

def build_scenarios() -> List[Scenario]:
    places = [
        "Potsdam Hauptbahnhof, Potsdam, Germany",
        "Brandenburger Tor, Potsdam, Germany",
        "Sanssouci Palace, Potsdam, Germany",
        "Holländisches Viertel, Potsdam, Germany",
        "Babelsberg Park, Potsdam, Germany",
    ]

    scenarios = []
    for place in places:
        lat, lon = geocode_place(place)
        scenarios.append(Scenario(name=place, latitude=lat, longitude=lon))

    return scenarios

def haversine_distance(lat1, lon1, lat2, lon2):
    r = 6371000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_node(G, lat, lon):
    best_node = None
    best_dist = float("inf")

    for node, data in G.nodes(data=True):
        node_lat = data.get("lat", data.get("y", data.get("latitude")))
        node_lon = data.get("lon", data.get("x", data.get("longitude")))

        if node_lat is None or node_lon is None:
            continue

        d = haversine_distance(lat, lon, node_lat, node_lon)
        if d < best_dist:
            best_dist = d
            best_node = node

    if best_node is None:
        raise ValueError("No graph node contains valid coordinates.")

    return best_node


def scenario_to_node(G, scenario: Scenario):
    return nearest_node(G, scenario.latitude, scenario.longitude)