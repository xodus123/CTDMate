"""검증 리포트 생성 도구"""
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def _load_ich_schema() -> Dict[str, Any]:
    """ICH M1/M2 스키마 로드"""
    # CTDMate 프로젝트의 data 폴더에서 스키마 로드
    script_dir = Path(__file__).resolve().parent.parent
    schema_paths = [
        script_dir.parent / "CTDMate" / "data" / "ICH_M1_M2_schema.yaml",
        script_dir / "data" / "ICH_M1_M2_schema.yaml",
        Path(__file__).parent.parent.parent / "CTDMate" / "data" / "ICH_M1_M2_schema.yaml"
    ]

    for schema_path in schema_paths:
        if schema_path.exists():
            try:
                with open(schema_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Failed to load schema from {schema_path}: {e}")

    return {"schema": {}}


def _extract_schema_items(schema_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """스키마에서 모든 검증 항목 추출"""
    items = []
    schema = schema_data.get("schema", {})

    for module_key, module_data in schema.items():
        if module_key.startswith("M"):
            # M1은 items, M2.x는 sections 구조
            if "items" in module_data:
                # M1 형식
                for item in module_data.get("items", []):
                    items.append({
                        "id": item.get("id", ""),
                        "module": module_key,
                        "title": item.get("title", ""),
                        "description": item.get("description", "")
                    })
            elif "sections" in module_data:
                # M2.x 형식
                sections = module_data.get("sections", {})
                _extract_sections_recursive(sections, module_key, items)

    return items


def _extract_sections_recursive(sections: Any, parent_key: str, items: List[Dict[str, Any]]):
    """재귀적으로 섹션 추출"""
    if isinstance(sections, dict):
        for key, value in sections.items():
            if isinstance(value, dict):
                # 제목이 있는 항목
                if "title" in value:
                    section_id = f"{parent_key}.{key}" if not key.startswith(parent_key) else key
                    items.append({
                        "id": section_id,
                        "module": parent_key,
                        "title": value.get("title", ""),
                        "description": value.get("description", "")
                    })
                # 하위 섹션 재귀 탐색
                _extract_sections_recursive(value, f"{parent_key}.{key}", items)


def _check_missing_items(schema_items: List[Dict[str, Any]], document_content: str = "") -> Dict[str, Any]:
    """문서에서 누락된 항목 확인"""
    missing_items = []
    found_items = []

    for item in schema_items:
        item_id = item.get("id", "")
        title = item.get("title", "")

        # 간단한 키워드 매칭 (실제로는 더 정교한 파싱 필요)
        # 문서 내용이 있으면 검색, 없으면 모두 누락으로 처리
        if document_content:
            # ID나 제목이 문서에 있는지 확인
            if item_id.lower() in document_content.lower() or title in document_content:
                found_items.append(item)
            else:
                missing_items.append(item)
        else:
            # 문서 내용이 없으면 모두 누락
            missing_items.append(item)

    return {
        "total_required": len(schema_items),
        "found": len(found_items),
        "missing": len(missing_items),
        "missing_items": missing_items,
        "found_items": found_items
    }


def generate_validation_report(
    output_dir: str = "output",
    output_format: str = "markdown",
    document_content: str = ""
) -> Dict[str, Any]:
    """
    검증 결과를 기반으로 리포트 생성 (ICH 스키마 기반 누락 항목 포함)

    Args:
        output_dir: 출력 디렉토리
        output_format: 출력 형식 (markdown, json)
        document_content: 검증할 문서 내용 (선택사항)

    Returns:
        리포트 생성 결과
    """
    try:
        # 디버깅: 문서 내용 확인
        print(f"\n{'='*80}")
        print(f"📄 VALIDATION REPORT GENERATION")
        print(f"{'='*80}")
        print(f"Document content length: {len(document_content)} chars")
        if document_content:
            print(f"First 200 chars: {document_content[:200]}")
        else:
            print("⚠️  WARNING: No document content provided!")
        print(f"{'='*80}\n")
        # 출력 디렉토리 생성
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)

        # 타임스탬프
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 파일명
        if output_format == "markdown":
            report_filename = f"validation_report_{timestamp}.md"
        else:
            report_filename = f"validation_report_{timestamp}.json"

        report_path = output_path / report_filename

        # ICH 스키마 로드 및 검증
        schema_data = _load_ich_schema()
        schema_items = _extract_schema_items(schema_data)
        missing_check = _check_missing_items(schema_items, document_content)

        # 기본 리포트 구조
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": missing_check["total_required"],
                "passed": missing_check["found"],
                "failed": missing_check["missing"],
                "warnings": 0
            },
            "items": [],
            "schema_check": missing_check
        }

        # 검증 YAML 파일이 있으면 읽기
        validation_files = list(output_path.glob("*_validation.yaml"))
        if validation_files:
            import yaml
            for vf in validation_files:
                try:
                    with open(vf, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict):
                            # 검증 결과 추출
                            if "validation" in data:
                                validation = data["validation"]
                                report_data["summary"]["total"] += 1
                                if validation.get("pass", False):
                                    report_data["summary"]["passed"] += 1
                                else:
                                    report_data["summary"]["failed"] += 1

                                report_data["items"].append({
                                    "file": vf.name,
                                    "status": "passed" if validation.get("pass") else "failed",
                                    "issues": validation.get("issues", [])
                                })
                except Exception as e:
                    print(f"Warning: Failed to read {vf}: {e}")

        # 리포트 작성
        if output_format == "markdown":
            content = _generate_markdown_report(report_data)
        else:
            content = json.dumps(report_data, ensure_ascii=False, indent=2)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {
            "ok": True,
            "report_path": str(report_path),
            "summary": report_data["summary"],
            "schema_check": report_data.get("schema_check", missing_check),
            "message": f"Validation report generated: {report_path}"
        }

    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to generate validation report: {str(e)}"
        }


