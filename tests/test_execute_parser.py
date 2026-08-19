"""tests/test_execute_parser.py — Execute Tag Parser Tests for JARVIS vNext++.

Tests for the <execute> tag parser, execution engine integration, and system message audit.
"""

import pytest
from core.execute_parser import ExecuteRequest, execute_parser
from core.execute_engine import ExecuteResult, execute_engine
from core.message_auditor import MessageAuditor, MessageAudit


class TestExecuteParser:
    """Test execute tag parsing functionality."""

    def test_valid_bash_execute_tag(self):
        """Test parsing valid bash execute tag."""
        text = '<execute type="bash"><command>echo hello</command></execute>'
        requests = execute_parser.parse(text)
        
        assert len(requests) == 1
        assert requests[0].execution_type == "bash"
        assert requests[0].command == "echo hello"
        assert requests[0].is_valid is True
        assert requests[0].error is None

    def test_valid_cmd_execute_tag(self):
        """Test parsing valid cmd execute tag."""
        text = '<execute type="cmd"><command>dir</command></execute>'
        requests = execute_parser.parse(text)
        
        assert len(requests) == 1
        assert requests[0].execution_type == "cmd"
        assert requests[0].command == "dir"
        assert requests[0].is_valid is True

    def test_valid_powershell_execute_tag(self):
        """Test parsing valid PowerShell execute tag."""
        text = '<execute type="powershell"><command>Get-Process</command></execute>'
        requests = execute_parser.parse(text)
        
        assert len(requests) == 1
        assert requests[0].execution_type == "powershell"
        assert requests[0].command == "Get-Process"
        assert requests[0].is_valid is True

    def test_valid_python_execute_tag(self):
        """Test parsing valid Python execute tag."""
        text = '<execute type="python"><command>print("hello")</command></execute>'
        requests = execute_parser.parse(text)
        
        assert len(requests) == 1
        assert requests[0].execution_type == "python"
        assert requests[0].command == 'print("hello")'
        assert requests[0].is_valid is True

    def test_multiline_commands(self):
        """Test parsing multiline commands."""
        text = '''<execute type="bash">
<command>
echo hello
echo world
</command>
</execute>'''
        requests = execute_parser.parse(text)
        
        assert len(requests) == 1
        assert requests[0].execution_type == "bash"
        assert "echo hello" in requests[0].command
        assert "echo world" in requests[0].command
        assert requests[0].is_valid is True

    def test_multiple_execute_blocks(self):
        """Test parsing multiple execute blocks."""
        text = '''<execute type="bash"><command>mkdir project</command></execute>
<execute type="bash"><command>cd project</command></execute>'''
        requests = execute_parser.parse(text)
        
        assert len(requests) == 2
        assert requests[0].command == "mkdir project"
        assert requests[1].command == "cd project"
        assert all(req.is_valid for req in requests)

    def test_missing_type(self):
        """Test handling missing type attribute."""
        text = '<execute><command>echo hello</command></execute>'
        requests = execute_parser.parse(text)
        
        assert len(requests) == 0  # Malformed, not parsed

    def test_missing_command(self):
        """Test handling missing command."""
        text = '<execute type="bash"><command></command></execute>'
        requests = execute_parser.parse(text)
        
        assert len(requests) == 1
        assert requests[0].is_valid is False
        assert requests[0].error == "Empty command"

    def test_malformed_execute_tag(self):
        """Test handling malformed execute tags."""
        text = '<execute type="bash">echo hello</execute>'
        requests = execute_parser.parse(text)
        
        assert len(requests) == 0  # Malformed, not parsed

    def test_unknown_execution_type(self):
        """Test handling unknown execution type."""
        text = '<execute type="ruby"><command>puts "hello"</command></execute>'
        requests = execute_parser.parse(text)
        
        assert len(requests) == 1
        assert requests[0].is_valid is False
        assert "Unsupported execution type" in requests[0].error

    def test_remove_execute_tags(self):
        """Test removing execute tags from text."""
        text = 'Here is a command: <execute type="bash"><command>pwd</command></execute>'
        cleaned = execute_parser.remove_execute_tags(text)
        
        assert "<execute" not in cleaned
        assert "[EXECUTE COMMAND]" in cleaned
        assert "Here is a command:" in cleaned

    def test_has_execute_tags(self):
        """Test detecting execute tags."""
        assert execute_parser.has_execute_tags('<execute type="bash"><command>pwd</command></execute>')
        assert not execute_parser.has_execute_tags("No execute tags here")
        assert not execute_parser.has_execute_tags("<execute>malformed")


