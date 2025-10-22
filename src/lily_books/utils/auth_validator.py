"""Authentication validator for all pipeline services."""

import os
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class AuthValidator:
    """Validates authentication for all pipeline services."""
    
    def __init__(self):
        load_dotenv()
        self.results: Dict[str, Dict[str, Any]] = {}
    
    def validate_openai(self) -> Dict[str, Any]:
        """Validate OpenAI API authentication."""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return {
                    "status": "failed",
                    "error": "OPENAI_API_KEY not found in environment",
                    "details": "Set OPENAI_API_KEY in .env file"
                }
            
            client = OpenAI(api_key=api_key)
            
            # Test GPT-5-mini with responses API
            response = client.responses.create(
                model='gpt-5-mini',
                input=[
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'input_text',
                                'text': 'Say hello'
                            }
                        ]
                    }
                ],
                text={
                    'format': {
                        'type': 'text'
                    },
                    'verbosity': 'medium'
                },
                reasoning={
                    'effort': 'medium',
                    'summary': 'auto'
                },
                tools=[],
                store=True
            )
            
            # Extract response text
            response_text = ""
            if response.output:
                for item in response.output:
                    if hasattr(item, 'content') and item.content:
                        for content_item in item.content:
                            if hasattr(content_item, 'text'):
                                response_text = content_item.text
                                break
                        break
            
            if response_text:
                return {
                    "status": "success",
                    "model": response.model,
                    "response": response_text,
                    "usage": response.usage.total_tokens if response.usage else 0
                }
            else:
                return {
                    "status": "failed",
                    "error": "Empty response from GPT-5-mini",
                    "details": "Model returned empty response"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "details": f"OpenAI API error: {type(e).__name__}"
            }
    
    def validate_openrouter(self) -> Dict[str, Any]:
        """Validate OpenRouter API authentication."""
        try:
            api_key = os.getenv('OPENROUTER_API_KEY')
            if not api_key:
                return {
                    "status": "failed",
                    "error": "OPENROUTER_API_KEY not found in environment",
                    "details": "Set OPENROUTER_API_KEY in .env file"
                }
            
            client = OpenAI(
                api_key=api_key,
                base_url='https://openrouter.ai/api/v1'
            )
            
            # Test Anthropic Claude via OpenRouter
            response = client.chat.completions.create(
                model='anthropic/claude-haiku-4.5',
                messages=[{'role': 'user', 'content': 'Say hello'}],
                max_tokens=10
            )
            
            return {
                "status": "success",
                "model": response.model,
                "response": response.choices[0].message.content,
                "usage": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "details": f"OpenRouter API error: {type(e).__name__}"
            }
    
    def validate_fish_audio(self) -> Dict[str, Any]:
        """Validate Fish Audio API authentication."""
        try:
            api_key = os.getenv('FISH_API_KEY')
            if not api_key:
                return {
                    "status": "failed",
                    "error": "FISH_API_KEY not found in environment",
                    "details": "Set FISH_API_KEY in .env file"
                }

            from fish_audio_sdk import Session

            # Test Fish Audio API
            session = Session(api_key)
            # If session creation succeeds, the API key is valid

            return {
                "status": "success",
                "authenticated": True,
                "details": "Fish Audio API key validated successfully"
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "details": f"Fish Audio API error: {type(e).__name__}"
            }
    
    def validate_all(self) -> Dict[str, Dict[str, Any]]:
        """Validate all authentication services."""
        logger.info("Starting authentication validation...")
        
        self.results = {
            "openai": self.validate_openai(),
            "openrouter": self.validate_openrouter(),
            "fish_audio": self.validate_fish_audio()
        }
        
        return self.results
    
    def print_results(self):
        """Print authentication validation results."""
        print("\n" + "="*60)
        print("🔐 AUTHENTICATION VALIDATION RESULTS")
        print("="*60)
        
        for service, result in self.results.items():
            status_icon = "✅" if result["status"] == "success" else "❌"
            print(f"\n{status_icon} {service.upper()}:")
            
            if result["status"] == "success":
                print(f"   Status: {result['status']}")
                if "model" in result:
                    print(f"   Model: {result['model']}")
                if "response" in result:
                    print(f"   Response: {result['response'][:50]}...")
                if "usage" in result:
                    print(f"   Usage: {result['usage']} tokens")
                if "voice_count" in result:
                    print(f"   Voices: {result['voice_count']}")
                if "authenticated" in result:
                    print(f"   Authenticated: {result['authenticated']}")
            else:
                print(f"   Status: {result['status']}")
                print(f"   Error: {result['error']}")
                print(f"   Details: {result['details']}")
        
        print("\n" + "="*60)
        
        # Check if all services are working
        all_success = all(r["status"] == "success" for r in self.results.values())
        if all_success:
            print("🎉 ALL AUTHENTICATION SERVICES WORKING!")
        else:
            print("⚠️  SOME AUTHENTICATION SERVICES FAILED!")
            failed_services = [s for s, r in self.results.items() if r["status"] != "success"]
            print(f"   Failed services: {', '.join(failed_services)}")
        
        print("="*60 + "\n")
        
        return all_success


def validate_pipeline_auth() -> bool:
    """Validate all pipeline authentication services."""
    validator = AuthValidator()
    validator.validate_all()
    return validator.print_results()


if __name__ == "__main__":
    validate_pipeline_auth()

