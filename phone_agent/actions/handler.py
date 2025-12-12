"""Action handler for processing AI model outputs."""

import time
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.adb import (
    back,
    clear_text,
    detect_and_set_adb_keyboard,
    double_tap,
    home,
    launch_app,
    long_press,
    restore_keyboard,
    swipe,
    tap,
    type_text,
)
from phone_agent.logging import get_logger

# Module logger
logger = get_logger("handler")


@dataclass
class ActionResult:
    """Result of an action execution."""

    success: bool
    should_finish: bool
    message: str | None = None
    requires_confirmation: bool = False


class ActionHandler:
    """
    Handles execution of actions from AI model output.

    Args:
        device_id: Optional ADB device ID for multi-device setups.
        confirmation_callback: Optional callback for sensitive action confirmation.
            Should return True to proceed, False to cancel.
        takeover_callback: Optional callback for takeover requests (login, captcha).
    """

    def __init__(
        self,
        device_id: str | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.device_id = device_id
        self.confirmation_callback = confirmation_callback or self._default_confirmation
        self.takeover_callback = takeover_callback or self._default_takeover

    def execute(
        self, action: dict[str, Any], screen_width: int, screen_height: int
    ) -> ActionResult:
        """
        Execute an action from the AI model.

        Args:
            action: The action dictionary from the model.
            screen_width: Current screen width in pixels.
            screen_height: Current screen height in pixels.

        Returns:
            ActionResult indicating success and whether to finish.
        """
        action_type = action.get("_metadata")

        if action_type == "finish":
            return ActionResult(
                success=True, should_finish=True, message=action.get("message")
            )

        if action_type != "do":
            return ActionResult(
                success=False,
                should_finish=True,
                message=f"Unknown action type: {action_type}",
            )

        action_name = action.get("action")
        handler_method = self._get_handler(action_name)

        if handler_method is None:
            return ActionResult(
                success=False,
                should_finish=False,
                message=f"Unknown action: {action_name}",
            )

        try:
            return handler_method(action, screen_width, screen_height)
        except Exception as e:
            return ActionResult(
                success=False, should_finish=False, message=f"Action failed: {e}"
            )

    def _get_handler(self, action_name: str) -> Callable | None:
        """Get the handler method for an action."""
        handlers = {
            "Launch": self._handle_launch,
            "Tap": self._handle_tap,
            "Type": self._handle_type,
            "Type_Name": self._handle_type,
            "Swipe": self._handle_swipe,
            "Back": self._handle_back,
            "Home": self._handle_home,
            "Double Tap": self._handle_double_tap,
            "Long Press": self._handle_long_press,
            "Wait": self._handle_wait,
            "Take_over": self._handle_takeover,
            "Note": self._handle_note,
            "Call_API": self._handle_call_api,
            "Interact": self._handle_interact,
        }
        return handlers.get(action_name)

    def _convert_relative_to_absolute(
        self, element: list[int], screen_width: int, screen_height: int
    ) -> tuple[int, int]:
        """Convert relative coordinates (0-1000) to absolute pixels."""
        x = int(element[0] / 1000 * screen_width)
        y = int(element[1] / 1000 * screen_height)
        return x, y

    def _handle_launch(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle app launch action."""
        app_name = action.get("app")
        if not app_name:
            return ActionResult(False, False, "No app name specified")

        success = launch_app(app_name, self.device_id)
        if success:
            return ActionResult(True, False)
        return ActionResult(False, False, f"App not found: {app_name}")

    def _handle_tap(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle tap action."""
        logger.debug("Handling tap action", action=action)
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        x, y = self._convert_relative_to_absolute(element, width, height)

        # Check for sensitive operation
        if "message" in action:
            if not self.confirmation_callback(action["message"]):
                return ActionResult(
                    success=False,
                    should_finish=True,
                    message="User cancelled sensitive operation",
                )

        tap(x, y, self.device_id)
        return ActionResult(True, False)

    def _handle_type(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle text input action."""
        text = action.get("text", "")

        # Switch to ADB keyboard
        original_ime = detect_and_set_adb_keyboard(self.device_id)
        time.sleep(1.0)

        # Clear existing text and type new text
        clear_text(self.device_id)
        time.sleep(1.0)

        type_text(text, self.device_id)
        time.sleep(1.0)

        # Restore original keyboard
        restore_keyboard(original_ime, self.device_id)
        time.sleep(1.0)

        return ActionResult(True, False)

    def _handle_swipe(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle swipe action."""
        start = action.get("start")
        end = action.get("end")

        if not start or not end:
            return ActionResult(False, False, "Missing swipe coordinates")

        start_x, start_y = self._convert_relative_to_absolute(start, width, height)
        end_x, end_y = self._convert_relative_to_absolute(end, width, height)

        swipe(start_x, start_y, end_x, end_y, device_id=self.device_id)
        return ActionResult(True, False)

    def _handle_back(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle back button action."""
        back(self.device_id)
        return ActionResult(True, False)

    def _handle_home(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle home button action."""
        home(self.device_id)
        return ActionResult(True, False)

    def _handle_double_tap(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle double tap action."""
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        x, y = self._convert_relative_to_absolute(element, width, height)
        double_tap(x, y, self.device_id)
        return ActionResult(True, False)

    def _handle_long_press(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle long press action."""
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        x, y = self._convert_relative_to_absolute(element, width, height)
        long_press(x, y, device_id=self.device_id)
        return ActionResult(True, False)

    def _handle_wait(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle wait action."""
        duration_str = action.get("duration", "1 seconds")
        try:
            duration = float(duration_str.replace("seconds", "").strip())
        except ValueError:
            duration = 1.0

        time.sleep(duration)
        return ActionResult(True, False)

    def _handle_takeover(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle takeover request (login, captcha, etc.)."""
        message = action.get("message", "User intervention required")
        self.takeover_callback(message)
        return ActionResult(True, False)

    def _handle_note(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle note action (placeholder for content recording)."""
        # This action is typically used for recording page content
        # Implementation depends on specific requirements
        return ActionResult(True, False)

    def _handle_call_api(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle API call action (placeholder for summarization)."""
        # This action is typically used for content summarization
        # Implementation depends on specific requirements
        return ActionResult(True, False)

    def _handle_interact(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle interaction request (user choice needed)."""
        # This action signals that user input is needed
        return ActionResult(True, False, message="User interaction required")

    @staticmethod
    def _default_confirmation(message: str) -> bool:
        """Default confirmation callback using console input."""
        response = input(f"Sensitive operation: {message}\nConfirm? (Y/N): ")
        return response.upper() == "Y"

    @staticmethod
    def _default_takeover(message: str) -> None:
        """Default takeover callback using console input."""
        input(f"{message}\nPress Enter after completing manual operation...")


def parse_action(response: str) -> dict[str, Any]:
    """
    Parse action from model response using safe AST parsing.

    This function safely parses LLM output without using eval(), preventing
    code injection attacks. Only literal values (strings, numbers, lists, dicts)
    are allowed.

    Args:
        response: Raw response string from the model.

    Returns:
        Parsed action dictionary.

    Raises:
        ValueError: If the response cannot be parsed or contains unsafe content.
    """
    import ast
    import re
    
    try:
        response = response.strip()
        
        # Find the LAST occurrence of 'do(' or 'finish(' to ignore CoT/Thinking
        idx_do = response.rfind("do(")
        idx_finish = response.rfind("finish(")
        start_idx = max(idx_do, idx_finish)
        
        if start_idx == -1:
            raise ValueError("No 'do(' or 'finish(' found in response")
        
        # Extract candidate string from the start of the action
        candidate = response[start_idx:]
        
        # Extract until matching closing parenthesis
        end_idx = candidate.rfind(")")
        if end_idx != -1:
            candidate = candidate[:end_idx + 1]
        
        # Determine action type
        if candidate.startswith("do("):
            action_type = "do"
            args_str = candidate[3:-1]  # Remove 'do(' and ')'
        elif candidate.startswith("finish("):
            action_type = "finish"
            args_str = candidate[7:-1]  # Remove 'finish(' and ')'
        else:
            raise ValueError(f"Unknown action format: {candidate}")
        
        # Parse arguments safely using AST
        action = _safe_parse_kwargs(args_str)
        action["_metadata"] = action_type
        
        return action
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to parse action: {e}\nResponse was: {response}")


def _safe_parse_kwargs(args_str: str) -> dict[str, Any]:
    """
    Safely parse keyword arguments string without using eval().
    
    Only allows literal values: strings, numbers, booleans, None, lists, dicts.
    Rejects any function calls, attribute access, or other code execution.
    
    Args:
        args_str: String like 'action="Tap", element=[500, 500]'
    
    Returns:
        Dictionary of parsed arguments.
    
    Raises:
        ValueError: If unsafe content is detected.
    """
    import ast
    
    if not args_str.strip():
        return {}
    
    # Wrap in dict() call for AST parsing
    safe_expr = f"dict({args_str})"
    
    try:
        tree = ast.parse(safe_expr, mode='eval')
    except SyntaxError as e:
        raise ValueError(f"Syntax error in action arguments: {e}")
    
    # Validate AST - only allow safe nodes
    for node in ast.walk(tree):
        # Allow these safe node types
        if isinstance(node, (
            ast.Expression,  # Top-level expression
            ast.Call,        # The dict() call we created
            ast.keyword,     # Keyword arguments
            ast.Load,        # Load context
            # Literal types
            ast.Constant,    # Python 3.8+ literals (str, int, float, bool, None)
            ast.Num,         # Legacy number literal
            ast.Str,         # Legacy string literal
            ast.NameConstant,# Legacy True/False/None
            ast.List,        # List literal
            ast.Dict,        # Dict literal
            ast.Tuple,       # Tuple literal
            ast.UnaryOp,     # For negative numbers like -1
            ast.UAdd,        # Unary +
            ast.USub,        # Unary -
        )):
            # For Call nodes, only allow our 'dict' call
            if isinstance(node, ast.Call):
                if not (isinstance(node.func, ast.Name) and node.func.id == 'dict'):
                    raise ValueError(f"Function calls not allowed (found: {ast.dump(node.func)})")
            continue
        
        # Allow Name only for 'dict' (our wrapper)
        if isinstance(node, ast.Name):
            if node.id != 'dict':
                raise ValueError(f"Variable reference not allowed: {node.id}")
            continue
        
        # Reject everything else
        raise ValueError(f"Unsafe AST node type: {type(node).__name__}")
    
    # Safe to evaluate - we've verified it only contains literals
    result = eval(compile(tree, '<action>', 'eval'), {"dict": dict, "__builtins__": {}})
    return result


def do(**kwargs) -> dict[str, Any]:
    """Helper function for creating 'do' actions."""
    kwargs["_metadata"] = "do"
    return kwargs


def finish(**kwargs) -> dict[str, Any]:
    """Helper function for creating 'finish' actions."""
    kwargs["_metadata"] = "finish"
    return kwargs


# =============================================================================
# Async Action Handler
# =============================================================================

class AsyncActionHandler:
    """
    Async version of ActionHandler for web applications.
    
    Uses async ADB functions for non-blocking action execution.
    """
    
    def __init__(
        self,
        device_id: str | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.device_id = device_id
        self.confirmation_callback = confirmation_callback or self._default_confirmation
        self.takeover_callback = takeover_callback or self._default_takeover
    
    async def execute(
        self, action: dict[str, Any], screen_width: int, screen_height: int
    ) -> ActionResult:
        """Execute an action asynchronously."""
        action_type = action.get("_metadata")
        
        if action_type == "finish":
            return ActionResult(
                success=True, should_finish=True, message=action.get("message")
            )
        
        if action_type == "error":
            return ActionResult(
                success=False, should_finish=True, message=action.get("message")
            )
        
        if action_type != "do":
            return ActionResult(
                success=False, should_finish=True,
                message=f"Unknown action type: {action_type}"
            )
        
        action_name = action.get("action")
        handler_method = self._get_handler(action_name)
        
        if handler_method is None:
            return ActionResult(
                success=False, should_finish=False,
                message=f"Unknown action: {action_name}"
            )
        
        try:
            return await handler_method(action, screen_width, screen_height)
        except Exception as e:
            return ActionResult(success=False, should_finish=False, message=f"Action failed: {e}")
    
    def _get_handler(self, action_name: str) -> Callable | None:
        """Get the async handler method for an action."""
        handlers = {
            "Launch": self._handle_launch,
            "Tap": self._handle_tap,
            "Type": self._handle_type,
            "Type_Name": self._handle_type,
            "Swipe": self._handle_swipe,
            "Back": self._handle_back,
            "Home": self._handle_home,
            "Double Tap": self._handle_double_tap,
            "Long Press": self._handle_long_press,
            "Wait": self._handle_wait,
            "Take_over": self._handle_takeover,
            "Note": self._handle_note,
            "Call_API": self._handle_call_api,
            "Interact": self._handle_interact,
        }
        return handlers.get(action_name)
    
    def _convert_relative_to_absolute(
        self, element: list[int], screen_width: int, screen_height: int
    ) -> tuple[int, int]:
        """Convert relative coordinates (0-1000) to absolute pixels."""
        x = int(element[0] / 1000 * screen_width)
        y = int(element[1] / 1000 * screen_height)
        return x, y
    
    async def _handle_launch(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle app launch action."""
        from phone_agent.adb import async_launch_app
        app_name = action.get("app")
        if not app_name:
            return ActionResult(False, False, "No app name specified")
        
        success = await async_launch_app(app_name, self.device_id)
        if success:
            return ActionResult(True, False)
        return ActionResult(False, False, f"App not found: {app_name}")
    
    async def _handle_tap(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle tap action."""
        from phone_agent.adb import async_tap
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")
        
        x, y = self._convert_relative_to_absolute(element, width, height)
        
        if "message" in action:
            if not self.confirmation_callback(action["message"]):
                return ActionResult(
                    success=False, should_finish=True,
                    message="User cancelled sensitive operation"
                )
        
        await async_tap(x, y, self.device_id)
        return ActionResult(True, False)
    
    async def _handle_type(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle text input action."""
        import asyncio
        from phone_agent.adb import (
            async_type_text, async_clear_text,
            async_detect_and_set_adb_keyboard, async_restore_keyboard
        )
        
        text = action.get("text", "")
        
        original_ime = await async_detect_and_set_adb_keyboard(self.device_id)
        await asyncio.sleep(1.0)
        
        await async_clear_text(self.device_id)
        await asyncio.sleep(1.0)
        
        await async_type_text(text, self.device_id)
        await asyncio.sleep(1.0)
        
        await async_restore_keyboard(original_ime, self.device_id)
        await asyncio.sleep(1.0)
        
        return ActionResult(True, False)
    
    async def _handle_swipe(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle swipe action."""
        from phone_agent.adb import async_swipe
        start = action.get("start")
        end = action.get("end")
        
        if not start or not end:
            return ActionResult(False, False, "Missing swipe coordinates")
        
        start_x, start_y = self._convert_relative_to_absolute(start, width, height)
        end_x, end_y = self._convert_relative_to_absolute(end, width, height)
        
        await async_swipe(start_x, start_y, end_x, end_y, device_id=self.device_id)
        return ActionResult(True, False)
    
    async def _handle_back(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle back button action."""
        from phone_agent.adb import async_back
        await async_back(self.device_id)
        return ActionResult(True, False)
    
    async def _handle_home(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle home button action."""
        from phone_agent.adb import async_home
        await async_home(self.device_id)
        return ActionResult(True, False)
    
    async def _handle_double_tap(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle double tap action."""
        from phone_agent.adb import async_double_tap
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")
        
        x, y = self._convert_relative_to_absolute(element, width, height)
        await async_double_tap(x, y, self.device_id)
        return ActionResult(True, False)
    
    async def _handle_long_press(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle long press action."""
        from phone_agent.adb import async_long_press
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")
        
        x, y = self._convert_relative_to_absolute(element, width, height)
        await async_long_press(x, y, device_id=self.device_id)
        return ActionResult(True, False)
    
    async def _handle_wait(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle wait action."""
        import asyncio
        duration_str = action.get("duration", "1 seconds")
        try:
            duration = float(duration_str.replace("seconds", "").strip())
        except ValueError:
            duration = 1.0
        
        await asyncio.sleep(duration)
        return ActionResult(True, False)
    
    async def _handle_takeover(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle takeover request."""
        message = action.get("message", "User intervention required")
        self.takeover_callback(message)
        return ActionResult(True, False)
    
    async def _handle_note(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle note action."""
        return ActionResult(True, False)
    
    async def _handle_call_api(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle API call action."""
        return ActionResult(True, False)
    
    async def _handle_interact(self, action: dict, width: int, height: int) -> ActionResult:
        """Handle interaction request."""
        return ActionResult(True, False, message="User interaction required")
    
    @staticmethod
    def _default_confirmation(message: str) -> bool:
        """Default confirmation (always True in async context)."""
        return True
    
    @staticmethod
    def _default_takeover(message: str) -> None:
        """Default takeover callback (log only)."""
        logger.warn("Takeover requested", message=message)

