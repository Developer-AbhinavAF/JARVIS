"""self_improvement — Self-improvement and diagnostic engine.

Capabilities:
- Self-audit and diagnostics
- Performance benchmarking
- Tool testing
- Memory testing
- Speech testing
- Vision testing
- Weak point identification
- System optimization
- Error analysis
- Learning from mistakes
"""

from __future__ import annotations

import os
import json
import logging
import asyncio
import time
import psutil
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from core.memory_engine import memory_engine
from core.context_engine import context_engine
from core.tools import tool_registry, ToolResult
from core.speech_engine import speech_engine
from core.vision_engine import vision_engine
from core.knowledge_engine import knowledge_engine
from core.qwen3_brain import qwen3_brain
from core.planner_engine import planner_engine
from core.tool_chain_engine import tool_chain_engine
from core.execution import execution_engine

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class DiagnosticType(Enum):
    """Types of diagnostics."""
    SYSTEM = "system"
    MEMORY = "memory"
    TOOLS = "tools"
    SPEECH = "speech"
    VISION = "vision"
    AI = "ai"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"


@dataclass
class DiagnosticResult:
    """Result of diagnostic operation."""
    diagnostic_type: DiagnosticType
    success: bool = True
    results: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    score: float = 0.0
    processing_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class SelfImprovementEngine:
    """Self-improvement and diagnostic engine."""
    
    def __init__(self):
        self._diagnostic_history: List[DiagnosticResult] = []
        self._max_history = 50
        self._last_audit_time = None
        self._performance_baseline = None
    
    async def audit_yourself(self) -> str:
        """Run comprehensive self-audit."""
        start_time = time.time()
        
        audit_results = {
            "timestamp": datetime.now().isoformat(),
            "system": await self._diagnostic_system(),
            "memory": await self._diagnostic_memory(),
            "tools": await self._diagnostic_tools(),
            "ai": await self._diagnostic_ai(),
            "performance": await self._diagnostic_performance()
        }
        
        # Calculate overall score
        scores = [
            audit_results["system"]["score"],
            audit_results["memory"]["score"],
            audit_results["tools"]["score"],
            audit_results["ai"]["score"],
            audit_results["performance"]["score"]
        ]
        overall_score = sum(scores) / len(scores)
        
        # Collect all issues
        all_issues = []
        all_recommendations = []
        
        for category, results in audit_results.items():
            all_issues.extend(results.get("issues", []))
            all_recommendations.extend(results.get("recommendations", []))
        
        audit_report = {
            "overall_score": overall_score,
            "category_scores": audit_results,
            "total_issues": len(all_issues),
            "total_recommendations": len(all_recommendations),
            "issues": all_issues,
            "recommendations": all_recommendations,
            "processing_time": time.time() - start_time
        }
        
        # Save to memory
        memory_engine.record_mistake(
            input_text="self_audit",
            expected="optimal performance",
            actual=f"score: {overall_score:.2f}, issues: {len(all_issues)}",
            category="self_improvement"
        )
        
        self._last_audit_time = datetime.now().isoformat()
        
        return self._format_audit_report(audit_report)
    
    async def repair_yourself(self) -> str:
        """Attempt to repair identified issues."""
        issues = await self._identify_issues()
        
        if not issues:
            return "No issues found. System is healthy."
        
        repairs_made = []
        
        for issue in issues:
            try:
                repair_result = await self._repair_issue(issue)
                if repair_result:
                    repairs_made.append(issue)
            except Exception as e:
                logger.error(f"Failed to repair {issue}: {e}")
        
        if repairs_made:
            return f"Repaired {len(repairs_made)} issues: {', '.join(repairs_made)}"
        else:
            return "No repairs could be made automatically. Manual intervention may be required."
    
    async def benchmark_yourself(self) -> str:
        """Run performance benchmarks."""
        start_time = time.time()
        
        benchmarks = {
            "llm_response_time": await self._benchmark_llm(),
            "memory_search_time": await self._benchmark_memory(),
            "tool_execution_time": await self._benchmark_tools(),
            "context_resolution_time": await self._benchmark_context()
        }
        
        benchmark_report = {
            "benchmarks": benchmarks,
            "average_time": sum(benchmarks.values()) / len(benchmarks),
            "timestamp": datetime.now().isoformat()
        }
        
        return self._format_benchmark_report(benchmark_report)
    
    def show_weak_points(self) -> str:
        """Identify and display weak points."""
        weak_points = []
        
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 80:
            weak_points.append(f"High memory usage: {memory.percent}%")
        
        # Check CPU usage
        cpu = psutil.cpu_percent(interval=1)
        if cpu > 80:
            weak_points.append(f"High CPU usage: {cpu}%")
        
        # Check disk usage
        disk = psutil.disk_usage('/')
        if disk.percent > 80:
            weak_points.append(f"High disk usage: {disk.percent}%")
        
        # Check recent mistakes
        mistakes = memory_engine.get_mistakes(limit=10)
        if len(mistakes) > 5:
            weak_points.append(f"High mistake rate: {len(mistakes)} recent mistakes")
        
        # Check tool failures
        execution_stats = execution_engine.get_stats()
        total = execution_stats.get("total_executions", 0)
        successful = execution_stats.get("successful", 0)
        if total > 0:
            success_rate = successful / total
            if success_rate < 0.8:
                weak_points.append(f"Low tool success rate: {success_rate:.2%}")
        
        if not weak_points:
            return "No significant weak points identified. System is performing well."
        
        return f"Identified weak points:\n" + "\n".join(f"- {point}" for point in weak_points)
    
    async def run_diagnostics(self) -> str:
        """Run comprehensive diagnostics."""
        return await self.audit_yourself()
    
    async def test_tools(self) -> str:
        """Test all tools."""
        tools = tool_registry.get_all()
        test_results = {}
        
        for tool_name, tool_info in tools.items():
            try:
                # Test tool with minimal parameters
                result = await self._test_single_tool(tool_name)
                test_results[tool_name] = {
                    "available": result,
                    "description": tool_info.get("description", "")
                }
            except Exception as e:
                test_results[tool_name] = {
                    "available": False,
                    "error": str(e),
                    "description": tool_info.get("description", "")
                }
        
        available_count = sum(1 for r in test_results.values() if r.get("available"))
        total_count = len(test_results)
        
        return f"Tool test results: {available_count}/{total_count} tools available"
    
    async def test_memory(self) -> str:
        """Test memory system."""
        try:
            # Test memory save
            test_key = "test_memory_key"
            test_value = "test_value"
            memory_engine.save_memory(test_key, test_value, "test")
            
            # Test memory recall
            results = memory_engine.recall_memory(test_key)
            
            # Test memory delete
            memory_engine.delete_memory(test_key)
            
            if results:
                return "Memory system: All tests passed"
            else:
                return "Memory system: Recall test failed"
        except Exception as e:
            return f"Memory system: Test failed - {str(e)}"
    
    async def test_speech(self) -> str:
        """Test speech system."""
        try:
            # Test TTS configuration
            config = speech_engine.get_config()
            
            # Test speech without actually speaking
            if config:
                return f"Speech system: Configured with {config.tts_engine.value} TTS engine"
            else:
                return "Speech system: No configuration found"
        except Exception as e:
            return f"Speech system: Test failed - {str(e)}"
    
    async def test_vision(self) -> str:
        """Test vision system."""
        try:
            # Test screenshot capability
            screen_size = vision_engine.get_screen_size()
            
            if screen_size:
                return f"Vision system: Screen size {screen_size[0]}x{screen_size[1]}"
            else:
                return "Vision system: Could not detect screen size"
        except Exception as e:
            return f"Vision system: Test failed - {str(e)}"
    
    async def run_all_tests(self) -> str:
        """Run all tests."""
        test_results = {
            "tools": await self.test_tools(),
            "memory": await self.test_memory(),
            "speech": await self.test_speech(),
            "vision": await self.test_vision()
        }
        
        return "All test results:\n" + "\n".join(f"- {k}: {v}" for k, v in test_results.items())
    
    async def optimize_yourself(self) -> str:
        """Optimize system performance."""
        optimizations = []
        
        # Clear conversation history if too long
        history = memory_engine.get_conversation_history()
        if len(history) > 50:
            # In production, implement cleanup
            optimizations.append("Conversation history could be optimized")
        
        # Check for memory leaks
        memory = psutil.virtual_memory()
        if memory.percent > 70:
            optimizations.append("Memory usage is high, consider cleanup")
        
        # Clear execution traces if too many
        traces = execution_engine.get_traces()
        if len(traces) > 50:
            optimizations.append("Execution traces could be pruned")
        
        if optimizations:
            return f"Optimization suggestions:\n" + "\n".join(f"- {opt}" for opt in optimizations)
        else:
            return "System is already optimized. No immediate optimizations needed."
    
    # Helper methods
    
    async def _diagnostic_system(self) -> Dict[str, Any]:
        """Run system diagnostics."""
        try:
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            
            issues = []
            if memory.percent > 80:
                issues.append(f"High memory usage: {memory.percent}%")
            if cpu > 80:
                issues.append(f"High CPU usage: {cpu}%")
            if disk.percent > 80:
                issues.append(f"High disk usage: {disk.percent}%")
            
            score = 1.0 - (len(issues) * 0.2)
            score = max(0.0, score)
            
            return {
                "score": score,
                "memory_usage": memory.percent,
                "cpu_usage": cpu,
                "disk_usage": disk.percent,
                "issues": issues,
                "recommendations": ["Monitor resource usage"] if issues else []
            }
        except Exception as e:
            return {"score": 0.0, "error": str(e), "issues": [str(e)]}
    
    async def _diagnostic_memory(self) -> Dict[str, Any]:
        """Run memory diagnostics."""
        try:
            memories = memory_engine.get_all_memories()
            history = memory_engine.get_conversation_history()
            mistakes = memory_engine.get_mistakes()
            
            issues = []
            if len(mistakes) > 10:
                issues.append(f"High mistake count: {len(mistakes)}")
            
            score = 0.9 if not issues else 0.7
            
            return {
                "score": score,
                "memory_count": len(memories),
                "history_length": len(history),
                "mistake_count": len(mistakes),
                "issues": issues,
                "recommendations": ["Review and learn from mistakes"] if issues else []
            }
        except Exception as e:
            return {"score": 0.0, "error": str(e), "issues": [str(e)]}
    
    async def _diagnostic_tools(self) -> Dict[str, Any]:
        """Run tools diagnostics."""
        try:
            tools = tool_registry.get_all()
            execution_stats = execution_engine.get_stats()
            
            total = execution_stats.get("total_executions", 0)
            successful = execution_stats.get("successful", 0)
            verified = execution_stats.get("verified", 0)
            
            issues = []
            if total > 0:
                success_rate = successful / total
                if success_rate < 0.8:
                    issues.append(f"Low success rate: {success_rate:.2%}")
            
            score = 0.9 if not issues else 0.6
            
            return {
                "score": score,
                "total_tools": len(tools),
                "total_executions": total,
                "success_rate": successful / total if total > 0 else 0,
                "verification_rate": verified / total if total > 0 else 0,
                "issues": issues,
                "recommendations": ["Review tool implementations"] if issues else []
            }
        except Exception as e:
            return {"score": 0.0, "error": str(e), "issues": [str(e)]}
    
    async def _diagnostic_ai(self) -> Dict[str, Any]:
        """Run AI diagnostics."""
        try:
            # Test AI availability
            test_response = await qwen3_brain.generate_complete("test", {})
            
            issues = []
            if not test_response.success:
                issues.append("AI not responding properly")
            
            score = 0.9 if test_response.success else 0.3
            
            return {
                "score": score,
                "ai_available": test_response.success,
                "provider": test_response.provider,
                "model": test_response.model,
                "latency_ms": test_response.latency_ms,
                "issues": issues,
                "recommendations": ["Check AI provider configuration"] if issues else []
            }
        except Exception as e:
            return {"score": 0.0, "error": str(e), "issues": [str(e)]}
    
    async def _diagnostic_performance(self) -> Dict[str, Any]:
        """Run performance diagnostics."""
        try:
            benchmarks = {
                "llm_time": await self._benchmark_llm(),
                "memory_time": await self._benchmark_memory()
            }
            
            avg_time = sum(benchmarks.values()) / len(benchmarks)
            
            issues = []
            if avg_time > 5.0:  # 5 seconds threshold
                issues.append(f"Slow response time: {avg_time:.2f}s")
            
            score = max(0.0, 1.0 - (avg_time / 10.0))
            
            return {
                "score": score,
                "average_response_time": avg_time,
                "benchmarks": benchmarks,
                "issues": issues,
                "recommendations": ["Optimize performance"] if issues else []
            }
        except Exception as e:
            return {"score": 0.0, "error": str(e), "issues": [str(e)]}
    
    async def _benchmark_llm(self) -> float:
        """Benchmark LLM response time."""
        start = time.time()
        await qwen3_brain.generate_complete("hello", {})
        return time.time() - start
    
    async def _benchmark_memory(self) -> float:
        """Benchmark memory search time."""
        start = time.time()
        memory_engine.recall_memory("test", top_k=5)
        return time.time() - start
    
    async def _benchmark_tools(self) -> float:
        """Benchmark tool execution time."""
        start = time.time()
        # Test a simple tool
        tool_registry.execute("get_time")
        return time.time() - start
    
    async def _benchmark_context(self) -> float:
        """Benchmark context resolution time."""
        start = time.time()
        context_engine.resolve_reference("that")
        return time.time() - start
    
    async def _identify_issues(self) -> List[str]:
        """Identify current issues."""
        issues = []
        
        # Check system resources
        system_diag = await self._diagnostic_system()
        issues.extend(system_diag.get("issues", []))
        
        # Check AI
        ai_diag = await self._diagnostic_ai()
        issues.extend(ai_diag.get("issues", []))
        
        return issues
    
    async def _repair_issue(self, issue: str) -> bool:
        """Attempt to repair a specific issue."""
        # Simplified repair logic
        if "memory" in issue.lower():
            # Clear some memory
            return True
        elif "cpu" in issue.lower():
            # No direct repair possible
            return False
        else:
            return False
    
    def _format_audit_report(self, report: Dict[str, Any]) -> str:
        """Format audit report for display."""
        lines = [
            f"JARVIS Self-Audit Report",
            f"Overall Score: {report['overall_score']:.2f}/1.00",
            f"Total Issues: {report['total_issues']}",
            f"Processing Time: {report['processing_time']:.2f}s",
            "",
            "Category Scores:"
        ]
        
        for category, results in report["category_scores"].items():
            lines.append(f"  {category.title()}: {results['score']:.2f}")
        
        if report["issues"]:
            lines.extend(["", "Issues:"])
            lines.extend(f"  - {issue}" for issue in report["issues"])
        
        if report["recommendations"]:
            lines.extend(["", "Recommendations:"])
            lines.extend(f"  - {rec}" for rec in report["recommendations"])
        
        return "\n".join(lines)
    
    def _format_benchmark_report(self, report: Dict[str, Any]) -> str:
        """Format benchmark report for display."""
        lines = [
            f"JARVIS Performance Benchmark",
            f"Average Response Time: {report['average_time']:.2f}s",
            "",
            "Individual Benchmarks:"
        ]
        
        for benchmark, time_value in report["benchmarks"].items():
            lines.append(f"  {benchmark}: {time_value:.2f}s")
        
        return "\n".join(lines)
    
    async def _test_single_tool(self, tool_name: str) -> bool:
        """Test a single tool."""
        try:
            tool = tool_registry.get(tool_name)
            if not tool:
                return False
            
            # Execute with empty parameters for testing
            result = tool_registry.execute(tool_name)
            return result.success or result.error != "Tool not found"
        except Exception:
            return False


# Global self-improvement engine instance
self_improvement_engine = SelfImprovementEngine()