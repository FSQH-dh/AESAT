# AESAT: Auto-Evolving SAT solving

*(English | [中文](README_zh.md))*

🎉 **Exciting News!** Our paper, **"Bridging LLMs and SAT Solving: Automated Evolution of High-Performance Heuristics"**, has been accepted by **IJCAI 2026**! We warmly invite everyone to read the paper once it is officially published.

Welcome to AESAT! This is the exact framework that powered our solver, AE-Kissat-MAB, to win the main track of the **SAT Competition 2025** by a wide and absolute margin. 

## What is AESAT?

Modern SAT solvers are incredibly sophisticated, making it extremely difficult for human experts to achieve significant further improvements. AESAT is a novel neuro-symbolic framework designed to automatically evolve and optimize the heuristic functions of SAT solvers. 

It employs a memetic-inspired approach that bridges Large Language Models (LLMs) and SAT solving:
- **Mixture-of-Experts (MoE) Architecture**: It dynamically utilizes different LLMs for specific tasks (e.g., GPT-4.5 for creative idea generation, Claude 3.7 for robust code implementation, and DeepSeek-R1 for deep logical analysis and evolutionary crossover).
- **Synergizing Search**: It combines LLM-guided individual local refinement with global evolutionary exploration.
- **Self-Optimizing Prompts**: The framework learns from historical performance data to iteratively refine its own prompts, avoiding repeated mistakes and guiding the LLMs toward more fruitful algorithmic directions.

## What Can You Use It For?

This framework was primarily developed around the end of **2024**. Its overall design was heavily influenced by the capabilities of LLMs at that time (specifically, limited context windows and attention spans). Therefore, its architecture is highly specialized for a very specific, yet incredibly powerful use case:

**🎯 You can use AESAT to optimize heuristic functions, scoring mechanisms, or any other critical snippets of code that you are uncertain about, but whose performance is absolutely vital to your system.**

Here is why you should use it:
- **Unrivaled Modular Optimization**: Through extensive experiments, we've found that AESAT's ability to optimize isolated, modular functions is astonishingly strong. Even compared to our latest, more advanced frameworks, AESAT's single-module optimization capability remains the absolute best. It consistently discovers counter-intuitive, highly effective algorithmic logic that human experts often overlook.
- **Perfect Companion for Human Intuition**: If you have a hunch that a specific function is a bottleneck, or you want to experiment with a new heuristic design but don't know the exact mathematical formulation, you can point AESAT to that specific module. It acts as an untiring research assistant, generating, testing, and evolving the code until it finds the optimal variant.

**A Note on Limitations and Future Work:**
The biggest strength of AESAT is also its main limitation: it can only optimize a single module at a time. It works best when paired with human experience to identify *where* to focus the optimization. Our subsequent and upcoming frameworks have improved upon this issue, gradually reducing the reliance on human factors and expanding to broader optimizations. Stay tuned!

---

## System Requirements
- **Operating System**: Linux
- **Python**: 3.8+
- **Dependencies**: `ray`, `requests`, `python-dotenv`
- **Build Environment**: GCC compiler (for compiling Kissat source code)

## Project Structure
- `work/data/`: Test Data Directory (contains SAT problem `.cnf` instance files).
- `prompt/`: Prompt Template Directory (core code, generation prompts, global brain experience, etc.).
- `originCode/code/`: Original Kissat Source Code directory.
- `work/results/` & `work/json_results/`: Execution and JSON format result directories.
- `replace/`: Code Replacement Directory (generated code variant files).

## Detailed Execution Steps

### 1. Environment Setup
```bash
pip install -r requirements.txt
pip install ray
cd originCode/code && make
```

### 2. Configure API Keys
Edit the `config.py` file to set your API keys and model configurations for OpenAI, Claude, and DeepSeek.

> [!TIP]
> **Model Configuration Recommendation**
> To maximize the synergistic effects of the Mixture-of-Experts (MoE) architecture, we **strongly recommend using three different models** for their respective tasks (e.g., GPT-4.5 for generation, Claude 3.7 for implementation, and DeepSeek-R1 for analysis). While it is technically possible to configure all three APIs to use the same model, doing so will significantly reduce the optimization performance.

### 3. Prepare Test Data
Please download the test case data from `work/data/download.txt`.

### 4. Run the System
```bash
python main.py
```
The system will initialize Ray, run baseline testing, generate solution variants, and execute a multi-round evolutionary optimization process.

### 5. View Results
Real-time monitoring is available in the console. Detailed iteration records, performance comparisons, and the final optimal solution can be found in `work/json_results/{timestamp}/`.

## Configuration Parameters
Key parameters in `config.py`:
- `SOLUTION_COUNT`: Number of solutions to generate (default 20).
- `VARIANT_COUNT`: Number of variants per solution (default 3).
- `DATA_PARALLEL_SIZE`: Data parallel processing size (default 60).
- `MAX_ITERATIONS`: Maximum iterations per solution (default 3).

## Important Notes
- **Extremely Low Token Cost**: The token cost for a single optimization round is incredibly low (less than 1 RMB / ~$0.15 USD).
- **API Quotas**: While token cost is low, the evolutionary process requires a large number of API calls. Test with small datasets first to ensure everything works.
- **Computing Resources**: Uses Ray for parallel computing; ensure sufficient CPU/memory.
- **Execution Time**: Complete runs may take several hours.
