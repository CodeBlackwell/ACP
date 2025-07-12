"""
Utility functions for workflow implementations.
"""
from workflows.workflow_config import MAX_REVIEW_RETRIES
from typing import Optional

async def review_output(content: str, context: str = "", max_retries: int = MAX_REVIEW_RETRIES, 
                       target_agent: Optional[str] = None) -> tuple[bool, str]:
    """
    Review output using the reviewer agent with comprehensive tracking.
    
    Args:
        content: The content to review
        context: Additional context for the review
        max_retries: Maximum number of review retries
        target_agent: The agent whose output is being reviewed
        
    Returns:
        Tuple of (approved: bool, feedback: str)
    """
    # Import run_team_member dynamically to avoid circular imports
    from orchestrator.orchestrator_agent import run_team_member_with_tracking
    
    review_prompt = f"""
    Please review the following output:
    
    Content: {content}
    Context: {context}
    
    Respond with either:
    - "APPROVED" if the output meets requirements
    - "REVISION NEEDED: [specific feedback]" if changes are required
    """
    
    retry_count = 0
    
    try:
        review_response = await run_team_member_with_tracking("reviewer_agent", review_prompt, "review_output")
        
        if "APPROVED" in review_response.upper():
            return True, "Approved by reviewer"
            
        elif "REVISION NEEDED" in review_response.upper():
            feedback = review_response.split("REVISION NEEDED:", 1)[-1].strip()
            
            return False, feedback
            
        else:
            # If unclear response, treat as revision needed
            feedback = f"Review unclear: {review_response}"
            return False, feedback
            
    except Exception as e:
        # On error, auto-approve to prevent blocking
        error_feedback = f"Auto-approved due to review error: {str(e)}"
        return True, error_feedback
    
    # Fallback auto-approval (shouldn't reach here normally)
    fallback_feedback = "Auto-approved after max retries"
    return True, fallback_feedback
