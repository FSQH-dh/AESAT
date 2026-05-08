from config import Config
import time
import os
import json
import ray
import random

EXECUTION_START_TIME = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

from file_utils import read_file, copy_code_folders, create_results_directories, save_solution_results
from solution_utils import parse_solutions, extract_code_from_response, apply_code_to_template, build_solution_json
from execution_utils import wait_for_completion, calculate_total_execution_time, execute_code_variant
from api_utils import init_api_clients
from parallel_cpp_runner import ExecutionWorker

GLOBAL_BRAIN_FILE = "prompt/global_brain.txt"
HISTORY_FILE = "prompt/history.txt"
gpt_api, claude_api, deepseek_api = init_api_clients()

def get_execution_count():
    global EXECUTION_START_TIME
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith("执行时间:"):
                        try:
                            return EXECUTION_START_TIME
                        except:
                            return EXECUTION_START_TIME
        return EXECUTION_START_TIME
    except Exception as e:
        print(f"Error getting execution time: {str(e)}")
        return EXECUTION_START_TIME

def increment_execution_count():
    global EXECUTION_START_TIME
    return EXECUTION_START_TIME

def update_global_brain(solution_desc, execution_time, base_time, solution_id=None, solution_code=None, initial_code=None):
    improvement = (base_time - execution_time) / base_time * 100
    status = "improved" if improvement > 0 else "degraded"
    abs_improvement = abs(improvement)
    
    reason = ""
    if solution_code and initial_code and deepseek_api:
        try:
            summary_template = read_file("prompt/summary.txt")
            if summary_template:
                prompt = summary_template.format(
                    origincode=initial_code,
                    advise=solution_desc,
                    code=solution_code,
                    property=f"{status} {abs_improvement:.2f}%"
                )
                response = deepseek_api.generate(prompt)
                reason = f"Analysis: {response.strip()}"
        except Exception as e:
            print(f"Error getting solution analysis: {str(e)}")
    
    record_id = solution_id if solution_id is not None else None
    
    if record_id is None:
        print("Reading global brain file to determine index...")
        current_index = 0
        try:
            if os.path.exists(GLOBAL_BRAIN_FILE):
                with open(GLOBAL_BRAIN_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.strip() and line.strip()[0].isdigit():
                            parts = line.split(":")
                            if len(parts) > 0 and parts[0].strip().isdigit():
                                index = int(parts[0].strip())
                                current_index = max(current_index, index + 1)
        except Exception as e:
            print(f"Error reading global brain file: {str(e)}")
        record_id = str(current_index)
    
    with open(GLOBAL_BRAIN_FILE, "a", encoding="utf-8") as f:
        f.write(f"{record_id}: {solution_desc} | Relative to baseline: {status} {abs_improvement:.2f}%{reason}\n")
    
    try:
        execution_time_str = get_execution_count()
        history_content = f"执行时间: {execution_time_str} | {record_id}: {solution_desc} | 相对基准: {status} {abs_improvement:.2f}%{reason}\n"
        
        if not os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                f.write(f"执行时间: {execution_time_str}\n")
        
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(history_content)
            
        print(f"Updated history [Execution time: {execution_time_str}, Record ID: {record_id}]: {solution_desc}, Relative to baseline: {status} {abs_improvement:.2f}%{' with analysis' if reason else ''}")
    except Exception as e:
        print(f"Error updating history file: {str(e)}")
    
    print(f"Updated global brain record [{record_id}]: {solution_desc}, Relative to baseline: {status} {abs_improvement:.2f}%{' with analysis' if reason else ''}")

def main():
    ray.init()
    
    current_execution_time = increment_execution_count()
    print(f"Current experiment execution time: {current_execution_time}")
    
    results_dir, results_json_dir = create_results_directories()
    
    time_based_dir = os.path.join(results_json_dir, current_execution_time.replace(":", "-").replace(" ", "_"))
    if not os.path.exists(time_based_dir):
        os.makedirs(time_based_dir)
        print(f"Created time-based subdirectory: {time_based_dir}")
    
    best_solutions = []
    
    if not copy_code_folders():
        print("Failed to copy code folders, terminating")
        return
        
    try:
        unique_execution_times = set()
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("执行时间:"):
                        exec_time = line.split("|")[0].strip()
                        unique_execution_times.add(exec_time)
        
        if len(unique_execution_times) > 0 and len(unique_execution_times) % 5 == 0:
            print(f"Detected {len(unique_execution_times)} unique execution times divisible by 5, calling enlightenment functions")
            
            from enlightenment import fix_advise, fix_code, experience_to_code
            
            fix_advise()
            fix_code()
            experience_to_code()
        else:
            print(f"Experiment rounds {len(unique_execution_times)} less than 5, skipping self-optimization")
    except Exception as e:
        print(f"Error checking history file or calling enlightenment functions: {str(e)}")
    
    worker = ExecutionWorker()
    
    id = 0
    success = worker.execute_original(id=id, data_parallel_size=Config.DATA_PARALLEL_SIZE)
    if success:
        print(f"Successfully executed task ID {id}, data_parallel_size: {Config.DATA_PARALLEL_SIZE}")
    else:
        print(f"Failed to execute task ID {id}")
    if wait_for_completion(id, Config.DATA_PARALLEL_SIZE):
        print("All subprocesses completed, starting subsequent processing")
    
    Base_times = calculate_total_execution_time(id, Config.DATA_PARALLEL_SIZE)
    base_total_time = sum(Base_times)
    print(f"Initial code total execution time: {base_total_time} seconds")
    
    try:
        execution_time_str = get_execution_count()
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"Execution time: {execution_time_str} | Initial code total execution time: {base_total_time} seconds\n")
        print(f"Recorded initial code total execution time in history: {base_total_time} seconds")
    except Exception as e:
        print(f"Error recording initial code execution time to history file: {str(e)}")
    
    
    advise_prompt_template = read_file("prompt/advise.txt")
    if not advise_prompt_template:
        print("Cannot read advise file")
        return
    
    code_content = read_file(Config.CODE_SOURCE_PATH)
    if not code_content:
        print(f"Cannot read code source file: {Config.CODE_SOURCE_PATH}")
        return
    
    prompt = advise_prompt_template.format(
        code=code_content,
        num=Config.SOLUTION_COUNT,
        nums=Config.VARIANT_COUNT
    )
    
    print("Generating solutions...")
    
    retry_count = 0
    solutions = None
    while retry_count < Config.MAX_RETRY_COUNT:
        try:
            response = gpt_api.generate(prompt)
            solutions = parse_solutions(response)
            if solutions and len(solutions) > 0:
                break
            print(f"Parsed solution result is empty, retry ({retry_count+1}/{Config.MAX_RETRY_COUNT})")
        except Exception as e:
            print(f"Error parsing solutions: {str(e)}, retry ({retry_count+1}/{Config.MAX_RETRY_COUNT})")
        retry_count += 1
        if retry_count >= Config.MAX_RETRY_COUNT:
            print(f"Max retry count {Config.MAX_RETRY_COUNT} reached, unable to parse solutions")
            return
    
    print(f"Generated {len(solutions)} solutions:")
    for i, solution in enumerate(solutions):
        print(f"Solution {i+1}: {solution['core']}")
        for j, variant in enumerate(solution['variants']):
            print(f" Variant {j+1}: {variant}")
    
    code_prompt_template = read_file("prompt/code.txt")
    if not code_prompt_template:
        print("Cannot read code.txt template")
        return
    
    newadvise_prompt_template = read_file("prompt/newadvise.txt")
    if not newadvise_prompt_template:
        print("Cannot read newadvise.txt template")
        return
    
    newcode_prompt_template = read_file("prompt/newcode.txt")
    if not newcode_prompt_template:
        print("Cannot read newcode.txt template")
        return
    
    for i, solution in enumerate(solutions):
        print(f"\nProcessing solution {i+1}: {solution['core']}")
        
        current_best_strategy = solution['core']
        solution_best_time = float('inf')
        current_best_code = None
        
        for iteration in range(Config.MAX_ITERATIONS):
            id += Config.VARIANT_COUNT
            print(f"\n==== Solution {i+1} iteration {iteration+1}/{Config.MAX_ITERATIONS} ====")
            print(f"Current best strategy: {current_best_strategy}")
            
            if iteration > 0:
                improvement = (base_total_time - solution_best_time) / base_total_time * 100
                status = "improved" if improvement > 0 else "degraded"
                abs_improvement = abs(improvement)
                performance_grade = f"{status} {abs_improvement:.2f}%"
                
                new_prompt = newadvise_prompt_template.format(
                    code=code_content,
                    advise=current_best_strategy,
                    nums=Config.VARIANT_COUNT,
                    grade=performance_grade
                )
                print("Generating new variants based on best strategy...")
                new_response = deepseek_api.generate(new_prompt)
                new_solutions = parse_solutions(new_response)
                
                if new_solutions and len(new_solutions) > 0:
                    current_variants = new_solutions[0]['variants']
                    print(f"Generated {len(current_variants)} new variants")
                    if len(current_variants) > Config.VARIANT_COUNT:
                        print("Variant count exceeds configuration, removing excess variants")
                        del current_variants[Config.VARIANT_COUNT:]
                    for j, variant in enumerate(current_variants):
                        print(f" Variant {j+1}: {variant}")
                else:
                    print("Unable to generate new variants, using original variants")
                    current_variants = solution['variants']
            else:
                current_variants = solution['variants']
            
            solution_results = []
            variant_code_results = {}
            
            for j, variant in enumerate(current_variants):
                print(f"Processing variant {j+1}: {variant}")
                
                if iteration == 0 or current_best_code is None:
                    code_prompt = code_prompt_template.format(
                        code=code_content,
                        advise=variant,
                        rule=Config.CODE_RULE
                    )
                else:
                    improvement = (base_total_time - solution_best_time) / base_total_time * 100
                    status = "improved" if improvement > 0 else "degraded"
                    abs_improvement = abs(improvement)
                    performance_grade = f"{status} {abs_improvement:.2f}%"
                    
                    code_prompt = newcode_prompt_template.format(
                        code=code_content,
                        old_advise=current_best_strategy,
                        old_code=current_best_code,
                        advise=variant,
                        grade=performance_grade,
                        rule=Config.CODE_RULE
                    )
                
                print("Calling Claude API...")
                
                retry_count = 0
                code_result = None
                while retry_count < Config.MAX_RETRY_COUNT:
                    try:
                        claude_response = claude_api.generate(code_prompt)
                        code_result = extract_code_from_response(claude_response)
                        if code_result:
                            break
                        print(f"Failed to extract code from Claude API response, retry ({retry_count+1}/{Config.MAX_RETRY_COUNT})")
                    except Exception as e:
                        print(f"Error parsing Claude API response: {str(e)}, retry ({retry_count+1}/{Config.MAX_RETRY_COUNT})")
                    retry_count += 1
                    if retry_count >= Config.MAX_RETRY_COUNT:
                        print(f"Max retry count {Config.MAX_RETRY_COUNT} reached, unable to parse Claude API response")
                
                if code_result:
                    apply_code_to_template(code_result, j)
                else:
                    print("Failed to extract code from Claude API response")

                variant_code_results[j] = code_result

            print(f"\nStarting Ray parallel execution of replaced code")
            print(f"Parallel launching {len(current_variants)} optimized variant executions")
            ray_tasks = []
            for variant_id in range(len(current_variants)):
                variant_task_id = id + 1 + variant_id
                print(f"Variant {variant_id} assigned task ID: {variant_task_id}")
                ray_task = execute_code_variant.remote(variant_id, variant_task_id)
                ray_tasks.append((variant_task_id, ray_task))
            
            successful_variants = []
            for variant_task_id, ray_task in ray_tasks:
                try:
                    success, variant_id = ray.get(ray_task)
                    
                    if success and wait_for_completion(variant_task_id, Config.DATA_PARALLEL_SIZE):
                        successful_variants.append(variant_task_id)
                    else:
                        print(f"Variant {variant_id} (task ID: {variant_task_id}) execution failed or timeout")
                except Exception as e:
                    print(f"Error processing task ID {variant_task_id}: {str(e)}")
            
            print(f"Ray parallel execution completed, successful variants: {len(successful_variants)}/{len(current_variants)}")
            
            best_variant = None
            best_execution_time = float('inf')
            
            for variant_task_id in successful_variants:
                variant_id = variant_task_id - (id + 1)
                
                if variant_id < len(current_variants):
                    execution_times = calculate_total_execution_time(variant_task_id, Config.DATA_PARALLEL_SIZE)
                    total_execution_time = sum(execution_times) if execution_times else 0
                    
                    variant_text = current_variants[variant_id]
                    
                    variant_result = {
                        "variant_id": variant_id,
                        "variant_task_id": variant_task_id,
                        "variant_text": variant_text,
                        "execution_time": total_execution_time,
                        "code_result": variant_code_results[variant_id]
                    }
                    
                    solution_results.append(variant_result)
                    
                    if total_execution_time < best_execution_time:
                        best_execution_time = total_execution_time
                        best_variant = variant_result
            
            iteration_json = build_solution_json(
                solution_id=i, 
                solution_core=current_best_strategy, 
                solution_results=solution_results,
                iteration=iteration
            )
            
            save_solution_results(iteration_json, f"{i}_iteration_{iteration}", time_based_dir)
            
            if best_variant:
                print(f"\nBest variant found in this iteration: {best_variant['variant_text']}")
                print(f"Best variant execution time: {best_variant['execution_time']} seconds")
                current_best_strategy = best_variant['variant_text']
                current_best_code = best_variant['code_result']
                
                if best_variant['execution_time'] < solution_best_time:
                    solution_best_time = best_variant['execution_time']
            else:
                print("\nNo valid variant found in this iteration, continuing with current strategy")
            
            print(f"Completed iteration {iteration+1}/{Config.MAX_ITERATIONS}")
        
        if solution_best_time != float('inf'):
            best_solutions.append({
                'solution_id': i,
                'strategy': current_best_strategy,
                'code': current_best_code,
                'execution_time': solution_best_time
            })
            
            update_global_brain(
                f"Solution {i}: {solution['core']}", 
                solution_best_time, 
                base_total_time,
                str(i),
                current_best_code,
                code_content
            )
    print("\n==== Starting solution evolution phase ====")
    
    try:
        extend_group_content = read_file("prompt/extendGroup.txt")
        if extend_group_content:
            print("Loading extendGroup.txt data...")
            
            extend_group_data = json.loads(extend_group_content)
            extend_solutions = extend_group_data.get("best_solutions", [])
            
            if extend_solutions:
                print(f"Loaded {len(extend_solutions)} additional solutions from extendGroup.txt")
                
                next_solution_id = len(best_solutions)
                
                for extend_solution in extend_solutions:
                    original_id = extend_solution['solution_id']
                    extend_solution['solution_id'] = str(next_solution_id)
                    next_solution_id += 1
                    
                    print(f"Adding external solution: original ID {original_id} -> new ID {extend_solution['solution_id']}, execution time: {extend_solution['execution_time']} seconds")
                    
                    update_global_brain(
                        f"External solution {extend_solution['solution_id']}: {extend_solution['strategy']}", 
                        extend_solution['execution_time'], 
                        base_total_time,
                        extend_solution['solution_id'],
                        extend_solution['code'],
                        code_content
                    )
                
                best_solutions.extend(extend_solutions)
                print(f"After adding external solutions, total {len(best_solutions)} solutions available for evolution")
    except Exception as e:
        print(f"Error loading extendGroup.txt data: {str(e)}")
    
    next_solution_id = len(best_solutions)
    
    evolve_prompt_template = read_file("prompt/evolve.txt")
    if not evolve_prompt_template:
        print("Cannot read evolve.txt template")
        return
    
    print(f"Collected {len(best_solutions)} solutions available for evolution")
    
    iteration = 0
    id += Config.VARIANT_COUNT
    
    final_iteration_done = False
    
    while len(best_solutions) > 1:
        print(f"\n==== Evolution iteration {iteration+1} ====")
        print(f"Currently {len(best_solutions)} strategies remaining")
        
        if len(best_solutions) == 2 and final_iteration_done:
            print("Only two strategies left, final iteration completed, ending evolution")
            break
            
        if len(best_solutions) == 2:
            final_iteration_done = True
            
        evolved_solutions = []
        
        global_brain_content = read_file(GLOBAL_BRAIN_FILE)
        if not global_brain_content:
            print("Cannot read global brain file")
            return     
        evolve_select_template = read_file("prompt/evolveSelect.txt")
        if not evolve_select_template:
            print("Cannot read evolveSelect.txt template")
            return
        
        evolve_select_prompt = evolve_select_template.format(
            origincode=code_content,
            globalbrain=global_brain_content             
        )
        
        print("Generating strategy combination scheme...")
        select_response = deepseek_api.generate(evolve_select_prompt)
        
        pairs = []
        if "@@" in select_response:
            match_content = select_response.split("@@")[1].strip()
            for line in match_content.strip().split("\n"):
                if line.strip():
                    pairs.append(line.strip())
            
            print(f"Obtained {len(pairs)} strategy pairs")
        else:
            print("Unable to parse strategy combinations from response")
            for i in range(0, len(best_solutions), 2):
                if i + 1 < len(best_solutions):
                    pairs.append(f"{i},{i+1}")
        
        for pair in pairs:
            idx_parts = pair.split(",")
            if len(idx_parts) < 2:
                print(f"Invalid strategy combination: {pair}")
                continue
            
            try:
                id1 = idx_parts[0].strip()
                id2 = idx_parts[1].strip()
                
                parent1 = None
                parent2 = None
                
                for solution in best_solutions:
                    if str(solution['solution_id']) == id1:
                        parent1 = solution
                    elif str(solution['solution_id']) == id2:
                        parent2 = solution
                
                if not parent1 or not parent2:
                    print(f"Unable to find strategy ID {id1} or {id2}, skipping this combination")
                    continue
                      
                print(f"Hybridizing strategies: {parent1['solution_id']} and {parent2['solution_id']}")
                
                evolve_prompt = evolve_prompt_template.format(
                    origincode=code_content,
                    advise=parent1['strategy'],
                    code=parent1['code'],
                    newadvise=parent2['strategy'],
                    newcode=parent2['code'],
                    rule=Config.CODE_RULE
                )
                
                print("Generating hybrid strategy...")
                
                retry_count = 0
                evolved_code = None
                while retry_count < Config.MAX_RETRY_COUNT:
                    try:
                        deepseek_response = deepseek_api.generate(evolve_prompt)
                        evolved_code = extract_code_from_response(deepseek_response)
                        if evolved_code:
                            break
                        print(f"Failed to extract hybrid code from response, retry ({retry_count+1}/{Config.MAX_RETRY_COUNT})")
                    except Exception as e:
                        print(f"Error parsing hybrid code: {str(e)}, retry ({retry_count+1}/{Config.MAX_RETRY_COUNT})")
                    retry_count += 1
                    if retry_count >= Config.MAX_RETRY_COUNT:
                        print(f"Max retry count {Config.MAX_RETRY_COUNT} reached, unable to parse hybrid code")
                
                if not evolved_code:
                    print("Failed to extract hybrid code from response, keeping better performing parent strategy")
                    # 保留性能更好的父策略
                    better_parent = parent1 if parent1['execution_time'] < parent2['execution_time'] else parent2
                    evolved_solutions.append(better_parent)
                    continue
                
                # 应用代码到模板
                apply_code_to_template(evolved_code, 0)
                
                # 为杂交策略分配新ID
                id += 1
                evolved_task_id = id
                
                print(f"Preparing to execute hybrid strategy (task ID: {evolved_task_id})...")
                
                ray_task = execute_code_variant.remote(0, evolved_task_id)
                success, variant_id = ray.get(ray_task)
                
                if success and wait_for_completion(evolved_task_id, Config.DATA_PARALLEL_SIZE):
                    print(f"Hybrid strategy (task ID: {evolved_task_id}) executed successfully")
                    
                    exec_times = calculate_total_execution_time(evolved_task_id, Config.DATA_PARALLEL_SIZE)
                    if exec_times:
                        total_execution_time = sum(exec_times)
                        
                        evolved_strategy = f"Hybrid strategy {parent1['solution_id']}+{parent2['solution_id']}"
                        hybrid_solution_id = str(next_solution_id)
                        next_solution_id += 1
                        
                        evolved_solution = {
                            'solution_id': hybrid_solution_id,
                            'strategy': evolved_strategy,
                            'code': evolved_code,
                            'execution_time': total_execution_time,
                            'parents': [parent1['solution_id'], parent2['solution_id']]
                        }
                        
                        evolved_solutions.append(evolved_solution)
                        print(f"Hybrid strategy execution time: {total_execution_time} seconds")
                        
                        update_global_brain(
                            f"Hybrid strategy {evolved_solution['solution_id']}: {evolved_strategy}", 
                            total_execution_time, 
                            base_total_time,
                            hybrid_solution_id,
                            evolved_code,
                            code_content
                        )
                    else:
                        print("Unable to get hybrid strategy execution time, keeping better performing parent strategy")
                        better_parent = parent1 if parent1['execution_time'] < parent2['execution_time'] else parent2
                        evolved_solutions.append(better_parent)
                else:
                    print(f"Hybrid strategy (task ID: {evolved_task_id}) execution failed or timeout")
            except Exception as e:
                print(f"Error processing strategy combination {pair}: {str(e)}")
        
        combined_solutions = best_solutions + evolved_solutions

        unique_solutions = {}
        for solution in combined_solutions:
            solution_id = str(solution['solution_id'])
            if solution_id in unique_solutions:
                print("Duplicate ID found, checking error")
                if solution['execution_time'] < unique_solutions[solution_id]['execution_time']:
                    unique_solutions[solution_id] = solution
            else:
                unique_solutions[solution_id] = solution

        combined_solutions = list(unique_solutions.values())
        
        score_prompt_template = read_file("prompt/score.txt")
        if not score_prompt_template:
            print("Cannot read score.txt template")
            return
            
        global_brain_content = read_file(GLOBAL_BRAIN_FILE)
        if not global_brain_content:
            print("Cannot read global brain file content")
            return
            
        score_prompt = score_prompt_template.format(
            tactics=global_brain_content
        )
        
        print("Getting strategy scores...")
        score_response = deepseek_api.generate(score_prompt)
        
        strategy_scores = {}
        if "@@" in score_response:
            score_content = score_response.split("@@")[1].strip() if len(score_response.split("@@")) > 1 else ""
            for line in score_content.strip().split("\n"):
                if line.strip() and "," in line:
                    try:
                        strategy_id, score = line.strip().split(",")
                        strategy_scores[strategy_id.strip()] = float(score.strip())
                    except Exception as e:
                        print(f"Error parsing score line '{line}': {str(e)}")
        
        print(f"Obtained scores for {len(strategy_scores)} strategies")
        
        for solution in combined_solutions:
            solution_id = str(solution['solution_id'])
            innovation_complexity_score = strategy_scores.get(solution_id, 10.0)
            if solution['execution_time']!=0:
               time_score = base_total_time / solution['execution_time']
            else:
               time_score = 1 
            random_score = random.random()
            final_score = (time_score * 0.4) + (innovation_complexity_score / 20 * 0.4) + (random_score * 0.2)
            solution['final_score'] = final_score
            solution['innovation_complexity_score'] = innovation_complexity_score
            solution['random_score'] = random_score
            
            print(f"Strategy {solution_id} final score: {final_score:.4f} (time performance: {time_score:.4f}, innovation complexity: {innovation_complexity_score}, random: {random_score:.4f})")
        
        best_time_solution = min(combined_solutions, key=lambda x: x['execution_time'])
        print(f"Best time performance strategy: {best_time_solution['solution_id']} ({best_time_solution['execution_time']} seconds)")
        
        remaining_solutions = [s for s in combined_solutions if s['solution_id'] != best_time_solution['solution_id']]
        
        remaining_solutions.sort(key=lambda x: x['final_score'], reverse=True)
        
        keep_count = max(0, len(remaining_solutions) // 2)
        
        kept_solutions = remaining_solutions[:keep_count]
        removed_solutions = remaining_solutions[keep_count:]
        
        kept_solutions.insert(0, best_time_solution)
        
        print(f"Kept total {len(kept_solutions)} strategies (including time-optimal strategy and {keep_count} highest-scoring strategies)")
        for k in kept_solutions:
            print(f"  + Kept strategy {k['solution_id']}: final score {k.get('final_score', 'time-optimal'):.4f}, execution time {k['execution_time']} seconds")
        
        print(f"Eliminated {len(removed_solutions)} worst-performing strategies")
        for r in removed_solutions:
            print(f"  - Eliminated strategy {r['solution_id']}: final score {r['final_score']:.4f}, execution time {r['execution_time']} seconds")
            
        best_solutions = kept_solutions
        
        evolved_json = {
            'iteration': iteration,
            'evolved_solutions': evolved_solutions
        }
        
        with open(os.path.join(time_based_dir, f"evolution_iteration_{iteration}.json"), 'w', encoding='utf-8') as f:
            json.dump(evolved_json, f, ensure_ascii=False, indent=2)
        
        try:
            if os.path.exists(GLOBAL_BRAIN_FILE):
                with open(GLOBAL_BRAIN_FILE, "r", encoding="utf-8") as f:
                    brain_lines = f.readlines()
                
                current_solution_ids = [str(sol['solution_id']) for sol in best_solutions]
                
                filtered_brain_lines = []
                for line in brain_lines:
                    line_stripped = line.strip()
                    if not (line_stripped and line_stripped[0].isdigit()):
                        filtered_brain_lines.append(line)
                        continue
                        
                    solution_id_match = line_stripped.split(':')[0].strip()
                    if solution_id_match in current_solution_ids:
                        filtered_brain_lines.append(line)
                
                with open(GLOBAL_BRAIN_FILE, "w", encoding="utf-8") as f:
                    f.writelines(filtered_brain_lines)
                
                print(f"Updated global brain records, deleted unused strategies")
        except Exception as e:
            print(f"Error updating global brain records: {str(e)}")
            
        iteration += 1
    
    if best_solutions:
        final_best = best_solutions[0]
        print("\n==== Evolution completed ====")
        print(f"Final best strategy: {final_best['solution_id']}")
        print(f"Execution time: {final_best['execution_time']} seconds")
        print(f"Improvement relative to baseline: {(base_total_time - final_best['execution_time']) / base_total_time * 100:.2f}%")
        
        final_result = {
            'best_strategy_id': final_best['solution_id'],
            'strategy_description': final_best['strategy'],
            'code': final_best['code'],
            'execution_time': final_best['execution_time'],
            'base_time': base_total_time,
            'improvement_percentage': (base_total_time - final_best['execution_time']) / base_total_time * 100
        }
        
        with open(os.path.join(time_based_dir, "final_best_solution.json"), 'w', encoding='utf-8') as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
    else:
        print("\n==== Evolution failed ====")
        print("Unable to produce valid final strategy")

    ray.shutdown()
    
if __name__ == "__main__":
    main()
