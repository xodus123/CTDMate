# ctdmate/app/router.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import os
import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# 내부 의존성
try:
    from ctdmate.app import config as CFG
    from ctdmate.app.fsm import CTDFSM
    from ctdmate.brain.router import Router, LlamaLocalClient
    from ctdmate.tools.reg_rag import RegulationRAGTool
    from ctdmate.tools.gen_solar import SolarGenerator
    from ctdmate.tools.smartdoc_upstage import run as parse_run
    from ctdmate.utils.pdf_generator import CTDPDFGenerator
except Exception:
    from . import config as CFG  # type: ignore
    from .fsm import CTDFSM  # type: ignore
    from ..brain.router import Router, LlamaLocalClient  # type: ignore
    from ..tools.reg_rag import RegulationRAGTool  # type: ignore
    from ..tools.gen_solar import SolarGenerator  # type: ignore
    from ..tools.smartdoc_upstage import run as parse_run  # type: ignore
    from ..utils.pdf_generator import CTDPDFGenerator  # type: ignore

app = FastAPI(title="CTDMate API", version="0.1.0")

# 정적 파일 및 업로드 디렉토리 설정
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
CTDAGENT_OUTPUT_DIR = BASE_DIR.parent / "CTDAgent" / "output"
STATIC_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# CTDAgent 통합
import sys
CTDAGENT_PATH = BASE_DIR.parent / "CTDAgent"
if CTDAGENT_PATH.exists():
    sys.path.insert(0, str(CTDAGENT_PATH))
    try:
        from agent import run_agent as run_ctd_agent
        CTDAGENT_AVAILABLE = True
        print(f"✓ CTDAgent loaded from {CTDAGENT_PATH}")
    except Exception as e:
        print(f"Warning: CTDAgent import failed: {e}")
        CTDAGENT_AVAILABLE = False
        run_ctd_agent = None
else:
    CTDAGENT_AVAILABLE = False
    run_ctd_agent = None
    print(f"Warning: CTDAgent not found at {CTDAGENT_PATH}")

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 단일 인스턴스(간단)
_llama = LlamaLocalClient()  # 구현체로 교체
_router = Router(llama=_llama)
_fsm = CTDFSM(llama_client=_llama)
_reg = RegulationRAGTool(auto_normalize=True, enable_rag=True, llama_client=_llama)
_gen = SolarGenerator(enable_rag=True, auto_normalize=True, output_format="yaml")
_pdf_gen = CTDPDFGenerator(output_dir=str(OUTPUT_DIR))


# ---------- Pydantic 모델 ----------
class RouteReq(BaseModel):
    desc: str = Field(..., description="요청 설명")


class ParseReq(BaseModel):
    files: List[str] = Field(..., description="파싱 대상 경로(.pdf/.xlsx)")


class ValidateReq(BaseModel):
    section: Optional[str] = Field(None, description="예: M2.3, M2.6, M2.7")
    content: Optional[str] = Field(None, description="검증 텍스트")
    excel_path: Optional[str] = Field(None, description="엑셀 파일 경로. 제공 시 시트별 검증")
    auto_fix: bool = True


class GenerateReq(BaseModel):
    section: str = Field(..., description="예: M2.3, M2.6, M2.7")
    prompt: str = Field(..., description="생성 프롬프트")
    format: str = Field("yaml", pattern="^(yaml|markdown)$")
    csv_present: Optional[Any] = None


class PipelineReq(BaseModel):
    desc: str = Field(..., description="요청 설명 또는 프롬프트")
    files: Optional[List[str]] = None
    section: Optional[str] = None
    format: Optional[str] = Field(None, pattern="^(yaml|markdown)$")
    auto_fix: bool = True


# ---------- 라우트 ----------
@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "ctdmate",
        "version": app.version,
        "qdrant_url": CFG.QDRANT_URL,
        "embed_model": CFG.EMBED_MODEL,
        "upstage_model": CFG.UPSTAGE_MODEL,
    }


@app.post("/v1/route")
def route(req: RouteReq) -> Dict[str, Any]:
    return _router.decide(req.desc)


@app.post("/v1/parse")
def parse(req: ParseReq) -> Dict[str, Any]:
    return parse_run(req.files)


