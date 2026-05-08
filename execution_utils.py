import os
import time
import ray
from config import Config
from parallel_cpp_runner import ExecutionWorker

def wait_for_completion(task_id, parallel_size, results_dir="./work/results", timeout=3000, check_interval=5):
    expected_files = {f'finished{task_id}_{i}.txt' for i in range(parallel_size)}
    print("Starting execution")
    start_time = time.time()
    while True:
        existing_files = set(os.listdir(results_dir))
        missing_files = expected_files - existing_files
        
        if not missing_files:
            elapsed = time.time() - start_time
            return True
        
        elapsed = time.time() - start_time
        if elapsed > timeout:         
            return False       
        time.sleep(check_interval)

def calculate_total_execution_time(task_id, parallel_size, results_dir="./work/results"):
    total_times = []
    
    for i in range(parallel_size):
        result_file = os.path.join(results_dir, f"{task_id}_{i}.txt")
        if not os.path.exists(result_file):
            print(f"Result file not found: {result_file}")
            continue
            
        try:
            with open(result_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                
            if len(lines) > 1:
                process_total_time = 0
                for line in lines[1:]:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        try:
                            time_value = float(parts[1])
                            process_total_time += time_value
                        except ValueError:
                            continue
                
                total_times.append(process_total_time)
                print(f"Process {i} total execution time: {process_total_time} seconds")
        except Exception as e:
            print(f"Error reading or processing file {result_file}: {str(e)}")
    
    return total_times

@ray.remote
def execute_code_variant(variant_id, task_id):
    worker = ExecutionWorker()
    success = worker.execute(
        id=task_id,
        batch_size=variant_id,
        data_parallel_size=Config.DATA_PARALLEL_SIZE
    )
    return success, variant_id 