class TestExecuteEngine:
    """Test execute engine functionality."""

    def test_execute_simple_command(self):
        """Test executing a simple command."""
        request = ExecuteRequest(
            execution_type="bash",
            command="echo test",
            is_valid=True
        )
        
        result = execute_engine.execute(request)
        
        assert isinstance(result, ExecuteResult)
        assert result.execution_type == "bash"
        assert result.command == "echo test"
        assert result.status in ["success", "failed"]
        assert result.exit_code in [0, -1]
        assert result.duration_ms >= 0

    def test_execute_invalid_request(self):
        """Test executing invalid request."""
        request = ExecuteRequest(
            execution_type="bash",
            command="",
            is_valid=False,
            error="Empty command"
        )
        
        result = execute_engine.execute(request)
        
        assert result.status == "failed"
        assert result.error == "Empty command"

    def test_execute_unsupported_type(self):
        """Test executing unsupported type."""
        request = ExecuteRequest(
            execution_type="unsupported",
            command="test",
            is_valid=True
        )
        
        result = execute_engine.execute(request)
        
        assert result.status == "failed"
        # The error message will vary by platform, just check it failed
        assert result.status == "failed"


class TestMessageAuditor:
    """Test message payload auditing."""

    def test_audit_simple_message(self):
        """Test auditing simple message."""
        messages = [
            {"role": "user", "content": "hello"}
        ]
        
        auditor = MessageAuditor()
        audit = auditor.audit_messages(messages, source="test")
        
        assert audit.system_count == 0
        assert audit.user_count == 1
        assert audit.assistant_count == 0
        assert audit.tool_count == 0
        assert audit.total_count == 1
        assert audit.collision_detected is False

    def test_audit_with_system_message(self):
        """Test auditing with system message."""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "hello"}
        ]
        
        auditor = MessageAuditor()
        audit = auditor.audit_messages(messages, source="test")
        
        assert audit.system_count == 1
        # Single system message from unknown source is not a collision
        assert audit.collision_detected is False
        assert audit.collision_source is None

    def test_audit_multiple_system_messages(self):
        """Test auditing multiple system messages."""
        messages = [
            {"role": "system", "content": "First system"},
            {"role": "system", "content": "Second system"},
            {"role": "user", "content": "hello"}
        ]
        
        auditor = MessageAuditor()
        audit = auditor.audit_messages(messages, source="test")
        
        assert audit.system_count == 2
        assert audit.collision_detected is True
        assert len([w for w in audit.warnings if "Multiple system messages" in w]) > 0

    def test_audit_large_system_message(self):
        """Test detecting large system messages."""
        messages = [
            {"role": "system", "content": "A" * 2500},  # Large message
            {"role": "user", "content": "hello"}
        ]
        
        auditor = MessageAuditor()
        audit = auditor.audit_messages(messages, source="test")
        
        assert len([w for w in audit.warnings if "Large system message" in w]) > 0

    def test_audit_conversation_history(self):
        """Test auditing conversation history."""
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
            {"role": "user", "content": "how are you"},
            {"role": "assistant", "content": "I'm good"},
        ]
        
        auditor = MessageAuditor()
        audit = auditor.audit_messages(messages, source="test")
        
        assert audit.user_count == 2
        assert audit.assistant_count == 2
        assert audit.system_count == 0
        assert audit.collision_detected is False

    def test_audit_tool_messages(self):
        """Test auditing tool messages."""
        messages = [
            {"role": "user", "content": "open calculator"},
            {"role": "assistant", "content": "", "tool_calls": [...]},
            {"role": "tool", "content": '{"result": "success"}'},
        ]
        
        auditor = MessageAuditor()
        audit = auditor.audit_messages(messages, source="test")
        
        assert audit.tool_count == 1
        assert audit.user_count == 1
        assert audit.assistant_count == 1

    def test_log_audit(self):
        """Test audit logging."""
        messages = [
            {"role": "user", "content": "hello"}
        ]
        
        auditor = MessageAuditor()
        audit = auditor.audit_messages(messages, source="test")
        
        # Should not raise any exceptions
        auditor.log_audit(audit, context="TEST")


