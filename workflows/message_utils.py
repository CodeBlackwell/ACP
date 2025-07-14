"""
Utility functions for extracting content from ACP messages
"""
from typing import List, Union

# Apply ACP SDK compatibility patches before importing
from utils.acp_sdk_compat import ensure_compatibility
ensure_compatibility()

from acp_sdk import Message


def extract_message_content(messages: Union[List[Message], Message]) -> str:
    """
    Extract the actual content from ACP Message objects.
    
    Args:
        messages: Either a single Message or a list of Messages
        
    Returns:
        The extracted content as a string
    """
    # Handle single message
    if isinstance(messages, Message):
        messages = [messages]
    
    # Extract content from messages
    content_parts = []
    
    for message in messages:
        if hasattr(message, 'parts'):
            for part in message.parts:
                if hasattr(part, 'content'):
                    content_parts.append(part.content)
    
    # Join all content parts
    return '\n'.join(content_parts)