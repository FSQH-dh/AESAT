import os
import shutil
from config import Config

def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None

def copy_code_folders():
    variant_count = Config.VARIANT_COUNT
    origin_code_path = os.path.join("originCode", "code")
    work_dir = "work"
    
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    
    if not os.path.exists(origin_code_path):
        print(f"Source code folder not found: {origin_code_path}")
        return False
    
    for i in range(variant_count):
        target_path = os.path.join(work_dir, f"code_{i}")
        
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        
        try:
            shutil.copytree(origin_code_path, target_path)
            print(f"Copied code folder to: {target_path}")
        except Exception as e:
            print(f"Error copying folder: {str(e)}")
            return False
    
    return True

def create_results_directories():
    results_dir = os.path.join("work", "results")
    if os.path.exists(results_dir):
        shutil.rmtree(results_dir)
    os.makedirs(results_dir, exist_ok=True)
    
    results_json_dir = os.path.join("work", "json_results")
    os.makedirs(results_json_dir, exist_ok=True)
    
    global_file = os.path.join("prompt", "global_brain.txt")
    if os.path.exists(global_file):
        with open(global_file, 'w', encoding='utf-8') as f:
            f.write('')
        print(f"Cleared global file content: {global_file}")
    
    return results_dir, results_json_dir

def save_solution_results(solution_json, solution_id, results_json_dir):
    json_file_path = os.path.join(results_json_dir, f"solution_{solution_id}_results.json")
    try:
        import json
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(solution_json, json_file, ensure_ascii=False, indent=2)
        print(f"Solution {solution_id} results saved to: {json_file_path}")
        return True
    except Exception as e:
        print(f"Error saving JSON file: {str(e)}")
        return False 