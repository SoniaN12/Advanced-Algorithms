import time
import psutil
import pandas as pd
import networkx as nx

def measure(func, *args):
    process = psutil.Process()
    mem_before = process.memory_info().rss
    start = time.perf_counter()

    result = func(*args)

    end = time.perf_counter()
    mem_after = process.memory_info().rss

    return result, (end - start) * 1000, (mem_after - mem_before) / 1024

def compare_with_baseline(G, hospital_nodes, source_node, weight="length"):
    distance, path = nx.multi_source_dijkstra(G, hospital_nodes, target=source_node, weight=weight)
    return distance, path

def save_results(df, filepath):
    df.to_csv(filepath, index=False)