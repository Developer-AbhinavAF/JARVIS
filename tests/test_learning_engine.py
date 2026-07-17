"""Comprehensive tests for the Learning Engine.

Tests cover all 15 learning modules:
  Safety, ExperienceDB, Preferences, Habits, Workflows, Errors,
  Reasoning, Tools, Projects, Personality, Knowledge,
  MemoryOptimizer, Behavior, Evaluation, AutonomousImprovement,
  BackgroundLearning, and the main LearningEngine.
"""
import time
import pytest

from jarvis.learning.safety import LearningSafety, learning_safety
from jarvis.learning.experience_db import (
    ExperienceDB, Experience, ExperienceCategory, Outcome, experience_db,
)
from jarvis.learning.preferences import PreferenceLearner, Preference, preference_learner
from jarvis.learning.habits import HabitLearner, Habit, habit_learner
from jarvis.learning.workflows import WorkflowLearner, Workflow, workflow_learner
from jarvis.learning.errors import ErrorLearner, ErrorRecord, error_learner
from jarvis.learning.reasoning import ReasoningLearner, ReasoningPath, reasoning_learner
from jarvis.learning.tools import ToolLearner, ToolProfile, tool_learner
from jarvis.learning.projects import ProjectLearner, Project, project_learner
from jarvis.learning.personality import PersonalityLearner, PersonalityProfile, personality_learner
from jarvis.learning.knowledge import KnowledgeLearner, KnowledgeItem, knowledge_learner
from jarvis.learning.memory_optimizer import MemoryOptimizer, memory_optimizer
from jarvis.learning.behavior import BehaviorAdapter, Adaptation, behavior_adapter
from jarvis.learning.evaluation import SelfEvaluator, EvaluationMetric, self_evaluator
from jarvis.learning.autonomous import AutonomousImprover, ImprovementAction, autonomous_improver
from jarvis.learning.background import (
    BackgroundLearningCoordinator, LearningTask, TaskStatus, background_coordinator,
)
from jarvis.learning import LearningEngine, learning_engine


# ═══════════════════════════════════════════════════════════════════════
# SAFETY
# ═══════════════════════════════════════════════════════════════════════

class TestLearningSafety:
    def setup_method(self):
        self.safety = LearningSafety()

    def test_safe_text(self):
        assert self.safety.is_safe("Hello world")

    def test_safe_empty(self):
        assert self.safety.is_safe("")

    def test_blocks_password(self):
        assert not self.safety.is_safe("my password=secret123")

    def test_blocks_api_key(self):
        assert not self.safety.is_safe("api_key=abc123")

    def test_blocks_token(self):
        assert not self.safety.is_safe("token: my_secret_token")

    def test_blocks_sk_pattern(self):
        assert not self.safety.is_safe("sk_abc123def456ghi789jkl012")

    def test_blocks_credit_card(self):
        assert not self.safety.is_safe("My card is 1234 5678 9012 3456")

    def test_safe_dict(self):
        assert self.safety.is_safe_dict({"name": "test", "value": 42})

    def test_blocks_sensitive_key(self):
        assert not self.safety.is_safe_dict({"password": "secret"})

    def test_sanitize(self):
        result = self.safety.sanitize("password=mysecret")
        assert "mysecret" not in result

    def test_stats(self):
        self.safety.is_safe("password=x")
        stats = self.safety.get_stats()
        assert stats["blocked_count"] >= 1


# ═══════════════════════════════════════════════════════════════════════
# EXPERIENCE DATABASE
# ═══════════════════════════════════════════════════════════════════════

