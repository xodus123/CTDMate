"""Solar 기반 CTD 생성 도구 (ctdmate 통합)"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ctdmate.tools.gen_solar import SolarGenerator
    SOLAR_AVAILABLE = True
except Exception as e:
    print(f"Warning: Solar generator not available: {e}")
    SOLAR_AVAILABLE = False


# 전역 Solar 생성기 인스턴스
_solar_gen = None


def get_solar_generator():
    """Solar 생성기 인스턴스 가져오기 (싱글톤)"""
    global _solar_gen
    if _solar_gen is None and SOLAR_AVAILABLE:
        try:
            _solar_gen = SolarGenerator(
                enable_rag=True,
                auto_normalize=True,
                output_format="yaml",
            )
        except Exception as e:
            print(f"Warning: Failed to initialize Solar generator: {e}")
    return _solar_gen


def generate_ctd(section: str = "M2.3",
                prompt: str = "",
                output_format: str = "yaml") -> Dict[str, Any]:
    """
    Solar로 CTD 문서 생성

    Args:
        section: CTD 섹션 (M1, M2.3, M2.4, M2.5, M2.6, M2.7)
        prompt: 생성 프롬프트
        output_format: 출력 형식 (yaml 또는 markdown)

    Returns:
        생성 결과 딕셔너리
    """
    solar_gen = get_solar_generator()
    if not solar_gen:
        return {
            "ok": False,
            "error": "Solar generator not available",
            "text": "",
            "section": section
        }

    try:
        result = solar_gen.generate(
            section=section,
            prompt=prompt,
            output_format=output_format
        )
        return {
            "ok": True,
            "text": result.get("text", ""),
            "section": section,
            "format": output_format,
            "rag_used": result.get("rag_used", False),
            "rag_refs": result.get("rag_refs", []),
            "ready": result.get("ready", False)
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "text": "",
            "section": section
        }


def generate_all_modules(excel_path: str, output_dir: str = "output") -> Dict[str, Any]:
    """
    모든 CTD 모듈 생성

    Args:
        excel_path: Excel 파일 경로
        output_dir: 출력 디렉토리

    Returns:
        생성 결과 딕셔너리
    """
    from pathlib import Path
    import json

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Excel 검증
    from .validate_rag import validate_excel
    validate_result = validate_excel(excel_path, auto_fix=True)

    if not validate_result.get("ok"):
        return {
            "ok": False,
            "error": "Validation failed",
            "modules": []
        }

    # 모듈별 생성
    modules = []
    for sheet_result in validate_result.get("results", []):
        module = sheet_result.get("module", "Unknown")
        content = sheet_result.get("normalized_content", "")

        if content:
            gen_result = generate_ctd(
                section=module,
                prompt=content,
                output_format="yaml"
            )

            if gen_result.get("ok"):
                # 파일 저장
                module_file = output_path / f"{module.replace('.', '_')}.yaml"
                with open(module_file, 'w', encoding='utf-8') as f:
                    f.write(gen_result.get("text", ""))

                modules.append({
                    "module": module,
                    "file": str(module_file),
                    "size": len(gen_result.get("text", ""))
                })

    return {
        "ok": True,
        "modules": modules,
        "total": len(modules)
    }


if __name__ == "__main__":
    # 테스트
    test_prompt = "TM-5 용액의 품질평가자료 요약"
    result = generate_ctd("M2.3", test_prompt)
    print("Generation result:", result.get("ok"))
