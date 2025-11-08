"""
MCP Client Bridge - Connects to OpenVDS MCP Server via stdio
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import os

logger = logging.getLogger("mcp-client-bridge")


class MCPClient:
    """
    Bridge to OpenVDS MCP Server using stdio transport
    """

    def __init__(self, server_path: str, server_args: List[str] = None):
        """
        Initialize MCP client

        Args:
            server_path: Path to MCP server script, shell script, or command (e.g., 'docker')
            server_args: Optional arguments for the server
        """
        self.server_command = server_path
        self.server_path = Path(server_path) if '/' in server_path else None

        # Only check file existence if it looks like a path (contains /)
        if self.server_path and not self.server_path.exists():
            raise FileNotFoundError(f"MCP server not found: {server_path}")

        self.server_args = server_args or []
        self.process: Optional[asyncio.subprocess.Process] = None
        self.message_id = 0
        self.is_connected = False

    async def connect(self):
        """Start the MCP server process and establish connection"""
        if self.is_connected:
            logger.warning("Already connected to MCP server")
            return

        try:
            # Build command - use server_command directly (supports docker, python3, bash, etc.)
            cmd = [self.server_command] + self.server_args

            # Pass environment variables to MCP server (including ES config)
            import os
            env = os.environ.copy()

            # Determine cwd - only use parent directory if it's a file path
            cwd = self.server_path.parent if self.server_path else None

            logger.info(f"Starting MCP server: {' '.join(cmd)}")

            # Create subprocess with increased buffer limit for large responses (base64 images)
            # Default limit is 64KB which is too small for seismic image data
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
                limit=10 * 1024 * 1024  # 10MB buffer for stdout/stderr
            )

            # Start background task to log stderr
            asyncio.create_task(self._log_stderr())

            # Send initialize request
            init_response = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "vds-explorer-ui",
                    "version": "1.0.0"
                }
            })

            if "error" in init_response:
                raise Exception(f"Initialization failed: {init_response['error']}")

            self.is_connected = True
            logger.info("Connected to MCP server successfully")

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            if self.process:
                self.process.kill()
                await self.process.wait()
            raise

    async def _log_stderr(self):
        """Background task to log stderr from MCP server"""
        if not self.process or not self.process.stderr:
            return

        try:
            async for line in self.process.stderr:
                decoded = line.decode('utf-8', errors='replace').strip()
                if decoded:
                    logger.info(f"[MCP Server] {decoded}")
        except Exception as e:
            logger.error(f"Error reading MCP server stderr: {e}")

    async def disconnect(self):
        """Close connection to MCP server"""
        if not self.is_connected:
            return

        try:
            if self.process:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            if self.process:
                self.process.kill()
                await self.process.wait()
        finally:
            self.is_connected = False
            self.process = None
            logger.info("Disconnected from MCP server")

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send JSON-RPC request to MCP server

        Args:
            method: The method name to call
            params: Parameters for the method

        Returns:
            Response from the server
        """
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise Exception("Not connected to MCP server")

        self.message_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": method,
            "params": params
        }

        # Send request
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode())
        await self.process.stdin.drain()

        # Read response (limit set to 10MB when subprocess was created)
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise Exception("Server closed connection")

        try:
            response = json.loads(response_line.decode())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MCP response (size: {len(response_line)} bytes): {e}")
            logger.error(f"Response preview: {response_line[:500]}")
            raise Exception(f"Invalid JSON response from MCP server: {e}")

        if "error" in response:
            logger.error(f"MCP error: {response['error']}")

        return response.get("result", response)

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from MCP server"""
        response = await self._send_request("tools/list", {})
        return response.get("tools", [])

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        response = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })

        # Extract content from response
        if "content" in response:
            content = response["content"]
            if isinstance(content, list) and len(content) > 0:
                # Check if this is a list of content blocks (image, text, etc.)
                first_content = content[0]
                if isinstance(first_content, dict) and "type" in first_content:
                    # Multiple content blocks - return all of them
                    # This handles cases where MCP returns [ImageContent, TextContent]
                    return content
            return content

        return response

    # Convenience methods for common operations

    async def search_surveys(
        self,
        search_query: Optional[str] = None,
        filter_region: Optional[str] = None,
        filter_year: Optional[int] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search for surveys"""
        args = {
            "offset": offset,
            "limit": limit
        }
        if search_query:
            args["search_query"] = search_query
        if filter_region:
            args["filter_region"] = filter_region
        if filter_year:
            args["filter_year"] = filter_year

        return await self.call_tool("search_surveys", args)

    async def get_survey_info(self, survey_id: str, include_stats: bool = True) -> Dict[str, Any]:
        """Get survey metadata"""
        return await self.call_tool("get_survey_info", {
            "survey_id": survey_id,
            "include_stats": include_stats
        })

    async def extract_inline_image(
        self,
        survey_id: str,
        inline_number: int,
        sample_range: Optional[List[int]] = None,
        colormap: str = "seismic",
        clip_percentile: float = 99.0
    ) -> Dict[str, Any]:
        """Extract inline image"""
        args = {
            "survey_id": survey_id,
            "inline_number": inline_number,
            "colormap": colormap,
            "clip_percentile": clip_percentile
        }
        if sample_range:
            args["sample_range"] = sample_range

        return await self.call_tool("extract_inline_image", args)

    async def extract_crossline_image(
        self,
        survey_id: str,
        crossline_number: int,
        sample_range: Optional[List[int]] = None,
        colormap: str = "seismic",
        clip_percentile: float = 99.0
    ) -> Dict[str, Any]:
        """Extract crossline image"""
        args = {
            "survey_id": survey_id,
            "crossline_number": crossline_number,
            "colormap": colormap,
            "clip_percentile": clip_percentile
        }
        if sample_range:
            args["sample_range"] = sample_range

        return await self.call_tool("extract_crossline_image", args)

    async def extract_timeslice_image(
        self,
        survey_id: str,
        time_value: int,
        inline_range: Optional[List[int]] = None,
        crossline_range: Optional[List[int]] = None,
        colormap: str = "seismic",
        clip_percentile: float = 99.0
    ) -> Dict[str, Any]:
        """Extract timeslice image"""
        args = {
            "survey_id": survey_id,
            "time_value": time_value,
            "colormap": colormap,
            "clip_percentile": clip_percentile
        }
        if inline_range:
            args["inline_range"] = inline_range
        if crossline_range:
            args["crossline_range"] = crossline_range

        return await self.call_tool("extract_timeslice_image", args)

    async def validate_statistics(
        self,
        survey_id: str,
        section_type: str,
        section_number: int,
        claimed_statistics: Dict[str, float],
        tolerance: float = 0.05
    ) -> Dict[str, Any]:
        """Validate extracted statistics"""
        return await self.call_tool("validate_extracted_statistics", {
            "survey_id": survey_id,
            "section_type": section_type,
            "section_number": section_number,
            "claimed_statistics": claimed_statistics,
            "tolerance": tolerance
        })

    async def verify_coordinates(
        self,
        survey_id: str,
        claimed_location: Dict[str, int]
    ) -> Dict[str, Any]:
        """Verify spatial coordinates"""
        return await self.call_tool("verify_spatial_coordinates", {
            "survey_id": survey_id,
            "claimed_location": claimed_location
        })

    async def check_consistency(
        self,
        statistics: Dict[str, float]
    ) -> Dict[str, Any]:
        """Check statistical consistency"""
        return await self.call_tool("check_statistical_consistency", {
            "statistics": statistics
        })

    async def start_agent(
        self,
        survey_id: str,
        instruction: str,
        auto_execute: bool = True
    ) -> Dict[str, Any]:
        """Start autonomous extraction agent"""
        return await self.call_tool("agent_start_extraction", {
            "survey_id": survey_id,
            "instruction": instruction,
            "auto_execute": auto_execute
        })

    async def get_agent_status(
        self,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get agent status"""
        args = {}
        if session_id:
            args["session_id"] = session_id
        return await self.call_tool("agent_get_status", args)

    async def get_agent_results(
        self,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get agent results"""
        args = {}
        if session_id:
            args["session_id"] = session_id
        return await self.call_tool("agent_get_results", args)

    async def pause_agent(
        self,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pause agent"""
        args = {}
        if session_id:
            args["session_id"] = session_id
        return await self.call_tool("agent_pause", args)

    async def resume_agent(
        self,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resume agent"""
        args = {}
        if session_id:
            args["session_id"] = session_id
        return await self.call_tool("agent_resume", args)


# Singleton instance
_mcp_client: Optional[MCPClient] = None


async def get_mcp_client() -> MCPClient:
    """Get or create MCP client instance"""
    global _mcp_client

    if _mcp_client is None:
        # Get server path from environment
        server_path = os.getenv(
            "MCP_SERVER_PATH",
            "/app/openvds-mcp-server/src/openvds_mcp_server.py"  # Default Docker path
        )
        server_args_str = os.getenv("MCP_SERVER_ARGS", "")
        # Support both comma-separated (for docker args) and space-separated
        if ',' in server_args_str:
            server_args = [arg.strip() for arg in server_args_str.split(',') if arg.strip()]
        else:
            server_args = server_args_str.split() if server_args_str else []

        _mcp_client = MCPClient(server_path, server_args)
        await _mcp_client.connect()

    return _mcp_client


async def shutdown_mcp_client():
    """Shutdown MCP client"""
    global _mcp_client
    if _mcp_client:
        await _mcp_client.disconnect()
        _mcp_client = None
