"""jarvis.automation

Automation engine with scheduled tasks, routines, and conditional actions.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from jarvis.error_handler import safe_executor
from jarvis.settings_manager import settings

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """Scheduled task definition."""
    id: str
    name: str
    command: str
    schedule_type: str  # "time", "interval", "condition"
    schedule_value: str  # time string or interval seconds
    enabled: bool = True
    last_run: datetime | None = None
    run_count: int = 0
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class Routine:
    """Routine with multiple steps."""
    id: str
    name: str
    trigger: str  # "morning", "evening", "custom"
    steps: list[str] = field(default_factory=list)
    enabled: bool = True
    last_run: datetime | None = None


class Scheduler:
    """Task scheduler with multiple scheduling modes."""
    
    def __init__(self) -> None:
        self.tasks: dict[str, ScheduledTask] = {}
        self.routines: dict[str, Routine] = {}
        self._running = False
        self._thread: threading.Thread | None = None
        self._callbacks: dict[str, Callable[[str], None]] = {}
        self._load()
    
    def _load(self) -> None:
        """Load scheduled tasks from file."""
        try:
            path = Path("jarvis_automation.json")
            if path.exists():
                with open(path, 'r') as f:
                    data = json.load(f)
                    for task_data in data.get("tasks", []):
                        task = ScheduledTask(**task_data)
                        if isinstance(task.last_run, str):
                            task.last_run = datetime.fromisoformat(task.last_run)
                        self.tasks[task.id] = task
                    
                    for routine_data in data.get("routines", []):
                        routine = Routine(**routine_data)
                        if isinstance(routine.last_run, str):
                            routine.last_run = datetime.fromisoformat(routine.last_run)
                        self.routines[routine.id] = routine
        except Exception as e:
            logger.error(f"Failed to load automation: {e}")
    
    def _save(self) -> None:
        """Save scheduled tasks to file."""
        try:
            path = Path("jarvis_automation.json")
            data = {
                "tasks": [asdict(t) for t in self.tasks.values()],
                "routines": [asdict(r) for r in self.routines.values()],
            }
            with open(path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save automation: {e}")
    
    def register_callback(self, action: str, callback: Callable[[str], None]) -> None:
        """Register a callback for automation actions."""
        self._callbacks[action] = callback
    
    def add_task(
        self,
        name: str,
        command: str,
        schedule_type: str,
        schedule_value: str,
        conditions: dict[str, Any] | None = None,
    ) -> str:
        """Add a scheduled task."""
        task_id = f"task_{int(time.time())}_{name.replace(' ', '_')}"
        task = ScheduledTask(
            id=task_id,
            name=name,
            command=command,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            conditions=conditions or {},
        )
        self.tasks[task_id] = task
        self._save()
        logger.info(f"Added task: {name}")
        return task_id
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save()
            return True
        return False
    
    def add_routine(self, name: str, trigger: str, steps: list[str]) -> str:
        """Add a routine."""
        routine_id = f"routine_{int(time.time())}_{name.replace(' ', '_')}"
        routine = Routine(
            id=routine_id,
            name=name,
            trigger=trigger,
            steps=steps,
        )
        self.routines[routine_id] = routine
        self._save()
        logger.info(f"Added routine: {name}")
        return routine_id
    
    def run_routine(self, routine_id: str) -> str:
        """Execute a routine."""
        routine = self.routines.get(routine_id)
        if not routine:
            return "Routine not found"
        
        if not routine.enabled:
            return "Routine is disabled"
        
        logger.info(f"Running routine: {routine.name}")
        results = []
        
        for i, step in enumerate(routine.steps, 1):
            try:
                # Execute step
                if "command" in self._callbacks:
                    result = self._callbacks["command"](step)
                    results.append(f"Step {i}: {result or 'Done'}")
                else:
                    results.append(f"Step {i}: {step}")
                    
            except Exception as e:
                results.append(f"Step {i} failed: {e}")
        
        routine.last_run = datetime.now()
        self._save()
        
        return f"Routine '{routine.name}' completed:\n" + "\n".join(results)
    
    def _should_run_task(self, task: ScheduledTask) -> bool:
        """Check if task should run now."""
        if not task.enabled:
            return False
        
        now = datetime.now()
        
        if task.schedule_type == "time":
            # Run at specific time (HH:MM format)
            try:
                hour, minute = map(int, task.schedule_value.split(":"))
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Check if already ran today
                if task.last_run and task.last_run.date() == now.date():
                    return False
                
                # Check if it's time
                return now >= target_time and (now - target_time) < timedelta(minutes=1)
            except Exception:
                return False
        
        elif task.schedule_type == "interval":
            # Run every N seconds
            try:
                interval = int(task.schedule_value)
                if task.last_run:
                    return (now - task.last_run).total_seconds() >= interval
                return True
            except Exception:
                return False
        
        elif task.schedule_type == "condition":
            # Check conditions
            return self._check_conditions(task.conditions)
        
        return False
    
    def _check_conditions(self, conditions: dict[str, Any]) -> bool:
        """Check if conditions are met."""
        for key, value in conditions.items():
            if key == "time_after":
                hour, minute = map(int, value.split(":"))
                now = datetime.now()
                if now.hour < hour or (now.hour == hour and now.minute < minute):
                    return False
            
            elif key == "day_of_week":
                days = value if isinstance(value, list) else [value]
                if datetime.now().strftime("%A") not in days:
                    return False
            
            elif key == "cpu_threshold":
                try:
                    import psutil
                    if psutil.cpu_percent() < value:
                        return False
                except Exception:
                    return False
        
        return True
    
    def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a task."""
        logger.info(f"Executing task: {task.name}")
        
        try:
            if "command" in self._callbacks:
                self._callbacks["command"](task.command)
            
            task.last_run = datetime.now()
            task.run_count += 1
            self._save()
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
    
    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        logger.info("Automation scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Automation scheduler stopped")
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                # Check tasks
                for task in list(self.tasks.values()):
                    if self._should_run_task(task):
                        self._execute_task(task)
                
                # Check routines (morning/evening triggers)
                self._check_routine_triggers()
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(30)
    
    def _check_routine_triggers(self) -> None:
        """Check and trigger time-based routines."""
        now = datetime.now()
        
        for routine in self.routines.values():
            if not routine.enabled:
                continue
            
            # Check if already ran today
            if routine.last_run and routine.last_run.date() == now.date():
                continue
            
            should_trigger = False
            
            if routine.trigger == "morning" and now.hour == 8:
                should_trigger = True
            elif routine.trigger == "evening" and now.hour == 20:
                should_trigger = True
            elif routine.trigger == "lunch" and now.hour == 12:
                should_trigger = True
            elif routine.trigger == "bedtime" and now.hour == 22:
                should_trigger = True
            
            if should_trigger:
                self.run_routine(routine.id)
    
    def list_tasks(self) -> list[ScheduledTask]:
        """List all scheduled tasks."""
        return list(self.tasks.values())
    
    def list_routines(self) -> list[Routine]:
        """List all routines."""
        return list(self.routines.values())
    
    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            self._save()
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            self._save()
            return True
        return False


