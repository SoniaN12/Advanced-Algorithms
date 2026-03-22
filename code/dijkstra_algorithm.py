import networkx as nx

def multi_target_dijkstra(G, source, targets, weight="length"):
    super_target = "__super_target__"
    G.add_node(super_target)

    for t in targets:
        G.add_edge(t, super_target, **{weight: 0})

    path = nx.dijkstra_path(G, source, super_target, weight=weight)
    dist = nx.dijkstra_path_length(G, source, super_target, weight=weight)

    real_path = path[:-1]
    nearest_target = real_path[-1]

    return real_path, nearest_target, dist, 0