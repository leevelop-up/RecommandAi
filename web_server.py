"""
RecommandAi 웹 대시보드 서버
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from api.web_dashboard import router as web_dashboard_router

# FastAPI 앱 생성
app = FastAPI(
    title="RecommandAi 웹 대시보드",
    description="금주 주식 추천 시스템 웹 인터페이스",
    version="1.0.0"
)

# 웹 대시보드 라우터 추가
app.include_router(web_dashboard_router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """메인 대시보드 페이지"""
    template_path = Path("templates/dashboard.html")

    if not template_path.exists():
        return "<h1>템플릿 파일을 찾을 수 없습니다</h1>"

    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "service": "RecommandAi Web Dashboard"
    }


if __name__ == "__main__":
    import uvicorn

    # 포트 설정 (환경 변수 또는 기본값 8000)
    port = int(os.getenv("WEB_PORT", "8000"))

    print(f"""
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║   📊 RecommandAi 웹 대시보드 시작                 ║
    ║                                                   ║
    ║   🌐 URL: http://localhost:{port}                ║
    ║                                                   ║
    ║   Ctrl+C를 눌러 종료하세요                        ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
