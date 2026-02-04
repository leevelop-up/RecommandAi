"""
웹 대시보드 API 라우터
"""
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel

router = APIRouter()

# 실행 상태 저장
execution_status = {
    "running": False,
    "start_time": None,
    "end_time": None,
    "status": "idle",  # idle, running, completed, error
    "message": ""
}


class ExecutionStatus(BaseModel):
    running: bool
    start_time: Optional[str]
    end_time: Optional[str]
    status: str
    message: str


class ResultFile(BaseModel):
    filename: str
    filepath: str
    created_at: str
    size_kb: float
    type: str  # json or txt


def run_weekly_recommendation():
    """백그라운드에서 weekly 추천 실행"""
    global execution_status

    try:
        execution_status["running"] = True
        execution_status["status"] = "running"
        execution_status["start_time"] = datetime.now().isoformat()
        execution_status["message"] = "금주 추천 실행 중..."

        # run_weekly_recommendation.py 실행
        result = subprocess.run(
            ["python", "run_weekly_recommendation.py"],
            capture_output=True,
            text=True,
            timeout=600  # 10분 타임아웃
        )

        if result.returncode == 0:
            execution_status["status"] = "completed"
            execution_status["message"] = "금주 추천 완료!"
        else:
            execution_status["status"] = "error"
            execution_status["message"] = f"실행 실패: {result.stderr[:200]}"

    except subprocess.TimeoutExpired:
        execution_status["status"] = "error"
        execution_status["message"] = "실행 시간 초과 (10분)"
    except Exception as e:
        execution_status["status"] = "error"
        execution_status["message"] = f"오류 발생: {str(e)}"
    finally:
        execution_status["running"] = False
        execution_status["end_time"] = datetime.now().isoformat()


@router.post("/api/run-weekly")
async def run_weekly(background_tasks: BackgroundTasks):
    """금주 추천 실행"""
    global execution_status

    if execution_status["running"]:
        raise HTTPException(status_code=400, detail="이미 실행 중입니다")

    # 백그라운드에서 실행
    background_tasks.add_task(run_weekly_recommendation)

    return {
        "success": True,
        "message": "금주 추천 실행을 시작했습니다"
    }


@router.get("/api/status")
async def get_status() -> ExecutionStatus:
    """실행 상태 조회"""
    return ExecutionStatus(**execution_status)


@router.get("/api/results")
async def get_results() -> List[ResultFile]:
    """결과 파일 목록 조회"""
    output_dir = Path("output")

    if not output_dir.exists():
        return []

    results = []

    # weekly_recommendation 파일들 찾기
    for file in output_dir.glob("weekly_recommendation_*"):
        if file.is_file():
            stat = file.stat()
            file_type = "json" if file.suffix == ".json" else "txt"

            results.append(ResultFile(
                filename=file.name,
                filepath=str(file),
                created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                size_kb=round(stat.st_size / 1024, 2),
                type=file_type
            ))

    # 최신순 정렬
    results.sort(key=lambda x: x.created_at, reverse=True)

    return results


@router.get("/api/results/{filename}")
async def get_result_file(filename: str):
    """특정 결과 파일 다운로드"""
    file_path = Path("output") / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    # 파일 확장자에 따라 적절한 Content-Type 설정
    if filename.endswith(".json"):
        return FileResponse(
            file_path,
            media_type="application/json",
            filename=filename
        )
    else:
        return FileResponse(
            file_path,
            media_type="text/plain; charset=utf-8",
            filename=filename
        )


@router.get("/api/results/{filename}/preview")
async def preview_result(filename: str):
    """결과 파일 미리보기 (JSON만)"""
    file_path = Path("output") / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    if not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="JSON 파일만 미리보기 가능합니다")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 요약 정보만 추출
        preview = {
            "generated_at": data.get("generated_at"),
            "schedule_time": data.get("schedule_time"),
            "hot_themes_count": len(data.get("hot_themes", [])),
            "hot_themes": [
                {
                    "rank": t["rank"],
                    "name": t["name"],
                    "score": t["score"],
                    "change_rate": t["change_rate"]
                }
                for t in data.get("hot_themes", [])[:5]
            ],
            "weekly_recommendations_count": len(data.get("weekly_recommendations", [])),
            "weekly_recommendations": [
                {
                    "name": s["name"],
                    "ticker": s["ticker"],
                    "country": s["country"],
                    "current_price": s["current_price"],
                    "daily_change_rate": s["daily_change_rate"]
                }
                for s in data.get("weekly_recommendations", [])[:10]
            ],
            "ai_engines": list(data.get("ai_recommendations", {}).keys())
        }

        return preview
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 읽기 실패: {str(e)}")


@router.get("/api/logs/recent")
async def get_recent_logs(lines: int = 50):
    """최근 로그 조회"""
    try:
        result = subprocess.run(
            ["tail", "-n", str(lines), "logs/app.log"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return {"logs": result.stdout}
        else:
            return {"logs": "로그 파일을 찾을 수 없습니다"}
    except Exception as e:
        return {"logs": f"로그 조회 실패: {str(e)}"}
