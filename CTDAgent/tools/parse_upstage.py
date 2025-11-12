"""Upstage Document Parse 도구 (ctdmate 통합)"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# ctdmate 모듈 임포트를 위한 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ctdmate.tools.smartdoc_upstage import run as upstage_parse_run
    UPSTAGE_AVAILABLE = True
except Exception as e:
    print(f"Warning: Upstage parser not available: {e}")
    UPSTAGE_AVAILABLE = False


def parse_documents(file_paths: Optional[List[str]] = None,
                   texts: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Upstage Document Parse로 파일 파싱

    Args:
        file_paths: 파싱할 파일 경로 리스트
        texts: 텍스트 리스트 (현재 미사용)

    Returns:
        파싱 결과 딕셔너리
    """
    if not UPSTAGE_AVAILABLE:
        return {
            "ok": False,
            "error": "Upstage parser not available",
            "results": []
        }

    if not file_paths:
        return {
            "ok": False,
            "error": "No files provided",
            "results": []
        }

    try:
        result = upstage_parse_run(file_paths)
        return {
            "ok": True,
            "results": result.get("results", []),
            "total_files": len(file_paths)
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "results": []
        }


if __name__ == "__main__":
    # 테스트
    test_file = PROJECT_ROOT / "data" / "input" / "TM_5_Admin_Labeling_KR.txt"
    if test_file.exists():
        result = parse_documents([str(test_file)])
        print("Parse result:", result)
