"""
xAI (Grok) API 클라이언트
- Grok 2 모델 사용
- OpenAI 호환 API
"""
import time
import json
import requests
from typing import Optional, Dict
from loguru import logger


class XAIClient:
    """xAI (Grok) API 클라이언트"""

    BASE_URL = "https://api.x.ai/v1"
    MODEL = "grok-2-latest"  # 또는 "grok-2-1212"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._last_call = 0.0
        self._call_count = 0

    def is_available(self) -> bool:
        """API 키 설정 여부 확인"""
        return bool(self.api_key and self.api_key.startswith("xai-"))

    def _wait_rate_limit(self, wait_time: float = 1.0):
        """Rate limit 준수를 위한 대기"""
        elapsed = time.time() - self._last_call
        if elapsed < wait_time:
            wait = wait_time - elapsed
            time.sleep(wait)

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> Optional[str]:
        """텍스트 생성"""
        if not self.is_available():
            logger.warning("xAI API 키가 설정되지 않았습니다")
            return None

        self._wait_rate_limit()

        try:
            messages = []

            if system_instruction:
                messages.append({
                    "role": "system",
                    "content": system_instruction
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            self._last_call = time.time()
            self._call_count += 1

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": self.MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                logger.debug(f"xAI (Grok) 응답 수신 (호출 #{self._call_count})")
                return content
            else:
                logger.error(f"xAI API 오류 {response.status_code}: {response.text[:300]}")
                return None

        except Exception as e:
            logger.error(f"xAI API 호출 실패: {e}")
            return None

    def generate_json(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> Optional[Dict]:
        """JSON 구조화 응답 생성"""
        if not self.is_available():
            logger.warning("xAI API 키가 설정되지 않았습니다")
            return None

        self._wait_rate_limit()

        try:
            messages = []

            # System instruction 강화
            json_system = system_instruction
            if system_instruction:
                json_system += "\n\n반드시 유효한 JSON 형식으로만 응답하세요. 추가 설명 없이 JSON만 출력하세요."
            else:
                json_system = "반드시 유효한 JSON 형식으로만 응답하세요. 추가 설명 없이 JSON만 출력하세요."

            messages.append({
                "role": "system",
                "content": json_system
            })

            messages.append({
                "role": "user",
                "content": prompt
            })

            self._last_call = time.time()
            self._call_count += 1

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": self.MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"}  # JSON mode
            }

            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                logger.debug(f"xAI (Grok) JSON 응답 수신 (호출 #{self._call_count})")

                try:
                    return json.loads(text)
                except json.JSONDecodeError as e:
                    logger.warning(f"xAI JSON 파싱 실패, 텍스트 재파싱 시도: {e}")
                    return self._extract_json(text)
            else:
                logger.error(f"xAI API 오류 {response.status_code}: {response.text[:300]}")
                return None

        except Exception as e:
            logger.error(f"xAI API JSON 호출 실패: {e}")
            return None

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict]:
        """텍스트에서 JSON 추출 시도"""
        import re

        # ```json ... ``` 블록 추출
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # { ... } 블록 추출
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error("xAI JSON 추출 실패")
        return None
