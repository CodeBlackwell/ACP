from collections.abc import AsyncGenerator
from functools import reduce
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import time
import json
import re

# Add the project root to the Python path so we can import from the agents module
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from acp_sdk import Message
from acp_sdk.models import MessagePart
from acp_sdk.server import Context, Server
from acp_sdk.client import Client
from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import TokenMemory
from beeai_framework.utils.dicts import exclude_none
from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.tools import ToolOutput
from beeai_framework.tools.tool import Tool
from beeai_framework.tools.types import ToolRunOptions
from beeai_framework.utils.strings import to_json
from pydantic import BaseModel, Field

# Import the modular agents
from agents.planner.planner_agent import planner_agent
from agents.designer.designer_agent import designer_agent
from agents.coder.coder_agent import coder_agent
from agents.test_writer.test_writer_agent import test_writer_agent
from agents.reviewer.reviewer_agent import reviewer_agent

# Import the modular tools
from orchestrator.regression_test_runner_tool import TestRunnerTool

# Import the enhanced orchestrator config
from orchestrator.orchestrator_configs import orchestrator_config
# Load environment variables from .env file
load_dotenv()

server = Server()

# ============================================================================
# ENHANCED PROGRESS TRACKING
# ============================================================================

@dataclass
class ObjectiveStatus:
    """Track individual objective completion"""
    name: str
    description: str
    agent: str
    status: str  # "pending", "in_progress", "completed", "failed"
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    output_length: int = 0
    challenges: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def status_emoji(self) -> str:
        return {
            "pending": "⏳", 
            "in_progress": "🔄", 
            "completed": "✅", 
            "failed": "❌"
        }.get(self.status, "❓")

@dataclass
class TestResults:
    """Track test execution results"""
    tests_written: int = 0
    tests_executed: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    test_details: List[Dict[str, Any]] = field(default_factory=list)
    coverage_info: Optional[str] = None
    
    @property
    def pass_rate(self) -> float:
        if self.tests_executed == 0:
            return 0.0
        return (self.tests_passed / self.tests_executed) * 100

@dataclass
class ProgressReport:
    """Comprehensive progress tracking"""
    session_id: str
    workflow_type: str
    start_time: float
    end_time: Optional[float] = None
    objectives: List[ObjectiveStatus] = field(default_factory=list)
    test_results: TestResults = field(default_factory=TestResults)
    challenges: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def success_rate(self) -> float:
        completed = sum(1 for obj in self.objectives if obj.status == "completed")
        total = len(self.objectives)
        return (completed / total * 100) if total > 0 else 0.0
    
    def generate_report(self) -> str:
        """Generate aesthetic progress report"""
        report = []
        
        # Header
        report.append("🎯 WORKFLOW PROGRESS REPORT")
        report.append("=" * 80)
        report.append(f"📋 Workflow: {self.workflow_type}")
        report.append(f"⏱️  Duration: {self.duration:.2f}s")
        report.append(f"📊 Success Rate: {self.success_rate:.1f}%")
        report.append("")
        
        # Objectives Summary
        completed = sum(1 for obj in self.objectives if obj.status == "completed")
        failed = sum(1 for obj in self.objectives if obj.status == "failed")
        in_progress = sum(1 for obj in self.objectives if obj.status == "in_progress")
        pending = sum(1 for obj in self.objectives if obj.status == "pending")
        
        report.append("📈 OBJECTIVES SUMMARY")
        report.append("-" * 40)
        report.append(f"✅ Completed: {completed}/{len(self.objectives)}")
        report.append(f"❌ Failed: {failed}")
        report.append(f"🔄 In Progress: {in_progress}")
        report.append(f"⏳ Pending: {pending}")
        report.append("")
        
        # Detailed Objectives Checklist
        report.append("📋 OBJECTIVES CHECKLIST")
        report.append("-" * 40)
        for i, obj in enumerate(self.objectives, 1):
            status_line = f"{obj.status_emoji} {i}. {obj.name} ({obj.agent})"
            if obj.status == "completed":
                status_line += f" - {obj.duration:.2f}s"
            report.append(status_line)
            
            if obj.description:
                report.append(f"   └─ {obj.description}")
            
            if obj.challenges:
                for challenge in obj.challenges:
                    report.append(f"   ⚠️  Challenge: {challenge}")
        report.append("")
        
        # Test Results
        if self.test_results.tests_written > 0:
            report.append("🧪 TEST RESULTS")
            report.append("-" * 40)
            report.append(f"📝 Tests Written: {self.test_results.tests_written}")
            report.append(f"▶️  Tests Executed: {self.test_results.tests_executed}")
            report.append(f"✅ Tests Passed: {self.test_results.tests_passed}")
            report.append(f"❌ Tests Failed: {self.test_results.tests_failed}")
            report.append(f"📊 Pass Rate: {self.test_results.pass_rate:.1f}%")
            
            if self.test_results.test_details:
                report.append("\n📋 Test Details:")
                for test in self.test_results.test_details:
                    status = "✅" if test.get("passed", False) else "❌"
                    report.append(f"  {status} {test.get('name', 'Unknown Test')}")
            report.append("")
        
        # Development Challenges
        if self.challenges:
            report.append("⚠️  DEVELOPMENT CHALLENGES")
            report.append("-" * 40)
            for i, challenge in enumerate(self.challenges, 1):
                report.append(f"{i}. {challenge}")
            report.append("")
        
        # Performance Metrics
        if self.performance_metrics:
            report.append("📊 PERFORMANCE METRICS")
            report.append("-" * 40)
            for key, value in self.performance_metrics.items():
                report.append(f"• {key}: {value}")
            report.append("")
        
        # Footer
        status = "🎉 SUCCESS" if self.success_rate == 100 else "⚠️  PARTIAL SUCCESS" if self.success_rate > 0 else "❌ FAILED"
        report.append(f"🎯 FINAL STATUS: {status}")
        report.append("=" * 80)
        
        return "\n".join(report)

