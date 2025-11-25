"""
Prompt classification module for LLM routing.

This module analyzes incoming prompts and classifies them into categories
to enable specialty-based provider matching and routing decisions.

Categories:
    - code: Programming-related requests
    - writing: Content creation and summarization
    - analysis: General analysis and reasoning tasks

Keywords are loaded from classifier_keywords.yaml for easy configuration.
"""

from pathlib import Path

import yaml


def _load_keywords() -> dict[str, list[str]]:
    """
    Load classification keywords from YAML configuration file.

    Returns:
        dict: Mapping of category names to keyword lists

    Raises:
        RuntimeError: If the keywords file cannot be loaded
    """
    try:
        # Look for classifier_keywords.yaml in the project root
        keywords_file = Path(__file__).parent.parent.parent / "classifier_keywords.yaml"

        with open(keywords_file, "r") as f:
            keywords = yaml.safe_load(f)

        return keywords
    except FileNotFoundError:
        raise RuntimeError(f"classifier_keywords.yaml not found at {keywords_file}")
    except Exception as e:
        raise RuntimeError(f"Failed to load classifier keywords: {e}")


# Load keywords once at module import time
_KEYWORDS = _load_keywords()


def classify(prompt: str) -> str:
    """
    Classify a prompt into one of three categories based on keyword analysis.

    The classification enables the routing system to match requests with
    providers that specialize in specific types of tasks, improving both
    quality and cost-effectiveness.

    Args:
        prompt: The user's input prompt to classify

    Returns:
        str: One of "code", "writing", or "analysis"

    Examples:
        >>> classify("Write a Python function to sort a list")
        'code'
        >>> classify("Summarize this article for me")
        'writing'
        >>> classify("What are the implications of this data?")
        'analysis'

    Classification Logic:
        - "code": Contains keywords from code category in YAML config
        - "writing": Contains keywords from writing category in YAML config
        - "analysis": Default for all other prompts
    """
    prompt_lower = prompt.lower()

    # Check for code-related keywords
    code_keywords = _KEYWORDS.get("code", [])
    if any(keyword in prompt_lower for keyword in code_keywords):
        return "code"

    # Check for writing-related keywords
    writing_keywords = _KEYWORDS.get("writing", [])
    if any(keyword in prompt_lower for keyword in writing_keywords):
        return "writing"

    # Default to analysis for everything else
    return "analysis"
