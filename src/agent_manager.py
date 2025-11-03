"""
Autonomous Seismic Extraction Agent - MCP Server Integration
Add this to your OpenVDS MCP server

File structure:
your_mcp_server/
├── server.py (your existing MCP server)
├── openvds_tools.py (your existing tools)
└── agent_manager.py (THIS FILE - NEW)
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent execution states"""
    IDLE = "idle"
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ExtractionTask:
    """Single extraction task"""
    task_id: str
    type: str  # 'inline', 'crossline', 'timeslice'
    number: int
    depth_range: Optional[List[int]] = None
    priority: str = "medium"
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class AgentSession:
    """Agent extraction session"""
    session_id: str
    survey_id: str
    instruction: str
    state: AgentState
    created_at: str
    tasks: List[ExtractionTask]
    completed_count: int = 0
    failed_count: int = 0
    current_task: Optional[str] = None


class SeismicAgentManager:
    """
    Manages autonomous seismic extraction agents.
    Integrated into MCP server - one instance per server.
    """
    
    def __init__(self, openvds_tools):
        """
        Initialize the agent manager.
        
        Args:
            openvds_tools: Your existing OpenVDS tools module/class
        """
        self.openvds = openvds_tools
        self.sessions: Dict[str, AgentSession] = {}
        self.active_session_id: Optional[str] = None
        self._background_task: Optional[asyncio.Task] = None
        
        logger.info("SeismicAgentManager initialized")
    
    async def start_extraction(
        self,
        survey_id: str,
        instruction: str,
        auto_execute: bool = True
    ) -> Dict[str, Any]:
        """
        Start a new extraction session from natural language instruction.

        This is called via MCP tool: agent_start_extraction
        Returns immediately without blocking.

        Args:
            survey_id: VDS survey identifier
            instruction: Natural language instruction
            auto_execute: If True, start execution immediately

        Returns:
            Session info (planning happens in background)
        """
        logger.info(f"Starting extraction for {survey_id}: {instruction}")

        # Create session immediately
        session_id = str(uuid.uuid4())
        session = AgentSession(
            session_id=session_id,
            survey_id=survey_id,
            instruction=instruction,
            state=AgentState.PLANNING,
            created_at=datetime.now().isoformat(),
            tasks=[]
        )

        self.sessions[session_id] = session
        self.active_session_id = session_id

        # Start background planning and execution (non-blocking)
        if auto_execute:
            asyncio.create_task(
                self._plan_and_execute(session_id, survey_id, instruction)
            )
        else:
            asyncio.create_task(
                self._plan_only(session_id, survey_id, instruction)
            )

        # Return immediately
        return {
            "session_id": session_id,
            "status": "planning",
            "message": "Session created, planning in background",
            "instruction": instruction,
            "state": "planning"
        }

    async def _plan_only(self, session_id: str, survey_id: str, instruction: str):
        """Plan extraction tasks in background"""
        session = self.sessions.get(session_id)
        if not session:
            return

        try:
            tasks = await self._parse_instruction(survey_id, instruction)
            session.tasks = tasks
            session.state = AgentState.IDLE
            logger.info(f"Created plan with {len(tasks)} tasks for session {session_id}")
        except Exception as e:
            session.state = AgentState.ERROR
            logger.error(f"Error creating extraction plan: {e}")

    async def _plan_and_execute(self, session_id: str, survey_id: str, instruction: str):
        """Plan and execute extraction tasks in background"""
        session = self.sessions.get(session_id)
        if not session:
            return

        try:
            # Parse instruction into tasks
            tasks = await self._parse_instruction(survey_id, instruction)
            session.tasks = tasks
            session.state = AgentState.RUNNING

            logger.info(f"Created plan with {len(tasks)} tasks, starting execution")

            # Execute tasks
            await self._execute_tasks(session)

        except Exception as e:
            session.state = AgentState.ERROR
            logger.error(f"Error in plan and execute: {e}")
    
    async def _parse_instruction(
        self,
        survey_id: str,
        instruction: str
    ) -> List[ExtractionTask]:
        """
        Parse natural language instruction into extraction tasks.
        
        Uses simple pattern matching. For production, integrate Claude API.
        """
        import re
        
        # Get survey info
        survey_info = await self.openvds.get_survey_metadata(survey_id)
        
        tasks = []
        
        # Extract numbers from instruction
        numbers = [int(n) for n in re.findall(r'\d+', instruction)]

        # Separate depth range from line numbers
        depth_start = None
        depth_end = None

        # Look for depth-related patterns
        depth_pattern = r'(?:depth|sample|time)[\s\w]*?(\d+)[\s-]*(?:to|through|-)?[\s]*(\d+)'
        depth_match = re.search(depth_pattern, instruction.lower())
        if depth_match:
            depth_start = int(depth_match.group(1))
            depth_end = int(depth_match.group(2))
            # Remove depth numbers from general numbers list
            if depth_start in numbers:
                numbers.remove(depth_start)
            if depth_end in numbers:
                numbers.remove(depth_end)

        # If no depth found, use survey defaults
        if depth_start is None:
            depth_start = survey_info['sample_range'][0]
            depth_end = survey_info['sample_range'][1]

        # Pattern: "every Nth inline from X to Y" (must check BEFORE general inline pattern)
        if 'every' in instruction.lower() and 'inline' in instruction.lower() and len(numbers) >= 3:
            spacing = numbers[0]
            start = numbers[1]
            end = numbers[2]

            for inline_num in range(start, end + 1, spacing):
                if inline_num >= survey_info['inline_range'][0] and \
                   inline_num <= survey_info['inline_range'][1]:
                    task = ExtractionTask(
                        task_id=str(uuid.uuid4()),
                        type='inline',
                        number=inline_num,
                        depth_range=[depth_start, depth_end],
                        priority='high' if 'priority' in instruction.lower() else 'medium'
                    )
                    tasks.append(task)

        # Pattern: "every Nth crossline from X to Y" OR "crosslines skipping N"
        elif (('every' in instruction.lower() or 'skipping' in instruction.lower()) and
              'crossline' in instruction.lower()):

            # Look for "start at" pattern
            start_pattern = r'start\s+at\s+(?:crossline\s+)?(\d+)'
            start_match = re.search(start_pattern, instruction.lower())

            # Look for "through" or "to" pattern for end
            end_pattern = r'(?:through|to)\s+(\d+)'
            end_match = re.search(end_pattern, instruction.lower())

            # Look for spacing (skipping/every)
            spacing_pattern = r'(?:every|skipping)\s+(\d+)'
            spacing_match = re.search(spacing_pattern, instruction.lower())

            if spacing_match:
                spacing = int(spacing_match.group(1))
            elif len(numbers) >= 1:
                spacing = numbers[0]
            else:
                spacing = 100

            if start_match:
                start = int(start_match.group(1))
            elif len(numbers) >= 2:
                start = numbers[0] if numbers[0] != spacing else numbers[1]
            else:
                start = survey_info['crossline_range'][0]

            if end_match:
                end = int(end_match.group(1))
            elif len(numbers) >= 2:
                end = numbers[-1]
            else:
                end = survey_info['crossline_range'][1]

            for crossline_num in range(start, end + 1, spacing):
                if crossline_num >= survey_info['crossline_range'][0] and \
                   crossline_num <= survey_info['crossline_range'][1]:
                    task = ExtractionTask(
                        task_id=str(uuid.uuid4()),
                        type='crossline',
                        number=crossline_num,
                        depth_range=[depth_start, depth_end],
                        priority='high' if 'priority' in instruction.lower() else 'medium'
                    )
                    tasks.append(task)

        # Pattern: "inlines from X to Y at Z spacing"
        elif 'inline' in instruction.lower() and len(numbers) >= 2:
            start = numbers[0]
            end = numbers[1]
            spacing = numbers[2] if len(numbers) > 2 else 1000

            for inline_num in range(start, end + 1, spacing):
                if inline_num >= survey_info['inline_range'][0] and \
                   inline_num <= survey_info['inline_range'][1]:
                    task = ExtractionTask(
                        task_id=str(uuid.uuid4()),
                        type='inline',
                        number=inline_num,
                        depth_range=[depth_start, depth_end],
                        priority='high' if 'priority' in instruction.lower() else 'medium'
                    )
                    tasks.append(task)
        
        # Pattern: "crosslines X, Y, Z"
        elif 'crossline' in instruction.lower():
            # Extract crossline numbers (comma-separated or range)
            crossline_nums = numbers

            for xl_num in crossline_nums:
                if xl_num >= survey_info['crossline_range'][0] and \
                   xl_num <= survey_info['crossline_range'][1]:
                    task = ExtractionTask(
                        task_id=str(uuid.uuid4()),
                        type='crossline',
                        number=xl_num,
                        depth_range=[depth_start, depth_end]
                    )
                    tasks.append(task)
        
        # Pattern: "every Nth inline/crossline" (general, full range)
        elif 'every' in instruction.lower() or 'skipping' in instruction.lower():
            spacing = numbers[0] if numbers else 1000

            if 'inline' in instruction.lower():
                for inline_num in range(
                    survey_info['inline_range'][0],
                    survey_info['inline_range'][1] + 1,
                    spacing
                ):
                    task = ExtractionTask(
                        task_id=str(uuid.uuid4()),
                        type='inline',
                        number=inline_num,
                        depth_range=[depth_start, depth_end]
                    )
                    tasks.append(task)
            elif 'crossline' in instruction.lower():
                for crossline_num in range(
                    survey_info['crossline_range'][0],
                    survey_info['crossline_range'][1] + 1,
                    spacing
                ):
                    task = ExtractionTask(
                        task_id=str(uuid.uuid4()),
                        type='crossline',
                        number=crossline_num,
                        depth_range=[depth_start, depth_end]
                    )
                    tasks.append(task)
        
        if not tasks:
            raise ValueError(f"Could not parse instruction: {instruction}")
        
        logger.info(f"Parsed {len(tasks)} tasks from instruction")
        return tasks
    
    async def execute_session(self, session_id: str):
        """
        Execute extraction session in background.
        
        This runs asynchronously - doesn't block MCP server.
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.state == AgentState.RUNNING:
            logger.warning(f"Session {session_id} already running")
            return
        
        # Start background execution
        session.state = AgentState.RUNNING
        self._background_task = asyncio.create_task(
            self._execute_tasks(session)
        )
        
        logger.info(f"Started background execution for session {session_id}")
    
    async def _execute_tasks(self, session: AgentSession):
        """Background task execution loop"""
        logger.info(f"Executing {len(session.tasks)} tasks for session {session.session_id}")
        
        for task in session.tasks:
            # Check if paused
            if session.state == AgentState.PAUSED:
                logger.info("Session paused, waiting...")
                while session.state == AgentState.PAUSED:
                    await asyncio.sleep(1)
            
            # Check if stopped
            if session.state not in [AgentState.RUNNING, AgentState.PAUSED]:
                break
            
            # Execute task
            session.current_task = task.task_id
            task.status = "running"
            task.started_at = datetime.now().isoformat()
            
            try:
                result = await self._execute_single_task(session.survey_id, task)
                task.status = "completed"
                task.result = result
                session.completed_count += 1
                
                logger.info(f"✓ Task {task.task_id} completed: {task.type} {task.number}")
                
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                session.failed_count += 1
                
                logger.error(f"✗ Task {task.task_id} failed: {e}")
            
            finally:
                task.completed_at = datetime.now().isoformat()
                session.current_task = None
            
            # Small delay between tasks
            await asyncio.sleep(0.5)
        
        session.state = AgentState.COMPLETED
        logger.info(f"Session {session.session_id} completed: "
                   f"{session.completed_count} successful, {session.failed_count} failed")
    
    async def _execute_single_task(
        self,
        survey_id: str,
        task: ExtractionTask
    ) -> Dict[str, Any]:
        """Execute a single extraction task using OpenVDS tools"""
        
        if task.type == 'inline':
            result = await self.openvds.extract_inline_image(
                survey_id=survey_id,
                inline_number=task.number,
                sample_range=task.depth_range,
                colormap='seismic',
                clip_percentile=98
            )
        elif task.type == 'crossline':
            result = await self.openvds.extract_crossline_image(
                survey_id=survey_id,
                crossline_number=task.number,
                sample_range=task.depth_range,
                colormap='seismic',
                clip_percentile=98
            )
        elif task.type == 'timeslice':
            result = await self.openvds.extract_timeslice_image(
                survey_id=survey_id,
                time_value=task.number,
                colormap='seismic',
                clip_percentile=98
            )
        else:
            raise ValueError(f"Unknown task type: {task.type}")
        
        return result
    
    def get_status(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get agent status.
        
        This is called via MCP tool: agent_get_status
        """
        if session_id is None:
            session_id = self.active_session_id
        
        if not session_id:
            return {
                "status": "no_active_session",
                "sessions": list(self.sessions.keys())
            }
        
        session = self.sessions.get(session_id)
        if not session:
            return {"error": f"Session {session_id} not found"}
        
        # Calculate progress
        total_tasks = len(session.tasks)
        completed = session.completed_count
        failed = session.failed_count
        pending = total_tasks - completed - failed
        
        # Get current task info
        current_task_info = None
        if session.current_task:
            current_task = next(
                (t for t in session.tasks if t.task_id == session.current_task),
                None
            )
            if current_task:
                current_task_info = {
                    "type": current_task.type,
                    "number": current_task.number,
                    "status": current_task.status
                }
        
        return {
            "session_id": session.session_id,
            "survey_id": session.survey_id,
            "state": session.state.value,
            "instruction": session.instruction,
            "progress": {
                "total": total_tasks,
                "completed": completed,
                "failed": failed,
                "pending": pending,
                "percent": round(completed / total_tasks * 100, 1) if total_tasks > 0 else 0
            },
            "current_task": current_task_info,
            "created_at": session.created_at
        }
    
    def pause_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Pause execution.
        
        This is called via MCP tool: agent_pause
        """
        if session_id is None:
            session_id = self.active_session_id
        
        session = self.sessions.get(session_id)
        if not session:
            return {"error": f"Session {session_id} not found"}
        
        if session.state != AgentState.RUNNING:
            return {"error": f"Session not running (state: {session.state.value})"}
        
        session.state = AgentState.PAUSED
        logger.info(f"Session {session_id} paused")
        
        return {"status": "paused", "session_id": session_id}
    
    def resume_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Resume paused session"""
        if session_id is None:
            session_id = self.active_session_id
        
        session = self.sessions.get(session_id)
        if not session:
            return {"error": f"Session {session_id} not found"}
        
        if session.state != AgentState.PAUSED:
            return {"error": f"Session not paused (state: {session.state.value})"}
        
        session.state = AgentState.RUNNING
        logger.info(f"Session {session_id} resumed")
        
        return {"status": "resumed", "session_id": session_id}
    
    def get_results(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get extraction results.
        
        This is called via MCP tool: agent_get_results
        """
        if session_id is None:
            session_id = self.active_session_id
        
        session = self.sessions.get(session_id)
        if not session:
            return {"error": f"Session {session_id} not found"}
        
        # Compile results (exclude binary image data)
        completed_tasks = []
        for t in session.tasks:
            if t.status == "completed":
                # Create a copy of result without binary data
                result_summary = None
                if t.result:
                    result_summary = {k: v for k, v in t.result.items() if k != 'image_data'}

                completed_tasks.append({
                    "task_id": t.task_id,
                    "type": t.type,
                    "number": t.number,
                    "depth_range": t.depth_range,
                    "result_summary": result_summary,
                    "started_at": t.started_at,
                    "completed_at": t.completed_at
                })
        
        failed_tasks = [
            {
                "task_id": t.task_id,
                "type": t.type,
                "number": t.number,
                "error": t.error
            }
            for t in session.tasks if t.status == "failed"
        ]
        
        return {
            "session_id": session.session_id,
            "survey_id": session.survey_id,
            "instruction": session.instruction,
            "state": session.state.value,
            "summary": {
                "total_tasks": len(session.tasks),
                "completed": session.completed_count,
                "failed": session.failed_count,
                "success_rate": round(
                    session.completed_count / len(session.tasks) * 100, 1
                ) if session.tasks else 0
            },
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks
        }


# =============================================================================
# MCP TOOL DEFINITIONS
# Add these to your MCP server tool registry
# =============================================================================

async def tool_agent_start_extraction(
    agent_manager: SeismicAgentManager,
    survey_id: str,
    instruction: str,
    auto_execute: bool = True
) -> Dict[str, Any]:
    """
    Start autonomous extraction from natural language instruction.
    
    Examples:
    - "Extract all inlines from 51000 to 59000 at 2000 spacing, depth 5500-7000m"
    - "Extract crosslines 8300, 8400, 8500, 8600 at depth 5800-6800m"
    - "Extract every 500th inline across the survey"
    """
    return await agent_manager.start_extraction(survey_id, instruction, auto_execute)


async def tool_agent_get_status(
    agent_manager: SeismicAgentManager,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get status of agent execution"""
    return agent_manager.get_status(session_id)


async def tool_agent_pause(
    agent_manager: SeismicAgentManager,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Pause agent execution"""
    return agent_manager.pause_session(session_id)


async def tool_agent_resume(
    agent_manager: SeismicAgentManager,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Resume paused agent"""
    return agent_manager.resume_session(session_id)


async def tool_agent_get_results(
    agent_manager: SeismicAgentManager,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get extraction results"""
    return agent_manager.get_results(session_id)