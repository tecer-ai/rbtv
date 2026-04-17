import re

def parse_simple_yaml(text: str) -> dict:
    """
    Parse a flat/one-level-nested YAML file into a dict.
    Handles: scalars, one-level nested dicts, and sequences (- item).
    Enough for bootstrap.yaml and config.yaml — not a general YAML parser.
    """
    result = {}
    current_key = None
    current_dict = None
    current_list = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip())

        if indent == 0 and ":" in stripped:
            if current_key and current_dict is not None:
                result[current_key] = current_dict
            if current_key and current_list is not None:
                result[current_key] = current_list

            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")

            if val:
                result[key] = val
                current_key = None
                current_dict = None
                current_list = None
            else:
                current_key = key
                current_dict = {}
                current_list = None

        elif indent > 0 and current_key is not None:
            if stripped.startswith("- "):
                if current_list is None:
                    current_list = []
                    current_dict = None
                item = stripped[2:].strip().strip('"').strip("'")
                current_list.append(item)
            elif ":" in stripped:
                if current_dict is None:
                    current_dict = {}
                    current_list = None
                k, _, v = stripped.partition(":")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                current_dict[k] = v

    if current_key and current_dict is not None:
        result[current_key] = current_dict
    if current_key and current_list is not None:
        result[current_key] = current_list

    return result


def read_yaml_field(text: str, field: str) -> str:
    """Extract a simple YAML string field value using regex."""
    match = re.search(rf'^{re.escape(field)}:\s*"?([^"\n]+)"?\s*$', text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def read_yaml_nested_field(text: str, parent: str, field: str) -> str:
    """Extract a nested YAML field (parent:\n  field: value)."""
    match = re.search(
        rf'^{re.escape(parent)}:.*?\n\s+{re.escape(field)}:\s+(\S+)',
        text, re.MULTILINE | re.DOTALL
    )
    return match.group(1).strip() if match else ""
