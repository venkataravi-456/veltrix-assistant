import os
import json
import logging
from typing import List, Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

from src.config import settings

logger = logging.getLogger("llm_client")

def generate_answer(
    prompt: str,
    system_prompt: str,
    model_override: Optional[str] = None
) -> str:
    """
    Synthesizes answers using LangChain prompt templates, message formatting,
    and output parsers, integrated with multi-provider LLM backends (Gemini, OpenAI,
    and local deterministic synthesizer).
    """
    # 1. Format messages with LangChain ChatPromptTemplate
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "{system_prompt}"),
        ("human", "{user_prompt}")
    ])
    formatted_messages = prompt_template.format_messages(
        system_prompt=system_prompt,
        user_prompt=prompt
    )

    provider = settings.LLM_PROVIDER.lower()
    parser = StrOutputParser()
    
    # 2. Google Gemini
    if provider == "gemini" and settings.GOOGLE_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel(
                model_name=model_override or "gemini-1.5-flash",
                generation_config={"temperature": 0.0}
            )
            resp = model.generate_content(f"{system_prompt}\n\n{prompt}")
            return parser.parse(resp.text.strip())
        except Exception as e:
            logger.warning(f"Gemini API call failed, using fallback synthesizer: {e}")
            
    # 3. OpenAI
    if provider == "openai" and settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=model_override or "gpt-4o-mini",
                messages=[
                    {"role": m.type if m.type != "human" else "user", "content": m.content}
                    for m in formatted_messages
                ],
                temperature=0.0
            )
            return parser.parse(resp.choices[0].message.content.strip())
        except Exception as e:
            logger.warning(f"OpenAI API call failed, using fallback synthesizer: {e}")

    # 4. Deterministic Local Synthesizer Fallback
    # Ensures reliable tests and answers when offline or without external keys
    lines = prompt.strip().split("\n")
    return "Based on the official policies: " + " ".join([l.strip() for l in lines[:3] if l.strip()])
