"""
Mount Health Checker - Validates NFS mount and VPN connectivity

This module provides robust checking for mounted volumes, detecting stale
NFS mounts that can occur when VPN connections drop.
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("mount-health")


class MountHealthStatus(Enum):
    """Status of mount health check"""
    HEALTHY = "healthy"
    STALE = "stale"
    INACCESSIBLE = "inaccessible"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class MountHealthResult:
    """Result of a mount health check"""
    status: MountHealthStatus
    path: str
    response_time_ms: float
    error_message: Optional[str] = None
    retry_count: int = 0

    @property
    def is_healthy(self) -> bool:
        return self.status == MountHealthStatus.HEALTHY

    def __str__(self) -> str:
        if self.is_healthy:
            return f"Mount {self.path}: HEALTHY ({self.response_time_ms:.1f}ms)"
        else:
            return f"Mount {self.path}: {self.status.value.upper()} - {self.error_message}"


class MountHealthChecker:
    """Checks health of mounted volumes with VPN awareness"""

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        retry_delay_seconds: float = 2.0
    ):
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    async def check_mount_health(self, mount_path: str) -> MountHealthResult:
        """
        Check if a mount point is healthy and accessible

        Args:
            mount_path: Path to the mounted volume

        Returns:
            MountHealthResult with status and details
        """
        path = Path(mount_path)
        start_time = time.time()

        # Check if path exists
        if not path.exists():
            return MountHealthResult(
                status=MountHealthStatus.NOT_FOUND,
                path=mount_path,
                response_time_ms=0,
                error_message=f"Path does not exist: {mount_path}"
            )

        # Try to access the mount with timeout
        try:
            # Use asyncio timeout for the entire check
            async with asyncio.timeout(self.timeout_seconds):
                # Attempt to list directory contents
                # This will detect stale NFS mounts
                try:
                    # Run in thread pool since os.listdir is blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, lambda: list(path.iterdir()))

                    response_time_ms = (time.time() - start_time) * 1000

                    # Warn if mount is slow (possible network issues)
                    if response_time_ms > 1000:
                        logger.warning(
                            f"Mount {mount_path} is slow ({response_time_ms:.1f}ms). "
                            "This may indicate network issues or VPN problems."
                        )

                    return MountHealthResult(
                        status=MountHealthStatus.HEALTHY,
                        path=mount_path,
                        response_time_ms=response_time_ms
                    )

                except PermissionError as e:
                    return MountHealthResult(
                        status=MountHealthStatus.PERMISSION_DENIED,
                        path=mount_path,
                        response_time_ms=(time.time() - start_time) * 1000,
                        error_message=f"Permission denied: {e}"
                    )

                except OSError as e:
                    # OSError often indicates stale NFS mount
                    if "Stale file handle" in str(e) or "Resource temporarily unavailable" in str(e):
                        return MountHealthResult(
                            status=MountHealthStatus.STALE,
                            path=mount_path,
                            response_time_ms=(time.time() - start_time) * 1000,
                            error_message=f"Stale NFS mount detected. VPN may have disconnected: {e}"
                        )
                    else:
                        return MountHealthResult(
                            status=MountHealthStatus.INACCESSIBLE,
                            path=mount_path,
                            response_time_ms=(time.time() - start_time) * 1000,
                            error_message=f"OS error accessing mount: {e}"
                        )

        except asyncio.TimeoutError:
            return MountHealthResult(
                status=MountHealthStatus.STALE,
                path=mount_path,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=f"Mount check timed out after {self.timeout_seconds}s. Likely stale NFS mount."
            )

        except Exception as e:
            return MountHealthResult(
                status=MountHealthStatus.INACCESSIBLE,
                path=mount_path,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=f"Unexpected error: {e}"
            )

    async def wait_for_mount_ready(
        self,
        mount_path: str,
        retry_count: int = 0
    ) -> MountHealthResult:
        """
        Wait for mount to become ready with exponential backoff

        Args:
            mount_path: Path to the mounted volume
            retry_count: Current retry attempt (for recursion)

        Returns:
            MountHealthResult with final status
        """
        result = await self.check_mount_health(mount_path)
        result.retry_count = retry_count

        if result.is_healthy:
            if retry_count > 0:
                logger.info(f"Mount {mount_path} became healthy after {retry_count} retries")
            return result

        if retry_count >= self.max_retries:
            logger.error(
                f"Mount {mount_path} failed health check after {retry_count} retries: "
                f"{result.error_message}"
            )
            return result

        # Exponential backoff
        delay = self.retry_delay_seconds * (2 ** retry_count)
        logger.warning(
            f"Mount {mount_path} unhealthy (attempt {retry_count + 1}/{self.max_retries + 1}). "
            f"Status: {result.status.value}. Retrying in {delay}s..."
        )

        await asyncio.sleep(delay)
        return await self.wait_for_mount_ready(mount_path, retry_count + 1)

    async def check_multiple_mounts(
        self,
        mount_paths: list[str]
    ) -> dict[str, MountHealthResult]:
        """
        Check health of multiple mounts concurrently

        Args:
            mount_paths: List of mount paths to check

        Returns:
            Dictionary mapping paths to their health results
        """
        tasks = [
            self.check_mount_health(path)
            for path in mount_paths
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            path: result if isinstance(result, MountHealthResult) else MountHealthResult(
                status=MountHealthStatus.INACCESSIBLE,
                path=path,
                response_time_ms=0,
                error_message=f"Check failed with exception: {result}"
            )
            for path, result in zip(mount_paths, results)
        }

    def get_remediation_advice(self, result: MountHealthResult) -> str:
        """
        Get human-readable advice for fixing mount issues

        Args:
            result: The health check result

        Returns:
            Remediation advice string
        """
        if result.status == MountHealthStatus.HEALTHY:
            return "Mount is healthy, no action needed."

        advice = {
            MountHealthStatus.NOT_FOUND:
                "1. Check if the mount path is correct\n"
                "2. Verify the volume is mounted: ls -la {parent}\n"
                "3. Check if NFS server is reachable",

            MountHealthStatus.STALE:
                "STALE NFS MOUNT DETECTED - This typically happens when VPN disconnects:\n"
                "1. Check VPN connection (try reconnecting)\n"
                "2. Force unmount: sudo umount -f {path}\n"
                "3. Remount the volume\n"
                "4. If inside Docker, restart the container after remounting",

            MountHealthStatus.INACCESSIBLE:
                "1. Check permissions: ls -la {path}\n"
                "2. Verify network connectivity to NFS server\n"
                "3. Check mount status: mount | grep {path}\n"
                "4. Check system logs: dmesg | tail",

            MountHealthStatus.PERMISSION_DENIED:
                "1. Check file permissions: ls -la {path}\n"
                "2. Verify user has read access\n"
                "3. Check NFS export permissions on server\n"
                "4. If in Docker, ensure volume mount permissions are correct"
        }

        advice_text = advice.get(
            result.status,
            "Unknown issue. Check mount status and network connectivity."
        )

        return advice_text.format(
            path=result.path,
            parent=str(Path(result.path).parent)
        )


async def main():
    """Test mount health checking"""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python mount_health.py <mount_path> [mount_path2 ...]")
        sys.exit(1)

    checker = MountHealthChecker(timeout_seconds=5.0, max_retries=2)
    mount_paths = sys.argv[1:]

    print(f"\nChecking {len(mount_paths)} mount(s)...\n")

    results = await checker.check_multiple_mounts(mount_paths)

    for path, result in results.items():
        print(f"\n{'='*70}")
        print(result)
        print(f"{'='*70}")

        if not result.is_healthy:
            print("\nREMEDIATION ADVICE:")
            print(checker.get_remediation_advice(result))

    # Summary
    healthy_count = sum(1 for r in results.values() if r.is_healthy)
    print(f"\n{'='*70}")
    print(f"SUMMARY: {healthy_count}/{len(results)} mounts healthy")
    print(f"{'='*70}\n")

    # Exit with error if any mount is unhealthy
    sys.exit(0 if healthy_count == len(results) else 1)


if __name__ == "__main__":
    asyncio.run(main())
