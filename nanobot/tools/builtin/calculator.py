"""Basic calculator tool."""

from nanobot.tools.decorator import tool


@tool(description="Perform a basic math operation: add, subtract, multiply, divide.")
async def calculator(operation: str, a: float, b: float) -> str:
    """
    Compute a op b. Operation must be one of: add, subtract, multiply, divide.
    """
    op = operation.lower()
    if op == "add":
        return str(a + b)
    if op == "subtract":
        return str(a - b)
    if op == "multiply":
        return str(a * b)
    if op == "divide":
        if b == 0:
            return "Error: division by zero"
        return str(a / b)
    return f"Error: unknown operation '{operation}'. Use add, subtract, multiply, or divide."
