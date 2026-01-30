"""
Google Gemini API 클라이언트 (Free Tier)
- Gemini 2.0 Flash: 15 RPM, 1500 RPD
- REST API 직접 호출 (추가 패키지 불필요)
"""
import time
import json
import requests
from typing import Optional, Dict, Any
from loguru import logger


class GeminiClient:
    """Gemini Free API 클라이언트"""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    MODEL = "gemini-2.0-flash"
    RPM_LIMIT = 15
    MIN_INTERVAL = 60.0 / RPM_LIMIT  # ~4초

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._last_call = 0.0
        self._call_count = 0

    def is_available(self) -> bool:
        """API 키 설정 여부 확인"""
        return bool(self.api_key and self.api_key != "your-gemini-api-key")

    def _wait_rate_limit(self):
        """Rate limit 준수를 위한 대기"""
        elapsed = time.time() - self._last_call
        if elapsed < self.MIN_INTERVAL:
            wait = self.MIN_INTERVAL - elapsed
            logger.debug(f"Rate limit 대기: {wait:.1f}초")
            time.sleep(wait)

    def _build_url(self, json_mode: bool = False) -> str:
        action = "generateContent"
        return f"{self.BASE_URL}/{self.MODEL}:{action}?key={self.api_key}"

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> Optional[str]:
        """텍스트 생성"""
        if not self.is_available():
            logger.warning("Gemini API 키가 설정되지 않았습니다")
            return None

        self._wait_rate_limit()

        body: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        return self._call_api(body)

    def generate_json(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> Optional[Dict]:
        """JSON 구조화 응답 생성"""
        if not self.is_available():
            logger.warning("Gemini API 키가 설정되지 않았습니다")
            return None

        self._wait_rate_limit()

        body: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }

        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        text = self._call_api(body)
        if text is None:
            return None

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 파싱 실패, 텍스트 재파싱 시도: {e}")
            return self._extract_json(text)

    def _call_api(self, body: Dict, retries: int = 3) -> Optional[str]:
        """API 호출 (재시도 포함)"""
        url = self._build_url()

        for attempt in range(retries):
            try:
                self._last_call = time.time()
                self._call_count += 1

                resp = requests.post(
                    url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                    timeout=60,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            logger.debug(f"Gemini 응답 수신 (호출 #{self._call_count})")
                            return parts[0].get("text", "")

                    logger.warning(f"Gemini 응답 비어있음: {data}")
                    return None

                elif resp.status_code == 429:
                    wait = (2 ** attempt) * 5
                    logger.warning(f"Rate limit 초과, {wait}초 후 재시도 ({attempt + 1}/{retries})")
                    time.sleep(wait)
                    continue

                elif resp.status_code in (500, 503):
                    wait = (2 ** attempt) * 3
                    logger.warning(f"서버 오류 {resp.status_code}, {wait}초 후 재시도")
                    time.sleep(wait)
                    continue

                else:
                    logger.error(f"Gemini API 오류 {resp.status_code}: {resp.text[:300]}")
                    return None

            except requests.exceptions.Timeout:
                logger.warning(f"Gemini API 타임아웃 ({attempt + 1}/{retries})")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                continue

            except requests.exceptions.RequestException as e:
                logger.error(f"Gemini API 요청 실패: {e}")
                return None

        logger.error(f"Gemini API 최대 재시도 횟수 초과 ({retries}회)")
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

        logger.error("JSON 추출 실패")
        return None