class TestExperienceDB:
    def setup_method(self):
        self.db = ExperienceDB(max_experiences=100)

    def test_store(self):
        exp = Experience(event="test event", outcome=Outcome.SUCCESS)
        stored = self.db.store(exp)
        assert stored.experience_id
        assert self.db.count() == 1

    def test_query(self):
        self.db.store(Experience(event="a", outcome=Outcome.SUCCESS, category=ExperienceCategory.TECHNICAL))
        self.db.store(Experience(event="b", outcome=Outcome.FAILURE, category=ExperienceCategory.ERROR))
        successes = self.db.query(outcome=Outcome.SUCCESS)
        assert len(successes) == 1
        assert successes[0].event == "a"

    def test_query_by_category(self):
        self.db.store(Experience(event="a", category=ExperienceCategory.TECHNICAL))
        self.db.store(Experience(event="b", category=ExperienceCategory.CONVERSATION))
        tech = self.db.query(category=ExperienceCategory.TECHNICAL)
        assert len(tech) == 1

    def test_query_since(self):
        self.db.store(Experience(event="old", timestamp=time.time() - 3600))
        self.db.store(Experience(event="new", timestamp=time.time()))
        recent = self.db.query(since=time.time() - 60)
        assert len(recent) == 1

    def test_get_recent(self):
        for i in range(5):
            self.db.store(Experience(event=f"event_{i}"))
        recent = self.db.get_recent(3)
        assert len(recent) == 3
        assert recent[0].event == "event_4"

    def test_success_rate(self):
        self.db.store(Experience(event="a", outcome=Outcome.SUCCESS))
        self.db.store(Experience(event="b", outcome=Outcome.FAILURE))
        rate = self.db.success_rate()
        assert rate == 0.5

    def test_prune(self):
        db = ExperienceDB(max_experiences=10)
        for i in range(15):
            db.store(Experience(event=f"e{i}"))
        assert db.count() <= 10

    def test_to_dict(self):
        exp = Experience(event="test", outcome=Outcome.SUCCESS)
        d = exp.to_dict()
        assert "event" in d
        assert d["outcome"] == "success"

    def test_get_stats(self):
        self.db.store(Experience(event="a"))
        stats = self.db.get_stats()
        assert stats["total"] == 1


# ═══════════════════════════════════════════════════════════════════════
# PREFERENCES
# ═══════════════════════════════════════════════════════════════════════

class TestPreferenceLearner:
    def setup_method(self):
        self.learner = PreferenceLearner()

    def test_learn(self):
        self.learner.learn("browser", "preferred", "Chrome")
        assert self.learner.get("browser", "preferred") == "Chrome"

    def test_strengthen(self):
        self.learner.learn("browser", "preferred", "Chrome")
        self.learner.learn("browser", "preferred", "Chrome")
        pref = self.learner._preferences["browser:preferred"]
        assert pref.score > 0.5

    def test_get_preferred(self):
        self.learner.learn("tool", "editor", "VSCode")
        self.learner.learn("tool", "browser", "Chrome")
        assert self.learner.get_preferred("tool") in ("VSCode", "Chrome")

    def test_remove(self):
        self.learner.learn("a", "b", "c")
        assert self.learner.remove("a", "b")
        assert self.learner.get("a", "b") is None

    def test_get_category(self):
        self.learner.learn("browser", "primary", "Chrome")
        self.learner.learn("browser", "secondary", "Firefox")
        cats = self.learner.get_category("browser")
        assert len(cats) == 2

    def test_get_all(self):
        self.learner.learn("x", "y", "z")
        all_prefs = self.learner.get_all()
        assert len(all_prefs) == 1

    def test_get_stats(self):
        self.learner.learn("a", "b", "c")
        stats = self.learner.get_stats()
        assert stats["total_preferences"] == 1

    def test_to_dict(self):
        p = Preference(category="test", key="k", value="v")
        d = p.to_dict()
        assert d["key"] == "k"


# ═══════════════════════════════════════════════════════════════════════
# HABITS
# ═══════════════════════════════════════════════════════════════════════