# Global progress tracking
current_progress_report: Optional[ProgressReport] = None

# ============================================================================
# INDIVIDUAL TEAM MEMBER AGENTS (Enhanced with Progress Tracking)
# ============================================================================

async def run_team_member_with_tracking(agent: str, input: str, objective_name: str) -> List[Message]:
    """Enhanced team member execution with progress tracking"""
    global current_progress_report
    
    if current_progress_report:
        # Find or create objective
        objective = None
        for obj in current_progress_report.objectives:
            if obj.name == objective_name:
                objective = obj
                break
        
        if not objective:
            objective = ObjectiveStatus(
                name=objective_name,
                description=f"Execute {agent} for {objective_name}",
                agent=agent,
                status="pending"
            )
            current_progress_report.objectives.append(objective)
        
        # Update status to in_progress
        objective.status = "in_progress"
        objective.start_time = time.time()
    
    try:
        # Execute the agent
        result = await run_team_member(agent, input)
        
        if current_progress_report and objective:
            # Update status to completed
            objective.status = "completed"
            objective.end_time = time.time()
            objective.output_length = len(str(result[0])) if result else 0
            
            # Analyze output for challenges
            output_text = str(result[0]).lower() if result else ""
            if any(keyword in output_text for keyword in ["error", "issue", "problem", "challenge"]):
                objective.challenges.append("Potential issues detected in output")
        
        return result
        
    except Exception as e:
        if current_progress_report and objective:
            objective.status = "failed"
            objective.end_time = time.time()
            objective.challenges.append(f"Execution failed: {str(e)}")
            
            # Add to global challenges
            current_progress_report.challenges.append(f"{agent} failed: {str(e)}")
        
        raise e

# Original run_team_member function (keeping for compatibility)
async def run_team_member(agent: str, input: str) -> list[Message]:
    """Calls a team member agent using ACP protocol"""
    agent_ports = {
        "planner_agent": 8080,
        "designer_agent": 8080,
        "coder_agent": 8080,
        "test_writer_agent": 8080,
        "reviewer_agent": 8080,
    }
    
    agent_name_mapping = {
        "planner_agent": "planner_agent_wrapper",
        "designer_agent": "designer_agent_wrapper",
        "coder_agent": "coder_agent_wrapper",
        "test_writer_agent": "test_writer_agent_wrapper",
        "reviewer_agent": "reviewer_agent_wrapper"
    }
    
    internal_agent_name = agent_name_mapping.get(agent, agent)
    port = agent_ports.get(agent, 8080)
    base_url = f"http://localhost:{port}"
    
    async with Client(base_url=base_url) as client:
        try:
            run = await client.run_sync(
                agent=internal_agent_name,
                input=[Message(parts=[MessagePart(content=input, content_type="text/plain")])]
            )
            return run.output
        except Exception as e:
            print(f"❌ Error calling {agent} on {base_url}: {e}")
            return [Message(parts=[MessagePart(content=f"Error from {agent}: {e}", content_type="text/plain")])]

# Register agent wrappers
@server.agent()
async def planner_agent_wrapper(input: list[Message]) -> AsyncGenerator:
    async for part in planner_agent(input):
        yield part

@server.agent()
async def designer_agent_wrapper(input: list[Message]) -> AsyncGenerator:
    async for part in designer_agent(input):
        yield part

