import os
import subprocess
import platform
import time
import glob
from datetime import datetime


class ExecutionWorker():
    def __init__(self, compile_timeout=200, execution_timeout=3000):
        self.compile_timeout = compile_timeout
        self.execution_timeout = execution_timeout
        self.error_log_path = "./prompt/historyerror.txt"
        os.makedirs(os.path.dirname(self.error_log_path), exist_ok=True)

    def _log_error(self, id, error_type, error_message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.error_log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] ID: {id} - {error_type}\n")
            f.write(f"Details:\n{error_message}\n")
            f.write("-" * 80 + "\n")

    def execute(self, id, batch_size, data_parallel_size):
        folder_index = batch_size
        print(f"Executing ID: {id}, using folder index: {folder_index}")

        compile_cmd = f"cd ./work/code_{folder_index} && ./configure && make"

        if platform.system() == 'Windows':
            raise ValueError("Windows system not supported for Kissat execution!")
        elif platform.system() == 'Linux':
            exe_ext = ""
        else:
            raise ValueError("Unsupported operating system!")

        try:
            result = subprocess.run(
                compile_cmd,
                shell=True,
                timeout=self.compile_timeout,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                error_message = f"Stdout: {result.stdout}\nStderr: {result.stderr}"
                print(f"Compilation error (ID: {id}):")
                print(error_message)
                self._log_error(id, "Compilation error", error_message)
                return False

            processes = []
            cnf_files = sorted(glob.glob("./work/data/*"))

            if not cnf_files:
                print(f"Warning (ID: {id}): No files found in ./work/data/ directory")
                return False

            for i in range(data_parallel_size):
                if i >= len(cnf_files):
                    print(f"Warning: Not enough files, skipping execution {i}")
                    continue

                cnf_file = cnf_files[i]
                abs_cnf_path = os.path.abspath(cnf_file)

                exec_cmd = f"cd ./work/code_{folder_index}/build && ./kissat -n --time=2500 {abs_cnf_path} {id}_{i}"

                proc = subprocess.Popen(
                    f"{exec_cmd} &",
                    shell=True
                )

                processes.append(proc)

            return True

        except subprocess.TimeoutExpired:
            error_message = f"Compilation timeout (ID: {id}), possibly due to serious code errors causing compiler to hang."
            print(error_message)
            self._log_error(id, "Compilation timeout", error_message)
            os.system("pkill -9 make 2>/dev/null")
            return False
        except Exception as e:
            error_message = f"Error during execution (ID: {id}): {str(e)}"
            print(error_message)
            self._log_error(id, "Execution error", error_message)
            return False

    def execute_original(self, id, data_parallel_size):
        return self.execute(id=id, batch_size=0, data_parallel_size=data_parallel_size)