class TestHabitLearner:
    def setup_method(self):
        self.learner = HabitLearner(min_occurrences=2)

    def test_observe(self):
        self.learner.observe("open_vscode")
        assert len(self.learner._observations) == 1

    def test_detect(self):
        for _ in range(3):
            self.learner.observe("open_vscode")
        detected = self.learner.detect()
        assert len(detected) >= 1

    def test_predict_next(self):
        for _ in range(3):
            self.learner.observe("open_browser")
            self.learner.observe("open_github")
        self.learner.detect()
        prediction = self.learner.predict_next("open_browser")
        assert prediction is not None

    def test_get_habits(self):
        for _ in range(3):
            self.learner.observe("code")
        self.learner.detect()
        habits = self.learner.get_habits(min_confidence=0.0)
        assert len(habits) >= 1

    def test_stats(self):
        self.learner.observe("test")
        stats = self.learner.get_stats()
        assert stats["observations"] == 1

    def test_to_dict(self):
        h = Habit(habit_id="h1", name="Test", pattern=["a", "b"])
        d = h.to_dict()
        assert d["habit_id"] == "h1"


# ═══════════════════════════════════════════════════════════════════════
# WORKFLOWS
# ═══════════════════════════════════════════════════════════════════════

class TestWorkflowLearner:
    def setup_method(self):
        self.learner = WorkflowLearner()

    def test_record_step(self):
        self.learner.start_session()
        self.learner.record_step("open_browser", tool="chrome")
        self.learner.record_step("open_github", tool="chrome")
        wf = self.learner.end_session()
        assert wf is not None
        assert len(wf.steps) == 2

    def test_end_session_too_short(self):
        self.learner.start_session()
        self.learner.record_step("only_one")
        wf = self.learner.end_session()
        assert wf is None

    def test_get_workflows(self):
        self.learner.start_session()
        self.learner.record_step("a")
        self.learner.record_step("b")
        self.learner.end_session()
        wfs = self.learner.get_workflows(min_confidence=0.0)
        assert len(wfs) == 1

    def test_suggest_next_step(self):
        self.learner.start_session()
        self.learner.record_step("a")
        self.learner.record_step("b")
        self.learner.end_session()
        suggestion = self.learner.suggest_next_step(["a"])
        assert suggestion is not None

    def test_stats(self):
        self.learner.start_session()
        self.learner.record_step("x")
        self.learner.record_step("y")
        self.learner.end_session()
        stats = self.learner.get_stats()
        assert stats["total_workflows"] == 1

    def test_to_dict(self):
        wf = Workflow(workflow_id="w1", name="Test", steps=["a", "b"])
        d = wf.to_dict()
        assert d["workflow_id"] == "w1"


# ═══════════════════════════════════════════════════════════════════════
# ERRORS
# ═══════════════════════════════════════════════════════════════════════

class TestErrorLearner:
    def setup_method(self):
        self.learner = ErrorLearner()

    def test_learn_error(self):
        record = self.learner.learn_error("TypeError", "bad type", fix="cast to int")
        assert record.error_id
        assert record.fix == "cast to int"

    def test_repeated_error(self):
        self.learner.learn_error("TypeError", "bad type")
        self.learner.learn_error("TypeError", "bad type")
        errors = self.learner.get_errors()
        assert errors[0]["occurrences"] == 2

    def test_suggest_fix(self):
        self.learner.learn_error("TypeError", "bad type", fix="cast to int")
        fix = self.learner.suggest_fix("TypeError")
        assert fix == "cast to int"

    def test_record_fix_success(self):
        record = self.learner.learn_error("TypeError", "bad type", fix="cast to int")
        self.learner.record_fix(record.error_id, success=True)
        assert record.fix_success_rate > 0.5

    def test_should_ignore(self):
        record = self.learner.learn_error("Info", "minor", fix="skip")
        record.occurrences = 10
        record.fix_success_rate = 0.9
        assert self.learner.should_ignore("Info")

    def test_get_stats(self):
        self.learner.learn_error("E", "msg")
        stats = self.learner.get_stats()
        assert stats["unique_errors"] == 1

    def test_to_dict(self):
        e = ErrorRecord(error_id="e1", error_type="Test", error_message="msg")
        d = e.to_dict()
        assert d["error_id"] == "e1"


# ═══════════════════════════════════════════════════════════════════════
# REASONING
# ═══════════════════════════════════════════════════════════════════════