@app.post("/v1/validate")
def validate(req: ValidateReq) -> Dict[str, Any]:
    if req.excel_path:
        return _reg.validate_excel(req.excel_path, auto_fix=req.auto_fix)
    section = req.section or "M2.3"
    content = req.content or ""
    return _reg.validate_and_normalize(section=section, content=content, auto_fix=req.auto_fix)


@app.post("/v1/generate")
def generate(req: GenerateReq) -> Dict[str, Any]:
    return _gen.generate(section=req.section, prompt=req.prompt, output_format=req.format, csv_present=req.csv_present)


@app.post("/v1/pipeline")
def pipeline(req: PipelineReq) -> Dict[str, Any]:
    return _fsm.run(
        desc=req.desc,
        files=req.files or [],
        section=req.section,
        output_format=req.format,
        auto_fix=req.auto_fix,
    )


@app.post("/v1/upload")
async def upload_files(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """파일 업로드 엔드포인트"""
    uploaded_files = []
    try:
        for file in files:
            # 파일 확장자 확인
            ext = Path(file.filename).suffix.lower()
            if ext not in ['.pdf', '.xlsx', '.csv', '.xls']:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

            # 파일 저장
            file_path = UPLOAD_DIR / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            uploaded_files.append({
                "filename": file.filename,
                "path": str(file_path),
                "size": file_path.stat().st_size
            })

        return {
            "ok": True,
            "files": uploaded_files,
            "message": f"{len(uploaded_files)} file(s) uploaded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/generate-ctd")
async def generate_ctd(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """파일 업로드 후 CTD 문서 생성 (CTDAgent 통합)"""
    try:
        # 파일 저장
        file_paths = []
        uploaded_files = []
        for file in files:
            ext = Path(file.filename).suffix.lower()
            if ext not in ['.pdf', '.xlsx', '.csv', '.xls']:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

            file_path = UPLOAD_DIR / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_paths.append(str(file_path))
            uploaded_files.append({
                "filename": file.filename,
                "path": str(file_path),
                "size": file_path.stat().st_size
            })

        # CTDMate 파이프라인 실행 (검증 및 분석)
        result = _fsm.run(
            desc="Generate CTD 2.3.P.1 documents from uploaded composition files",
            files=file_paths,
            section="M2.3.P.1",
            output_format="yaml",
            auto_fix=True,
        )

        # CTDAgent로 최종 PDF 생성
        pdf_path = None
        pdf_filename = None
        agent_mode = "generate"  # 기본값
        agent_result = {}

        if CTDAGENT_AVAILABLE and run_ctd_agent:
            try:
                print("\n" + "="*80)
                print("🤖 CTD ReAct AGENT STARTING")
                print("="*80)
                print(f"📁 Input files: {file_paths}")
                print(f"⚙️  Max steps: 10")
                print("="*80 + "\n")

                agent_result = run_ctd_agent(file_paths=file_paths, max_steps=10)

                # Agent 모드 가져오기
                agent_mode = agent_result.get("mode", "generate")
                print("\n" + "="*80)
                print(f"✅ AGENT COMPLETED - Mode: {agent_mode.upper()}")
                print("="*80 + "\n")

                # 모드별 처리
                if agent_mode == "validate":
                    # 검증 모드: 리포트 경로 확인
                    if agent_result.get("report_path"):
                        report_path = agent_result["report_path"]
                        print(f"✓ Validation report generated: {report_path}")
                else:
                    # 생성 모드: PDF 경로 확인
                    if agent_result.get("pdf_path"):
                        pdf_path = agent_result["pdf_path"]
                        pdf_filename = Path(pdf_path).name
                        print(f"✓ CTDAgent generated PDF: {pdf_path}")
                    else:
                        # output 디렉토리에서 최신 PDF 찾기
                        if CTDAGENT_OUTPUT_DIR.exists():
                            pdf_files = list(CTDAGENT_OUTPUT_DIR.glob("*.pdf"))
                            if pdf_files:
                                # 가장 최근 파일 선택
                                pdf_path = str(max(pdf_files, key=lambda p: p.stat().st_mtime))
                                pdf_filename = Path(pdf_path).name
                                print(f"✓ Found latest PDF: {pdf_path}")

            except Exception as e:
                print(f"CTDAgent error: {e}")
                import traceback
                traceback.print_exc()

        # 대체: CTDMate PDF 생성
        if not pdf_path and agent_mode == "generate":
            pdf_path = _pdf_gen.generate_pdf(result)
            pdf_filename = Path(pdf_path).name

        # 응답 구성
        response = {
            "ok": result.get("ok", False),
            "mode": agent_mode,  # Agent 모드 전달
            "files": uploaded_files,
            "result": result
        }

        # 생성 모드: PDF 정보 추가
        if agent_mode == "generate" and pdf_path:
            response["pdf"] = {
                "filename": pdf_filename,
                "path": pdf_path,
                "download_url": f"/v1/download/{pdf_filename}",
                "preview_url": f"/v1/preview/{pdf_filename}"
            }

            # Module 2 PDF 정보도 추가 (있는 경우)
            if agent_result.get("module2_pdf_path"):
                module2_path = agent_result["module2_pdf_path"]
                module2_filename = Path(module2_path).name
                response["module2_pdf"] = {
                    "filename": module2_filename,
                    "path": module2_path,
                    "download_url": f"/v1/download/{module2_filename}",
                    "preview_url": f"/v1/preview/{module2_filename}"
                }

        # 검증 모드: 검증 리포트 정보 추가
        elif agent_mode == "validate":
            validation_info = {
                "report_path": agent_result.get("report_path"),
                "summary": agent_result.get("summary", {}),
                "final_message": agent_result.get("final_message")
            }

            # 스키마 체크 정보가 있으면 추가
            if "schema_check" in agent_result:
                schema_check = agent_result["schema_check"]
                validation_info["schema_check"] = schema_check

                # 누락 항목을 리스트로 변환 (웹 UI 표시용)
                if schema_check.get("missing_items"):
                    validation_info["missing_items"] = [
                        f"{item.get('id', '')}: {item.get('title', '')}"
                        for item in schema_check["missing_items"][:10]  # 최대 10개만
                    ]

                # 발견된 항목을 리스트로 변환
                if schema_check.get("found_items"):
                    validation_info["passed_items"] = [
                        f"{item.get('id', '')}: {item.get('title', '')}"
                        for item in schema_check["found_items"][:10]  # 최대 10개만
                    ]

            response["validation"] = validation_info

            # 검증 리포트를 다운로드 가능하도록
            if agent_result.get("report_path"):
                report_filename = Path(agent_result["report_path"]).name
                response["validation"]["download_url"] = f"/v1/download/{report_filename}"

        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/download/{filename}")
async def download_pdf(filename: str):
    """파일 다운로드 (PDF, Markdown 리포트 등)"""
    # 파일 확장자에 따른 MIME type 설정
    ext = Path(filename).suffix.lower()
    mime_types = {
        ".pdf": "application/pdf",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json"
    }
    media_type = mime_types.get(ext, "application/octet-stream")

    # CTDMate output 먼저 확인
    file_path = OUTPUT_DIR / filename
    if file_path.exists():
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=media_type
        )

    # CTDAgent output 확인
    if CTDAGENT_OUTPUT_DIR.exists():
        ctd_file_path = CTDAGENT_OUTPUT_DIR / filename
        if ctd_file_path.exists():
            return FileResponse(
                path=str(ctd_file_path),
                filename=filename,
                media_type=media_type
            )

    raise HTTPException(status_code=404, detail="File not found")


@app.get("/v1/preview/{filename}")
async def preview_pdf(filename: str):
    """PDF 파일 미리보기 (브라우저에서 열기)"""
    # CTDMate output 먼저 확인
    file_path = OUTPUT_DIR / filename
    if file_path.exists():
        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )

    # CTDAgent output 확인
    if CTDAGENT_OUTPUT_DIR.exists():
        ctd_file_path = CTDAGENT_OUTPUT_DIR / filename
        if ctd_file_path.exists():
            return FileResponse(
                path=str(ctd_file_path),
                media_type="application/pdf",
                headers={"Content-Disposition": f"inline; filename={filename}"}
            )

    raise HTTPException(status_code=404, detail="File not found")


@app.get("/")
async def index():
    """메인 페이지 서빙"""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return {"message": "Welcome to CTDMate API. Please create static/index.html"}
    return FileResponse(str(index_file))


# ---------- 로컬 실행 ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ctdmate.app.router:app", host="0.0.0.0", port=8000, reload=False)
