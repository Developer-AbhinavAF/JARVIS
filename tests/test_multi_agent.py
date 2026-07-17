"""Comprehensive Multi-Agent Framework Tests.

Tests all components:
- AgentBase, AgentMessage, AgentHealth, AgentCapability
- Orchestrator (selection, execution, parallel, health)
- All 15 agents (Planner, Reasoning, Memory, Tool, Vision, Speech,
  Browser, Desktop, Research, Coding, Learning, Knowledge, Reflection,
  Scheduling, Environment)
- Parallel execution
- Failure handling
- Agent communication
"""

import time
import pytest
from unittest.mock import MagicMock


# ════════════════════════════════════════════════════════════════════
# FIXTURES
# ════════════════════════════════════════════════════════════════════


@pytest.fixture
def orchestrator():
    from jarvis.agents.orchestrator import Orchestrator
    return Orchestrator(max_workers=2)


@pytest.fixture
def all_agents():
    from jarvis.agents.planner_agent import PlannerAgent
    from jarvis.agents.reasoning_agent import ReasoningAgent
    from jarvis.agents.memory_agent import MemoryAgent
    from jarvis.agents.tool_agent import ToolAgent
    from jarvis.agents.vision_agent import VisionAgent
    from jarvis.agents.speech_agent import SpeechAgent
    from jarvis.agents.browser_agent import BrowserAgent
    from jarvis.agents.desktop_agent import DesktopAgent
    from jarvis.agents.research_agent import ResearchAgent
    from jarvis.agents.coding_agent import CodingAgent
    from jarvis.agents.learning_agent import LearningAgent
    from jarvis.agents.knowledge_agent import KnowledgeAgent
    from jarvis.agents.reflection_agent import ReflectionAgent
    from jarvis.agents.scheduling_agent import SchedulingAgent
    from jarvis.agents.environment_agent import EnvironmentAgent
    return {
        "planner": PlannerAgent(),
        "reasoning": ReasoningAgent(),
        "memory": MemoryAgent(),
        "tool": ToolAgent(),
        "vision": VisionAgent(),
        "speech": SpeechAgent(),
        "browser": BrowserAgent(),
        "desktop": DesktopAgent(),
        "research": ResearchAgent(),
        "coding": CodingAgent(),
        "learning": LearningAgent(),
        "knowledge": KnowledgeAgent(),
        "reflection": ReflectionAgent(),
        "scheduling": SchedulingAgent(),
        "environment": EnvironmentAgent(),
    }


@pytest.fixture
def populated_orchestrator(all_agents, orchestrator):
    for agent in all_agents.values():
        orchestrator.register_agent(agent)
    return orchestrator


# ════════════════════════════════════════════════════════════════════
# BASE INFRASTRUCTURE TESTS
# ════════════════════════════════════════════════════════════════════


class TestAgentHealth:
    def test_health_initial_state(self):
        from jarvis.agents.base import AgentHealth, AgentStatus
        h = AgentHealth()
        assert h.status == AgentStatus.IDLE
        assert h.success_count == 0
        assert h.failure_count == 0
        assert h.success_rate == 1.0
        assert h.availability is True

    def test_health_record_success(self):
        from jarvis.agents.base import AgentHealth, AgentStatus
        h = AgentHealth()
        h.record_success(15.0)
        assert h.success_count == 1
        assert h.total_count == 1
        assert h.latency_ms == 15.0
        assert h.status == AgentStatus.IDLE

    def test_health_record_failure(self):
        from jarvis.agents.base import AgentHealth, AgentStatus
        h = AgentHealth()
        h.record_failure("test error")
        assert h.failure_count == 1
        assert h.last_error == "test error"
        assert h.status == AgentStatus.FAILED
        assert h.availability is False

    def test_health_success_rate(self):
        from jarvis.agents.base import AgentHealth
        h = AgentHealth()
        h.record_success(10)
        h.record_success(20)
        h.record_failure("err")
        assert h.success_rate == pytest.approx(2 / 3, abs=0.01)

    def test_health_to_dict(self):
        from jarvis.agents.base import AgentHealth
        h = AgentHealth()
        d = h.to_dict()
        assert "status" in d
        assert "success_rate" in d
        assert "latency_ms" in d


