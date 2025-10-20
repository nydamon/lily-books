"""Observability for LangChain chains using Langfuse."""

import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from .config import get_project_paths, settings

# Try to import Langfuse, fall back to custom callback if not available
try:
    from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    LangfuseCallbackHandler = None

# LangSmith removed - using Langfuse only


class ChainTraceCallback(BaseCallbackHandler):
    """Callback handler that logs chain invocations to JSONL file."""
    
    def __init__(self, slug: str):
        self.slug = slug
        self.paths = get_project_paths(slug)
        self.log_file = self.paths["meta"] / "chain_traces.jsonl"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Track chain start times
        self.chain_starts: Dict[str, float] = {}
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs) -> None:
        """Log chain start."""
        chain_name = serialized.get("name", "unknown") if serialized else "unknown"
        chain_id = f"{chain_name}_{int(time.time() * 1000)}"
        self.chain_starts[chain_id] = time.time()
        
        # Create input hash (truncate large inputs)
        input_str = str(inputs)
        if len(input_str) > 1000:
            input_str = input_str[:1000] + "..."
        input_hash = hashlib.md5(input_str.encode()).hexdigest()[:8]
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "chain_start",
            "chain_name": chain_name,
            "chain_id": chain_id,
            "input_hash": input_hash,
            "input_size": len(str(inputs)),
            "run_id": str(kwargs.get("run_id", "unknown"))  # Convert UUID to string
        }
        
        self._write_log_entry(entry)
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        """Log chain completion."""
        chain_id = str(kwargs.get("run_id", ""))
        if chain_id not in self.chain_starts:
            return
            
        duration_ms = int((time.time() - self.chain_starts[chain_id]) * 1000)
        
        # Create output hash (truncate large outputs)
        output_str = str(outputs)
        if len(output_str) > 1000:
            output_str = output_str[:1000] + "..."
        output_hash = hashlib.md5(output_str.encode()).hexdigest()[:8]
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "chain_end",
            "chain_id": chain_id,
            "duration_ms": duration_ms,
            "output_hash": output_hash,
            "output_size": len(str(outputs)),
            "run_id": str(kwargs.get("run_id", "unknown"))  # Convert UUID to string
        }
        
        self._write_log_entry(entry)
        del self.chain_starts[chain_id]
    
    def on_chain_error(self, error: Exception, **kwargs) -> None:
        """Log chain error."""
        chain_id = str(kwargs.get("run_id", ""))
        if chain_id not in self.chain_starts:
            return
            
        duration_ms = int((time.time() - self.chain_starts[chain_id]) * 1000)
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "chain_error",
            "chain_id": chain_id,
            "duration_ms": duration_ms,
            "error": str(error),
            "error_type": type(error).__name__,
            "run_id": str(kwargs.get("run_id", "unknown"))  # Convert UUID to string
        }
        
        self._write_log_entry(entry)
        del self.chain_starts[chain_id]
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Log LLM start."""
        model_name = serialized.get("name", "unknown") if serialized else "unknown"
        chain_id = kwargs.get("run_id", "")
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "llm_start",
            "chain_id": chain_id,
            "model": model_name,
            "prompt_count": len(prompts),
            "total_prompt_length": sum(len(p) for p in prompts)
        }
        
        self._write_log_entry(entry)
    
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Log LLM completion."""
        chain_id = kwargs.get("run_id", "")
        
        # Extract token usage if available
        token_usage = {}
        if hasattr(response, 'llm_output') and response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "llm_end",
            "chain_id": chain_id,
            "generation_count": len(response.generations),
            "token_usage": token_usage
        }
        
        self._write_log_entry(entry)
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Log LLM error."""
        chain_id = kwargs.get("run_id", "")
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "llm_error",
            "chain_id": chain_id,
            "error": str(error),
            "error_type": type(error).__name__
        }
        
        self._write_log_entry(entry)
    
    def _write_log_entry(self, entry: Dict[str, Any]) -> None:
        """Write log entry to JSONL file."""
        try:
            # Convert any UUID objects to strings
            safe_entry = {}
            for key, value in entry.items():
                if hasattr(value, '__str__') and 'UUID' in str(type(value)):
                    safe_entry[key] = str(value)
                else:
                    safe_entry[key] = value
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(safe_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            # Don't let logging errors break the pipeline
            print(f"Failed to write chain trace: {e}")


def get_chain_traces(slug: str) -> List[Dict[str, Any]]:
    """Load chain traces from JSONL file."""
    paths = get_project_paths(slug)
    log_file = paths["meta"] / "chain_traces.jsonl"
    
    if not log_file.exists():
        return []
    
    traces = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    traces.append(json.loads(line))
    except Exception as e:
        print(f"Error loading chain traces: {e}")
    
    return traces


def clear_chain_traces(slug: str) -> None:
    """Clear chain traces file."""
    paths = get_project_paths(slug)
    log_file = paths["meta"] / "chain_traces.jsonl"
    
    if log_file.exists():
        log_file.unlink()


def create_langfuse_callback(slug: str) -> Optional[LangfuseCallbackHandler]:
    """Create Langfuse callback handler if available and configured."""
    if not LANGFUSE_AVAILABLE or not settings.langfuse_enabled:
        return None
    
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        print("Langfuse not configured: missing public_key or secret_key")
        return None
    
    try:
        callback = LangfuseCallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            session_id=slug,  # Use slug as session ID
            user_id="lily-books",
            tags=["book-modernization", slug]
        )
        print(f"Langfuse callback initialized for project: {slug}")
        return callback
    except Exception as e:
        print(f"Failed to initialize Langfuse callback: {e}")
        return None


# LangSmith callback removed - using Langfuse only


class StreamingProgressCallback(BaseCallbackHandler):
    """Callback handler for streaming progress updates."""
    
    def __init__(self, slug: str, progress_callback=None):
        self.slug = slug
        self.progress_callback = progress_callback
        self.current_step = 0
        self.total_steps = 0
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs) -> None:
        """Log chain start and update progress."""
        chain_name = serialized.get("name", "unknown") if serialized else "unknown"
        self.current_step += 1
        
        if self.progress_callback:
            self.progress_callback({
                "step": self.current_step,
                "total": self.total_steps,
                "chain": chain_name,
                "status": "started"
            })
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        """Log chain completion."""
        if self.progress_callback:
            self.progress_callback({
                "step": self.current_step,
                "total": self.total_steps,
                "status": "completed"
            })
    
    def on_chain_error(self, error: Exception, **kwargs) -> None:
        """Log chain error."""
        if self.progress_callback:
            self.progress_callback({
                "step": self.current_step,
                "total": self.total_steps,
                "status": "error",
                "error": str(error)
            })


def create_observability_callback(slug: str, progress_callback=None) -> List[BaseCallbackHandler]:
    """Create appropriate callback handlers for observability."""
    callbacks = []
    
    # Try Langfuse first
    langfuse_callback = create_langfuse_callback(slug)
    if langfuse_callback:
        callbacks.append(langfuse_callback)
    
    # Always add custom callback for local logging
    callbacks.append(ChainTraceCallback(slug))
    
    # Add streaming progress callback if provided
    if progress_callback:
        callbacks.append(StreamingProgressCallback(slug, progress_callback))
    
    return callbacks
