"""LLM client with OpenAI/DeepSeek/Claude/HTTP fallback support"""
import json, re, time
from typing import Dict, Optional, Callable

class LLMTuner:
    def __init__(self, config: Dict):
        self.config = config; self._client = None; self._provider_type = None

    def _get_client(self):
        if self._client is not None: return self._client
        provider = self.config.get("LLM_PROVIDER", "openai")
        try:
            if provider == "anthropic":
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.config["LLM_API_KEY"])
                self._provider_type = "anthropic"
            else:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.config["LLM_API_KEY"], base_url=self.config["LLM_API_BASE_URL"])
                self._provider_type = "openai"
        except ImportError:
            print("[WARN] SDK not installed, using HTTP fallback")
            self._provider_type = "http"
        return self._client

    def analyze(self, data_block: str, history_text: str = "", tuning_mode: str = "speed_pi",
                prompt_context: Optional[Dict] = None, abort_check: Optional[Callable] = None) -> Dict:
        from .prompts import SYSTEM_PROMPT_SPEED_PI, build_user_prompt
        system = SYSTEM_PROMPT_SPEED_PI; user = build_user_prompt(data_block, history_text, tuning_mode)

        for attempt in range(2):
            if abort_check and abort_check(): return _empty("Aborted")
            try:
                raw = self._call_api(system, user)
                parsed = _parse_json(raw)
                if parsed: return parsed
                print(f"[WARN] Parse retry {attempt+1}")
                time.sleep(1)
            except Exception as e:
                err_msg=str(e)[:60]
                if attempt==0: print(f"[WARN] LLM 错误: {err_msg}, 重试...")
                time.sleep(0.5)
        return _empty("LLM 不可用 (检查 API Key 和网络)")

    def _call_api(self, system: str, user: str) -> str:
        self._get_client(); model = self.config["LLM_MODEL_NAME"]; timeout = self.config.get("LLM_REQUEST_TIMEOUT", 10)
        if self._provider_type == "anthropic":
            resp = self._client.messages.create(model=model, max_tokens=1024, system=system,
                messages=[{"role":"user","content":user}])
            return resp.content[0].text
        elif self._provider_type == "openai":
            resp = self._client.chat.completions.create(model=model, temperature=0.3, max_tokens=1024,
                messages=[{"role":"system","content":system},{"role":"user","content":user}], timeout=timeout)
            return resp.choices[0].message.content or ""
        else:
            import requests
            resp = requests.post(f"{self.config['LLM_API_BASE_URL']}/chat/completions",
                headers={"Authorization":f"Bearer {self.config['LLM_API_KEY']}","Content-Type":"application/json"},
                json={"model":model,"messages":[{"role":"system","content":system},{"role":"user","content":user}],
                      "temperature":0.3,"max_tokens":1024}, timeout=timeout)
            return resp.json()["choices"][0]["message"]["content"]

def _parse_json(text: str) -> Optional[Dict]:
    if not text: return None
    try: return json.loads(text)
    except: pass
    m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    m = re.search(r'\{[^{}]*"p"\s*:\s*[\d.]+[^{}]*\}', text)
    if m:
        try: return json.loads(m.group(0))
        except: pass
    return None

def _empty(reason: str) -> Dict:
    return {"p":-1,"i":-1,"d":0,"thought_process":reason,"analysis_summary":reason,"status":"TUNING","tuning_action":"FALLBACK"}
