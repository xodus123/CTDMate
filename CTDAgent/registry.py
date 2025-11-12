"""도구 등록 시스템 (ctdmate 통합)"""
from typing import Any, Dict, Optional, Callable

# ctdmate 통합 도구들
try:
    from tools.parse_upstage import parse_documents
except Exception as e:
    print(f"Warning: parse_upstage import failed: {e}")
    parse_documents = None

try:
    from tools.validate_rag import validate_excel, validate_content
except Exception as e:
    print(f"Warning: validate_rag import failed: {e}")
    validate_excel = None
    validate_content = None

try:
    from tools.generate_solar import generate_ctd, generate_all_modules
except Exception as e:
    print(f"Warning: generate_solar import failed: {e}")
    generate_ctd = None
    generate_all_modules = None

try:
    from tools.save_pdf import save_as_pdf
except Exception as e:
    print(f"Warning: save_pdf import failed: {e}")
    save_as_pdf = None

try:
    from tools.ctdmate_pipeline import generate_ctd_from_excel
except Exception as e:
    print(f"Warning: ctdmate_pipeline import failed: {e}")
    generate_ctd_from_excel = None

try:
    from tools.generate_validation_report import generate_validation_report
except Exception as e:
    print(f"Warning: generate_validation_report import failed: {e}")
    generate_validation_report = None


def _as_callable(fn_or_tool: Any) -> Optional[Callable]:
    """도구를 호출 가능한 함수로 래핑"""
    if fn_or_tool is None:
        return None
    if hasattr(fn_or_tool, "invoke"):
        return lambda args=None, state=None, _tool=fn_or_tool: _tool.invoke(args or {})
    return fn_or_tool


# 도구 등록
TOOLS: Dict[str, Any] = {}

if parse_documents:
    TOOLS["parse_documents"] = _as_callable(parse_documents)

if validate_excel:
    def _validate_excel_tool(args=None, state=None):
        excel_path = args.get("excel_path") if isinstance(args, dict) else None
        auto_fix = args.get("auto_fix", True) if isinstance(args, dict) else True
        if not excel_path:
            return {"ok": False, "error": "excel_path required"}
        return validate_excel(excel_path, auto_fix=auto_fix)
    TOOLS["validate_excel"] = _validate_excel_tool

if validate_content:
    def _validate_content_tool(args=None, state=None):
        section = args.get("section", "M2.3") if isinstance(args, dict) else "M2.3"
        content = args.get("content", "") if isinstance(args, dict) else ""
        auto_fix = args.get("auto_fix", True) if isinstance(args, dict) else True
        return validate_content(section, content, auto_fix=auto_fix)
    TOOLS["validate_content"] = _validate_content_tool

if generate_ctd:
    def _generate_ctd_tool(args=None, state=None):
        section = args.get("section", "M2.3") if isinstance(args, dict) else "M2.3"
        prompt = args.get("prompt", "") if isinstance(args, dict) else ""
        output_format = args.get("format", "yaml") if isinstance(args, dict) else "yaml"
        return generate_ctd(section, prompt, output_format)
    TOOLS["generate_ctd"] = _generate_ctd_tool

if generate_all_modules:
    def _generate_all_tool(args=None, state=None):
        excel_path = args.get("excel_path") if isinstance(args, dict) else None
        output_dir = args.get("output_dir", "output") if isinstance(args, dict) else "output"
        if not excel_path:
            return {"ok": False, "error": "excel_path required"}
        return generate_all_modules(excel_path, output_dir)
    TOOLS["generate_all_modules"] = _generate_all_tool

if save_as_pdf:
    def _save_pdf_tool(args=None, state=None):
        output_dir = args.get("output_dir", "output") if isinstance(args, dict) else "output"
        filename = args.get("filename", "CTD_Complete.pdf") if isinstance(args, dict) else "CTD_Complete.pdf"
        return save_as_pdf(output_dir=output_dir, filename=filename)
    TOOLS["save_as_pdf"] = _save_pdf_tool

if generate_ctd_from_excel:
    def _generate_from_excel_tool(args=None, state=None):
        excel_path = args.get("excel_path") if isinstance(args, dict) else None
        output_dir = args.get("output_dir", "output") if isinstance(args, dict) else "output"
        if not excel_path:
            return {"ok": False, "error": "excel_path required"}
        return generate_ctd_from_excel(excel_path, output_dir)
    TOOLS["generate_ctd_from_excel"] = _generate_from_excel_tool

if generate_validation_report:
    def _generate_validation_report_tool(args=None, state=None):
        output_dir = args.get("output_dir", "output") if isinstance(args, dict) else "output"
        output_format = args.get("output_format", "markdown") if isinstance(args, dict) else "markdown"
        document_content = args.get("document_content", "") if isinstance(args, dict) else ""

        # state에서 파싱된 문서 내용을 가져와서 검증에 사용
        if not document_content and state and "parsed_content" in state:
            document_content = state.get("parsed_content", "")

        return generate_validation_report(
            output_dir=output_dir,
            output_format=output_format,
            document_content=document_content
        )
    TOOLS["generate_validation_report"] = _generate_validation_report_tool


# 도구 스펙 (ReAct 에이전트용)
TOOL_SPEC = {
    "parse_documents": {
        "args": {"file_paths": "List[str]"},
        "desc": "Upstage Document Parse로 파일 파싱 (PDF, Excel 등)"
    },
    "validate_excel": {
        "args": {"excel_path": "str", "auto_fix": "bool?"},
        "desc": "Excel 파일 전체 검증 및 정규화"
    },
    "validate_content": {
        "args": {"section": "str", "content": "str", "auto_fix": "bool?"},
        "desc": "텍스트 내용 검증 및 정규화 (RAG 기반)"
    },
    "generate_ctd": {
        "args": {"section": "str", "prompt": "str", "format": "str?"},
        "desc": "Solar로 CTD 문서 생성 (M1, M2.3~M2.7)"
    },
    "generate_all_modules": {
        "args": {"excel_path": "str", "output_dir": "str?"},
        "desc": "Excel에서 모든 CTD 모듈 자동 생성"
    },
    "save_as_pdf": {
        "args": {"output_dir": "str?", "filename": "str?"},
        "desc": "YAML 파일들을 CTD 형식 PDF로 변환"
    },
    "generate_ctd_from_excel": {
        "args": {"excel_path": "str", "output_dir": "str?"},
        "desc": "CTDMate 파이프라인으로 Excel에서 전체 CTD 생성 (권장)"
    },
    "generate_validation_report": {
        "args": {"output_dir": "str?", "output_format": "str?"},
        "desc": "검증 결과를 기반으로 리포트 생성 (markdown 또는 json)"
    },
}


print(f"✓ {len(TOOLS)} tools registered: {list(TOOLS.keys())}")
