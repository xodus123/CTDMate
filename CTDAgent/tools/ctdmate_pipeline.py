"""CTDMate Pipeline 직접 호출 래퍼"""
import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ctdmate.pipeline import CTDPipeline
    from ctdmate.convert_to_pdf import create_ctd_pdf
    PIPELINE_AVAILABLE = True
except Exception as e:
    print(f"Warning: CTDMate pipeline not available: {e}")
    PIPELINE_AVAILABLE = False


def generate_ctd_from_excel(excel_path: str, output_dir: str = "output") -> Dict[str, Any]:
    """
    CTDMate 파이프라인으로 Excel에서 전체 CTD 생성

    Args:
        excel_path: Excel 파일 경로
        output_dir: 출력 디렉토리

    Returns:
        생성 결과 딕셔너리
    """
    if not PIPELINE_AVAILABLE:
        return {
            "ok": False,
            "error": "CTDMate pipeline not available"
        }

    try:
        # CTDMate 파이프라인 초기화
        pipe = CTDPipeline(use_finetuned=True)

        # 전체 모듈 생성
        result = pipe.generate_all_modules(
            excel_path=excel_path,
            output_dir=output_dir,
            auto_fix=True
        )

        # PDF 생성
        output_path = Path(output_dir)
        pdf_path = output_path / "CTD_Complete.pdf"

        pdf_result = create_ctd_pdf(output_path, pdf_path)

        return {
            "ok": True,
            "modules": result.get("generate", {}).get("success", []),
            "pdf_path": str(pdf_path) if pdf_result else None,
            "summary": result
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "ok": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # 테스트
    result = generate_ctd_from_excel(
        excel_path="../ctdmate/input/CTD_bundle.xlsx",
        output_dir="output"
    )
    print("Result:", result.get("ok"))
    print("PDF:", result.get("pdf_path"))