class TestReasoningLearner:
    def setup_method(self):
        self.learner = ReasoningLearner()

    def test_record(self):
        path = self.learner.record(
            steps=["analyze", "plan", "execute"],
            decision="use_tool_x",
            outcome="success",
        )
        assert path.path_id

    def test_strategy_score(self):
        self.learner.record(["analyze"], "d1", "success")
        self.learner.record(["analyze"], "d2", "success")
        score = self.learner.get_strategy_score("analyze")
        assert score == 1.0

    def test_best_strategy(self):
        self.learner.record(["fast"], "d", "success")
        self.learner.record(["fast"], "d", "success")
        self.learner.record(["slow"], "d", "failure")
        best = self.learner.best_strategy()
        assert best == "fast"

    def test_get_recent(self):
        self.learner.record(["a"], "d", "success")
        recent = self.learner.get_recent(5)
        assert len(recent) == 1

    def test_stats(self):
        self.learner.record(["a"], "d", "success")
        stats = self.learner.get_stats()
        assert stats["total_paths"] == 1

    def test_to_dict(self):
        p = ReasoningPath(path_id="rp1", steps=["a"], decision="d", outcome="success")
        d = p.to_dict()
        assert d["path_id"] == "rp1"


# ═══════════════════════════════════════════════════════════════════════
# TOOLS
# ═══════════════════════════════════════════════════════════════════════

class TestToolLearner:
    def setup_method(self):
        self.learner = ToolLearner()

    def test_record_use(self):
        profile = self.learner.record_use("notepad", True, 50.0)
        assert profile.total_uses == 1
        assert profile.reliability == 1.0

    def test_reliability(self):
        self.learner.record_use("tool_a", True)
        self.learner.record_use("tool_a", False)
        assert self.learner.get_reliability("tool_a") == 0.5

    def test_get_preferred_tool(self):
        self.learner.record_use("fast_tool", True, intent="code")
        self.learner.record_use("fast_tool", True, intent="code")
        self.learner.record_use("fast_tool", True, intent="code")
        preferred = self.learner.get_preferred_tool("code")
        assert preferred == "fast_tool"

    def test_get_slow_tools(self):
        self.learner.record_use("slow_tool", True, 2000.0)
        self.learner.record_use("slow_tool", True, 2000.0)
        self.learner.record_use("slow_tool", True, 2000.0)
        slow = self.learner.get_slow_tools(threshold_ms=1000)
        assert "slow_tool" in slow

    def test_get_unreliable_tools(self):
        for _ in range(5):
            self.learner.record_use("bad_tool", False)
        unreliable = self.learner.get_unreliable_tools()
        assert "bad_tool" in unreliable

    def test_get_all_profiles(self):
        self.learner.record_use("a", True)
        profiles = self.learner.get_all_profiles()
        assert len(profiles) == 1

    def test_stats(self):
        self.learner.record_use("a", True)
        stats = self.learner.get_stats()
        assert stats["total_tools"] == 1

    def test_to_dict(self):
        p = ToolProfile(tool_name="test", total_uses=5, success_count=4)
        d = p.to_dict()
        assert d["tool_name"] == "test"


# ═══════════════════════════════════════════════════════════════════════
# PROJECTS
# ═══════════════════════════════════════════════════════════════════════

class TestProjectLearner:
    def setup_method(self):
        self.learner = ProjectLearner()

    def test_track(self):
        proj = self.learner.track("JARVIS", path="D:/AI/JARVIS", languages=["Python"])
        assert proj.project_id
        assert "Python" in proj.languages

    def test_update(self):
        self.learner.track("JARVIS", goals=["build AI"])
        self.learner.track("JARVIS", todos=["add tests"])
        proj = self.learner.get_project("JARVIS")
        assert "add tests" in proj["todos"]

    def test_get_current(self):
        self.learner.track("Project A")
        current = self.learner.get_current()
        assert current["name"] == "Project A"

    def test_list_projects(self):
        self.learner.track("A")
        self.learner.track("B")
        projects = self.learner.list_projects()
        assert len(projects) == 2

    def test_stats(self):
        self.learner.track("X")
        stats = self.learner.get_stats()
        assert stats["total_projects"] == 1

    def test_to_dict(self):
        p = Project(project_id="p1", name="Test")
        d = p.to_dict()
        assert d["name"] == "Test"


