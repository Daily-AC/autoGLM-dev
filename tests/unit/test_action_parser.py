"""
Unit tests for action parser.
"""
import pytest


class TestParseAction:
    """Tests for parse_action function."""
    
    def test_parse_do_action(self):
        """Test parsing a do action."""
        from phone_agent.actions.handler import parse_action
        
        result = parse_action('do(action="Tap", element=[500, 300])')
        
        assert result["_metadata"] == "do"
        assert result["action"] == "Tap"
        assert result["element"] == [500, 300]
    
    def test_parse_finish_action(self):
        """Test parsing a finish action."""
        from phone_agent.actions.handler import parse_action
        
        result = parse_action('finish(message="Done")')
        
        assert result["_metadata"] == "finish"
        assert result["message"] == "Done"
    
    def test_parse_swipe_action(self):
        """Test parsing a swipe action."""
        from phone_agent.actions.handler import parse_action
        
        result = parse_action('do(action="Swipe", start=[500, 800], end=[500, 200])')
        
        assert result["action"] == "Swipe"
        assert result["start"] == [500, 800]
        assert result["end"] == [500, 200]
    
    def test_parse_type_action(self):
        """Test parsing a type action."""
        from phone_agent.actions.handler import parse_action
        
        result = parse_action('do(action="Type", text="Hello World")')
        
        assert result["action"] == "Type"
        assert result["text"] == "Hello World"
    
    def test_parse_with_whitespace(self):
        """Test parsing with extra whitespace."""
        from phone_agent.actions.handler import parse_action
        
        result = parse_action('  do(action="Tap", element=[100, 200])  ')
        
        assert result["action"] == "Tap"
    
    def test_parse_empty_raises(self):
        """Test that empty input raises ValueError."""
        from phone_agent.actions.handler import parse_action
        
        with pytest.raises(ValueError):
            parse_action("")
    
    def test_parse_invalid_raises(self):
        """Test that invalid input raises ValueError."""
        from phone_agent.actions.handler import parse_action
        
        with pytest.raises(ValueError):
            parse_action("not a valid action")
    
    def test_parse_security_no_eval(self):
        """Test that malicious input is safely handled."""
        from phone_agent.actions.handler import parse_action
        
        # This should not execute any code
        malicious = 'do(action="Tap", element=__import__("os").system("echo pwned"))'
        
        # Should raise an error, not execute
        with pytest.raises(Exception):
            parse_action(malicious)
    
    def test_parse_complex_text(self):
        """Test parsing text with special characters."""
        from phone_agent.actions.handler import parse_action
        
        result = parse_action('do(action="Type", text="Hello, World! 你好")')
        
        assert result["text"] == "Hello, World! 你好"
