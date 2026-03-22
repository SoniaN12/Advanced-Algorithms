import matplotlib.pyplot as plt

def save_route_map(G, route, filepath):
    x = [G.nodes[n]["lon"] for n in route]
    y = [G.nodes[n]["lat"] for n in route]

    plt.figure(figsize=(6, 6))
    plt.plot(x, y)
    plt.title("Route")
    plt.savefig(filepath)
    plt.close()