import os
import openai
# Uncomment necessary libraries if needed
# import requests
# import networkx as nx
# import pandas as pd
# import geopandas as gpd
# from pyvis.network import Network

from LLM_Geo_kernel import Solution
import LLM_Geo_Constants as constants
import helper

# Case 3: Visualization of Building Data in Pesaro
task_name = 'Pesaro_Building_Visualization'

TASK = """
1) Generate a map to show the distribution of building heights in Pesaro. 
Color-code the buildings by height to indicate different ranges of building heights. 
Note that the building height column is 'height' in the CSV and 'altezza' in the shapefile.

2) Generate another map to show the distribution of buildings based on the year of construction, 
highlighting historical and more recent buildings. 
Note that the year of construction column is 'year_ctr' in the CSV and 'annoctr' in the shapefile.
"""
DATA_LOCATIONS = [
    "Building data from 'Buildings2005Pesaro.csv' which contains information such as building heights (column: 'height') and years of construction (column: 'year_ctr'), stored locally at 'FB_world/CSV GIS Pesaro/Buildings2005Pesaro.csv'.",
    "Shapefile for the buildings in Pesaro from 'edifici2005.shp', which provides the spatial geometry for each building along with building heights (column: 'altezza') and years of construction (column: 'annoctr'), stored locally at 'FB_world/Dati_Pesaro/edifici2005.shp'."
]

save_dir = os.path.join(os.getcwd(), task_name)
os.makedirs(save_dir, exist_ok=True)

# Assuming Solution is a class capable of handling tasks with GIS data
model = "gpt-4o"
solution = Solution(
    task=TASK,
    task_name=task_name,
    save_dir=save_dir,
    data_locations=DATA_LOCATIONS,
    model=model,
)

print("Prompt to get solution graph:\n")
print(solution.direct_request_prompt)

try:
    direct_request_LLM_response = solution.get_direct_request_LLM_response(review=True)
    code = solution.execute_complete_program(code=solution.direct_request_code, try_cnt=10)
    print(code)
except Exception as e:
    print(f"An error occurred: {e}")
