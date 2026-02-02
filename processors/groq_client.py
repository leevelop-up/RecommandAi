"""
Groq API 클라이언트 (Free Tier)
- llama-3.3-70b-versatile: 30 RPM, 14,400 RPD
- llama-3.1-70b-versatile: 30 RPM, 14,400 RPD
- mixtral-8x7b-32768: 30 RPM, 14,400 RPD
- 초고속 추론 (LPU 사용)
"""
import time
import json
from typing import Optional, Dict
from loguru import logger

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("groq 패키지 미설치. pip install groq 실행 필요")


class GroqClient:
    """Groq Free API 클라이언트"""

    # 가장 빠르고 정확한 모델 선택
    MODEL = "llama-3.3-70b-versatile"
    RPM_LIMIT = 30
    MIN_INTERVAL = 60.0 / RPM_LIMIT  # ~2초

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._last_call = 0.0
        self._call_count = 0

        if GROQ_AVAILABLE and self.api_key:
            self.client = Groq(api_key=api_key)
        else:
            self.client = None

    def is_available(self) -> bool:
        """API 키 설정 여부 확인"""
        return bool(
            GROQ_AVAILABLE
            and self.api_key
            and self.api_key != "your-groq-api-key"
            and self.client is not None
        )

    def _wait_rate_limit(self):
        """Rate limit 준수를 위한 대기"""
        elapsed = time.time() - self._last_call
        if elapsed < self.MIN_INTERVAL:
            wait = self.MIN_INTERVAL - elapsed
            logger.debug(f"Groq rate limit 대기: {wait:.1f}초")
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
            logger.warning("Groq API 키가 설정되지 않았거나 패키지 미설치")
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

            completion = self.client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            logger.debug(f"Groq 응답 수신 (호출 #{self._call_count})")
            return completion.choices[0].message.content

        except Exception as e:
            logger.error(f"Groq API 호출 실패: {e}")
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
            logger.warning("Groq API 키가 설정되지 않았거나 패키지 미설치")
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

            completion = self.client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}  # JSON mode
            )

            text = completion.choices[0].message.content
            logger.debug(f"Groq JSON 응답 수신 (호출 #{self._call_count})")

            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                logger.warning(f"Groq JSON 파싱 실패, 텍스트 재파싱 시도: {e}")
                return self._extract_json(text)

        except Exception as e:
            logger.error(f"Groq API JSON 호출 실패: {e}")
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

        logger.error("Groq JSON 추출 실패")
        return None
