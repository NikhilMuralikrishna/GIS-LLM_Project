import re
import subprocess
import pandas as pd
import geopandas as gpd
import networkx as nx
from pyvis.network import Network
import logging
import time
from collections import deque
import LLM_Geo_Constants as constants


def ollama_query(prompt: str) -> str:
    try:
        result = subprocess.run(
            ["ollama", "query", "deepseek-r1:70b", prompt],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print("[ERROR] Ollama subprocess query failed:", e)
        return ""

def extract_content_from_LLM_reply(response):
    if isinstance(response, str):
        return response
    content = ""
    if isinstance(response, list):
        for chunk in response:
            chunk_content = chunk["choices"][0]["delta"].get("content")
            if chunk_content:
                content += chunk_content
    else:
        content = response.get("message", {}).get("content", "")
    return content

def extract_code(response, verbose=False):
    python_code = ""
    reply_content = extract_content_from_LLM_reply(response)
    python_code_match = re.search(r"```(?:python)?(.*?)```", reply_content, re.DOTALL)
    if python_code_match:
        python_code = python_code_match.group(1).strip()
    if verbose:
        print(python_code)
    return python_code

def get_LLM_reply(prompt,
                  system_role=None,
                  model={"query_function": ollama_query, "model_name": "deepseek-r1:70b"},
                  stream=True,
                  verbose=True,
                  retry_cnt=3,
                  sleep_sec=10):
    """
    Query DeepSeek backend via ollama_query.
    """
    # Append system_role into prompt if provided
    if system_role:
        prompt = f"{system_role}\n\n{prompt}"

    for attempt in range(retry_cnt):
        try:
            response_text = model["query_function"](prompt)
            simulated_response = [{"choices": [{"delta": {"content": response_text}}]}]
            if verbose:
                print("[LLM Response]:", response_text)
            return simulated_response
        except Exception as e:
            if verbose:
                print(f"[ERROR] Attempt {attempt + 1}/{retry_cnt} failed: {e}")
            time.sleep(sleep_sec)
    raise RuntimeError("Exceeded max retries, no response from DeepSeek model.")



def has_disconnected_components(directed_graph, verbose=True):
    weakly_connected = list(nx.weakly_connected_components(directed_graph))
    if len(weakly_connected) > 1:
        if verbose:
            print("[WARNING] Graph has disconnected components!")
        return True
    return False

def bfs_traversal(graph, start_nodes):
    from collections import deque
    visited = set()
    queue = deque(start_nodes)
    traversal_order = []
    while queue:
        node = queue.popleft()
        if node not in visited:
            visited.add(node)
            traversal_order.append(node)
            queue.extend(neighbor for neighbor in graph[node] if neighbor not in visited)
    return traversal_order

def generate_function_def(node_name, G):
    node_dict = G.nodes[node_name]
    para_str, para_default_str = '', ''
    for predecessor in G.predecessors(node_name):
        para_node = G.nodes[predecessor]
        data_path = para_node.get('data_path', '')
        if data_path:
            para_default_str += f"{predecessor}='{data_path}', "
        else:
            para_str += f"{predecessor}, "
    all_params = f"{para_str}{para_default_str}".rstrip(', ')
    function_definition = f"def {node_name}({para_str}{para_default_str.rstrip(', ')}):"
    return_line = f"    return {', '.join(G.successors(node_name))}"
    return {
        'node_name': node_name,
        'description': node_dict.get('description', ''),
        'function_definition': function_def,
        'return_line': return_line
    }

def generate_function_def_list(G):
    nodes_without_predecessors = [node for node in G.nodes() if G.in_degree(node) == 0]
    traversal_order = bfs_traversal(G, nodes_without_predecessors)
    def_list, data_nodes = [], []
    for node_name in traversal_order:
        node_type = G.nodes[node_name]['node_type']
        if node_type == 'operation':
            def_list.append(generate_function_def(node_name, G))
        elif node_type == 'data':
            data_nodes.append(node_name)
    return def_list, data_nodes

def get_data_sample_text(file_path, file_type="csv", encoding="utf-8"):
    try:
        if file_type == "csv":
            df = pd.read_csv(file_path)
            return df.head(3).to_string()
        elif file_type == "shp":
            gdf = gpd.read_file(file_path)
            return gdf.head(3).to_string()
        elif file_type == "txt":
            with open(file_path, encoding=encoding) as f:
                lines = f.readlines()[:3]
                return ''.join(lines)
    except Exception as e:
        return f"[ERROR] Failed to read sample data: {e}"

def show_graph(G):    
    if has_disconnected_components(directed_graph=G):
        print("[ERROR] Graph has disconnected components! Review your graph structure.")
        return
    nt = Network(notebook=True, directed=True, height="800px")
    nt.from_nx(G)
    for node in nt.nodes:
        node_data = G.nodes[node['id']]
        if node_data['node_type'] == 'data':
            node['color'] = 'orange'
        elif node_data['node_type'] == 'operation':
            node['color'] = 'deepskyblue'
    nt.show('graph.html')

def find_sink_node(G):
    return [node for node in G.nodes() if G.out_degree(node) == 0 and G.in_degree(node) > 0]

def find_source_node(G):
    return [node for node in G.nodes() if G.in_degree(node) == 0]
