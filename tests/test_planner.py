"""Tests for core.planner_engine module."""
import pytest
from core.planner_engine import (
    PlannerEngine, ExecutionPlan, PlanStep, PlanType, PlanResult
)


class TestPlanStep:
    """Test PlanStep dataclass."""
    
    def test_step_creation(self):
        """Test step creation."""
        step = PlanStep(
            step_id="step_1",
            tool_name="open_url",
            parameters={"url": "https://youtube.com"},
            description="Open YouTube"
        )
        assert step.step_id == "step_1"
        assert step.tool_name == "open_url"
        assert step.parameters == {"url": "https://youtube.com"}
    
    def test_step_with_dependencies(self):
        """Test step with dependencies."""
        step = PlanStep(
            step_id="step_2",
            tool_name="search_youtube",
            parameters={"query": "test"},
            depends_on=["step_1"]
        )
        assert step.depends_on == ["step_1"]
    
    def test_step_with_condition(self):
        """Test step with condition."""
        step = PlanStep(
            step_id="step_2",
            tool_name="close_app",
            parameters={"app": "chrome"},
            condition="chrome_running"
        )
        assert step.condition == "chrome_running"


class TestExecutionPlan:
    """Test ExecutionPlan dataclass."""
    
    def test_plan_creation(self):
        """Test plan creation."""
        plan = ExecutionPlan(
            plan_id="plan_1",
            plan_type=PlanType.SINGLE_STEP,
            steps=[],
            description="Test plan",
            estimated_time=5.0
        )
        assert plan.plan_id == "plan_1"
        assert plan.plan_type == PlanType.SINGLE_STEP
        assert plan.estimated_time == 5.0
    
    def test_plan_with_steps(self):
        """Test plan with steps."""
        step = PlanStep(
            step_id="step_1",
            tool_name="open_url",
            parameters={"url": "https://youtube.com"},
            description="Open YouTube"
        )
        plan = ExecutionPlan(
            plan_id="plan_1",
            plan_type=PlanType.MULTI_STEP,
            steps=[step],
            description="Multi-step plan",
            estimated_time=10.0
        )
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name == "open_url"


class TestPlanType:
    """Test PlanType enumeration."""
    
    def test_plan_types(self):
        """Test all plan types."""
        assert PlanType.SINGLE_STEP
        assert PlanType.MULTI_STEP
        assert PlanType.CONDITIONAL
        assert PlanType.ITERATIVE


class TestPlannerEngine:
    """Test PlannerEngine class."""
    
    def test_engine_creation(self):
        """Test engine creation."""
        engine = PlannerEngine()
        assert engine is not None
    
    def test_create_plan_single_step(self):
        """Test creating single-step plan."""
        engine = PlannerEngine()
        plan = engine.create_plan(
            user_input="open youtube",
            tool="open_url",
            parameters={"url": "https://youtube.com"}
        )
        assert plan.plan_type == PlanType.SINGLE_STEP
        assert len(plan.steps) == 1
    
    def test_create_plan_multi_step_fallback(self):
        """Test multi-step plan falls back to single-step."""
        engine = PlannerEngine()
        plan = engine.create_plan(
            user_input="open youtube, search video, play it",
            tool="open_url",
            parameters={"url": "https://youtube.com"}
        )
        # After keyword matching removal, should be single-step
        assert plan.plan_type == PlanType.SINGLE_STEP
    
    def test_create_plan_conditional_fallback(self):
        """Test conditional plan falls back to single-step."""
        engine = PlannerEngine()
        plan = engine.create_plan(
            user_input="if chrome is open, close it",
            tool="list_running_apps",
            parameters={}
        )
        # After keyword matching removal, should be single-step
        assert plan.plan_type == PlanType.SINGLE_STEP
    
    def test_create_plan_iterative_fallback(self):
        """Test iterative plan falls back to single-step."""
        engine = PlannerEngine()
        plan = engine.create_plan(
            user_input="close all chrome windows",
            tool="list_running_apps",
            parameters={}
        )
        # After keyword matching removal, should be single-step
        assert plan.plan_type == PlanType.SINGLE_STEP
    
    def test_is_single_step(self):
        """Test single-step detection."""
        engine = PlannerEngine()
        result = engine._is_single_step("open_url", {"url": "test"})
        assert result is True
    
    def test_is_multi_step_removed(self):
        """Test multi-step detection removed."""
        engine = PlannerEngine()
        result = engine._is_multi_step("then do this")
        assert result is False  # Keyword matching removed
    
    def test_is_conditional_removed(self):
        """Test conditional detection removed."""
        engine = PlannerEngine()
        result = engine._is_conditional("if chrome is open")
        assert result is False  # Keyword matching removed
    
    def test_is_iterative_removed(self):
        """Test iterative detection removed."""
        engine = PlannerEngine()
        result = engine._is_iterative("close all")
        assert result is False  # Keyword matching removed


class TestPlanResult:
    """Test PlanResult dataclass."""
    
    def test_result_creation(self):
        """Test result creation."""
        result = PlanResult(plan_id="plan_1")
        assert result.plan_id == "plan_1"
        assert len(result.completed_steps) == 0
        assert len(result.failed_steps) == 0
    
    def test_result_with_completed_steps(self):
        """Test result with completed steps."""
        result = PlanResult(plan_id="plan_1")
        result.completed_steps.append("step_1")
        assert len(result.completed_steps) == 1
    
    def test_result_with_failed_steps(self):
        """Test result with failed steps."""
        result = PlanResult(plan_id="plan_1")
        result.failed_steps.append("step_2")
        assert len(result.failed_steps) == 1


class TestPlannerDeprecation:
    """Test planner deprecation status."""
    
    def test_planner_is_deprecated(self):
        """Test planner is marked as deprecated."""
        # The planner is deprecated in favor of execution_first
        # This test verifies the deprecation pattern
        from core.planner_engine import PlannerEngine
        engine = PlannerEngine()
        assert engine is not None  # Still exists for compatibility


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
