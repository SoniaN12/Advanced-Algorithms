import requests
import pandas as pd
import time
from helpers import nearest_node

HEADERS = {
    "User-Agent": "EmergencyPathfindingProject/1.0 (case study)"
}

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def load_city_bbox(city: str):
    params = {
        "q": city,
        "format": "jsonv2",
        "limit": 1,
    }

    response = requests.get(
        NOMINATIM_URL,
        params=params,
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    if not data:
        raise ValueError(f"Could not geocode city: {city}")

    item = data[0]
    bbox = item["boundingbox"]  # [south, north, west, east]

    return {
        "south": float(bbox[0]),
        "north": float(bbox[1]),
        "west": float(bbox[2]),
        "east": float(bbox[3]),
    }


def load_road_data(bbox: dict):
    query = f"""
    [out:json][timeout:60];
    (
      way["highway"]["highway"!~"footway|cycleway|path|steps|pedestrian|track|bridleway"]
      ({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});
    );
    (._;>;);
    out body;
    """

    last_error = None

    for url in OVERPASS_URLS:
        for _ in range(3):
            try:
                response = requests.post(
                    url,
                    data={"data": query},
                    headers=HEADERS,
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()

                if "elements" not in data:
                    raise ValueError("Invalid Overpass road response")

                return data

            except Exception as e:
                last_error = e
                time.sleep(2)

    raise RuntimeError(f"Failed to download road data. Last error: {last_error}")


def load_hospitals(bbox: dict):
    query = f"""
    [out:json][timeout:40];
    (
      node["amenity"="hospital"]
      ({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});
      way["amenity"="hospital"]
      ({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});
      relation["amenity"="hospital"]
      ({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});
    );
    out center tags;
    """

    last_error = None

    for url in OVERPASS_URLS:
        for _ in range(3):
            try:
                response = requests.post(
                    url,
                    data={"data": query},
                    headers=HEADERS,
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()

                rows = []
                for element in data.get("elements", []):
                    tags = element.get("tags", {})
                    name = tags.get("name", "Unnamed hospital")

                    if element["type"] == "node":
                        lat = element["lat"]
                        lon = element["lon"]
                    else:
                        center = element.get("center")
                        if not center:
                            continue
                        lat = center["lat"]
                        lon = center["lon"]

                    rows.append(
                        {
                            "hospital_name": name,
                            "latitude": lat,
                            "longitude": lon,
                        }
                    )

                hospitals_df = pd.DataFrame(rows).drop_duplicates()

                if hospitals_df.empty:
                    raise ValueError("No hospitals found in city bounding box.")

                return hospitals_df

            except Exception as e:
                last_error = e
                time.sleep(2)

    raise RuntimeError(f"Failed to download hospital data. Last error: {last_error}")


def attach_hospitals_to_graph(G, hospitals_df: pd.DataFrame):
    hospital_nodes = []

    for _, row in hospitals_df.iterrows():
        node_id = nearest_node(G, row["latitude"], row["longitude"])
        hospital_nodes.append(node_id)

    hospitals_df = hospitals_df.copy()
    hospitals_df["node"] = hospital_nodes
    hospitals_df = hospitals_df.drop_duplicates(
        subset=["node", "hospital_name"]
    ).reset_index(drop=True)

    return hospitals_df