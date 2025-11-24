def classify(prompt: str) -> str:
    prompt_lower = prompt.lower()
    
    code_keywords = ["def", "class", "import", "exception"]
    if any(keyword in prompt_lower for keyword in code_keywords):
        return "code"
    
    writing_keywords = ["essay", "blog", "email", "summarize"]
    if any(keyword in prompt_lower for keyword in writing_keywords):
        return "writing"
    
    return "analysis"
