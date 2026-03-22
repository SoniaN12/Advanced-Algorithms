import networkx as nx

def nearest_hospital_astar(G, source, targets, weight="length"):
    best_path = None
    best_target = None
    best_dist = float("inf")

    for t in targets:
        try:
            path = nx.astar_path(G, source, t, weight=weight)
            dist = nx.astar_path_length(G, source, t, weight=weight)

            if dist < best_dist:
                best_dist = dist
                best_path = path
                best_target = t

        except nx.NetworkXNoPath:
            continue

    return best_path, best_target, best_dist, 0