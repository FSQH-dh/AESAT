import os

# Mixture of Experts Mode
class Config:
    # ChatGPT Configuration
    OPENAI_API_KEY = "*****"
    OPENAI_API_BASE = "****"
    OPENAI_MODEL = "*****"
    # Claude Configuration
    CLAUDE_API_KEY = "********"
    CLAUDE_API_BASE = "********"
    CLAUDE_MODEL = "********"
    
    # DeepSeek Configuration
    DEEPSEEK_API_KEY = "********"
    DEEPSEEK_API_BASE = "********"
    DEEPSEEK_MODEL = "********"
    
    # Code Rule Configuration
    CODE_RULE = "void restart_mab(kissat * solver) {// new code}"
    
    # Solution Generation Configuration
    SOLUTION_COUNT = 20  # Number of solutions to generate
    VARIANT_COUNT = 3   # Number of variants per solution
    CODE_SOURCE_PATH = "prompt/keycode.txt"  # Code source file path
    DATA_PARALLEL_SIZE = 60  # Data parallel size
    MAX_ITERATIONS = 3  # Maximum iterations per solution
    MAX_RETRY_COUNT = 10  # Maximum retry count when parsing response fails

class LLMConfig:
    def __init__(self, api_base, api_key, model_name, stream=False):
        self.api_base = api_base
        self.api_key = api_key
        self.model_name = model_name
        self.stream = stream
