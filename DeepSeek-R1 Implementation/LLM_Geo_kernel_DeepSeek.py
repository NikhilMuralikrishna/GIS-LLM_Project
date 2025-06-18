import LLM_Geo_Constants as constants
import helper_DeepSeek as helper
import os
import pandas as pd
import geopandas as gpd
import networkx as nx
import pickle
import time
import sys
import traceback

class Solution():
    """
    Class for GIS solutions integrated with DeepSeek.
    """

    def __init__(self,
                 task,
                 task_name,
                 save_dir,
                 role=constants.graph_role,
                 model={"query_function": helper.ollama_query, "model_name": "deepseek-r1:70b"},
                 data_locations=None,
                 stream=True,
                 verbose=True):
        
        self.task = task        
        self.solution_graph = None
        self.graph_response = None
        self.role = role
        self.data_locations = data_locations or []
        self.task_name = task_name
        self.save_dir = save_dir
        self.model = model
        self.stream = stream
        self.verbose = verbose
        self.graph_file = os.path.join(self.save_dir, f"{self.task_name}.graphml")
        self.operations = []
        self.code_for_graph = ""
        self.code_for_assembly = ""

        self.data_locations_str = '\n'.join(
            [f"{idx + 1}. {line}" for idx, line in enumerate(self.data_locations)]
        )
        self.graph_prompt = self.create_graph_prompt()

        self.direct_request_LLM_response = ''
        self.direct_request_code = ''
        self.chat_history = [{'role': 'system', 'content': role}]

    def create_graph_prompt(self):
        graph_req = constants.graph_requirement + [f"Save the network into GraphML format at: {self.graph_file}"]
        graph_req_str = '\n'.join([f"{idx + 1}. {line}" for idx, line in enumerate(graph_req)])

        return (f'Your role: {self.role}\n\n'
                f'Your task: {constants.graph_task_prefix}\n{self.task}\n\n'
                f'Requirements:\n{graph_req_str}\n\n'
                f'Example:\n{constants.graph_reply_example}\n\n'
                f'Data locations:\n{self.data_locations_str}\n')

    def get_LLM_reply(self, prompt, retry_cnt=3, sleep_sec=10, system_role=None):
        system_role = system_role or self.role
        for attempt in range(retry_cnt):
            try:
                response_text = self.model["query_function"](prompt)
                return [{"choices": [{"delta": {"content": response_text}}]}]
            except Exception as e:
                print(f"[ERROR] DeepSeek query failed ({attempt + 1}/{retry_cnt}): {e}")
                time.sleep(sleep_sec)
        raise Exception("Max retries exceeded with DeepSeek model.")

    def get_LLM_response_for_graph(self, execute=True):
        response = self.get_LLM_reply(prompt=self.graph_prompt)
        self.graph_response = response
        try:
            self.code_for_graph = helper.extract_code(response)
            if execute:
                exec(self.code_for_graph, globals())
                self.load_graph_file()
        except Exception as e:
            print("[ERROR] Graph Python code execution failed:", e)
        return self.graph_response

    def load_graph_file(self, file=""):
        file = file or self.graph_file
        if os.path.exists(file):
            self.solution_graph = nx.read_graphml(file)
            self.source_nodes = helper.find_source_node(self.solution_graph)
            self.sink_nodes = helper.find_sink_node(self.solution_graph)
        else:
            print("[WARNING] Graph file not found:", file)
            self.solution_graph = None
        return self.solution_graph

    @property
    def operation_node_names(self):
        assert self.solution_graph, "Solution graph not found. Generate it first!"
        return [name for name, attr in self.solution_graph.nodes(data=True) if attr['node_type'] == 'operation']

    def initial_operations(self):
        self.operations = []
        for node_name in self.operation_node_names:
            func_def = helper.generate_function_def(node_name, self.solution_graph)
            self.operations.append(func_def)

    def get_prompt_for_an_operation(self, operation):
        ancestors = self.get_ancestor_operations(operation['node_name'])
        ancestor_codes = '\n'.join([op['operation_code'] for oper in ancestors])
        descendants = self.get_descendant_operations_definition(self.get_descendant_operations(operation['node_name']))
        operation_prompt = (f'Your role: {constants.operation_role}\n'
                            f'Operation task: {constants.operation_task_prefix} {operation["description"]}\n'
                            f'Task context: {self.task}\n'
                            f"Python graph code:\n{self.code_for_graph}\n"
                            f'Data locations:\n{self.data_locations_str}\n'
                            f'Example reply:\n{constants.operation_reply_example}\n'
                            f'Requirements:\n{operation["description"]}\n'
                            f'Function definition: {operation["function_definition"]}\n'
                            f'Return line: {operation["return_line"]}\n'
                            f"Ancestor code:\n{ancestors}\n"
                            f"Descendants definitions:\n{descendant_defs}")
        operation['operation_prompt'] = operation_prompt = operation_prompt
        return operation_prompt

    def get_LLM_responses_for_operations(self, review=True):
        self.initial_operations()
        for idx, operation in enumerate(self.operations):
            print(f"[INFO] Generating operation {idx+1}/{len(self.operations)}: {operation['node_name']}")
            response = self.get_LLM_reply(prompt=self.get_prompt_for_an_operation(operation))
            operation['operation_code'] = helper.extract_code(response=response)
            if review:
                self.ask_LLM_to_review_operation_code(operation)
        return self.operations

    def prompt_for_assembly_program(self):
        ops_code = '\n'.join([op['operation_code'] for op in self.operations])
        assembly_req = '\n'.join([f"{idx + 1}. {line}" for idx, line in enumerate(constants.assembly_requirement)])
        self.assembly_prompt = (f"Your role: {constants.assembly_role}\n"
                                f"Task: {self.task}\n"
                                f"Requirements:\n{assembly_req}\n"
                                f"Data locations:\n{self.data_locations_str}\n"
                                f"Code:\n{ops_code}")
        return self.assembly_prompt

    def get_LLM_assembly_response(self, review=True):
        self.prompt_for_assembly_program()
        response = self.get_LLM_reply(prompt=self.assembly_prompt)
        self.assembly_LLM_response = response
        self.code_for_assembly = helper.extract_code(response)
        if review:
            self.ask_LLM_to_review_assembly_code()
        return self.assembly_LLM_response

    def save_solution(self):
        file_path = os.path.join(self.save_dir, f"{self.task_name}.pkl")
        with open(file_path, "wb") as f:
            pickle.dump(self, f)

    
    @property
    def direct_request_prompt(self):
        reqs = '\n'.join([f"{idx + 1}. {line}" for idx, line in enumerate(constants.direct_request_requirement)])
        static_output_instruction = (
            f"Always save any generated files (e.g., maps, shapefiles, or graphs) into the directory '{self.save_dir}'. "
            f"Create the directory if it does not exist. DO NOT save outputs in other locations. "
            f"In your Python code, always use: output_dir = r'{self.save_dir}'\n"
        )
        explicit_no_main_block = "\nDO NOT INCLUDE the statement 'if __name__ == \"__main__\":' in your solution. Call the function directly instead.\n"

        return (
            f'Your role: {constants.direct_request_role}\n'
            f'Your task: {constants.direct_request_task_prefix} to address: {self.task}\n'
            f'Data locations:\n{self.data_locations_str}\n'
            f'Requirements:\n{reqs}\n{explicit_no_main_block}\n'
            f'{static_output_instruction}'
        )



    def get_direct_request_LLM_response(self, review=True):
        response = self.get_LLM_reply(prompt=self.direct_request_prompt)
        self.direct_request_LLM_response = response
        self.direct_request_code = helper.extract_code(response)
        if review:
            self.ask_LLM_to_review_direct_code()
        return self.direct_request_LLM_response

    def execute_complete_program(self, code, try_cnt=10):
       unwanted_pattern = 'if __name__ == "__main__":'

       for attempt in range(try_cnt):
           print(f"\n[INFO] Executing attempt {attempt+1}/{try_cnt}")
           if unwanted_pattern in code:
              print("[WARNING] '__main__' block detected. Explicitly asking LLM to remove.")
              debug_prompt = (
                f"Your role: {constants.debug_role}\n"
                f"Your task: Remove the '{unwanted_pattern}' block from the following code and directly call the function without it.\n"
                f"The current code:\n{code}\n\n"
                "Return the corrected code explicitly."
              )
              response = self.get_LLM_reply(prompt=debug_prompt)
              code = helper.extract_code(response)

              if unwanted_pattern in code:
                print("[ERROR] '__main__' block persists after explicit request. Retrying...")
                continue

           try:
              exec(code, globals())
              print("[SUCCESS] Execution successful!")
              return code
           except Exception as err:
            print(f"[ERROR] Execution failed: {err}")
            debug_prompt = self.get_debug_prompt(err, code)
            response = self.get_LLM_reply(prompt=debug_prompt)
            corrected_code = helper.extract_code(response)
            if corrected_code.strip() == code.strip():
                print("[INFO] No further improvement detected.")
                break
            code = corrected_code

       print("[ERROR] Maximum retry attempts exceeded without successful execution.")
       return code



    def get_debug_prompt(self, exception, code):
        error_str = ''.join(traceback.format_exception(None, exception, exception.__traceback__))
        debug_prompt = (
            f"Your role: {constants.debug_role}\n"
            f"Task: Fix code according to error information.\n"
            f"Error:\n{error_str}\n"
            f"Code:\n{code}\n"
            f"Task context:\n{self.task}\n"
            f"Data locations:\n{self.data_locations_str}\n")
        return debug_prompt

    def ask_LLM_to_review_operation_code(self, operation):
        code = operation['operation_code']
        operation_prompt = operation['operation_prompt']
        review_requirement_str = '\n'.join([f"{idx + 1}. {line}" for idx, line in enumerate(constants.operation_review_requirement)])
        review_prompt = (f"Your role: {constants.operation_review_role} \n"
                         f"Your task: {constants.operation_review_task_prefix} \n\n"
                         f"Requirement: \n{review_requirement_str} \n\n"
                         f"The code is: \n----------\n{code}\n----------\n\n"
                         f"The requirements for the code is: \n----------\n{operation_prompt} \n----------\n\n")
        print("LLM is reviewing the operation code... \n")
        response = helper.get_LLM_reply(
            prompt=review_prompt,
            system_role=constants.operation_review_role,
            model=self.model,
            verbose=True,
            stream=True,
            retry_cnt=5,
        )
        new_code = helper.extract_code(response)
        reply_content = helper.extract_content_from_LLM_reply(response)
        if (reply_content == "PASS") or (new_code == ""):
            print("Code review passed, no revision.\n\n")
            new_code = code
        operation['code'] = new_code
        return operation

    def ask_LLM_to_review_assembly_code(self):
        code = self.code_for_assembly
        assembly_prompt = self.assembly_prompt
        review_requirement_str = '\n'.join([f"{idx + 1}. {line}" for idx, line in enumerate(constants.assembly_review_requirement)])
        review_prompt = (f"Your role: {constants.assembly_review_role} \n"
                         f"Your task: {constants.assembly_review_task_prefix} \n\n"
                         f"Requirement: \n{review_requirement_str} \n\n"
                         f"The code is: \n----------\n{code} \n----------\n\n"
                         f"The requirements for the code is: \n----------\n{assembly_prompt} \n----------\n\n")
        print("LLM is reviewing the assembly code... \n")
        response = helper.get_LLM_reply(
            prompt=review_prompt,
            system_role=constants.assembly_review_role,
            model=self.model,
            verbose=True,
            stream=True,
            retry_cnt=5,
        )
        new_code = helper.extract_code(response)
        if (new_code == "PASS") or (new_code == ""):
            print("Code review passed, no revision.\n\n")
            new_code = code
        self.code_for_assembly = new_code

    def ask_LLM_to_review_direct_code(self):
        code = self.direct_request_code
        direct_prompt = self.direct_request_prompt
        unwanted_pattern = 'if __name__ == "__main__":'

    # Explicit check before sending to LLM
        if unwanted_pattern in code:
           print("[WARNING] Unwanted '__main__' block detected. Asking LLM explicitly to remove it.")

           correction_prompt = (
               f"Your role: {constants.direct_review_role}\n"
               f"Your task: Remove the statement '{unwanted_pattern}' and directly call the function 'direct_solution()'.\n"
               f"The provided code:\n{code}\n\n"
               f"Return the corrected code clearly without the unwanted statement.\n"
            )
           
           response = helper.get_LLM_reply(
            prompt=correction_prompt,
            system_role=constants.direct_review_role,
            model=self.model,
            verbose=True,
            stream=True,
            retry_cnt=5,
            )
 
           corrected_code = helper.extract_code(response)
           if unwanted_pattern not in corrected_code:
                print("[SUCCESS] Unwanted block explicitly removed by LLM.")
                self.direct_request_code = corrected_code
           else:
                print("[ERROR] LLM failed to remove unwanted block.")
        else:
                print("[INFO] No unwanted blocks detected. Proceeding normally.")


