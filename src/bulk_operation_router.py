"""
Automatic Bulk Operation Detection and Routing

This module ensures agents are ALWAYS used for bulk operations,
preventing fragile behavior where Claude might make individual calls.

Core Principle: "Route automatically, don't rely on LLM decisions"
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("bulk-router")


class BulkOperationRouter:
    """
    Detects bulk operation patterns and routes to appropriate handlers.

    Ensures robustness by intercepting patterns that should use agents
    instead of individual tool calls.
    """

    def __init__(self):
        logger.info("BulkOperationRouter initialized")

    def detect_bulk_pattern(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect if a tool call is actually a bulk operation that should use an agent.

        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments
            context: Optional conversation context for better detection

        Returns:
            Tuple of (is_bulk, routing_info)
            - is_bulk: True if this should be routed to agent
            - routing_info: Dictionary with routing details if is_bulk=True
        """

        # Check single extraction tools that might be misused for bulk
        if tool_name in ["extract_inline_image", "extract_crossline_image", "extract_timeslice_image"]:
            return self._detect_extraction_bulk(tool_name, arguments, context)

        # Not a bulk-capable tool
        return False, None

    def _detect_extraction_bulk(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect if an extraction call is part of a bulk operation.

        Patterns that indicate bulk:
        - Multiple numbers in context (e.g., "51000 to 59000")
        - Words like: every, all, skipping, through, range, from...to
        - Spacing indicators: "every 100th", "spacing 500"
        """

        if not context:
            # No context, can't detect bulk intent
            return False, None

        context_lower = context.lower()

        # Pattern 1: "every Nth" - strongest indicator
        if re.search(r'every\s+\d+', context_lower):
            logger.info("Detected 'every Nth' pattern - BULK OPERATION")
            return True, self._create_routing_info(tool_name, arguments, context, "every_nth")

        # Pattern 2: "from X to Y" or "X through Y"
        range_pattern = r'(?:from|start.*?at)\s+\d+\s+(?:to|through|until)\s+\d+'
        if re.search(range_pattern, context_lower):
            logger.info("Detected 'from X to Y' pattern - BULK OPERATION")
            return True, self._create_routing_info(tool_name, arguments, context, "range")

        # Pattern 3: "skipping" or "spacing"
        if re.search(r'\b(?:skip|spacing)\b', context_lower):
            logger.info("Detected 'skipping/spacing' pattern - BULK OPERATION")
            return True, self._create_routing_info(tool_name, arguments, context, "spacing")

        # Pattern 4: "all inlines" or "all crosslines"
        if re.search(r'\ball\s+(?:inline|crossline|timeslice)s?\b', context_lower):
            logger.info("Detected 'all X' pattern - BULK OPERATION")
            return True, self._create_routing_info(tool_name, arguments, context, "all")

        # Pattern 5: Multiple explicit numbers (comma-separated)
        # e.g., "inlines 51000, 52000, 53000, 54000"
        numbers = re.findall(r'\b\d{4,}\b', context)
        if len(numbers) >= 3:
            logger.info(f"Detected {len(numbers)} numbers - BULK OPERATION")
            return True, self._create_routing_info(tool_name, arguments, context, "multiple")

        # Pattern 6: Words indicating bulk: "multiple", "several", "various"
        if re.search(r'\b(?:multiple|several|various|many)\b', context_lower):
            logger.info("Detected bulk quantity words - BULK OPERATION")
            return True, self._create_routing_info(tool_name, arguments, context, "quantity")

        # Not detected as bulk
        return False, None

    def _create_routing_info(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: str,
        pattern_type: str
    ) -> Dict[str, Any]:
        """
        Create routing information for agent invocation.

        Returns:
            Dictionary with routing details
        """

        # Extract survey_id from arguments
        survey_id = arguments.get("survey_id")

        return {
            "detected_pattern": pattern_type,
            "original_tool": tool_name,
            "original_arguments": arguments,
            "instruction": context,  # Use the full context as instruction
            "survey_id": survey_id,
            "recommendation": "use_agent_start_extraction",
            "reason": f"Detected bulk operation pattern: {pattern_type}",
            "auto_execute": True
        }

    def should_block_single_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if a single tool call should be blocked and routed to agent.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            context: Conversation context

        Returns:
            Tuple of (should_block, reason)
        """
        is_bulk, routing_info = self.detect_bulk_pattern(tool_name, arguments, context)

        if is_bulk:
            reason = (
                f"Detected bulk operation pattern: {routing_info['detected_pattern']}. "
                f"Automatically routing to agent for efficient execution. "
                f"You can check progress with agent_get_status."
            )
            return True, reason

        return False, None


# Singleton instance
_router: Optional[BulkOperationRouter] = None


def get_router() -> BulkOperationRouter:
    """Get singleton router instance"""
    global _router
    if _router is None:
        _router = BulkOperationRouter()
    return _router