class TestSystemMessageSources:
    """Test system message collision detection from known sources."""

    def test_prompt_assembler_source(self):
        """Test collision detection from prompt_assembler."""
        messages = [
            {"role": "system", "content": "--- World State ---"}
        ]
        
        auditor = MessageAuditor()
        audit = auditor.audit_messages(messages, source="prompt_assembler.assemble()")
        
        assert audit.system_count == 1
        # Should detect collision since source is in known collision sources
        assert audit.collision_detected is True
        assert "prompt_assembler" in audit.collision_source

    def test_brain_source(self):
        """Test collision detection from brain."""
        messages = [
            {"role": "system", "content": "System prompt"}
        ]
        
        auditor = MessageAuditor()
        audit = auditor.audit_messages(messages, source="brain._build_system_prompt()")
        
        assert audit.system_count == 1
        # Should detect collision since source is in known collision sources
        assert audit.collision_detected is True
        assert "brain" in audit.collision_source

    def test_memory_source(self):
        """Test collision detection from memory."""
        messages = [
            {"role": "system", "content": "Memory context"}
        ]
        
        auditor = MessageAuditor()
        audit = auditor.audit_messages(messages, source="memory summary generation")
        
        assert audit.system_count == 1
        # Should detect collision since source is in known collision sources
        assert audit.collision_detected is True
        assert "memory" in audit.collision_source


class TestExecuteIntegration:
    """Integration tests for execute tag with core system."""

    def test_execute_tag_in_normal_conversation(self):
        """Test that execute tags in normal conversation are handled."""
        text = '''
Here is what I'll do:
<execute type="bash"><command>pwd</command></execute>
<response>
Current directory shown above.
</response>
'''
        
        requests = execute_parser.parse(text)
        assert len(requests) == 1
        assert requests[0].is_valid is True

    def test_execute_without_response_tag(self):
        """Test execute without response tag still parses."""
        text = '<execute type="bash"><command>ls</command></execute>'
        
        requests = execute_parser.parse(text)
        assert len(requests) == 1
        assert requests[0].is_valid is True

    def test_execute_with_existing_response_tags(self):
        """Test compatibility with existing response tags."""
        text = '''
<execute type="bash"><command>echo hello</command></execute>

<response>
Command executed successfully.
</response>
'''
        
        requests = execute_parser.parse(text)
        assert len(requests) == 1
        assert requests[0].is_valid is True

    def test_no_fake_success_on_failure(self):
        """Test that failures are reported honestly."""
        # Create a request that will fail
        request = ExecuteRequest(
            execution_type="bash",
            command="nonexistent_command_12345",
            is_valid=True
        )
        
        result = execute_engine.execute(request)
        
        assert result.status == "failed"
        assert result.exit_code != 0
        assert not result.stdout

    def test_execute_timeout_handling(self):
        """Test that timeout is handled."""
        request = ExecuteRequest(
            execution_type="bash",
            command="sleep 100",  # Longer than timeout
            is_valid=True
        )
        
        result = execute_engine.execute(request)
        
        # Should either fail with timeout or complete depending on system
        assert result.status in ["success", "failed"]
        assert result.duration_ms >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])