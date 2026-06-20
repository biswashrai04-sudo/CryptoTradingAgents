import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "data_dir": "/Users/yluo/Documents/Code/ScAI/FR1-data",
    # Output settings
    "save_report": True,
    "report_type": "pdf",  # either 'pdf' or 'md'
    "report_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")), "reports"
    ),
    "send_report_to_email": False,
    # LLM settings
    "llm_provider": "openrouter",
    "deep_think_llm": "deepseek/deepseek-v4-flash",
    "quick_think_llm": "deepseek/deepseek-v4-flash",
    "search_llm": "deepseek/deepseek-v4-flash",
    "backend_url": "https://openrouter.ai/api/v1",
    "search_backend_url": "https://openrouter.ai/api/v1",
    "api_key_env_name": "OPENROUTER_API_KEY",
    "max_tokens": 4096,  # Maximum tokens for LLM responses
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 200,
    # Language settings
    "language": "zh",  # 支持 'zh' 或 'en'
}