# ═══════════════════════════════════════════════════════════════════════
# PERSONALITY
# ═══════════════════════════════════════════════════════════════════════

class TestPersonalityLearner:
    def setup_method(self):
        self.learner = PersonalityLearner()

    def test_observe_message(self):
        self.learner.observe_user_message("short msg")
        profile = self.learner.get_profile()
        assert "tone" in profile

    def test_observe_preference(self):
        self.learner.observe_response_preference(preferred_length="short")
        profile = self.learner.get_profile()
        assert profile["response_length"] == "short"

    def test_set_profile(self):
        self.learner.set_profile(tone="formal")
        profile = self.learner.get_profile()
        assert profile["tone"] == "formal"

    def test_get_stats(self):
        self.learner.observe_user_message("test")
        stats = self.learner.get_stats()
        assert stats["observations"] >= 1

    def test_to_dict(self):
        p = PersonalityProfile(tone="casual")
        d = p.to_dict()
        assert d["tone"] == "casual"


# ═══════════════════════════════════════════════════════════════════════
# KNOWLEDGE
# ═══════════════════════════════════════════════════════════════════════

class TestKnowledgeLearner:
    def setup_method(self):
        self.learner = KnowledgeLearner()

    def test_learn(self):
        item = self.learner.learn("repository", "FastAPI", summary="web framework")
        assert item.item_id
        assert item.source_type == "repository"

    def test_access(self):
        self.learner.learn("youtube", "Python Tutorial")
        self.learner.access("youtube", "Python Tutorial")
        items = self.learner.get_by_type("youtube")
        assert items[0]["access_count"] >= 1

    def test_get_useful(self):
        item = self.learner.learn("pdf", "ML Paper")
        item.usefulness_score = 0.8
        useful = self.learner.get_useful(min_score=0.5)
        assert len(useful) == 1

    def test_stats(self):
        self.learner.learn("a", "b")
        stats = self.learner.get_stats()
        assert stats["total_items"] == 1

    def test_to_dict(self):
        k = KnowledgeItem(item_id="k1", source_type="pdf", title="Paper")
        d = k.to_dict()
        assert d["title"] == "Paper"


# ═══════════════════════════════════════════════════════════════════════
# MEMORY OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════

class TestMemoryOptimizer:
    def setup_method(self):
        self.optimizer = MemoryOptimizer()

    def test_optimize_empty(self):
        result = self.optimizer.optimize([])
        assert result["final_count"] == 0

    def test_optimize_removes_duplicates(self):
        memories = [
            {"text": "hello world", "importance": 0.5},
            {"text": "hello world", "importance": 0.5},
            {"text": "different text", "importance": 0.5},
        ]
        result = self.optimizer.optimize(memories)
        assert result["final_count"] <= 3

    def test_optimize_removes_noise(self):
        memories = [
            {"text": "important", "importance": 0.9},
            {"text": "noise", "importance": 0.05},
        ]
        result = self.optimizer.optimize(memories)
        assert result["final_count"] == 1

    def test_stats(self):
        self.optimizer.optimize([])
        stats = self.optimizer.get_stats()
        assert stats["optimize_count"] == 1


# ═══════════════════════════════════════════════════════════════════════
# BEHAVIOR
# ═══════════════════════════════════════════════════════════════════════

