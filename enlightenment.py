import os
from typing import Optional, List, Dict, Any
import json
import time
import shutil
from api_utils import init_api_clients
import ray
import re
from execution_utils import wait_for_completion, calculate_total_execution_time
from parallel_cpp_runner import ExecutionWorker
from file_utils import read_file
from config import Config
from solution_utils import extract_code_from_response, apply_code_to_template

def read_file_content(file_path: str) -> Optional[str]:
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return None
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None

def append_to_file(file_path: str, content: str) -> bool:
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n" + content)
        return True
    except Exception as e:
        print(f"Error writing to file {file_path}: {str(e)}")
        return False

def get_initial_execution_time() -> float:
    try:
        history_content = read_file_content("prompt/history.txt")
        if not history_content:
            print("Cannot read history.txt file")
            return 0.0
            
        for line in history_content.split('\n'):
            if "Initial code total execution time" in line:
                match = re.search(r'Initial code total execution time: (\d+\.?\d*) seconds', line)
                if match:
                    return float(match.group(1))
        
        print("Initial execution time not found in history.txt")
        return 0.0
    except Exception as e:
        print(f"Error getting initial execution time: {str(e)}")
        return 0.0

def fix_advise():
    _, _, deepseek_api = init_api_clients()
    
    history_content = read_file_content("prompt/history.txt")
    advise_content = read_file_content("prompt/advise.txt")
    fixadvise_template = read_file_content("prompt/fixadvise.txt")
    
    if not all([history_content, advise_content, fixadvise_template]):
        print("Cannot read required files")
        return False
    
    try:
        fixadvise_prompt = fixadvise_template.format(
            history=history_content,
            advises=advise_content
        )
        
        print("Calling DeepSeek API for advice optimization...")
        response = deepseek_api.generate(fixadvise_prompt)
        
        if not response:
            print("No valid advice optimization response")
            return False
            
        print("Updating advise file...")
        success = append_to_file("prompt/advise.txt", "\ntip:" + response)
        
        if success:
            print("Advice optimization completed")
            return True
        else:
            print("Failed to update advise file")
            return False
            
    except Exception as e:
        print(f"Error in advice optimization: {str(e)}")
        return False

def fix_code():
    _, _, deepseek_api = init_api_clients()
    
    historyerror_content = read_file_content("prompt/historyerror.txt")
    code_content = read_file_content("prompt/code.txt")
    fixcode_template = read_file_content("prompt/fixcode.txt")
    
    if not all([historyerror_content, code_content, fixcode_template]):
        print("Cannot read required files")
        return False
    
    try:
        fixcode_prompt = fixcode_template.format(
            historyerror=historyerror_content,
            code=code_content
        )
        
        print("Calling DeepSeek API for code optimization...")
        response = deepseek_api.generate(fixcode_prompt)
        
        if not response:
            print("No valid code optimization response")
            return False
            
        print("Updating code file...")
        success = append_to_file("prompt/code.txt", response)
        
        if success:
            print("Code optimization completed")
            return True
        else:
            print("Failed to update code file")
            return False
            
    except Exception as e:
        print(f"Error in code optimization: {str(e)}")
        return False

def analyze_code_performance(initial_code: str, optimized_code: str, performance_improvement: float) -> str:
    _, _, deepseek_api = init_api_clients()
    
    try:
        summary_template = read_file("prompt/summary.txt")
        if not summary_template:
            print("Cannot read summary.txt template")
            return "Unable to get performance analysis"
            
        status = "improved" if performance_improvement > 0 else "degraded"
        abs_improvement = abs(performance_improvement)
        
        summary_prompt = summary_template.format(
            origincode=initial_code,
            advise="Code optimization",
            code=optimized_code,
            property=f"{status} {abs_improvement:.2f}%"
        )
        
        print("Analyzing code performance...")
        response = deepseek_api.generate(summary_prompt)
        
        if response:
            return f"Analysis: {response.strip()}"
        else:
            return "Unable to get performance analysis"
    except Exception as e:
        print(f"Error analyzing code performance: {str(e)}")
        return "Error analyzing code performance"

