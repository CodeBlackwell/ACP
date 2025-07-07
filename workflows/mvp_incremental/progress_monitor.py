"""
Progress Monitor for MVP Incremental Workflow
Provides real-time visibility into workflow execution progress
"""
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StepStatus(Enum):
    """Status of a workflow step"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    # TDD-specific states
    WRITING_TESTS = "writing_tests"
    TESTS_WRITTEN = "tests_written"
    TESTS_FAILING = "tests_failing"  # Red phase
    IMPLEMENTING = "implementing"
    TESTS_PASSING = "tests_passing"   # Green phase
    REFACTORING = "refactoring"       # Refactor phase


@dataclass
class StepProgress:
    """Progress information for a single step"""
    step_name: str
    step_type: str  # planning, design, feature, validation
    status: StepStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate step duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def is_complete(self) -> bool:
        """Check if step is complete (either succeeded or failed)"""
        return self.status in [StepStatus.COMPLETED, StepStatus.FAILED]


@dataclass
class FeatureProgress:
    """Progress tracking for a specific feature"""
    feature_id: str
    feature_title: str
    total_attempts: int = 0
    validation_passed: bool = False
    current_status: StepStatus = StepStatus.PENDING
    errors: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    # TDD-specific tracking
    tests_written: bool = False
    tests_initial_run: bool = False
    tests_passing: bool = False
    test_file_count: int = 0
    test_function_count: int = 0
    code_coverage: Optional[float] = None


class ProgressMonitor:
    """
    Monitor and report progress of MVP incremental workflow execution.
    Provides real-time updates and summary statistics.
    """
    
    def __init__(self):
        self.workflow_start_time = None
        self.workflow_end_time = None
        self.steps: List[StepProgress] = []
        self.features: Dict[str, FeatureProgress] = {}
        self.current_phase = None
        self.total_features = 0
        
    def start_workflow(self, total_features: int = 0):
        """Mark workflow start"""
        self.workflow_start_time = datetime.now()
        self.total_features = total_features
        self._print_header()
        
    def end_workflow(self):
        """Mark workflow end and print summary"""
        self.workflow_end_time = datetime.now()
        self._print_summary()
        
    def start_phase(self, phase_name: str):
        """Start a new phase (planning, design, implementation)"""
        self.current_phase = phase_name
        print(f"\n{'='*60}")
        print(f"📍 PHASE: {phase_name.upper()}")
        print(f"{'='*60}")
        
    def start_step(self, step_name: str, step_type: str, metadata: Dict[str, Any] = None):
        """Start tracking a new step"""
        step = StepProgress(
            step_name=step_name,
            step_type=step_type,
            status=StepStatus.IN_PROGRESS,
            start_time=datetime.now(),
            metadata=metadata or {}
        )
        self.steps.append(step)
        
        # Print progress indicator
        if step_type == "feature":
            feature_num = metadata.get("feature_num", "?")
            feature_title = metadata.get("feature_title", "Unknown")
            print(f"\n⚙️  Feature {feature_num}/{self.total_features}: {feature_title}")
            print(f"   Status: Starting implementation...")
        else:
            print(f"\n⚙️  {step_type.title()}: Starting...")
            
    def update_step(self, step_name: str, status: StepStatus, error_message: str = None):
        """Update step status"""
        step = self._find_step(step_name)
        if step:
            step.status = status
            if error_message:
                step.error_message = error_message
            
            # Print status update
            if status == StepStatus.RETRYING:
                print(f"   🔄 Retrying (attempt {step.retry_count + 1})...")
                step.retry_count += 1
            elif status == StepStatus.FAILED:
                print(f"   ❌ Failed: {error_message or 'Unknown error'}")
            elif status == StepStatus.COMPLETED:
                duration = (datetime.now() - step.start_time).total_seconds()
                print(f"   ✅ Completed in {duration:.1f}s")
            # TDD-specific status updates
            elif status == StepStatus.WRITING_TESTS:
                print(f"   ✍️  Writing tests...")
            elif status == StepStatus.TESTS_WRITTEN:
                print(f"   📝 Tests written")
            elif status == StepStatus.TESTS_FAILING:
                print(f"   🔴 Tests failing (expected - TDD red phase)")
            elif status == StepStatus.IMPLEMENTING:
                print(f"   🔨 Implementing code to pass tests...")
            elif status == StepStatus.TESTS_PASSING:
                print(f"   🟢 Tests passing (TDD green phase)")
            elif status == StepStatus.REFACTORING:
                print(f"   🔧 Refactoring code...")
                
    def complete_step(self, step_name: str, success: bool = True, metadata: Dict[str, Any] = None):
        """Mark step as complete"""
        step = self._find_step(step_name)
        if step:
            step.end_time = datetime.now()
            step.status = StepStatus.COMPLETED if success else StepStatus.FAILED
            if metadata:
                step.metadata.update(metadata)
                
    def start_feature(self, feature_id: str, feature_title: str, feature_num: int):
        """Start tracking a new feature"""
        feature = FeatureProgress(
            feature_id=feature_id,
            feature_title=feature_title,
            start_time=datetime.now()
        )
        self.features[feature_id] = feature
        
        # Start the feature step
        self.start_step(
            f"feature_{feature_id}",
            "feature",
            {
                "feature_num": feature_num,
                "feature_title": feature_title
            }
        )
        
    def update_feature_validation(self, feature_id: str, passed: bool, error: str = None):
        """Update feature validation status"""
        if feature_id in self.features:
            feature = self.features[feature_id]
            feature.validation_passed = passed
            if error:
                feature.errors.append(error)
            
            status_icon = "✅" if passed else "❌"
            print(f"   {status_icon} Validation: {'PASSED' if passed else 'FAILED'}")
            
    def complete_feature(self, feature_id: str, success: bool):
        """Mark feature as complete"""
        if feature_id in self.features:
            feature = self.features[feature_id]
            feature.end_time = datetime.now()
            feature.current_status = StepStatus.COMPLETED if success else StepStatus.FAILED
            
    def get_progress_percentage(self) -> float:
        """Calculate overall progress percentage"""
        if self.total_features == 0:
            return 0.0
            
        completed_features = sum(1 for f in self.features.values() if f.current_status == StepStatus.COMPLETED)
        return (completed_features / self.total_features) * 100
        
    def get_elapsed_time(self) -> str:
        """Get elapsed time since workflow start"""
        if not self.workflow_start_time:
            return "0:00"
            
        elapsed = datetime.now() - self.workflow_start_time
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        return f"{minutes}:{seconds:02d}"
        
    def print_progress_bar(self):
        """Print a visual progress bar"""
        percentage = self.get_progress_percentage()
        bar_length = 40
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        elapsed = self.get_elapsed_time()
        print(f"\n📊 Progress: [{bar}] {percentage:.0f}% | Time: {elapsed}")
        
    def _find_step(self, step_name: str) -> Optional[StepProgress]:
        """Find a step by name"""
        for step in reversed(self.steps):  # Search from most recent
            if step.step_name == step_name:
                return step
        return None
        
    def _print_header(self):
        """Print workflow start header"""
        print("\n" + "="*60)
        print("🚀 MVP INCREMENTAL WORKFLOW")
        print("="*60)
        print(f"⏰ Started at: {self.workflow_start_time.strftime('%H:%M:%S')}")
        if self.total_features > 0:
            print(f"📋 Total features to implement: {self.total_features}")
        print("="*60)
        
    def _print_summary(self):
        """Print workflow summary"""
        if not self.workflow_end_time:
            self.workflow_end_time = datetime.now()
            
        total_duration = (self.workflow_end_time - self.workflow_start_time).total_seconds()
        
        print("\n" + "="*60)
        print("📈 WORKFLOW SUMMARY")
        print("="*60)
        
        # Overall stats
        print(f"\n⏱️  Total Duration: {total_duration:.1f} seconds")
        print(f"📊 Total Steps: {len(self.steps)}")
        
        # Phase breakdown
        phase_times = self._calculate_phase_times()
        if phase_times:
            print("\n📋 Phase Breakdown:")
            for phase, duration in phase_times.items():
                print(f"   - {phase}: {duration:.1f}s")
                
        # Feature stats
        if self.features:
            successful_features = sum(1 for f in self.features.values() if f.validation_passed)
            failed_features = len(self.features) - successful_features
            retried_features = sum(1 for f in self.features.values() if f.total_attempts > 1)
            
            print(f"\n🔧 Feature Implementation:")
            print(f"   - Total: {len(self.features)}")
            print(f"   - Successful: {successful_features}")
            print(f"   - Failed: {failed_features}")
            print(f"   - Required Retry: {retried_features}")
            
            # TDD stats
            features_with_tests = sum(1 for f in self.features.values() if f.tests_written)
            features_tests_passing = sum(1 for f in self.features.values() if f.tests_passing)
            total_test_files = sum(f.test_file_count for f in self.features.values())
            total_test_functions = sum(f.test_function_count for f in self.features.values())
            avg_coverage = self._calculate_average_coverage()
            
            print(f"\n🧪 TDD Metrics:")
            print(f"   - Features with tests: {features_with_tests}/{len(self.features)}")
            print(f"   - Features with passing tests: {features_tests_passing}/{len(self.features)}")
            print(f"   - Total test files: {total_test_files}")
            print(f"   - Total test functions: {total_test_functions}")
            if avg_coverage is not None:
                print(f"   - Average code coverage: {avg_coverage:.1f}%")
            
        # Error summary
        all_errors = []
        for feature in self.features.values():
            all_errors.extend(feature.errors)
            
        if all_errors:
            print(f"\n⚠️  Errors Encountered: {len(all_errors)}")
            # Show unique error types
            error_types = {}
            for error in all_errors:
                error_type = error.split(':')[0] if ':' in error else 'Unknown'
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            print("   Error Types:")
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   - {error_type}: {count}")
                
        print("\n" + "="*60)
        
    def _calculate_phase_times(self) -> Dict[str, float]:
        """Calculate time spent in each phase"""
        phase_times = {}
        
        for step in self.steps:
            if step.duration_seconds:
                phase = step.step_type
                if phase not in phase_times:
                    phase_times[phase] = 0
                phase_times[phase] += step.duration_seconds
                
        return phase_times
        
    def update_tdd_progress(self, feature_id: str, tdd_phase: str, metadata: Dict[str, Any] = None):
        """Update TDD-specific progress for a feature"""
        if feature_id in self.features:
            feature = self.features[feature_id]
            
            if tdd_phase == "tests_written":
                feature.tests_written = True
                feature.test_file_count = metadata.get("test_files", 0) if metadata else 0
                feature.test_function_count = metadata.get("test_functions", 0) if metadata else 0
                print(f"   📝 Tests written: {feature.test_file_count} files, {feature.test_function_count} test functions")
            elif tdd_phase == "tests_initial_run":
                feature.tests_initial_run = True
                passed = metadata.get("passed", 0) if metadata else 0
                failed = metadata.get("failed", 0) if metadata else 0
                print(f"   🔴 Initial test run: {passed} passed, {failed} failed (expected failures)")
            elif tdd_phase == "tests_passing":
                feature.tests_passing = True
                feature.code_coverage = metadata.get("coverage", None) if metadata else None
                if feature.code_coverage:
                    print(f"   🟢 All tests passing! Coverage: {feature.code_coverage:.1f}%")
                else:
                    print(f"   🟢 All tests passing!")
                    
    def export_metrics(self) -> Dict[str, Any]:
        """Export progress metrics for analysis"""
        # Calculate TDD metrics
        tdd_metrics = {
            "features_with_tests": sum(1 for f in self.features.values() if f.tests_written),
            "features_tests_passing": sum(1 for f in self.features.values() if f.tests_passing),
            "total_test_files": sum(f.test_file_count for f in self.features.values()),
            "total_test_functions": sum(f.test_function_count for f in self.features.values()),
            "average_coverage": self._calculate_average_coverage()
        }
        
        return {
            "workflow_duration": (self.workflow_end_time - self.workflow_start_time).total_seconds() if self.workflow_end_time else None,
            "total_steps": len(self.steps),
            "total_features": len(self.features),
            "successful_features": sum(1 for f in self.features.values() if f.validation_passed),
            "failed_features": sum(1 for f in self.features.values() if not f.validation_passed),
            "retried_features": sum(1 for f in self.features.values() if f.total_attempts > 1),
            "phase_times": self._calculate_phase_times(),
            "tdd_metrics": tdd_metrics,
            "feature_details": {
                fid: {
                    "title": f.feature_title,
                    "passed": f.validation_passed,
                    "attempts": f.total_attempts,
                    "errors": f.errors,
                    "tests_written": f.tests_written,
                    "tests_passing": f.tests_passing,
                    "test_files": f.test_file_count,
                    "test_functions": f.test_function_count,
                    "coverage": f.code_coverage
                }
                for fid, f in self.features.items()
            }
        }
    
    def _calculate_average_coverage(self) -> Optional[float]:
        """Calculate average code coverage across features"""
        coverages = [f.code_coverage for f in self.features.values() if f.code_coverage is not None]
        if coverages:
            return sum(coverages) / len(coverages)
        return None