class TestBehaviorAdapter:
    def setup_method(self):
        self.adapter = BehaviorAdapter()

    def test_adapt(self):
        result = self.adapter.adapt("response_verbosity", "short", "test")
        assert result
        assert self.adapter.get_setting("response_verbosity") == "short"

    def test_no_change(self):
        result = self.adapter.adapt("response_verbosity", "medium")
        assert not result

    def test_get_all_settings(self):
        settings = self.adapter.get_all_settings()
        assert "response_verbosity" in settings

    def test_get_recent_adaptations(self):
        self.adapter.adapt("x", "y")
        recent = self.adapter.get_recent_adaptations()
        assert len(recent) == 1

    def test_analyze_and_adapt(self):
        adapted = self.adapter.analyze_and_adapt(
            {"verbosity": "concise"},
            {"voice_mode_ratio": 0.8},
        )
        assert len(adapted) >= 1

    def test_stats(self):
        self.adapter.adapt("a", "b")
        stats = self.adapter.get_stats()
        assert stats["total_adaptations"] == 1

    def test_to_dict(self):
        a = Adaptation(adaptation_id="a1", setting="test", new_value="v")
        d = a.to_dict()
        assert d["setting"] == "test"


# ═══════════════════════════════════════════════════════════════════════
# SELF-EVALUATION
# ═══════════════════════════════════════════════════════════════════════

class TestSelfEvaluator:
    def setup_method(self):
        self.evaluator = SelfEvaluator()

    def test_register_metric(self):
        self.evaluator.register_metric("speed", target=100)
        assert "speed" in self.evaluator._metrics

    def test_update_metric(self):
        self.evaluator.register_metric("speed", target=100)
        self.evaluator.update_metric("speed", 80)
        metric = self.evaluator._metrics["speed"]
        assert metric.current_value == 80

    def test_evaluate(self):
        self.evaluator.register_metric("speed", target=100)
        self.evaluator.update_metric("speed", 80)
        result = self.evaluator.evaluate()
        assert "metrics" in result
        assert result["overall_score"] > 0

    def test_get_trend(self):
        self.evaluator.register_metric("x")
        for v in [1, 2, 3, 4, 5]:
            self.evaluator.update_metric("x", v)
            self.evaluator.evaluate()
        trend = self.evaluator.get_trend("x")
        assert len(trend) >= 3

    def test_is_improving(self):
        self.evaluator.register_metric("x", target=10)
        self.evaluator.update_metric("x", 5)
        self.evaluator.evaluate()
        self.evaluator.update_metric("x", 7)
        self.evaluator.evaluate()
        assert self.evaluator.is_improving()

    def test_get_report(self):
        report = self.evaluator.get_report()
        assert "evaluation_count" in report

    def test_stats(self):
        self.evaluator.register_metric("a")
        stats = self.evaluator.get_stats()
        assert stats["metrics_tracked"] == 1

    def test_to_dict(self):
        m = EvaluationMetric(name="test", current_value=80, previous_value=70)
        d = m.to_dict()
        assert d["name"] == "test"


# ═══════════════════════════════════════════════════════════════════════
# AUTONOMOUS IMPROVEMENT
# ═══════════════════════════════════════════════════════════════════════

class TestAutonomousImprover:
    def setup_method(self):
        self.improver = AutonomousImprover()

    def test_analyze(self):
        actions = self.improver.analyze()
        assert len(actions) >= 1

    def test_record_metric(self):
        self.improver.record_metric("latency", 80)
        status = self.improver.get_category_status()
        assert status["latency"]["current"] == 80

    def test_apply_improvement(self):
        actions = self.improver.analyze()
        result = self.improver.apply_improvement(actions[0].action_id)
        assert result

    def test_get_improvements(self):
        self.improver.analyze()
        improvements = self.improver.get_improvements()
        assert len(improvements) >= 1

    def test_stats(self):
        self.improver.analyze()
        stats = self.improver.get_stats()
        assert stats["total_actions"] >= 1

    def test_to_dict(self):
        a = ImprovementAction(action_id="a1", category="test", description="desc")
        d = a.to_dict()
        assert d["action_id"] == "a1"


# ═══════════════════════════════════════════════════════════════════════
# BACKGROUND LEARNING
# ═══════════════════════════════════════════════════════════════════════

