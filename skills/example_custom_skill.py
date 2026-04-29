"""Example custom skill — use as a template for new skills.

To enable: set "enabled": true in agent_config.json and set "path" to this file.
"""
from strands import tool


@tool
def example_custom_skill(input_text: str) -> str:
    """An example custom skill that echoes input. Replace with your own logic.

    Args:
        input_text: The text to process.
    """
    return f"[ExampleSkill] Received: {input_text}"
