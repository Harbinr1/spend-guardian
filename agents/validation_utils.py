import json
from typing import Type, TypeVar, Any
from pydantic import BaseModel, ValidationError

T = TypeVar('T', bound=BaseModel)

def validate_and_retry(
    llm_raw_output: str,
    schema_class: Type[T],
    retry_prompt_function: callable,
    max_retries: int = 1
) -> T:
    """
    Tries to parse LLM output against a Pydantic schema.
    If it fails, re-prompts with the validation error (once), then hard-fails.
    """
    attempts = 0
    current_output = llm_raw_output
    
    while attempts <= max_retries:
        try:
            # Attempt to parse JSON and validate against schema
            parsed = json.loads(current_output)
            validated = schema_class(**parsed)
            return validated
        except (json.JSONDecodeError, ValidationError) as e:
            attempts += 1
            if attempts > max_retries:
                # Loud, visible terminal failure
                print(f"\n❌ FATAL: Schema validation failed after {max_retries+1} attempts.")
                print(f"Last error: {e}")
                print(f"Malformed output was: {current_output[:500]}...")
                raise ValueError(f"Pipeline halted: {schema_class.__name__} validation failed permanently.")
            
            # Re-prompt the LLM with the validation error
            print(f"⚠️ Schema mismatch (attempt {attempts}). Re-prompting LLM with fix instructions...")
            current_output = retry_prompt_function(current_output, str(e))
    
    raise RuntimeError("Unreachable: validation loop exited without returning.")