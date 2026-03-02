import requests
import json
import time
from src.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODEL_NAME

class Translator:
    def __init__(self):
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables.")
        
        self.api_key = OPENROUTER_API_KEY
        self.base_url = OPENROUTER_BASE_URL.rstrip('/')
        
    def translate_text(self, text, source_lang="auto", target_lang="pt-BR", system_instruction=None):
        """
        Translates text using OpenRouter API via direct HTTP requests.
        """
        if not text or not text.strip():
            return text

        if system_instruction:
             sys_prompt = system_instruction
        else:
            sys_prompt = (
                "You are a professional translator. Translate the input text from English to Portuguese (Brazil). "
                "Pay close attention to:\n"
                "- **False cognates** (e.g., 'pretend' means 'fingir', not 'pretender').\n"
                "- **Gender and number agreement** (ensure articles, adjectives, and nouns agree).\n"
                "- **Word order** natural to Portuguese.\n"
                "- **Verb tenses** corresponding to the context.\n"
                "- **Idiomatic expressions** (translate the meaning, not literally).\n"
                "- **Maintain the register** (formal/informal) and tone of the original text.\n"
                "Do not add any explanations or notes, just the translation."
            )

        max_retries = 5
        base_delay = 2
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/TraeAI/TradutorEPub", # Placeholder
            "X-Title": "TradutorEPub"
        }

        for attempt in range(max_retries):
            try:
                # Adjust temperature based on attempt to avoid getting stuck in loops
                temperature = 0.3 + (attempt * 0.1) 

                payload = {
                    "model": MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": text}
                    ],
                    "temperature": temperature,
                }
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                response.raise_for_status()
                data = response.json()
                
                if 'choices' not in data or not data['choices']:
                    raise ValueError(f"Invalid API response: {data}")
                    
                translated_text = data['choices'][0]['message']['content'].strip()

                # check for repetition
                if self._has_repetition(translated_text):
                     print(f"Repetition detected in translation (attempt {attempt + 1}). Retrying...")
                     # Add a stronger instruction against repetition for the next attempt if possible
                     if "Do not repeat sentences" not in sys_prompt:
                         sys_prompt += " Do not repeat sentences. If the text is repetitive, summarize or translate it once."
                     continue
                
                return translated_text

            except Exception as e:
                print(f"Error translating text (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    sleep_time = base_delay * (2 ** attempt)
                    time.sleep(sleep_time)
                else:
                    print(f"Failed to translate after {max_retries} attempts. Returning original text.")
                    return text # Fallback to original text

    def _has_repetition(self, text):
        """
        Checks if the text contains significant repetition.
        Simple heuristic: check if the first half is identical to the second half,
        or if a sentence is repeated 3+ times.
        """
        if not text:
            return False
            
        # Check for immediate halve duplication (common AI failure mode)
        # e.g. "Hello world. Hello world."
        n = len(text)
        if n > 50: # Only check substantial text
            mid = n // 2
            first_half = text[:mid].strip()
            second_half = text[mid:].strip()
            # fuzzy check
            if first_half == second_half or (second_half.startswith(first_half) and len(second_half) < len(first_half) * 1.1):
                 return True

        # Check for repeated sentences
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if len(sentences) > 4:
            from collections import Counter
            counts = Counter(sentences)
            most_common = counts.most_common(1)
            if most_common and most_common[0][1] >= 3:
                # If a sentence appears 3 or more times, it's likely a loop
                return True
        
        return False