class CustomVoiceCommands:
    """Manage custom voice commands."""
    
    def __init__(self) -> None:
        self.commands: dict[str, str] = {}
        self._load()
    
    def _load(self) -> None:
        """Load custom commands."""
        try:
            path = Path("jarvis_custom_commands.json")
            if path.exists():
                with open(path, 'r') as f:
                    self.commands = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load custom commands: {e}")
    
    def _save(self) -> None:
        """Save custom commands."""
        try:
            path = Path("jarvis_custom_commands.json")
            with open(path, 'w') as f:
                json.dump(self.commands, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save custom commands: {e}")
    
    def add_command(self, phrase: str, action: str) -> None:
        """Add custom voice command."""
        self.commands[phrase.lower()] = action
        self._save()
        logger.info(f"Added custom command: {phrase}")
    
    def remove_command(self, phrase: str) -> bool:
        """Remove custom voice command."""
        if phrase.lower() in self.commands:
            del self.commands[phrase.lower()]
            self._save()
            return True
        return False
    
    def get_action(self, phrase: str) -> str | None:
        """Get action for phrase."""
        return self.commands.get(phrase.lower())
    
    def list_commands(self) -> dict[str, str]:
        """List all custom commands."""
        return self.commands.copy()


# Global instances
scheduler = Scheduler()
custom_commands = CustomVoiceCommands()


def schedule_task(name: str, command: str, when: str) -> str:
    """Schedule a task."""
    # Parse when (e.g., "daily at 9:00" or "every 300 seconds")
    if "daily at" in when:
        time_str = when.replace("daily at", "").strip()
        task_id = scheduler.add_task(name, command, "time", time_str)
        return f"Task scheduled: {name} at {time_str}"
    
    elif "every" in when and "seconds" in when:
        seconds = when.replace("every", "").replace("seconds", "").strip()
        task_id = scheduler.add_task(name, command, "interval", seconds)
        return f"Task scheduled: {name} every {seconds} seconds"
    
    return "Invalid schedule format. Use 'daily at HH:MM' or 'every N seconds'"


def create_routine(name: str, steps: list[str], trigger: str = "custom") -> str:
    """Create a routine."""
    routine_id = scheduler.add_routine(name, trigger, steps)
    return f"Routine created: {name} with {len(steps)} steps"


def run_routine(name: str) -> str:
    """Run a routine by name."""
    for routine_id, routine in scheduler.routines.items():
        if routine.name.lower() == name.lower():
            return scheduler.run_routine(routine_id)
    return f"Routine '{name}' not found"


def add_custom_command(phrase: str, action: str) -> str:
    """Add custom voice command."""
    custom_commands.add_command(phrase, action)
    return f"Custom command added: '{phrase}' -> '{action}'"
