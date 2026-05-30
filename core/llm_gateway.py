"""
AI小说工厂 v3.0 - LLM网关 (商用加固版)
统一AI调用接口。支持重试、Token预算、速率控制、自动降级。
"""
import json
import time
import os
import re
from typing import Optional, Dict, Tuple
from config import cfg


class LLMGateway:
    def __init__(self):
        self._client = None
        self._mode = "offline"
        self._total_tokens = 0
        self._total_cost = 0.0
        self._call_count = 0
        self._token_budget = 500_000
        self._last_call_time = 0
        self._min_call_interval = 0.5
        self._max_retries = 3
    
    def initialize(self) -> str:
        provider_order = []
        if cfg.LLM_PROVIDER in ("deepseek", "claude", "openai"):
            provider_order.append(cfg.LLM_PROVIDER)
        for provider, api_key in [
            ("deepseek", cfg.DEEPSEEK_API_KEY),
            ("claude", cfg.ANTHROPIC_API_KEY),
            ("openai", cfg.OPENAI_API_KEY),
        ]:
            if api_key and provider not in provider_order:
                provider_order.append(provider)

        for provider in provider_order:
            if provider == "deepseek" and cfg.DEEPSEEK_API_KEY:
                try:
                    import openai
                    self._client = openai.OpenAI(
                        api_key=cfg.DEEPSEEK_API_KEY,
                        base_url=cfg.DEEPSEEK_BASE_URL,
                    )
                    self._mode = "deepseek"
                    print(f"  [LLM] DeepSeek API 已连接 (模型: {cfg.DEEPSEEK_MODEL})")
                    return "deepseek"
                except ImportError:
                    print("  [LLM] DeepSeek 需安装: pip install openai")
                except Exception as e:
                    print(f"  [LLM] DeepSeek连接失败: {e}")

            if provider == "claude" and cfg.ANTHROPIC_API_KEY:
                try:
                    import anthropic
                    self._client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)
                    self._mode = "claude"
                    print(f"  [LLM] Claude API 已连接 (模型: {cfg.CLAUDE_MODEL})")
                    return "claude"
                except ImportError:
                    print("  [LLM] 需安装: pip install anthropic")
                except Exception as e:
                    print(f"  [LLM] Claude连接失败: {e}")

            if provider == "openai" and cfg.OPENAI_API_KEY:
                try:
                    import openai
                    self._client = openai.OpenAI(api_key=cfg.OPENAI_API_KEY)
                    self._mode = "openai"
                    print(f"  [LLM] OpenAI API 已连接 (模型: {cfg.OPENAI_MODEL})")
                    return "openai"
                except ImportError:
                    print("  [LLM] 需安装: pip install openai")
                except Exception as e:
                    print(f"  [LLM] OpenAI连接失败: {e}")
        
        self._mode = "offline"
        print("  [LLM] 离线模式 — 设置 DEEPSEEK_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY 可启用自动模式")
        return "offline"
    
    @property
    def mode(self) -> str: return self._mode
    @property
    def is_online(self) -> bool: return self._mode in ("claude", "openai", "deepseek")
    @property
    def total_tokens(self) -> int: return self._total_tokens
    @property
    def total_cost(self) -> float: return self._total_cost
    @property
    def call_count(self) -> int: return self._call_count
    @property
    def budget_remaining(self) -> int: return max(0, self._token_budget - self._total_tokens)
    @property
    def budget_exhausted(self) -> bool: return self._total_tokens >= self._token_budget
    
    def set_budget(self, max_tokens: int):
        self._token_budget = max_tokens

    def generate(self,
                 system_prompt: str,
                 user_prompt: str,
                 max_tokens: int = 4000,
                 temperature: float = 0.7,
                 step_name: str = "generation",
                 min_length: int = 0,
                 expect_json: bool = False) -> Optional[str]:
        """
        统一生成接口 — 带自动重试、长度验证、JSON验证。
        
        在线模式返回AI响应文本。离线模式导出Prompt文件并返回None。
        """
        if self.is_online and self.budget_exhausted:
            print(f"  [LLM] ⚠️ Token预算已尽 ({self._total_tokens}/{self._token_budget})，降级离线")
            return self._export_offline(system_prompt, user_prompt, step_name)
        
        if not self.is_online:
            return self._export_offline(system_prompt, user_prompt, step_name)
        
        last_error = None
        for attempt in range(1, self._max_retries + 1):
            try:
                self._rate_limit()
                
                if self._mode == "claude":
                    text, tokens = self._call_claude(system_prompt, user_prompt, max_tokens, temperature)
                elif self._mode == "deepseek":
                    text, tokens = self._call_deepseek(system_prompt, user_prompt, max_tokens, temperature)
                else:
                    text, tokens = self._call_openai(system_prompt, user_prompt, max_tokens, temperature)
                
                if text is None:
                    raise Exception("空响应")
                
                self._total_tokens += tokens
                self._call_count += 1
                self._total_cost += tokens * 6.0 / 1_000_000
                
                # 验证响应
                ok, reason = self._validate(text, min_length, expect_json)
                if ok:
                    return text
                
                print(f"  [LLM] 验证失败({reason})，重试 {attempt}/{self._max_retries}")
                last_error = reason
                temperature = min(1.0, temperature + 0.05)
                
            except Exception as e:
                last_error = str(e)
                if attempt < self._max_retries:
                    wait = 2 ** attempt
                    print(f"  [LLM] 失败: {e}，{wait}s后重试 ({attempt}/{self._max_retries})")
                    time.sleep(wait)
                else:
                    print(f"  [LLM] 全部重试失败: {last_error}")
        
        print(f"  [LLM] 降级为离线导出")
        return self._export_offline(system_prompt, user_prompt, step_name)
    
    def _call_claude(self, system, user, max_tokens, temp) -> Tuple[str, int]:
        response = self._client.messages.create(
            model=cfg.CLAUDE_MODEL, max_tokens=max_tokens, temperature=temp,
            system=system, messages=[{"role": "user", "content": user}]
        )
        text = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens
        print(f"  [LLM] Claude ✅ ({tokens}tok, 累计{self._total_tokens + tokens})")
        return text, tokens
    
    def _call_openai(self, system, user, max_tokens, temp) -> Tuple[str, int]:
        response = self._client.chat.completions.create(
            model=cfg.OPENAI_MODEL, max_tokens=max_tokens, temperature=temp,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens
        print(f"  [LLM] OpenAI ✅ ({tokens}tok, 累计{self._total_tokens + tokens})")
        return text, tokens

    def _call_deepseek(self, system, user, max_tokens, temp) -> Tuple[str, int]:
        response = self._client.chat.completions.create(
            model=cfg.DEEPSEEK_MODEL, max_tokens=max_tokens, temperature=temp,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        text = response.choices[0].message.content
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "total_tokens", 0) if usage else 0
        print(f"  [LLM] DeepSeek ✅ ({tokens}tok, 累计{self._total_tokens + tokens})")
        return text, tokens
    
    def _export_offline(self, system, user, step_name) -> None:
        from datetime import datetime
        prompt = f"""{'='*60}
AI小说工厂 - 离线Prompt | 步骤: {step_name}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
{'='*60}

===== 系统提示词（设为System Prompt）=====

{system}

===== 用户提示词（发送给AI）=====

{user}
"""
        filepath = os.path.join(cfg.OUTPUT_DIR, f"prompt_{step_name}.txt")
        os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"  [LLM] 📄 已导出: {os.path.basename(filepath)}")
        return None
    
    def _validate(self, text, min_length, expect_json):
        if not text or not text.strip():
            return False, "空响应"
        if min_length > 0 and len(text.strip()) < min_length:
            return False, f"太短({len(text.strip())}字<{min_length}字)"
        if expect_json and self.parse_json_response(text) is None:
            return False, "JSON解析失败"
        return True, "OK"
    
    def _rate_limit(self):
        elapsed = time.time() - self._last_call_time
        if elapsed < self._min_call_interval:
            time.sleep(self._min_call_interval - elapsed)
        self._last_call_time = time.time()
    
    def parse_json_response(self, text: str) -> Optional[Dict]:
        if not text: return None
        text = text.strip()
        try: return json.loads(text)
        except: pass
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
        if m:
            try: return json.loads(m.group(1))
            except: pass
        for start_ch, end_ch in [('{','}'),('[',']')]:
            s, e = text.find(start_ch), text.rfind(end_ch)
            if s >= 0 and e > s:
                try: return json.loads(text[s:e+1])
                except: pass
        return None
    
    def get_stats(self) -> Dict:
        return {
            "mode": self._mode, "calls": self._call_count,
            "total_tokens": self._total_tokens,
            "cost_usd": round(self._total_cost, 4),
            "budget_remaining": self.budget_remaining,
            "budget_pct": round(self._total_tokens / max(1, self._token_budget) * 100, 1)
        }

llm = LLMGateway()
