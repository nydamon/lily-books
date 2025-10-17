"""Checker chain for QA validation using Claude Sonnet."""

import re
from typing import Dict, Tuple, List
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import textstat

from ..models import ChapterDoc, ParaPair, QAReport, QAIssue
from ..config import settings


# Checker prompt template from spec
CHECKER_USER = """Compare ORIGINAL vs MODERN. Rate and list issues.

ORIGINAL: {original}
MODERN: {modern}

Return JSON:
{{
 "fidelity_score": 0-100,
 "readability_appropriate": true/false,
 "formatting_preserved": true/false,
 "tone_consistent": true/false,
 "quote_count_match": true/false,
 "emphasis_preserved": true/false,
 "issues":[{{"type","description","severity","suggestion"}}]
}}"""

checker_prompt = PromptTemplate.from_template(CHECKER_USER)


def local_checks(orig: str, modern: str) -> Dict:
    """Perform local validation checks on paragraph pair."""
    def normalize_quotes(s: str) -> str:
        """Normalize different quote styles to standard quotes."""
        return s.replace(""", '"').replace(""", '"').replace("'", "'").replace("'", "'")
    
    # Quote parity check
    orig_quotes = normalize_quotes(orig)
    modern_quotes = normalize_quotes(modern)
    quote_parity = orig_quotes.count('"') == modern_quotes.count('"')
    
    # Emphasis parity check (underscore markers)
    orig_emphasis = len(re.findall(r'_(.+?)_', orig))
    modern_emphasis = len(re.findall(r'_(.+?)_', modern))
    emphasis_parity = orig_emphasis == modern_emphasis
    
    # Archaic phrase detection
    archaic_patterns = [
        r'\bto-day\b',
        r'\ba fortnight\b', 
        r'\bupon my word\b',
        r'\bsaid (he|she)\b'
    ]
    missed_archaic = []
    for pattern in archaic_patterns:
        if re.search(pattern, modern, re.I):
            missed_archaic.append(pattern)
    
    # Flesch-Kincaid grade calculation
    try:
        fk_grade = textstat.flesch_kincaid_grade(modern) if len(modern) >= 120 else 8.0
    except:
        fk_grade = 8.0
    
    # Character count ratio
    ratio = len(modern) / max(1, len(orig))
    
    return {
        "quote_parity": quote_parity,
        "emphasis_parity": emphasis_parity,
        "missed_archaic": missed_archaic,
        "fk_grade": fk_grade,
        "ratio": ratio
    }


def qa_chapter(doc: ChapterDoc, fidelity_threshold: int = 92) -> Tuple[bool, List[Dict], ChapterDoc]:
    """QA a complete chapter and return results."""
    issues = []
    min_fidelity = 100
    readability_ok = True
    
    # Initialize checker chain
    checker = ChatAnthropic(
        model=settings.anthropic_model,
        temperature=0.0,
        api_key=settings.anthropic_api_key
    )
    checker_chain = (
        {"original": lambda d: d["orig"], "modern": lambda d: d["modern"]}
        | checker_prompt
        | checker
        | JsonOutputParser()
    )
    
    for pair in doc.pairs:
        try:
            # Run LLM checker
            checker_result = checker_chain.invoke({
                "orig": pair.orig,
                "modern": pair.modern
            })
            
            # Run local checks
            local_result = local_checks(pair.orig, pair.modern)
            
            # Update tracking variables
            fidelity_score = checker_result.get("fidelity_score", 0)
            min_fidelity = min(min_fidelity, fidelity_score)
            readability_ok = readability_ok and checker_result.get("readability_appropriate", True)
            
            # Check for formatting issues
            if not local_result["quote_parity"] or not local_result["emphasis_parity"] or local_result["missed_archaic"]:
                issues.append({
                    "i": pair.i,
                    "type": "formatting_or_archaic",
                    "description": f"Formatting issues: quotes={local_result['quote_parity']}, emphasis={local_result['emphasis_parity']}, archaic={len(local_result['missed_archaic'])}"
                })
            
            # Create QA report
            pair.qa = QAReport(
                fidelity_score=fidelity_score,
                readability_grade=local_result["fk_grade"],
                character_count_ratio=local_result["ratio"],
                modernization_complete=len(local_result["missed_archaic"]) == 0,
                formatting_preserved=local_result["quote_parity"] and local_result["emphasis_parity"],
                tone_consistent=checker_result.get("tone_consistent", True),
                quote_count_match=local_result["quote_parity"],
                emphasis_preserved=local_result["emphasis_parity"],
                issues=[
                    QAIssue(
                        type=issue.get("type", "unknown"),
                        description=issue.get("description", ""),
                        severity=issue.get("severity", "low")
                    ) for issue in checker_result.get("issues", [])
                ]
            )
            
        except Exception as e:
            # Fallback QA report for errors
            pair.qa = QAReport(
                fidelity_score=0,
                readability_grade=8.0,
                character_count_ratio=1.0,
                modernization_complete=False,
                formatting_preserved=False,
                tone_consistent=False,
                quote_count_match=False,
                emphasis_preserved=False,
                issues=[QAIssue(
                    type="checker_error",
                    description=f"Checker failed: {str(e)}",
                    severity="high"
                )]
            )
            issues.append({
                "i": pair.i,
                "type": "checker_error",
                "description": f"Checker failed: {str(e)}"
            })
    
    # Determine if chapter passed QA
    passed = (
        min_fidelity >= fidelity_threshold and
        readability_ok and
        all(pair.qa.modernization_complete and pair.qa.formatting_preserved for pair in doc.pairs)
    )
    
    return passed, issues, doc
