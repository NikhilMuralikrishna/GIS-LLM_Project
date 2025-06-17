# DeepSeek_custom.py
import os
import re
import ollama
from LLM_Geo_kernel_DeepSeek import Solution
import LLM_Geo_Constants as constants
import helper_DeepSeek as helper


def ollama_query(prompt: str) -> str:
    formatted_prompt = f"Question: {prompt}\n\nContext: "
    try:
        response = ollama.chat(
            model="deepseek-r1:70b",
            messages=[{"role": "user", "content": formatted_prompt}],
        )
        response_content = response["message"]["content"]
        final_answer = re.sub(r"<think>.*?</think>", "", response_content, flags=re.DOTALL).strip()
        return final_answer
    except Exception as e:
        print("Error querying Ollama:", e)
        return ""


task_name = 'Buildings in Neighborhood'
TASK = """
Create a 1 km buffer around the 'Centro Storico' using the 'denominazi' attribute from the neighborhood shapefile.
Extract all buildings within this buffer, assign them to their respective neighborhoods by naming them, and generate a color-coded map displaying the buffer, neighborhood boundaries, and buildings. 
Save the result as a single shapefile..



"""

DATA_LOCATIONS = [
    "Shapefile for neighborhoods are in 'Dataset/Dati_Pesaro/neighborhoods.shp'.",
    "Shapefile for buildings are in 'Dataset/Dati_Pesaro/buildings.shp'."

]

save_dir = os.path.join(os.getcwd(),'BN')
os.makedirs(save_dir, exist_ok=True)

llm_backend = {
    "query_function": ollama_query,
    "model_name": "deepseek-r1:70b"
}

solution = Solution(
    task=TASK,
    task_name=task_name,
    save_dir=save_dir,
    data_locations=DATA_LOCATIONS,
    model=llm_backend
)

# Print prompt to LLM
print("Prompt to get solution from DeepSeek model:\n")
print(solution.direct_request_prompt)

try:
    response = solution.get_direct_request_LLM_response(review=True)
    code = solution.execute_complete_program(code=solution.direct_request_code, try_cnt=10)
    print("Generated and executed code:\n", code)
except Exception as e:
    print(f"An error occurred during LLM query or code execution: {e}")

# Confirm outputs saved
output_files = os.listdir(save_dir)
if output_files:
    print("Outputs saved successfully in:", save_dir)
    print("Files:", output_files)
else:
    print("Warning: No outputs were saved in", save_dir)
