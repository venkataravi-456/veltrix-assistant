import logging
import math
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("context_budget")

MAX_CORPUS_TOKENS = 3000

try:
    import tiktoken
    ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception as e:
    logger.warning(f"Could not load tiktoken cl100k_base encoding directly: {e}. Using approximate fallback.")
    ENCODER = None

def count_tokens(text: str) -> int:
    if not text:
        return 0
    if ENCODER is not None:
        try:
            return len(ENCODER.encode(text))
        except Exception:
            pass
    # Fallback approximation: 1 token ~= 4 characters / 0.75 words
    return max(1, math.ceil(len(text) / 4))

def fit_chunks_within_budget(
    chunks: List[Dict[str, Any]],
    max_tokens: int = MAX_CORPUS_TOKENS
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Fits retrieved chunks into the context budget of 3,000 corpus tokens.
    Records and logs the total corpus tokens.
    """
    selected = []
    total_tokens = 0
    
    for chunk in chunks:
        text = chunk.get("text", "")
        tok_len = count_tokens(text)
        if total_tokens + tok_len <= max_tokens:
            selected.append(chunk)
            total_tokens += tok_len
        else:
            remaining = max_tokens - total_tokens
            if remaining >= 50:
                if ENCODER is not None:
                    try:
                        tokens = ENCODER.encode(text)[:remaining]
                        truncated_text = ENCODER.decode(tokens)
                    except Exception:
                        char_cutoff = remaining * 4
                        truncated_text = text[:char_cutoff]
                else:
                    char_cutoff = remaining * 4
                    truncated_text = text[:char_cutoff]
                partial_chunk = dict(chunk)
                partial_chunk["text"] = truncated_text
                selected.append(partial_chunk)
                total_tokens += remaining
            break
            
    logger.info(f"LLM Call Corpus Tokens: {total_tokens}/{max_tokens} (cl100k_base)")
    return selected, total_tokens
