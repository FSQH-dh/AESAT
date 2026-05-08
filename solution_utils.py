from config import Config
from file_utils import read_file
import os 
import re

def parse_solutions(response):
    """Parse solutions from LLM response"""
    solutions = []

    try:
        lines = response.strip().split('\n')

        core_pattern = re.compile(r'^(\d+)([^\.\d].*)')
        variant_pattern = re.compile(r'^(\d+\.\d+)(.*)')
        
        current_core = None
        current_variants = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            i += 1

            if not line:
                continue

            core_match = core_pattern.match(line)
            if core_match:
                if current_core is not None and current_variants:
                    solutions.append({
                        "core": current_core,
                        "variants": current_variants
                    })

                core_id = core_match.group(1)
                core_content = core_match.group(2).strip()
                current_core = core_id + core_content

                while i < len(lines):
                    next_line = lines[i].strip()
                    if not next_line:
                        i += 1
                        continue

                    if core_pattern.match(next_line) or variant_pattern.match(next_line):
                        break

                    current_core += " " + next_line
                    i += 1

                current_variants = []
                continue

            variant_match = variant_pattern.match(line)
            if variant_match:
                variant_id = variant_match.group(1)
                variant_content = variant_match.group(2).strip()
                current_variant = variant_id + variant_content

                while i < len(lines):
                    next_line = lines[i].strip()
                    if not next_line:
                        i += 1
                        continue

                    if core_pattern.match(next_line) or variant_pattern.match(next_line):
                        break

                    current_variant += " " + next_line
                    i += 1

                if current_variant.strip():
                    current_variants.append(current_variant)

        if current_core is not None and current_variants:
            solutions.append({
                "core": current_core,
                "variants": current_variants
            })

    except Exception as e:
        print(f"Error parsing solutions: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return solutions

def extract_code_from_response(response):
    """Extract code content from Claude API response"""
    try:
        start_marker = "@@@"
        end_marker = "@@@"

        start_index = response.find(start_marker)
        if start_index == -1:
            print("Code start marker not found")
            return None

        start_index += len(start_marker)
        end_index = response.find(end_marker, start_index)

        if end_index == -1:
            print("Code end marker not found")
            return None

        code_content = response[start_index:end_index].strip()
        return code_content
    except Exception as e:
        print(f"Error extracting code: {str(e)}")
        return None

def apply_code_to_template(code_result, variant_id):
    """Apply code to template"""
    try:
        replace_template = read_file("replace/restart.c")
        if replace_template:
            new_code = replace_template.replace("{{ replace_code }}", code_result)

            target_file = os.path.join("work", f"code_{variant_id}", "src","restart.c")
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(new_code)
            print(f"Successfully updated file: {target_file}")
            return True
        else:
            print("Failed to read replace template file")
            return False
    except Exception as e:
        print(f"Error replacing file: {str(e)}")
        return False

def build_solution_json(solution_id, solution_core, solution_results,iteration):
    """Build solution JSON result"""
    return {
        "solution_id": solution_id,
        "solution_core": solution_core,
        "variants_results": solution_results,
        "iteration": iteration
    }

