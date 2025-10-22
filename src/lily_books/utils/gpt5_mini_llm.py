"""Custom LangChain integration for GPT-5-mini using the responses API."""

import os
from typing import Any, List, Optional
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from openai import OpenAI
import logging
from .fail_fast import check_gpt5_mini_response, FAIL_FAST_ENABLED
from .debug_logger import log_step, log_api_call, update_activity, check_for_hang
from .circuit_breaker import gpt5_mini_circuit_breaker

logger = logging.getLogger(__name__)


class GPT5MiniLLM(LLM):
    """Custom LangChain LLM for GPT-5-mini using the responses API."""
    
    api_key: str
    model: str = "gpt-5-mini"
    temperature: float = 1.0
    max_completion_tokens: Optional[int] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self._client = OpenAI(api_key=api_key)
    
    @property
    def _llm_type(self) -> str:
        return 'gpt-5-mini'
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call GPT-5-mini using the responses API with timeout."""
        import time
        import threading
        
        def api_call():
            return self._client.responses.create(
                model=self.model,
                input=[
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'input_text',
                                'text': prompt
                            }
                        ]
                    }
                ],
                text={
                    'format': {
                        'type': 'text'
                    },
                    'verbosity': 'low'
                },
                reasoning={
                    'effort': 'low',
                    'summary': 'detailed'
                },
                tools=[],
                store=False,
                temperature=self.temperature,
                max_output_tokens=self.max_completion_tokens
            )
        
        try:
            log_step("GPT5MiniLLM._call", prompt_length=len(prompt))
            update_activity("GPT-5-mini API call start")
            
            # Check circuit breaker state
            circuit_stats = gpt5_mini_circuit_breaker.get_stats()
            log_step("GPT5MiniLLM.circuit_state", **circuit_stats)
            
            # Use threading timeout instead of signal
            result = [None]
            exception = [None]
            
            def target():
                try:
                    log_step("GPT5MiniLLM.api_call_thread", thread_id=threading.get_ident())
                    update_activity("GPT-5-mini API call in thread")
                    
                    # Use circuit breaker to protect the API call
                    result[0] = gpt5_mini_circuit_breaker.call(api_call)
                    log_step("GPT5MiniLLM.api_call_success", result_type=type(result[0]))
                except Exception as e:
                    log_step("GPT5MiniLLM.api_call_error", error=str(e))
                    exception[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            log_step("GPT5MiniLLM.thread_start", thread_id=thread.ident)
            thread.start()
            
            # Check for hang every 5 seconds
            for i in range(6):  # 6 * 5 = 30 seconds total
                thread.join(timeout=5)
                if not thread.is_alive():
                    break
                log_step("GPT5MiniLLM.thread_check", elapsed_seconds=(i+1)*5, thread_alive=thread.is_alive())
                check_for_hang("GPT-5-mini API call", 5)
            
            if thread.is_alive():
                log_step("GPT5MiniLLM.timeout", timeout_seconds=30)
                logger.error("GPT-5-mini API call timed out after 30 seconds")
                
                # Try fallback to GPT-4o-mini if circuit breaker allows
                circuit_stats = gpt5_mini_circuit_breaker.get_stats()
                if circuit_stats["state"] == "closed":
                    log_step("GPT5MiniLLM.fallback_attempt", fallback_model="gpt-4o-mini")
                    try:
                        from langchain_openai import ChatOpenAI
                        fallback_llm = ChatOpenAI(
                            model="gpt-4o-mini",
                            api_key=self.api_key,
                            temperature=self.temperature,
                            max_tokens=self.max_completion_tokens
                        )
                        fallback_result = fallback_llm.invoke(prompt)
                        log_step("GPT5MiniLLM.fallback_success", fallback_model="gpt-4o-mini")
                        return fallback_result.content
                    except Exception as fallback_error:
                        log_step("GPT5MiniLLM.fallback_failed", error=str(fallback_error))
                
                from .fail_fast import fail_fast_on_exception
                fail_fast_on_exception(TimeoutError("GPT-5-mini API call timed out"), "GPT-5-mini timeout")
            
            if exception[0]:
                raise exception[0]
            
            if result[0] is None:
                raise TimeoutError("GPT-5-mini API call timed out")
            
            response = result[0]
            logger.info(f"GPT-5-mini API call completed successfully")
            
            # Extract text from output
            if response.output:
                for item in response.output:
                    # Check if this is a ResponseOutputMessage
                    if hasattr(item, 'content') and item.content:
                        for content_item in item.content:
                            if hasattr(content_item, 'text') and content_item.text:
                                logger.info(f"GPT-5-mini response length: {len(content_item.text)}")
                                return content_item.text
            
            # Fallback: check if there's a direct text field
            if hasattr(response, 'output_text') and response.output_text:
                logger.info(f"GPT-5-mini response length (fallback): {len(response.output_text)}")
                return response.output_text
            
            # Fail-fast on empty response with detailed logging
            logger.error(f"GPT-5-mini empty response. Full prompt: {prompt}")
            logger.error(f"Prompt length: {len(prompt)}")
            logger.error(f"Response output: {response.output}")
            check_gpt5_mini_response(None, f"GPT-5-mini API call with prompt: {prompt[:100]}...")
            return ''
            
        except TimeoutError as e:
            logger.error(f"GPT-5-mini timeout: {e}")
            from .fail_fast import fail_fast_on_exception
            fail_fast_on_exception(e, f"GPT-5-mini timeout")
        except Exception as e:
            logger.error(f"GPT-5-mini error: {e}")
            from .fail_fast import fail_fast_on_exception
            fail_fast_on_exception(e, f"GPT-5-mini API error")


def create_gpt5_mini_llm(
    api_key: str,
    temperature: float = 1.0,
    max_completion_tokens: Optional[int] = None
) -> GPT5MiniLLM:
    """Create a GPT-5-mini LLM instance."""
    return GPT5MiniLLM(
        api_key=api_key,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens
    )