def _generate_markdown_report(data: Dict[str, Any]) -> str:
    """마크다운 리포트 생성 (ICH 스키마 기반 누락 항목 포함)"""
    lines = [
        "# CTD Validation Report",
        "",
        f"**Generated:** {data['timestamp']}",
        "",
        "## Summary",
        "",
        f"- **Total Required Items (ICH):** {data['summary']['total']}",
        f"- **Found:** ✅ {data['summary']['passed']}",
        f"- **Missing:** ❌ {data['summary']['failed']}",
        f"- **Warnings:** ⚠️ {data['summary']['warnings']}",
        "",
    ]

    # ICH 스키마 기반 누락 항목
    if "schema_check" in data:
        schema_check = data["schema_check"]
        lines.extend([
            "## ICH M1/M2 Schema Compliance",
            "",
            f"**Completeness:** {schema_check['found']}/{schema_check['total_required']} items found",
            ""
        ])

        # 누락된 항목 표시
        if schema_check.get("missing_items"):
            lines.extend([
                "### ❌ Missing Required Items",
                ""
            ])

            # 모듈별로 그룹화
            missing_by_module = {}
            for item in schema_check["missing_items"]:
                module = item.get("module", "Unknown")
                if module not in missing_by_module:
                    missing_by_module[module] = []
                missing_by_module[module].append(item)

            for module, items in sorted(missing_by_module.items()):
                lines.append(f"#### {module}")
                lines.append("")
                for item in items:
                    item_id = item.get("id", "")
                    title = item.get("title", "No title")
                    description = item.get("description", "")
                    lines.append(f"- **{item_id}**: {title}")
                    if description:
                        # 설명의 첫 100자만 표시
                        desc_preview = description[:100] + "..." if len(description) > 100 else description
                        lines.append(f"  - {desc_preview}")
                lines.append("")

        # 발견된 항목 표시
        if schema_check.get("found_items"):
            lines.extend([
                "### ✅ Found Items",
                ""
            ])

            # 모듈별로 그룹화
            found_by_module = {}
            for item in schema_check["found_items"]:
                module = item.get("module", "Unknown")
                if module not in found_by_module:
                    found_by_module[module] = []
                found_by_module[module].append(item)

            for module, items in sorted(found_by_module.items()):
                lines.append(f"#### {module}")
                lines.append("")
                for item in items:
                    item_id = item.get("id", "")
                    title = item.get("title", "No title")
                    lines.append(f"- **{item_id}**: {title}")
                lines.append("")

    # 기존 검증 결과
    if data.get("items"):
        lines.extend([
            "## Validation Results",
            ""
        ])

        for i, item in enumerate(data["items"], 1):
            status_icon = "✅" if item["status"] == "passed" else "❌"
            lines.append(f"### {i}. {item['file']} {status_icon}")
            lines.append("")
            lines.append(f"**Status:** {item['status'].upper()}")

            if item.get("issues"):
                lines.append("")
                lines.append("**Issues:**")
                for issue in item["issues"]:
                    lines.append(f"- {issue}")
            else:
                lines.append("")
                lines.append("*No issues found.*")

            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Report generated by CTDAgent validation system*")
    lines.append("")
    lines.append("**Note:** This report is based on ICH M1/M2 schema compliance checking.")

    return "\n".join(lines)


if __name__ == "__main__":
    # 테스트
    result = generate_validation_report(output_dir="output", output_format="markdown")
    print(json.dumps(result, ensure_ascii=False, indent=2))