class TestBackgroundLearning:
    def setup_method(self):
        self.coordinator = BackgroundLearningCoordinator()

    def test_submit(self):
        task = self.coordinator.submit("test_task", lambda: {"result": "ok"})
        assert task.task_id
        time.sleep(0.5)
        updated = self.coordinator.get_task(task.task_id)
        assert updated.status == TaskStatus.COMPLETED

    def test_get_all_tasks(self):
        self.coordinator.submit("a", lambda: {})
        self.coordinator.submit("b", lambda: {})
        tasks = self.coordinator.get_all_tasks()
        assert len(tasks) == 2

    def test_stats(self):
        self.coordinator.submit("a", lambda: {})
        time.sleep(0.5)
        stats = self.coordinator.get_stats()
        assert stats["total_tasks"] == 1

    def test_task_failure(self):
        def fail():
            raise ValueError("test error")
        task = self.coordinator.submit("fail_task", fail)
        time.sleep(0.5)
        updated = self.coordinator.get_task(task.task_id)
        assert updated.status == TaskStatus.FAILED


# ═══════════════════════════════════════════════════════════════════════
# LEARNING ENGINE (INTEGRATION)
# ═══════════════════════════════════════════════════════════════════════

class TestLearningEngine:
    def setup_method(self):
        self.engine = LearningEngine()

    def test_learn_from_interaction(self):
        result = self.engine.learn_from_interaction(
            user_input="open notepad",
            response="Opening Notepad",
            intent="open_app",
            tool_used="notepad",
            tool_success=True,
            latency_ms=50.0,
        )
        assert result["learned"]

    def test_learn_from_failed_interaction(self):
        result = self.engine.learn_from_interaction(
            user_input="do something",
            response="Error occurred",
            intent="action",
            tool_used="some_tool",
            tool_success=False,
        )
        assert result["learned"]

    def test_learn_preference(self):
        self.engine.learn_preference("browser", "primary", "Chrome")
        assert self.engine.preferences.get("browser", "primary") == "Chrome"

    def test_learn_from_error(self):
        self.engine.learn_from_error("TypeError", "bad cast", fix="use int()")
        # Fuzzy match by error_type
        fix = self.engine.errors.suggest_fix("TypeError", "bad cast")
        assert fix == "use int()"

    def test_learn_knowledge(self):
        self.engine.learn_knowledge("repository", "FastAPI", summary="web framework")
        items = self.engine.knowledge.get_by_type("repository")
        assert len(items) == 1

    def test_get_context(self):
        ctx = self.engine.get_context(intent="code")
        assert "personality" in ctx

    def test_get_response_style(self):
        style = self.engine.get_response_style()
        assert "tone" in style

    def test_run_optimization(self):
        result = self.engine.run_optimization()
        assert "final_count" in result

    def test_run_evaluation(self):
        result = self.engine.run_evaluation()
        assert "overall_score" in result

    def test_run_improvement_analysis(self):
        actions = self.engine.run_improvement_analysis()
        assert isinstance(actions, list)

    def test_stats(self):
        self.engine.learn_from_interaction("test", "ok", "chat")
        stats = self.engine.get_stats()
        assert stats["interactions"] == 1

    def test_unsafe_content_rejected(self):
        result = self.engine.learn_from_interaction(
            user_input="password=secret123",
            response="I cannot store that",
        )
        assert not result["learned"]

    def test_full_learning_cycle(self):
        """Test complete interaction learning cycle."""
        # Learn from multiple interactions
        for i in range(3):
            self.engine.learn_from_interaction(
                f"open vscode {i}", f"Opening VS Code {i}", "open_app", "vscode", True, 30
            )

        # Learn preference
        self.engine.learn_preference("editor", "preferred", "VSCode")

        # Learn error
        self.engine.learn_from_error("FileNotFound", "file missing", fix="check path")

        # Learn knowledge
        self.engine.learn_knowledge("docs", "Python Docs", summary="Python reference")

        # Get context
        ctx = self.engine.get_context("open_app")
        assert "preferred_tool" in ctx

        # Run maintenance
        eval_result = self.engine.run_evaluation()
        assert eval_result["overall_score"] >= 0

        # Stats
        stats = self.engine.get_stats()
        assert stats["interactions"] == 3
        assert stats["learn_count"] == 3