@server.agent()
async def coder_agent_wrapper(input: list[Message]) -> AsyncGenerator:
    async for part in coder_agent(input):
        yield part

@server.agent()
async def test_writer_agent_wrapper(input: list[Message]) -> AsyncGenerator:
    async for part in test_writer_agent(input):
        yield part

@server.agent()
async def reviewer_agent_wrapper(input: list[Message]) -> AsyncGenerator:
    async for part in reviewer_agent(input):
        yield part

# ============================================================================
# ENHANCED CODING TEAM COORDINATION TOOL
# ============================================================================

class TeamMember(str, Enum):
    planner = "planner"
    designer = "designer"
    test_writer = "test_writer"
    coder = "coder"
    reviewer = "reviewer"

class WorkflowStep(str, Enum):
    planning = "planning"
    design = "design"
    test_writing = "test_writing"
    implementation = "implementation"
    review = "review"
    tdd_workflow = "tdd_workflow"
    full_workflow = "full_workflow"

class CodingTeamInput(BaseModel):
    requirements: str = Field(description="The project requirements or task description")
    workflow: WorkflowStep = Field(description="The workflow step to execute")
    team_members: list[TeamMember] = Field(
        default=[TeamMember.planner, TeamMember.designer, TeamMember.test_writer, TeamMember.coder, TeamMember.reviewer],
        description="Team members to involve in the process"
    )

class TeamMemberResult(BaseModel):
    team_member: TeamMember = Field(description="The team member who produced this result")
    output: str = Field(description="The output from the team member")

class CodingTeamResult(BaseModel):
    results: list[TeamMemberResult] = Field(description="Results from each team member")
    final_summary: str = Field(description="Summary of the complete workflow")
    progress_report: str = Field(description="Detailed progress report")
    success_metrics: Dict[str, Any] = Field(default_factory=dict, description="Success metrics and statistics")

class CodingTeamOutput(ToolOutput):
    result: CodingTeamResult = Field(description="Enhanced coding team result")

    def get_text_content(self) -> str:
        return self.result.progress_report

    def is_empty(self) -> bool:
        return False

    def __init__(self, result: CodingTeamResult) -> None:
        super().__init__()
        self.result = result

