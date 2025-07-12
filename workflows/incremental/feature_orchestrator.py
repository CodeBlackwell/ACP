"""
Feature orchestrator for managing incremental feature-based development.
Simplified version without tracing for debugging.
"""
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from dataclasses import dataclass

from shared.utils.feature_parser import Feature, FeatureParser, ComplexityLevel
from shared.data_models import TeamMemberResult, TeamMember


@dataclass
class FeatureImplementationResult:
    """Result of feature implementation following ACP result patterns"""
    feature: Feature
    code_output: str
    files_created: Dict[str, str]
    validation_passed: bool
    validation_feedback: str
    retry_count: int
    execution_time: float


async def run_incremental_coding_phase(
    designer_output: str,
    requirements: str,
    tests: Optional[str] = None,
    max_retries: int = 3,
    session_id: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Helper function for workflow integration.
    
    Returns:
        Tuple of (aggregated_code_output, execution_metrics)
    """
    # For now, just run the standard coder implementation
    # This is a simplified version for debugging
    
    from orchestrator.orchestrator_agent import run_team_member
    from workflows.message_utils import extract_message_content
    
    # Prepare input for coder
    coder_input = f"Design:\n{designer_output}\n\nRequirements: {requirements}"
    if tests:
        coder_input += f"\n\nTests:\n{tests}"
    if session_id:
        coder_input = f"SESSION_ID: {session_id}\n\n{coder_input}"
        print(f"🔗 Passing session ID to coder: {session_id}")
        # Debug: print first 100 chars of coder input
        print(f"📝 Coder input preview: {coder_input[:100]}...")
    else:
        print("⚠️  No session ID provided to feature orchestrator")
    
    # Run coder
    code_result = await run_team_member("coder_agent", coder_input)
    code_output = extract_message_content(code_result)
    
    # Return simplified metrics
    execution_metrics = {
        'total_features': 1,
        'completed_features': 1,
        'failed_features': 0,
        'success_rate': 100.0,
        'total_retries': 0,
        'execution_time_seconds': 0
    }
    
    return code_output, execution_metrics


async def execute_features_incrementally(
    features: List[Feature],
    requirements: str,
    design: str,
    tests: Optional[str],
    max_retries: int = 3,
    session_id: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Execute features incrementally with retry logic.
    Simplified version for debugging.
    """
    from orchestrator.orchestrator_agent import run_agent
    
    completed_features = []
    final_codebase = {}
    
    for idx, feature in enumerate(features):
        print(f"\n🔨 Implementing {feature.id}: {feature.title}")
        
        # Prepare context for the feature
        context = {
            "feature": feature,
            "requirements": requirements,
            "design": design,
            "tests": tests,
            "previous_code": final_codebase
        }
        
        # Implement feature
        retry_count = 0
        success = False
        
        while retry_count < max_retries and not success:
            try:
                # Generate code for this feature
                coder_input = f"""
Implement the following feature:

Feature ID: {feature.id}
Title: {feature.title}
Description: {feature.description}
Requirements: {', '.join(feature.requirements)}

Context:
{design}

Previous implementations:
{str(final_codebase)}
"""
                
                # Add session ID if provided
                if session_id:
                    coder_input = f"SESSION_ID: {session_id}\n\n{coder_input}"
                
                code_output = await run_agent("coder", coder_input, f"feature_{feature.id}")
                
                # For now, assume success
                success = True
                
                # Update codebase
                final_codebase[feature.id] = code_output
                
                completed_features.append({
                    "feature": feature,
                    "code_output": code_output,
                    "success": True,
                    "retry_count": retry_count
                })
                
            except Exception as e:
                retry_count += 1
                print(f"❌ Error implementing {feature.id}: {str(e)}")
                if retry_count >= max_retries:
                    completed_features.append({
                        "feature": feature,
                        "code_output": "",
                        "success": False,
                        "retry_count": retry_count,
                        "error": str(e)
                    })
    
    return completed_features, final_codebase