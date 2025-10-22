"""Health check utilities for pipeline monitoring with Langfuse integration."""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PipelineHealthCheck:
    """Monitor pipeline health and progress."""
    
    def __init__(self, slug: str):
        self.slug = slug
        self.start_time = time.time()
        self.last_activity = time.time()
        self.chapter_progress = {}
        self.error_count = 0
        self.timeout_count = 0
        
    def update_chapter_progress(self, chapter: int, status: str, paragraphs: int = 0):
        """Update chapter progress tracking."""
        self.chapter_progress[chapter] = {
            'status': status,
            'paragraphs': paragraphs,
            'timestamp': time.time()
        }
        self.last_activity = time.time()
        
        logger.info(f"Chapter {chapter} progress: {status} ({paragraphs} paragraphs)")
        
    def record_error(self, error_type: str, error_message: str):
        """Record pipeline errors."""
        if error_type == "APITimeoutError":
            self.timeout_count += 1
        else:
            self.error_count += 1
            
        logger.warning(f"Pipeline error [{error_type}]: {error_message}")
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        current_time = time.time()
        runtime = current_time - self.start_time
        time_since_activity = current_time - self.last_activity
        
        completed_chapters = sum(1 for ch in self.chapter_progress.values() 
                               if ch['status'] == 'completed')
        total_chapters = len(self.chapter_progress)
        
        health_score = 100
        if self.error_count > 0:
            health_score -= min(self.error_count * 10, 50)
        if self.timeout_count > 0:
            health_score -= min(self.timeout_count * 5, 30)
        if time_since_activity > 300:  # 5 minutes
            health_score -= 20
            
        return {
            'slug': self.slug,
            'runtime_seconds': runtime,
            'time_since_activity_seconds': time_since_activity,
            'completed_chapters': completed_chapters,
            'total_chapters': total_chapters,
            'progress_percentage': (completed_chapters / max(total_chapters, 1)) * 100,
            'error_count': self.error_count,
            'timeout_count': self.timeout_count,
            'health_score': max(health_score, 0),
            'status': self._get_status_text(health_score, time_since_activity),
            'last_activity': datetime.fromtimestamp(self.last_activity).isoformat()
        }
        
    def _get_status_text(self, health_score: int, time_since_activity: float) -> str:
        """Get human-readable status text."""
        if health_score >= 90:
            return "Excellent"
        elif health_score >= 70:
            return "Good"
        elif health_score >= 50:
            return "Fair"
        elif time_since_activity > 300:
            return "Stalled"
        else:
            return "Poor"
            
    def is_healthy(self) -> bool:
        """Check if pipeline is healthy."""
        status = self.get_health_status()
        return status['health_score'] >= 70 and status['time_since_activity_seconds'] < 300


def create_health_check(slug: str) -> PipelineHealthCheck:
    """Create a new health check instance."""
    return PipelineHealthCheck(slug)


def log_pipeline_health(health_check: PipelineHealthCheck):
    """Log current pipeline health status and send to Langfuse."""
    status = health_check.get_health_status()
    
    logger.info(f"Pipeline Health [{status['slug']}]:")
    logger.info(f"  Status: {status['status']} (Score: {status['health_score']}/100)")
    logger.info(f"  Progress: {status['completed_chapters']}/{status['total_chapters']} chapters ({status['progress_percentage']:.1f}%)")
    logger.info(f"  Runtime: {status['runtime_seconds']:.1f}s")
    logger.info(f"  Last Activity: {status['last_activity']}")
    logger.info(f"  Errors: {status['error_count']}, Timeouts: {status['timeout_count']}")
    
    if not health_check.is_healthy():
        logger.warning(f"Pipeline health is below threshold: {status['health_score']}/100")
    
    # Send health metrics to Langfuse
    _send_health_to_langfuse(status)


def _send_health_to_langfuse(health_status: Dict[str, Any]):
    """Send health metrics to Langfuse as an event."""
    try:
        from .langfuse_tracer import is_langfuse_enabled, get_langfuse_client
        from .debug_logger import get_trace_context
        
        if not is_langfuse_enabled():
            return
        
        client = get_langfuse_client()
        if not client:
            return
        
        trace_ctx = get_trace_context()
        if not trace_ctx['trace_id']:
            return
        
        # Create health check event in current trace
        client.event(
            trace_id=trace_ctx['trace_id'],
            name="pipeline_health_check",
            metadata=health_status,
            level="DEFAULT" if health_status['health_score'] >= 70 else "WARNING"
        )
    except Exception as e:
        # Don't let Langfuse errors break health checks
        logger.debug(f"Failed to send health check to Langfuse: {e}")
