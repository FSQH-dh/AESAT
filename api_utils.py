from config import Config
from llm_api import GPTCallAPI, ClaudeCallAPI, DeepSeekCallAPI

def init_api_clients():
    """initialize LLM"""
    gpt_api = GPTCallAPI(
        api_base=Config.OPENAI_API_BASE,
        api_key=Config.OPENAI_API_KEY,
        model_name=Config.OPENAI_MODEL
    )
    
    claude_api = ClaudeCallAPI(
        api_base=Config.CLAUDE_API_BASE,
        api_key=Config.CLAUDE_API_KEY,
        model_name=Config.CLAUDE_MODEL
    )
    
    deepseek_api = DeepSeekCallAPI(
        api_base=Config.DEEPSEEK_API_BASE,
        api_key=Config.DEEPSEEK_API_KEY,
        model_name=Config.DEEPSEEK_MODEL
    )
    
    return gpt_api, claude_api, deepseek_api 