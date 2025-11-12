"""RAG 기반 검증 도구 (ctdmate 통합)"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ctdmate.tools.reg_rag import RegulationRAGTool
    RAG_AVAILABLE = True
except Exception as e:
    print(f"Warning: RAG tool not available: {e}")
    RAG_AVAILABLE = False


# 전역 RAG 도구 인스턴스
_rag_tool = None


def get_rag_tool():
    """RAG 도구 인스턴스 가져오기 (싱글톤)"""
    global _rag_tool
    if _rag_tool is None and RAG_AVAILABLE:
        try:
            _rag_tool = RegulationRAGTool(
                auto_normalize=True,
                enable_rag=True,
            )
        except Exception as e:
            print(f"Warning: Failed to initialize RAG tool: {e}")
    return _rag_tool


def validate_excel(excel_path: str, auto_fix: bool = True) -> Dict[str, Any]:
    """
    Excel 파일 검증

    Args:
        excel_path: Excel 파일 경로
        auto_fix: 자동 정규화 여부

    Returns:
        검증 결과 딕셔너리
    """
    rag_tool = get_rag_tool()
    if not rag_tool:
        return {
            "ok": False,
            "error": "RAG tool not available",
            "results": []
        }

    try:
        result = rag_tool.validate_excel(excel_path, auto_fix=auto_fix)
        return result
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "results": []
        }


def validate_content(section: str, content: str, auto_fix: bool = True) -> Dict[str, Any]:
    """
    텍스트 내용 검증

    Args:
        section: CTD 섹션 (예: M2.3, M2.6)
        content: 검증할 내용
        auto_fix: 자동 정규화 여부

    Returns:
        검증 결과 딕셔너리
    """
    rag_tool = get_rag_tool()
    if not rag_tool:
        return {
            "ok": False,
            "error": "RAG tool not available",
            "pass": False
        }

    try:
        result = rag_tool.validate_and_normalize(
            section=section,
            content=content,
            auto_fix=auto_fix
        )
        return result
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "pass": False
        }


if __name__ == "__main__":
    # 테스트
    test_content = "당뇨병 환자의 혈압 관리"
    result = validate_content("M2.3", test_content)
    print("Validation result:", result)
