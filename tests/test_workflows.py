"""
🧪 Modern Workflow Testing Framework

A comprehensive testing system that leverages the full monitoring and tracing
capabilities of the enhanced workflow architecture. Designed for clarity,
aesthetics, and detailed reporting.
"""

import asyncio
import sys
import os
import time
import json
import traceback
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import our modern architecture components
from shared.data_models import (
    TeamMember, WorkflowStep, CodingTeamInput, TeamMemberResult
)
from workflows import execute_workflow
# Monitoring imports removed - tracing disabled
from workflows.workflow_manager import get_available_workflows, get_workflow_description

# Import Test Runner components
from agents.validator import TestRunnerAgent, TestReportGenerator


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

class TestComplexity(Enum):
    """Test complexity levels"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    COMPLEX = "complex"
    STRESS = "stress"


@dataclass
class TestScenario:
    """Defines a test scenario"""
    name: str
    complexity: TestComplexity
    requirements: str
    timeout: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)


# Comprehensive test scenarios
TEST_SCENARIOS = {
    TestComplexity.MINIMAL: TestScenario(
        name="Hello World API : In Python",
        complexity=TestComplexity.MINIMAL,
        requirements="Create a basic 'Hello World' REST API endpoint that returns a JSON response.Write tests using pytest. **Only Use Python**",
        timeout=180
    ),
    TestComplexity.STANDARD: TestScenario(
        name="TODO List API : In Python",
        complexity=TestComplexity.STANDARD,
        requirements="""Create a complete TODO list REST API with the following endpoints:
        - GET /todos - List all todos
        - POST /todos - Create a new todo
        - GET /todos/:id - Get a specific todo
        - PUT /todos/:id - Update a todo
        - DELETE /todos/:id - Delete a todo
        Include proper error handling and validation. 
        Write tests using pytest.
        **Only Use Python**""",
        timeout=300
    ),
    TestComplexity.COMPLEX: TestScenario(
        name="E-Commerce Platform : In Python",
        complexity=TestComplexity.COMPLEX,
        requirements="""Build a full-stack e-commerce application with:
        - User authentication and authorization
        - Product catalog with search and filtering
        - Shopping cart functionality
        - Order management system
        - Payment processing integration
        - Admin dashboard
        - Email notifications
        - API documentation
        **Only Use Python**""",
        timeout=600
    ),
    TestComplexity.STRESS: TestScenario(
        name="Microservices Architecture : In Python",
        complexity=TestComplexity.STRESS,
        requirements="""Design and implement a microservices architecture for a social media platform with:
        - User service (authentication, profiles)
        - Post service (create, read, update, delete posts)
        - Comment service
        - Notification service
        - Media service (image/video upload)
        - API Gateway
        - Service discovery
        - Message queue integration
        - Monitoring and logging
        - Docker containerization.
        **Only Use Python**""",
        timeout=900
    )
}


# ============================================================================
# TEST RESULT TRACKING
# ============================================================================

@dataclass
class TestObservations:
    """Observations from test execution"""
    agents_involved: List[str] = field(default_factory=list)
    agent_interaction_sequence: List[str] = field(default_factory=list)
    review_patterns: Dict[str, Any] = field(default_factory=dict)
    retry_patterns: Dict[str, Any] = field(default_factory=dict)
    performance_patterns: Dict[str, Any] = field(default_factory=dict)
    notable_events: List[str] = field(default_factory=list)
    validation_result: Optional[Dict[str, Any]] = None
    generated_app_path: Optional[str] = None
    test_run_result: Optional[Dict[str, Any]] = None


@dataclass
class TestMetrics:
    """Comprehensive metrics for a test run"""
    start_time: float
    end_time: Optional[float] = None
    
    # Execution metrics
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    
    # Review metrics
    total_reviews: int = 0
    approved_reviews: int = 0
    revision_requests: int = 0
    auto_approvals: int = 0
    
    # Retry metrics
    total_retries: int = 0
    retry_reasons: List[str] = field(default_factory=list)
    
    # Performance metrics
    agent_timings: Dict[str, float] = field(default_factory=dict)
    step_timings: Dict[str, float] = field(default_factory=dict)
    
    # Output metrics
    total_output_size: int = 0
    output_by_agent: Dict[str, int] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def success_rate(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100
    
    @property
    def review_approval_rate(self) -> float:
        if self.total_reviews == 0:
            return 0.0
        return (self.approved_reviews / self.total_reviews) * 100


@dataclass
class TestResult:
    """Complete test result with monitoring integration"""
    test_id: str
    scenario: TestScenario
    workflow_type: str
    
    # Status tracking
    status: str = "pending"  # pending, running, success, failed, timeout
    error_message: Optional[str] = None
    
    # Results
    agent_results: List[TeamMemberResult] = field(default_factory=list)
    # execution_report removed - tracing disabled
    
    # Observations and metrics
    observations: TestObservations = field(default_factory=TestObservations)
    metrics: TestMetrics = field(default_factory=lambda: TestMetrics(time.time()))
    
    # Artifacts
    artifacts_path: Optional[Path] = None
    
    def __post_init__(self):
        self.test_id = f"{self.workflow_type}_{self.scenario.complexity.value}_{int(time.time())}"


# ============================================================================
# MODERN TEST RUNNER
# ============================================================================

class ModernWorkflowTester:
    """
    Modern testing framework with full monitoring integration and beautiful reporting.
    Focuses on observation and reporting rather than expectations.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize the modern test runner"""
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = time.time()
        
        # Setup output directory
        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = Path(project_root) / "tests" / "outputs" / f"session_{self.session_id}"
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Test tracking
        self.test_results: Dict[str, TestResult] = {}
        self.current_test: Optional[TestResult] = None
        
        # Session metadata
        self.session_metadata = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "python_version": sys.version,
            "platform": sys.platform,
            "workflows_available": get_available_workflows()
        }
        
        self._print_header()
    
    def _print_header(self):
        """Print beautiful test session header"""
        print("\n" + "=" * 80)
        print("🧪 MODERN WORKFLOW TESTING FRAMEWORK")
        print("=" * 80)
        print(f"📅 Session ID: {self.session_id}")
        print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Output Directory: {self.output_dir}")
        print(f"🐍 Python Version: {sys.version.split()[0]}")
        print("=" * 80 + "\n")
    
    async def run_test(self, 
                      workflow_type: str, 
                      scenario: TestScenario,
                      save_artifacts: bool = True,
                      run_tests: bool = False) -> TestResult:
        """
        Run a single test with comprehensive monitoring and observation.
        """
        # Create test result
        result = TestResult(
            test_id=f"{workflow_type}_{scenario.complexity.value}_{int(time.time())}",
            scenario=scenario,
            workflow_type=workflow_type
        )
        
        self.current_test = result
        self.test_results[result.test_id] = result
        
        # Print test header
        print(f"\n{'─' * 70}")
        print(f"🚀 EXECUTING TEST: {scenario.name}")
        print(f"📊 Workflow: {workflow_type.upper()}")
        print(f"🎯 Complexity: {scenario.complexity.value.upper()}")
        print(f"⏱️  Timeout: {scenario.timeout}s")
        print(f"{'─' * 70}\n")
        
        try:
            result.status = "running"
            result.metrics.start_time = time.time()
            
            # Create workflow input
            input_data = CodingTeamInput(
                requirements=scenario.requirements,
                workflow_type=workflow_type,
                max_retries=3,
                timeout_seconds=scenario.timeout
            )
            
            # Validate input
            print("🔍 Validating input...")
            from workflows.workflow_manager import validate_workflow_input
            is_valid, error_msg = validate_workflow_input(input_data)
            if not is_valid:
                raise ValueError(f"Invalid input: {error_msg}")
            print("   ✅ Input validated\n")
            
            # Execute workflow with monitoring
            print("⚡ Executing workflow...")
            start_exec = time.time()
            
            # Use timeout
            agent_results = await asyncio.wait_for(
                execute_workflow(input_data),
                timeout=scenario.timeout
            )
            
            exec_duration = time.time() - start_exec
            print(f"   ✅ Workflow completed in {exec_duration:.2f}s\n")
            
            # Store results
            result.agent_results = agent_results
            # execution_report removed - tracing disabled
            
            # Extract metrics from execution report
            self._extract_metrics(result, None)
            
            # Make observations about the execution
            self._observe_execution(result)
            
            # Run tests if requested
            if run_tests:
                await self._run_tests_on_output(result)
            
            # Mark as successful
            result.status = "success"
            result.metrics.end_time = time.time()
            
            # Save artifacts if requested
            if save_artifacts:
                await self._save_test_artifacts(result)
            
            # Print observations
            self._print_test_observations(result)
            
        except asyncio.TimeoutError:
            result.status = "timeout"
            result.error_message = f"Test timed out after {scenario.timeout}s"
            result.metrics.end_time = time.time()
            print(f"\n⏰ TIMEOUT: Test exceeded {scenario.timeout}s limit")
            
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            result.metrics.end_time = time.time()
            print(f"\n❌ ERROR: {str(e)}")
            print(f"📋 Traceback:\n{traceback.format_exc()}")
        
        finally:
            self.current_test = None
        
        return result
    
    def _extract_metrics(self, result: TestResult, report):
        """Extract metrics from execution report"""
        metrics = result.metrics
        
        # Always extract output metrics from agent results
        for agent_result in result.agent_results:
            agent_name = agent_result.name or agent_result.team_member.value
            output_size = len(agent_result.output)
            metrics.output_by_agent[agent_name] = output_size
            metrics.total_output_size += output_size
        
        # Extract from report if available (currently disabled)
        if report:
            # Step metrics
            metrics.total_steps = report.step_count
            metrics.completed_steps = report.completed_steps
            metrics.failed_steps = report.failed_steps
            
            # Review metrics
            metrics.total_reviews = report.total_reviews
            metrics.approved_reviews = report.approved_reviews
            metrics.revision_requests = report.revision_requests
            metrics.auto_approvals = report.auto_approvals
            
            # Retry metrics
            metrics.total_retries = report.total_retries
            for retry in report.retries:
                metrics.retry_reasons.append(retry.reason)
            
            # Performance metrics
            for agent, perf in report.agent_performance.items():
                if 'average_duration' in perf:
                    metrics.agent_timings[agent] = perf['average_duration']
    
    def _observe_execution(self, result: TestResult):
        """Make observations about the test execution"""
        print("🔬 Making observations...")
        
        observations = result.observations
        
        # Observe which agents were involved
        actual_agents = [r.name or r.team_member.value for r in result.agent_results]
        observations.agents_involved = actual_agents
        print(f"   👥 Agents involved: {', '.join(actual_agents)}")
        
        # Observe agent interaction sequence - disabled (tracing removed)
        
        # Observe review patterns
        if result.metrics.total_reviews > 0:
            observations.review_patterns = {
                "total_reviews": result.metrics.total_reviews,
                "approval_rate": result.metrics.review_approval_rate,
                "revision_requests": result.metrics.revision_requests,
                "auto_approvals": result.metrics.auto_approvals
            }
            print(f"   📝 Review approval rate: {result.metrics.review_approval_rate:.1f}%")
        
        # Observe retry patterns
        if result.metrics.total_retries > 0:
            observations.retry_patterns = {
                "total_retries": result.metrics.total_retries,
                "retry_reasons": result.metrics.retry_reasons
            }
            print(f"   🔁 Retries observed: {result.metrics.total_retries}")
        
        # Observe performance patterns
        if result.metrics.agent_timings:
            slowest_agent = max(result.metrics.agent_timings.items(), key=lambda x: x[1])
            fastest_agent = min(result.metrics.agent_timings.items(), key=lambda x: x[1])
            observations.performance_patterns = {
                "slowest_agent": {"name": slowest_agent[0], "avg_time": slowest_agent[1]},
                "fastest_agent": {"name": fastest_agent[0], "avg_time": fastest_agent[1]},
                "timing_variance": max(result.metrics.agent_timings.values()) - min(result.metrics.agent_timings.values())
            }
            print(f"   ⚡ Performance variance: {observations.performance_patterns['timing_variance']:.2f}s")
        
        # Note any interesting patterns
        if result.metrics.auto_approvals > 0:
            observations.notable_events.append(f"Auto-approvals occurred: {result.metrics.auto_approvals}")
        
        if result.metrics.total_retries > result.metrics.total_steps * 0.5:
            observations.notable_events.append("High retry rate observed (>50% of steps)")
        
        if result.metrics.total_output_size > 50000:
            observations.notable_events.append(f"Large output generated: {result.metrics.total_output_size:,} chars")
        
        print("   ✅ Observations complete\n")
    
    def _print_test_observations(self, result: TestResult):
        """Print detailed test observations"""
        print("\n" + "═" * 70)
        print(f"🔍 TEST OBSERVATIONS: {result.scenario.name}")
        print("═" * 70)
        
        # Status
        status_emoji = {
            "success": "✅",
            "failed": "❌",
            "timeout": "⏰",
            "pending": "⏳",
            "running": "🔄"
        }.get(result.status, "❓")
        
        print(f"\n{status_emoji} Status: {result.status.upper()}")
        print(f"⏱️  Duration: {result.metrics.duration:.2f}s")
        
        # Execution observations
        print(f"\n📊 Execution Observations:")
        print(f"   • Workflow Type: {result.workflow_type}")
        print(f"   • Steps Executed: {result.metrics.total_steps}")
        print(f"   • Success Rate: {result.metrics.success_rate:.1f}%")
        
        # Agent observations
        print(f"\n👥 Agent Observations:")
        print(f"   • Agents Involved: {len(result.observations.agents_involved)}")
        for i, agent in enumerate(result.observations.agents_involved, 1):
            output_size = result.metrics.output_by_agent.get(agent, 0)
            timing = result.metrics.agent_timings.get(agent, 0)
            print(f"   {i}. {agent}:")
            print(f"      - Output: {output_size:,} characters")
            if timing > 0:
                print(f"      - Avg Time: {timing:.2f}s")
        
        # Review observations
        if result.observations.review_patterns:
            print(f"\n📝 Review Process Observations:")
            patterns = result.observations.review_patterns
            print(f"   • Total Reviews: {patterns['total_reviews']}")
            print(f"   • Approval Rate: {patterns['approval_rate']:.1f}%")
            if patterns['revision_requests'] > 0:
                print(f"   • Revisions Requested: {patterns['revision_requests']}")
            if patterns['auto_approvals'] > 0:
                print(f"   • Auto-Approvals: {patterns['auto_approvals']}")
        
        # Retry observations
        if result.observations.retry_patterns:
            print(f"\n🔁 Retry Observations:")
            print(f"   • Total Retries: {result.observations.retry_patterns['total_retries']}")
            unique_reasons = set(result.observations.retry_patterns['retry_reasons'])
            print(f"   • Unique Retry Reasons: {len(unique_reasons)}")
        
        # Performance observations
        if result.observations.performance_patterns:
            print(f"\n⚡ Performance Observations:")
            perf = result.observations.performance_patterns
            print(f"   • Slowest Agent: {perf['slowest_agent']['name']} ({perf['slowest_agent']['avg_time']:.2f}s)")
            print(f"   • Fastest Agent: {perf['fastest_agent']['name']} ({perf['fastest_agent']['avg_time']:.2f}s)")
            print(f"   • Timing Variance: {perf['timing_variance']:.2f}s")
        
        # Notable events
        if result.observations.notable_events:
            print(f"\n📌 Notable Events:")
            for event in result.observations.notable_events:
                print(f"   • {event}")
        
        # Output statistics
        print(f"\n📝 Output Statistics:")
        print(f"   • Total Output: {result.metrics.total_output_size:,} characters")
        print(f"   • Average per Agent: {result.metrics.total_output_size // len(result.observations.agents_involved):,} characters")
        
        # Test results if available
        if result.observations.test_run_result:
            print(f"\n🧪 Test Results:")
            test_res = result.observations.test_run_result
            print(f"   • Status: {'✅ SUCCESS' if test_res['success'] else '❌ FAILED'}")
            if test_res.get('error'):
                print(f"   • Error: {test_res['error']}")
            else:
                print(f"   • Framework: {test_res.get('test_framework', 'unknown')}")
                print(f"   • Total Tests: {test_res.get('total_tests', 0)}")
                print(f"   • Passed: {test_res.get('passed', 0)} ✅")
                print(f"   • Failed: {test_res.get('failed', 0)} ❌")
                print(f"   • Skipped: {test_res.get('skipped', 0)} ⏭️")
                print(f"   • Test Command: {test_res.get('test_command', 'N/A')}")
                if test_res.get('reports', {}).get('test_results_csv'):
                    print(f"   • CSV Report: {test_res['reports']['test_results_csv']}")
        
        if result.error_message:
            print(f"\n❌ Error: {result.error_message}")
        
        print("\n" + "═" * 70)
    
    async def _run_tests_on_output(self, result: TestResult):
        """Run tests on the generated code using TestRunnerAgent"""
        print("🧪 Running tests on generated code...")
        
        # First, extract the generated app path
        self._extract_generated_app_path(result)
        
        if not result.observations.generated_app_path:
            print("   ⚠️  No generated app path found, cannot run tests")
            result.observations.test_run_result = {
                "success": False,
                "error": "No generated app path found"
            }
            return
        
        try:
            # Initialize test runner and report generator
            test_runner = TestRunnerAgent(timeout=300)
            report_generator = TestReportGenerator(
                report_dir=str(result.artifacts_path) if result.artifacts_path else "./test_reports"
            )
            
            # Run tests
            test_result = await test_runner.run_tests(
                project_path=result.observations.generated_app_path,
                session_id=result.test_id
            )
            
            # Generate reports
            reports = report_generator.generate_report(test_result, result.agent_results)
            
            # Store test results
            result.observations.test_run_result = {
                "success": test_result.success,
                "total_tests": test_result.total_tests,
                "passed": test_result.passed,
                "failed": test_result.failed,
                "skipped": test_result.skipped,
                "test_framework": test_result.test_framework,
                "execution_time": test_result.execution_time,
                "test_command": test_result.test_command,
                "reports": reports
            }
            
            print(f"   ✅ Test run complete:")
            print(f"      • Framework: {test_result.test_framework}")
            print(f"      • Total: {test_result.total_tests} | Passed: {test_result.passed} | Failed: {test_result.failed}")
            print(f"      • CSV Report: {reports['test_results_csv']}")
            
        except Exception as e:
            print(f"   ❌ Error running tests: {e}")
            result.observations.test_run_result = {
                "success": False,
                "error": str(e)
            }
    
    def _extract_generated_app_path(self, result: TestResult):
        """Extract generated app path from agent outputs"""
        # Look for generated app path in coder output
        for agent_result in result.agent_results:
            if agent_result.name == "coder":
                output = agent_result.output
                # Extract path from patterns like "Location: /path/to/generated/app"
                import re
                path_match = re.search(r'Location: (.+?)(?:\n|$)', output)
                if path_match:
                    result.observations.generated_app_path = path_match.group(1).strip()
                    print(f"   📁 Generated app path: {result.observations.generated_app_path}")
                break
    
    def _extract_value(self, text: str, prefix: str) -> Optional[str]:
        """Extract value after a prefix in text"""
        if prefix in text:
            start = text.find(prefix) + len(prefix)
            end = text.find('\n', start)
            if end == -1:
                end = len(text)
            return text[start:end].strip()
        return None
    
    async def _save_test_artifacts(self, result: TestResult):
        """Save comprehensive test artifacts"""
        print("💾 Saving artifacts...")
        
        # Create test-specific directory
        test_dir = self.output_dir / f"{result.workflow_type}_{result.scenario.complexity.value}"
        test_dir.mkdir(exist_ok=True)
        result.artifacts_path = test_dir
        
        # Save test observations
        observations_file = test_dir / "test_observations.json"
        with open(observations_file, 'w') as f:
            json.dump({
                "test_id": result.test_id,
                "scenario": {
                    "name": result.scenario.name,
                    "complexity": result.scenario.complexity.value,
                    "requirements": result.scenario.requirements
                },
                "workflow_type": result.workflow_type,
                "status": result.status,
                "duration": result.metrics.duration,
                "observations": {
                    "agents_involved": result.observations.agents_involved,
                    "agent_interaction_sequence": result.observations.agent_interaction_sequence,
                    "review_patterns": result.observations.review_patterns,
                    "retry_patterns": result.observations.retry_patterns,
                    "performance_patterns": result.observations.performance_patterns,
                    "notable_events": result.observations.notable_events,
                    "validation_result": result.observations.validation_result,
                    "generated_app_path": result.observations.generated_app_path,
                    "test_run_result": result.observations.test_run_result
                },
                "metrics": {
                    "total_steps": result.metrics.total_steps,
                    "completed_steps": result.metrics.completed_steps,
                    "success_rate": result.metrics.success_rate,
                    "total_reviews": result.metrics.total_reviews,
                    "review_approval_rate": result.metrics.review_approval_rate,
                    "total_retries": result.metrics.total_retries,
                    "total_output_size": result.metrics.total_output_size,
                    "output_by_agent": result.metrics.output_by_agent,
                    "agent_timings": result.metrics.agent_timings
                },
                "error": result.error_message
            }, f, indent=2)
        
        # Save execution report - disabled (tracing removed)
        
        # Save agent outputs
        outputs_dir = test_dir / "agent_outputs"
        outputs_dir.mkdir(exist_ok=True)
        
        for i, agent_result in enumerate(result.agent_results):
            agent_name = agent_result.name or agent_result.team_member.value
            output_file = outputs_dir / f"{i+1}_{agent_name}.txt"
            with open(output_file, 'w') as f:
                f.write(f"AGENT: {agent_name}\n")
                f.write("=" * 60 + "\n\n")
                f.write(agent_result.output)
        
        print(f"   ✅ Artifacts saved to: {test_dir.relative_to(self.output_dir)}")
        
        # If tests were run and we have test results, copy test report to generated app directory
        if result.observations.test_run_result and result.observations.generated_app_path:
            try:
                gen_app_path = Path(result.observations.generated_app_path)
                if gen_app_path.exists() and result.observations.test_run_result.get('reports'):
                    # Copy test results CSV to generated app directory
                    csv_src = result.observations.test_run_result['reports'].get('test_results_csv')
                    if csv_src and Path(csv_src).exists():
                        csv_dst = gen_app_path / "test_results.csv"
                        import shutil
                        shutil.copy2(csv_src, csv_dst)
                        print(f"   📋 Test results CSV copied to generated app: {csv_dst.name}")
            except Exception as e:
                print(f"   ⚠️  Could not copy test results to app directory: {e}")
    
    async def run_workflow_suite(self, 
                               workflow_type: str,
                               complexities: Optional[List[TestComplexity]] = None,
                               run_tests: bool = False):
        """Run a complete test suite for a workflow type"""
        print(f"\n{'━' * 80}")
        print(f"🔬 TESTING WORKFLOW: {workflow_type.upper()}")
        print(f"📖 Description: {get_workflow_description(workflow_type)}")
        print(f"{'━' * 80}\n")
        
        if complexities is None:
            complexities = [TestComplexity.MINIMAL, TestComplexity.STANDARD]
        
        suite_results = []
        
        for complexity in complexities:
            scenario = TEST_SCENARIOS[complexity]
            
            # Skip complex scenarios for individual workflows
            if workflow_type in ["planning", "design", "review"] and complexity in [TestComplexity.COMPLEX, TestComplexity.STRESS]:
                print(f"⏭️  Skipping {complexity.value} test for {workflow_type} (not applicable)")
                continue
            
            result = await self.run_test(workflow_type, scenario, run_tests=run_tests)
            suite_results.append(result)
            
            # Brief pause between tests
            await asyncio.sleep(1)
        
        return suite_results
    
    async def run_comprehensive_test_suite(self, complexities=None, run_tests=False):
        """Run comprehensive test suite across all workflows"""
        print("\n" + "🌟" * 40)
        print("🎯 STARTING COMPREHENSIVE TEST SUITE")
        print("🌟" * 40 + "\n")
        
        # If no complexities specified, use default test plan
        if complexities is None:
            # Define test plan
            test_plan = [
                ("tdd", [TestComplexity.MINIMAL, TestComplexity.STANDARD]),
                ("full", [TestComplexity.MINIMAL, TestComplexity.STANDARD]),
                ("planning", [TestComplexity.MINIMAL]),
                ("design", [TestComplexity.MINIMAL]),
                ("implementation", [TestComplexity.MINIMAL]),
            ]
        else:
            # Custom test plan with specified complexities
            test_plan = [
                ("tdd", complexities),
                ("full", complexities),
                ("planning", complexities),
                ("design", complexities),
                ("implementation", complexities),
            ]
        
        all_results = []
        
        for workflow_type, test_complexities in test_plan:
            results = await self.run_workflow_suite(workflow_type, test_complexities, run_tests)
            all_results.extend(results)
        
        # Generate final report
        await self._generate_session_report(all_results)
    
    async def _generate_session_report(self, all_results: List[TestResult]):
        """Generate comprehensive session report focusing on observations"""
        duration = time.time() - self.start_time
        
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST SESSION REPORT")
        print("=" * 80)
        
        # Session info
        print(f"\n📅 Session ID: {self.session_id}")
        print(f"⏱️  Total Duration: {duration:.2f}s")
        print(f"🧪 Total Tests: {len(all_results)}")
        
        # Results breakdown
        success_count = sum(1 for r in all_results if r.status == "success")
        failed_count = sum(1 for r in all_results if r.status == "failed")
        timeout_count = sum(1 for r in all_results if r.status == "timeout")
        
        success_rate = (success_count / len(all_results) * 100) if all_results else 0
        
        print(f"\n📈 Results Breakdown:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Failed: {failed_count}")
        print(f"   ⏰ Timed Out: {timeout_count}")
        print(f"   📊 Success Rate: {success_rate:.1f}%")
        
        # Aggregate observations
        all_agents = set()
        total_steps = 0
        total_reviews = 0
        total_retries = 0
        all_notable_events = []
        
        for result in all_results:
            all_agents.update(result.observations.agents_involved)
            total_steps += result.metrics.total_steps
            total_reviews += result.metrics.total_reviews
            total_retries += result.metrics.total_retries
            all_notable_events.extend(result.observations.notable_events)
        
        print(f"\n🔬 Aggregate Observations:")
        print(f"   • Unique Agents Observed: {len(all_agents)}")
        print(f"   • Total Steps Executed: {total_steps}")
        print(f"   • Total Reviews: {total_reviews}")
        print(f"   • Total Retries: {total_retries}")
        
        # Agent participation summary
        agent_participation = {}
        for result in all_results:
            for agent in result.observations.agents_involved:
                agent_participation[agent] = agent_participation.get(agent, 0) + 1
        
        print(f"\n👥 Agent Participation Summary:")
        for agent, count in sorted(agent_participation.items(), key=lambda x: x[1], reverse=True):
            participation_rate = (count / len(all_results) * 100)
            print(f"   • {agent}: {count} tests ({participation_rate:.1f}%)")
        
        # Notable patterns across all tests
        if all_notable_events:
            print(f"\n📌 Notable Patterns Observed:")
            event_counts = {}
            for event in all_notable_events:
                event_type = event.split(':')[0]
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            for event_type, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {event_type}: {count} occurrences")
        
        # Save session report
        session_report = {
            "session_id": self.session_id,
            "duration": duration,
            "total_tests": len(all_results),
            "success_count": success_count,
            "failed_count": failed_count,
            "timeout_count": timeout_count,
            "success_rate": success_rate,
            "observations": {
                "unique_agents": list(all_agents),
                "total_steps": total_steps,
                "total_reviews": total_reviews,
                "total_retries": total_retries,
                "agent_participation": agent_participation,
                "notable_events": all_notable_events
            },
            "test_results": [
                {
                    "test_id": r.test_id,
                    "workflow_type": r.workflow_type,
                    "complexity": r.scenario.complexity.value,
                    "status": r.status,
                    "duration": r.metrics.duration,
                    "agents_involved": r.observations.agents_involved
                }
                for r in all_results
            ]
        }
        
        report_file = self.output_dir / "session_report.json"
        with open(report_file, 'w') as f:
            json.dump(session_report, f, indent=2)
        
        print(f"\n📁 All artifacts saved to: {self.output_dir}")
        print(f"📊 Session report: {report_file.name}")
        
        print("\n" + "=" * 80)
        print("✨ TEST SESSION COMPLETE!")
        print("=" * 80 + "\n")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main test execution entry point"""
    parser = argparse.ArgumentParser(description='Modern Workflow Testing Framework')
    
    # Add workflow type options
    parser.add_argument('--workflow', '-w', choices=['tdd', 'full', 'planning', 'design', 'implementation', 'all'],
                        default='all', help='Specific workflow type to test (default: all)')
    
    # Add complexity options
    parser.add_argument('--complexity', '-c', 
                       choices=['minimal', 'standard', 'complex', 'stress', 'all'],
                       default='minimal', 
                       help='Test complexity level (default: minimal)')
    
    # Option to list available tests without running them
    parser.add_argument('--list', '-l', action='store_true',
                       help='List available tests without running them')
    
    # Option to save artifacts
    parser.add_argument('--save-artifacts', '-s', action='store_true', default=True,
                       help='Save test artifacts (default: True)')
    
    # Option to run tests on generated code
    parser.add_argument('--run-tests', '-t', action='store_true',
                       help='Run tests on generated code using the Test Runner Agent')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Convert string complexity to enum
    complexity_map = {
        'minimal': TestComplexity.MINIMAL,
        'standard': TestComplexity.STANDARD,
        'complex': TestComplexity.COMPLEX,
        'stress': TestComplexity.STRESS,
        'all': None
    }
    
    selected_complexity = complexity_map[args.complexity]
    complexities = [selected_complexity] if selected_complexity else list(TestComplexity)
    
    # Initialize tester
    tester = ModernWorkflowTester()
    
    # If list option is selected, just show available tests and exit
    if args.list:
        _list_available_tests(args.workflow)
        return
        
    try:
        if args.workflow == 'all':
            # Run the comprehensive test suite with filter on complexity
            await tester.run_comprehensive_test_suite(complexities, run_tests=args.run_tests)
        else:
            # Run specific workflow tests
            await tester.run_workflow_suite(args.workflow, complexities, run_tests=args.run_tests)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test execution interrupted by user")
        
    except Exception as e:
        print(f"\n\n💥 Critical error in test execution: {e}")
        traceback.print_exc()

def _list_available_tests(workflow_filter='all'):
    """List all available tests without running them"""
    print("\n📋 Available Tests:")
    
    test_plan = [
        ("tdd", list(TestComplexity)),
        ("full", list(TestComplexity)),
        ("planning", list(TestComplexity)),
        ("design", list(TestComplexity)),
        ("implementation", list(TestComplexity)),
    ]
    
    for workflow_type, complexities in test_plan:
        if workflow_filter != 'all' and workflow_filter != workflow_type:
            continue
            
        workflow_desc = get_workflow_description(workflow_type)
        print(f"\n🔹 {workflow_type.upper()} - {workflow_desc}")
        
        for complexity in complexities:
            if complexity.value in TEST_SCENARIOS:
                scenario = TEST_SCENARIOS[complexity]
                print(f"  ┣ {complexity.value}: {scenario.name}")
                print(f"  ┗ Timeout: {scenario.timeout}s")
    
    print("\n💡 Run tests with: python test_workflows.py --workflow <type> --complexity <level>")

if __name__ == "__main__":
    # Clear the console for a fresh start
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print("🚀 Initializing Modern Workflow Testing Framework...")
    print("📚 Loading dependencies...")
    
    # Run the async main function
    asyncio.run(main())