def experience_to_code():
    if not ray.is_initialized():
        ray.init()
    results_dir = os.path.join("work", "results")
    if os.path.exists(results_dir):
        shutil.rmtree(results_dir)
    os.makedirs(results_dir, exist_ok=True)    
    _, claude_api, deepseek_api = init_api_clients()
    
    history_content = read_file_content("prompt/history.txt")
    keycode_content = read_file_content("prompt/keycode.txt")
    experience_template = read_file_content("prompt/experience.txt")
    code_template = read_file_content("prompt/code.txt")
    
    if not all([history_content, keycode_content, experience_template, code_template]):
        print("Cannot read required files")
        return False
    
    base_execution_time = get_initial_execution_time()
    if base_execution_time <= 0:
        print("Failed to get initial execution time, using default 5000 seconds")
        base_execution_time = 5000.0
    else:
        print(f"Initial execution time from history: {base_execution_time} seconds")
    
    best_solutions = []
    
    try:
        experience_prompt = experience_template.format(
            history=history_content,
            keycode=keycode_content
        )
        
        print("Calling DeepSeek API to generate improvement idea...")
        idea_response = deepseek_api.generate(experience_prompt)
        
        if not idea_response:
            print("No valid improvement idea response")
            return False
            
        print(f"Generated improvement idea: {idea_response}")
        
        attempt_count = 0
        max_attempts = 5
        execution_time = float('inf')
        best_code_result = None
        id = 999999 
        while execution_time >= base_execution_time and attempt_count < max_attempts:
            attempt_count += 1
            print(f"\n=== Attempt {attempt_count}/{max_attempts} ===")
            
            code_prompt = code_template.format(
                code=keycode_content,
                advise=idea_response,
                rule=Config.CODE_RULE
            )
            
            print("Calling DeepSeek API to generate optimized code...")
            
            retry_count = 0
            code_result = None
            while retry_count < Config.MAX_RETRY_COUNT:
                try:
                    deepseek_response = deepseek_api.generate(code_prompt)
                    code_result = extract_code_from_response(deepseek_response)
                    if code_result:
                        break
                    print(f"Failed to extract code from DeepSeek API response, retry ({retry_count+1}/{Config.MAX_RETRY_COUNT})")
                except Exception as e:
                    print(f"Error parsing DeepSeek API response: {str(e)}, retry ({retry_count+1}/{Config.MAX_RETRY_COUNT})")
                retry_count += 1
                if retry_count >= Config.MAX_RETRY_COUNT:
                    print(f"Max retry count {Config.MAX_RETRY_COUNT} reached, unable to parse DeepSeek API response")
            
            if not code_result:
                print("Failed to extract code from DeepSeek API response")
                continue

            print("Applying generated code to solver...")
            if not apply_code_to_template(code_result, 0):
                print("Failed to apply code to template")
                continue
                
            print("Executing code and evaluating performance...")
            worker = ExecutionWorker()
            id+=1
            success = worker.execute_original(id=id, data_parallel_size=Config.DATA_PARALLEL_SIZE)
            if success:
                print(f"Code evaluation started, waiting for completion...")
                if wait_for_completion(id, Config.DATA_PARALLEL_SIZE):
                    execution_times = calculate_total_execution_time(id, Config.DATA_PARALLEL_SIZE)
                    current_execution_time = sum(execution_times) if execution_times else float('inf')
                    
                    print(f"Code execution completed, total execution time: {current_execution_time} seconds")
                    
                    if current_execution_time < execution_time:
                        execution_time = current_execution_time
                        best_code_result = code_result
                        
                    if current_execution_time < base_execution_time:
                        print(f"Execution time ({current_execution_time} seconds) is below baseline ({base_execution_time} seconds), requirement met")
                        
                        improvement_percentage = (base_execution_time - current_execution_time) / base_execution_time * 100
                        performance_analysis = analyze_code_performance(keycode_content, code_result, improvement_percentage)
                        
                        solution = {
                            'solution_id': 0,
                            'strategy': idea_response,
                            'code': code_result,
                            'execution_time': current_execution_time,
                            'base_time': base_execution_time,
                            'improvement_percentage': improvement_percentage,
                            'performance_analysis': performance_analysis
                        }
                        best_solutions.append(solution)
                        break
                    else:
                        print(f"Execution time ({current_execution_time} seconds) is above baseline ({base_execution_time} seconds), continuing...")
                        
                else:
                    print("Code execution timeout")
            else:
                print("Code execution failed")
        
        if best_solutions:
            extendGroup_content = json.dumps({
                "best_solutions": best_solutions
            }, ensure_ascii=False, indent=2)
            
            with open("prompt/extendGroup.txt", "w", encoding="utf-8") as f:
                f.write(extendGroup_content)
            
            print("Best solution saved to prompt/extendGroup.txt")
            return True
        else:
            print(f"No solution found with execution time below baseline ({base_execution_time} seconds)")
            
            if best_code_result and execution_time < float('inf'):
                print(f"Best attempt execution time: {execution_time} seconds, did not meet baseline requirement, not saving result")
            
            return False
            
    except Exception as e:
        print(f"Error in experience_to_code: {str(e)}")
        return False

if __name__ == "__main__":
    fix_advise()
    fix_code()
    experience_to_code()