class TestAgentMessage:
    def test_message_creation(self):
        from jarvis.agents.base import AgentMessage, MessageType
        msg = AgentMessage(
            source_agent="a",
            target_agent="b",
            task_id="t1",
            message_type=MessageType.TASK,
            payload={"text": "hello"},
        )
        assert msg.source_agent == "a"
        assert msg.target_agent == "b"
        assert msg.task_id == "t1"
        assert msg.payload["text"] == "hello"

    def test_message_auto_id(self):
        from jarvis.agents.base import AgentMessage
        msg1 = AgentMessage()
        msg2 = AgentMessage()
        assert msg1.message_id != msg2.message_id

    def test_message_to_dict(self):
        from jarvis.agents.base import AgentMessage
        msg = AgentMessage(source_agent="a", target_agent="b")
        d = msg.to_dict()
        assert "message_id" in d
        assert "source_agent" in d


class TestAgentCapability:
    def test_capability_matches_intent(self):
        from jarvis.agents.base import AgentCapability
        cap = AgentCapability(
            name="test",
            intent_patterns=["GREETING", "TIME"],
            keywords=["hello", "time"],
        )
        assert cap.matches(intent="GREETING") > 0
        assert cap.matches(intent="UNKNOWN") == 0

    def test_capability_matches_keywords(self):
        from jarvis.agents.base import AgentCapability
        cap = AgentCapability(
            name="test",
            keywords=["hello", "hi", "hey"],
        )
        score = cap.matches(text="hello there")
        assert score > 0

    def test_capability_no_match(self):
        from jarvis.agents.base import AgentCapability
        cap = AgentCapability(name="test", keywords=["xyz"])
        assert cap.matches(text="hello") == 0


class TestAgentBase:
    def test_agent_inherits(self, all_agents):
        from jarvis.agents.base import AgentBase
        for agent in all_agents.values():
            assert isinstance(agent, AgentBase)

    def test_agent_has_name(self, all_agents):
        for agent in all_agents.values():
            assert agent.name
            assert len(agent.name) > 0

    def test_agent_has_capabilities(self, all_agents):
        for agent in all_agents.values():
            assert len(agent.capabilities) > 0

    def test_agent_can_handle(self, all_agents):
        reasoning = all_agents["reasoning"]
        score = reasoning.can_handle(intent="GREETING")
        assert score > 0

    def test_agent_health(self, all_agents):
        for agent in all_agents.values():
            h = agent.get_health()
            assert "name" in h
            assert "status" in h
            assert "success_rate" in h

    def test_agent_stats(self, all_agents):
        for agent in all_agents.values():
            s = agent.get_stats()
            assert "name" in s
            assert "health" in s
            assert "capabilities" in s


# ════════════════════════════════════════════════════════════════════
# ORCHESTRATOR TESTS
# ════════════════════════════════════════════════════════════════════


class TestOrchestrator:
    def test_orchestrator_instantiates(self, orchestrator):
        assert orchestrator is not None

    def test_register_agent(self, orchestrator, all_agents):
        orchestrator.register_agent(all_agents["reasoning"])
        assert orchestrator.agent_count == 1

    def test_register_all_agents(self, populated_orchestrator):
        assert populated_orchestrator.agent_count == 15

    def test_select_agents(self, populated_orchestrator):
        agents = populated_orchestrator.select_agents(text="hello")
        assert len(agents) > 0
        assert agents[0][0].name == "reasoning"

    def test_select_primary_agent(self, populated_orchestrator):
        agent = populated_orchestrator.select_primary_agent(text="hello")
        assert agent is not None
        assert agent.name == "reasoning"

    def test_select_for_open_app(self, populated_orchestrator):
        agents = populated_orchestrator.select_agents(intent="OPEN_APP")
        names = [a[0].name for a in agents]
        assert "tool" in names or "desktop" in names

    def test_execute_greeting(self, populated_orchestrator):
        result = populated_orchestrator.execute("hello")
        assert result["response"]
        assert len(result["agents_used"]) > 0
        assert result["latency_ms"] > 0

    def test_execute_open_app(self, populated_orchestrator):
        result = populated_orchestrator.execute(
            "open chrome",
            intent="OPEN_APP",
            entities={"app_name": "chrome"},
        )
        assert "chrome" in result["response"].lower()

    def test_execute_time(self, populated_orchestrator):
        result = populated_orchestrator.execute("what time is it", intent="DATETIME")
        assert result["response"]
        assert "AM" in result["response"] or "PM" in result["response"]

    def test_execute_memory(self, populated_orchestrator):
        result = populated_orchestrator.execute(
            "remember my name is John",
            intent="SAVE_MEMORY",
            entities={"content": "my name is John"},
        )
        assert result["response"]
        assert "memory" in result["response"].lower() or "saved" in result["response"].lower()

    def test_execute_no_agents(self, orchestrator):
        result = orchestrator.execute("hello")
        assert result["response"] == ""
        assert result["error"] == "No agents available"

    def test_get_all_health(self, populated_orchestrator):
        health = populated_orchestrator.get_all_health()
        assert len(health) == 15
        for name, h in health.items():
            assert "status" in h
            assert "success_rate" in h

    def test_get_healthy_agents(self, populated_orchestrator):
        healthy = populated_orchestrator.get_healthy_agents()
        assert len(healthy) == 15

    def test_get_stats(self, populated_orchestrator):
        stats = populated_orchestrator.get_stats()
        assert stats["agent_count"] == 15
        assert stats["total_tasks"] == 0

    def test_unregister_agent(self, orchestrator, all_agents):
        orchestrator.register_agent(all_agents["reasoning"])
        assert orchestrator.agent_count == 1
        orchestrator.unregister_agent("reasoning")
        assert orchestrator.agent_count == 0

    def test_get_agent(self, populated_orchestrator):
        agent = populated_orchestrator.get_agent("reasoning")
        assert agent is not None
        assert agent.name == "reasoning"

    def test_get_agents(self, populated_orchestrator):
        agents = populated_orchestrator.get_agents()
        assert len(agents) == 15