class EnhancedCodingTeamTool(Tool[CodingTeamInput, ToolRunOptions, CodingTeamOutput]):
    """Enhanced tool with comprehensive progress tracking and parallel execution"""
    name = "CodingTeam"
    description = "Coordinate a coding team with detailed progress tracking and parallel execution capabilities"
    input_schema = CodingTeamInput

    def _create_emitter(self) -> Emitter:
        return Emitter.root().child(
            namespace=["tool", "enhanced_coding_team"],
            creator=self,
        )

    async def _run(
        self, input: CodingTeamInput, options: ToolRunOptions | None, context: RunContext
    ) -> CodingTeamOutput:
        """Enhanced workflow execution with comprehensive tracking"""
        global current_progress_report
        
        # Initialize progress tracking
        session_id = f"session_{int(time.time())}"
        current_progress_report = ProgressReport(
            session_id=session_id,
            workflow_type=input.workflow.value,
            start_time=time.time()
        )
        
        print(f"🚀 Starting Enhanced Workflow: {input.workflow.value}")
        print(f"📋 Session ID: {session_id}")
        
        try:
            # Import here to avoid circular imports
            from workflows import execute_workflow
            
            # Execute the workflow with tracking
            results = await execute_workflow(input)
            
            # Analyze test results from outputs
            await self._analyze_test_results(results)
            
            # Generate performance metrics
            await self._calculate_performance_metrics(results)
            
            # Complete progress tracking
            current_progress_report.end_time = time.time()
            
            # Generate comprehensive report
            progress_report = current_progress_report.generate_report()
            
            # Create success metrics
            success_metrics = {
                "total_objectives": len(current_progress_report.objectives),
                "completed_objectives": sum(1 for obj in current_progress_report.objectives if obj.status == "completed"),
                "success_rate": current_progress_report.success_rate,
                "total_duration": current_progress_report.duration,
                "tests_pass_rate": current_progress_report.test_results.pass_rate,
                "challenges_encountered": len(current_progress_report.challenges)
            }
            
            # Create final summary
            summary = f"""
🎯 Workflow Completed: {input.workflow.value}
📊 Success Rate: {current_progress_report.success_rate:.1f}%
⏱️  Duration: {current_progress_report.duration:.2f}s
👥 Team Members: {len(results)} agents
🧪 Test Pass Rate: {current_progress_report.test_results.pass_rate:.1f}%
⚠️  Challenges: {len(current_progress_report.challenges)}
            """.strip()
            
            result = CodingTeamResult(
                results=results,
                final_summary=summary,
                progress_report=progress_report,
                success_metrics=success_metrics
            )
            
            return CodingTeamOutput(result=result)
            
        except Exception as e:
            if current_progress_report:
                current_progress_report.challenges.append(f"Critical workflow error: {str(e)}")
                current_progress_report.end_time = time.time()
                
                error_report = current_progress_report.generate_report()
                error_report += f"\n\n❌ CRITICAL ERROR: {str(e)}"
                
                result = CodingTeamResult(
                    results=[],
                    final_summary=f"Workflow failed: {str(e)}",
                    progress_report=error_report,
                    success_metrics={"error": str(e)}
                )
                
                return CodingTeamOutput(result=result)
            
            raise e
    
    async def _analyze_test_results(self, results: List[TeamMemberResult]):
        """Analyze test results from agent outputs"""
        global current_progress_report
        
        if not current_progress_report:
            return
        
        for result in results:
            if result.team_member == TeamMember.test_writer:
                # Count tests written
                output = result.output.lower()
                test_keywords = ["test", "describe", "it(", "def test_", "assert", "expect"]
                tests_written = sum(output.count(keyword) for keyword in test_keywords)
                current_progress_report.test_results.tests_written = max(
                    current_progress_report.test_results.tests_written, 
                    tests_written
                )
            
            elif result.team_member == TeamMember.coder:
                # Analyze for test execution results
                output = result.output
                if "test" in output.lower():
                    # Simple heuristic for test results
                    passed_matches = re.findall(r'(\d+)\s*(?:test|spec)s?\s*passed', output, re.IGNORECASE)
                    failed_matches = re.findall(r'(\d+)\s*(?:test|spec)s?\s*failed', output, re.IGNORECASE)
                    
                    if passed_matches:
                        current_progress_report.test_results.tests_passed = int(passed_matches[0])
                    if failed_matches:
                        current_progress_report.test_results.tests_failed = int(failed_matches[0])
                    
                    current_progress_report.test_results.tests_executed = (
                        current_progress_report.test_results.tests_passed + 
                        current_progress_report.test_results.tests_failed
                    )
    
    async def _calculate_performance_metrics(self, results: List[TeamMemberResult]):
        """Calculate performance metrics"""
        global current_progress_report
        
        if not current_progress_report:
            return
        
        # Agent output analysis
        total_chars = sum(len(result.output) for result in results)
        avg_chars = total_chars / len(results) if results else 0
        
        # Objective timing analysis
        completed_objectives = [obj for obj in current_progress_report.objectives if obj.status == "completed"]
        avg_objective_time = sum(obj.duration for obj in completed_objectives) / len(completed_objectives) if completed_objectives else 0
        
        current_progress_report.performance_metrics.update({
            "total_output_chars": total_chars,
            "avg_output_chars": int(avg_chars),
            "avg_objective_duration": round(avg_objective_time, 2),
            "fastest_objective": min(obj.duration for obj in completed_objectives) if completed_objectives else 0,
            "slowest_objective": max(obj.duration for obj in completed_objectives) if completed_objectives else 0,
            "agents_executed": len(results)
        })

# ============================================================================
# ENHANCED ORCHESTRATOR CONFIGURATION
# ============================================================================

enhanced_orchestrator_config = {
    "model": orchestrator_config["model"],
    "instructions": orchestrator_config["instructions"] 
}

# ============================================================================
# MAIN ORCHESTRATOR AGENT
# ============================================================================

@server.agent(name="orchestrator", metadata={"ui": {"type": "handsoff"}})
async def enhanced_orchestrator(input: list[Message], context: Context) -> AsyncGenerator:
    """Enhanced orchestrator with comprehensive progress tracking"""
    llm = ChatModel.from_name(enhanced_orchestrator_config["model"])

    agent = ReActAgent(
        llm=llm,
        tools=[EnhancedCodingTeamTool(), TestRunnerTool()],
        templates={
            "system": lambda template: template.update(
                defaults=exclude_none({
                    "instructions": enhanced_orchestrator_config["instructions"],
                    "role": "system",
                })
            )
        },
        memory=TokenMemory(llm),
    )

    prompt = reduce(lambda x, y: x + y, input)
    response = await agent.run(str(prompt)).observe(
        lambda emitter: emitter.on(
            "update", lambda data, event: print(f"Enhanced Orchestrator({data.update.key}) 🎯: ", data.update.parsed_value)
        )
    )

    yield MessagePart(content=response.result.text)

# Run the server
if __name__ == "__main__":
    print("🚀 Starting Enhanced Coding Team Agent System on port 8080...")
    print("✨ Features: Progress Tracking | Parallel Execution | Comprehensive Reporting")
    server.run(port=8080)