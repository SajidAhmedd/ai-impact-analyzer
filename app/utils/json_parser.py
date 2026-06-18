"""
Robust JSON parser for LLM outputs.

Handles common issues with LLM-generated JSON:
- Missing commas
- Trailing commas
- Single quotes instead of double quotes
- Unescaped newlines in strings
- JavaScript-style comments
- Markdown code blocks
"""

import json
import re
from typing import Any, Dict, Optional
import structlog

logger = structlog.get_logger()


def extract_json_from_text(text: str) -> str:
    """
    Extract JSON object from text that may contain other content.

    Handles:
    - Markdown code blocks (```json ... ```)
    - Text before/after JSON
    - Multiple JSON objects (returns first complete one)
    """
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # Find the outermost JSON object
    brace_count = 0
    start_idx = -1
    end_idx = -1

    for i, char in enumerate(text):
        if char == '{':
            if brace_count == 0:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                end_idx = i + 1
                break

    if start_idx != -1 and end_idx > start_idx:
        return text[start_idx:end_idx]

    return text


def fix_json_string(json_str: str) -> str:
    """
    Fix common JSON formatting issues from LLM outputs.
    """
    # Remove any leading/trailing whitespace
    json_str = json_str.strip()

    # Remove JavaScript-style comments
    json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

    # Fix trailing commas before } or ]
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    # Fix missing commas between elements (simple cases)
    # Match: "value" "key" or "value" { or } "key" or ] "key"
    json_str = re.sub(r'"\s*\n\s*"', '",\n"', json_str)
    json_str = re.sub(r'"\s*\n\s*{', '",\n{', json_str)
    json_str = re.sub(r'}\s*\n\s*"', '},\n"', json_str)
    json_str = re.sub(r']\s*\n\s*"', '],\n"', json_str)
    json_str = re.sub(r'(\d)\s*\n\s*"', r'\1,\n"', json_str)
    json_str = re.sub(r'(true|false|null)\s*\n\s*"', r'\1,\n"', json_str)

    # Fix single quotes to double quotes (careful with apostrophes)
    # Only replace single quotes that look like JSON delimiters
    # This is a simple heuristic - replace 'key': with "key":
    json_str = re.sub(r"'(\w+)'(\s*:)", r'"\1"\2', json_str)

    # Fix unescaped newlines inside strings (replace with \n)
    # This is tricky - we need to be inside a string
    lines = json_str.split('\n')
    fixed_lines = []
    in_string = False

    for line in lines:
        # Count unescaped quotes to track if we're in a string
        quote_count = 0
        i = 0
        while i < len(line):
            if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                quote_count += 1
            i += 1

        if in_string and quote_count % 2 == 0:
            # We're continuing a string from previous line
            fixed_lines[-1] = fixed_lines[-1].rstrip('"') + '\\n' + line.lstrip()
        else:
            fixed_lines.append(line)

        # Update in_string state
        if quote_count % 2 == 1:
            in_string = not in_string

    return '\n'.join(fixed_lines)


def parse_json_safely(text: str, default: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Safely parse JSON from LLM output with multiple fallback strategies.

    Args:
        text: Raw text from LLM that should contain JSON
        default: Default value to return if all parsing fails

    Returns:
        Parsed JSON as dict, or default if parsing fails
    """
    if default is None:
        default = {}

    if not text or not text.strip():
        logger.warning("Empty text provided to JSON parser")
        return default

    # Strategy 1: Try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract JSON from text and try parsing
    json_str = extract_json_from_text(text)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Fix common issues and try again
    fixed_json = fix_json_string(json_str)
    try:
        return json.loads(fixed_json)
    except json.JSONDecodeError as e:
        logger.warning("JSON parsing failed after fixes", error=str(e))

    # Strategy 4: Try with ast.literal_eval for Python-style dicts
    try:
        import ast
        # Replace true/false/null with Python equivalents
        py_str = fixed_json.replace('true', 'True').replace('false', 'False').replace('null', 'None')
        result = ast.literal_eval(py_str)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    # Strategy 5: Use regex to extract key-value pairs as last resort
    try:
        result = extract_key_values(text)
        if result:
            logger.info("Extracted key-values using regex fallback")
            return result
    except Exception:
        pass

    logger.error("All JSON parsing strategies failed", text_preview=text[:200])
    return {**default, "parse_error": True, "raw_text": text[:500]}


def extract_key_values(text: str) -> Dict[str, Any]:
    """
    Extract key-value pairs from text using regex as last resort.
    """
    result = {}

    # Extract string values: "key": "value"
    string_pattern = r'"(\w+)"\s*:\s*"([^"]*)"'
    for match in re.finditer(string_pattern, text):
        result[match.group(1)] = match.group(2)

    # Extract boolean values: "key": true/false
    bool_pattern = r'"(\w+)"\s*:\s*(true|false)'
    for match in re.finditer(bool_pattern, text, re.IGNORECASE):
        result[match.group(1)] = match.group(2).lower() == 'true'

    # Extract numeric values: "key": 123 or "key": 1.23
    num_pattern = r'"(\w+)"\s*:\s*(\d+\.?\d*)'
    for match in re.finditer(num_pattern, text):
        value = match.group(2)
        result[match.group(1)] = float(value) if '.' in value else int(value)

    # Extract simple arrays: "key": ["a", "b"]
    array_pattern = r'"(\w+)"\s*:\s*\[(.*?)\]'
    for match in re.finditer(array_pattern, text, re.DOTALL):
        key = match.group(1)
        array_content = match.group(2)
        items = re.findall(r'"([^"]*)"', array_content)
        if items:
            result[key] = items

    return result