# ════════════════════════════════════════════════════════════════════
# INDIVIDUAL AGENT TESTS
# ════════════════════════════════════════════════════════════════════


class TestPlannerAgent:
    def test_planner_processes(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        planner = all_agents["planner"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="planner",
            message_type=MessageType.TASK,
            payload={"text": "analyze and code a function", "intent": "PLAN"},
        )
        result = planner.process_sync(msg)
        assert result.payload["task_count"] >= 1


class TestReasoningAgent:
    def test_reasoning_greeting(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        reasoning = all_agents["reasoning"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="reasoning",
            message_type=MessageType.TASK,
            payload={"text": "hello", "intent": "GREETING"},
        )
        result = reasoning.process_sync(msg)
        assert "hello" in result.payload["response"].lower()

    def test_reasoning_time(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        reasoning = all_agents["reasoning"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="reasoning",
            message_type=MessageType.TASK,
            payload={"text": "what time is it", "intent": "DATETIME"},
        )
        result = reasoning.process_sync(msg)
        assert "AM" in result.payload["response"] or "PM" in result.payload["response"]


class TestMemoryAgent:
    def test_memory_save_and_recall(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        memory = all_agents["memory"]

        # Save
        save_msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="memory",
            message_type=MessageType.TASK,
            payload={"text": "my name is John", "intent": "SAVE_MEMORY", "entities": {"content": "my name is John"}},
        )
        save_result = memory.process_sync(save_msg)
        assert "saved" in save_result.payload["response"].lower()

        # Recall
        recall_msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="memory",
            message_type=MessageType.TASK,
            payload={"text": "what is my name", "intent": "RECALL_MEMORY", "entities": {"query": "name"}},
        )
        recall_result = memory.process_sync(recall_msg)
        assert "John" in recall_result.payload["response"]


class TestToolAgent:
    def test_tool_open_app(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        tool = all_agents["tool"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="tool",
            message_type=MessageType.TASK,
            payload={"text": "open chrome", "intent": "OPEN_APP", "entities": {"app_name": "chrome"}},
        )
        result = tool.process_sync(msg)
        assert "chrome" in result.payload["response"].lower()
        assert result.payload["success"] is True

    def test_tool_stats(self, all_agents):
        tool = all_agents["tool"]
        stats = tool.get_stats()
        assert "execution_count" in stats


class TestVisionAgent:
    def test_vision_processes(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        vision = all_agents["vision"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="vision",
            message_type=MessageType.TASK,
            payload={"text": "what's on my screen", "intent": "VISUAL_ANALYSIS"},
        )
        result = vision.process_sync(msg)
        assert "response" in result.payload


class TestSpeechAgent:
    def test_speech_processes(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        speech = all_agents["speech"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="speech",
            message_type=MessageType.TASK,
            payload={"text": "hello", "intent": "SPEAK"},
        )
        result = speech.process_sync(msg)
        assert result.payload["response"]


class TestBrowserAgent:
    def test_browser_search(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        browser = all_agents["browser"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="browser",
            message_type=MessageType.TASK,
            payload={"text": "search python docs", "intent": "WEB_SEARCH", "entities": {"query": "python docs"}},
        )
        result = browser.process_sync(msg)
        assert "python docs" in result.payload["response"].lower()


class TestDesktopAgent:
    def test_desktop_open(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        desktop = all_agents["desktop"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="desktop",
            message_type=MessageType.TASK,
            payload={"text": "open notepad", "intent": "OPEN_APP", "entities": {"app_name": "notepad"}},
        )
        result = desktop.process_sync(msg)
        assert "notepad" in result.payload["response"].lower()


class TestResearchAgent:
    def test_research_processes(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        research = all_agents["research"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="research",
            message_type=MessageType.TASK,
            payload={"text": "research quantum computing", "intent": "RESEARCH"},
        )
        result = research.process_sync(msg)
        assert result.payload["response"]


class TestCodingAgent:
    def test_coding_processes(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        coding = all_agents["coding"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="coding",
            message_type=MessageType.TASK,
            payload={"text": "write a python function", "intent": "CODE_GENERATE", "entities": {"language": "python"}},
        )
        result = coding.process_sync(msg)
        assert "python" in result.payload["language"].lower()


class TestLearningAgent:
    def test_learning_processes(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        learning = all_agents["learning"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="learning",
            message_type=MessageType.TASK,
            payload={"text": "I prefer dark mode", "intent": "PREFERENCE"},
        )
        result = learning.process_sync(msg)
        assert "learned" in result.payload["response"].lower() or "recorded" in result.payload["response"].lower()


class TestKnowledgeAgent:
    def test_knowledge_processes(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        knowledge = all_agents["knowledge"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="knowledge",
            message_type=MessageType.TASK,
            payload={"text": "what do you know about python", "intent": "KNOWLEDGE_QUERY"},
        )
        result = knowledge.process_sync(msg)
        assert result.payload["response"]


class TestReflectionAgent:
    def test_reflection_processes(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        reflection = all_agents["reflection"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="reflection",
            message_type=MessageType.TASK,
            payload={"text": "analyze performance", "intent": "REFLECT"},
        )
        result = reflection.process_sync(msg)
        assert result.payload["response"]


class TestSchedulingAgent:
    def test_scheduling_processes(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        scheduling = all_agents["scheduling"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="scheduling",
            message_type=MessageType.TASK,
            payload={"text": "remind me to drink water", "intent": "SET_REMINDER"},
        )
        result = scheduling.process_sync(msg)
        assert "schedule" in result.payload["response"].lower()


class TestEnvironmentAgent:
    def test_environment_processes(self, all_agents):
        from jarvis.agents.base import AgentMessage, MessageType
        env = all_agents["environment"]
        msg = AgentMessage(
            source_agent="orchestrator",
            target_agent="environment",
            message_type=MessageType.TASK,
            payload={"text": "system status", "intent": "SYSTEM_STATUS"},
        )
        result = env.process_sync(msg)
        assert result.payload["response"]


# ════════════════════════════════════════════════════════════════════
# PARALLEL EXECUTION TESTS
# ════════════════════════════════════════════════════════════════════


class TestParallelExecution:
    def test_parallel_multiple_agents(self, populated_orchestrator):
        result = populated_orchestrator.execute(
            "open chrome and search python docs",
            intent="OPEN_APP",
            entities={"app_name": "chrome"},
        )
        assert result["response"]
        assert len(result["agents_used"]) >= 1


# ════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ════════════════════════════════════════════════════════════════════


class TestAgentIntegration:
    def test_full_pipeline(self):
        from jarvis.agents import get_orchestrator
        orch = get_orchestrator()

        # Greeting
        r = orch.execute("hello")
        assert r["response"]

        # Open app
        r = orch.execute("open chrome", intent="OPEN_APP", entities={"app_name": "chrome"})
        assert "chrome" in r["response"].lower()

        # Time
        r = orch.execute("what time is it", intent="DATETIME")
        assert r["response"]

        # Memory
        r = orch.execute("remember milk", intent="SAVE_MEMORY", entities={"content": "buy milk"})
        assert r["response"]

        # Health check
        health = orch.get_all_health()
        assert len(health) == 15

        # Stats
        stats = orch.get_stats()
        assert stats["total_tasks"] >= 4


# ════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION TESTS
# ════════════════════════════════════════════════════════════════════


class TestFactoryFunctions:
    def test_execute_function(self):
        from jarvis.agents import execute
        result = execute("hello")
        assert result["response"]

    def test_get_orchestrator(self):
        from jarvis.agents import get_orchestrator
        orch = get_orchestrator()
        assert orch.agent_count == 15

    def test_get_agent_health(self):
        from jarvis.agents import get_agent_health
        health = get_agent_health()
        assert len(health) == 15
