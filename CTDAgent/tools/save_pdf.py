"""PDF 저장 도구"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import time
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _generate_single_pdf(output_path: Path, module_order: List[tuple],
                        pdf_filename: str, title: str) -> Dict[str, Any]:
    """
    단일 PDF 생성 (헬퍼 함수)

    Args:
        output_path: 출력 디렉토리 Path 객체
        module_order: (파일명, 제목) 튜플 리스트
        pdf_filename: PDF 파일명
        title: PDF 문서 제목

    Returns:
        생성 결과 딕셔너리
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
    except ImportError:
        return {
            "ok": False,
            "error": "reportlab not installed",
            "path": None
        }

    pdf_path = output_path / pdf_filename

    # 통합 마크다운 생성
    markdown_parts = []
    markdown_parts.append(f"# {title}\n\n")
    markdown_parts.append("---\n\n")

    for filename_pattern, section_title in module_order:
        file_path = output_path / filename_pattern
        if file_path.exists():
            markdown_parts.append(f"\n\n# {section_title}\n\n")
            markdown_parts.append("---\n\n")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # ```yaml 코드 블록 제거
            if content.strip().startswith('```yaml'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content

            markdown_parts.append(content)
            markdown_parts.append("\n\n")

    full_markdown = "".join(markdown_parts)

    # PDF 생성
    try:
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=50,
            rightMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        styles = getSampleStyleSheet()
        story = []

        lines = full_markdown.split('\n')
        for line in lines:
            if not line.strip():
                story.append(Spacer(1, 0.1*inch))
                continue

            if line.startswith('# '):
                text = line.replace('# ', '')
                para = Paragraph(f"<b>{text}</b>", styles['Title'])
                story.append(para)
                story.append(Spacer(1, 0.2*inch))
            elif line.startswith('## '):
                text = line.replace('## ', '')
                para = Paragraph(f"<b>{text}</b>", styles['Heading1'])
                story.append(para)
                story.append(Spacer(1, 0.1*inch))
            elif line.startswith('### '):
                text = line.replace('### ', '')
                para = Paragraph(f"<b>{text}</b>", styles['Heading2'])
                story.append(para)
            elif line.startswith('---'):
                story.append(Spacer(1, 0.1*inch))
            else:
                text = line.replace('**', '<b>', 1)
                if '<b>' in text:
                    text = text.replace('**', '</b>', 1)

                try:
                    para = Paragraph(text, styles['Normal'])
                    story.append(para)
                except:
                    pass

        doc.build(story)

        return {
            "ok": True,
            "path": str(pdf_path),
            "size": pdf_path.stat().st_size
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "path": None
        }


def save_as_pdf(yaml_files: Optional[List[str]] = None,
                output_dir: str = "output",
                filename: str = "CTD_Complete2.pdf") -> Dict[str, Any]:
    """
    YAML 파일들을 PDF로 변환 (전체 통합본 + Module 2 별도본)

    Args:
        yaml_files: YAML 파일 경로 리스트
        output_dir: 출력 디렉토리
        filename: PDF 파일명

    Returns:
        저장 결과 딕셔너리 (전체 PDF + Module 2 PDF 경로 포함)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # CTD 전체 모듈 순서
    full_module_order = [
        ("M1.yaml", "제1부 행정정보"),
        ("M2_3.yaml", "제2부 - 2.3 품질평가자료요약"),
        ("M2_4.yaml", "제2부 - 2.4 비임상시험자료개요"),
        ("M2_5.yaml", "제2부 - 2.5 임상시험자료개요"),
        ("M2_6.yaml", "제2부 - 2.6 비임상시험자료요약문"),
        ("M2_7.yaml", "제2부 - 2.7 임상시험자료요약"),
    ]

    # Module 2만 (M2.3 ~ M2.7)
    module2_order = [
        ("M2_3.yaml", "제2부 - 2.3 품질평가자료요약"),
        ("M2_4.yaml", "제2부 - 2.4 비임상시험자료개요"),
        ("M2_5.yaml", "제2부 - 2.5 임상시험자료개요"),
        ("M2_6.yaml", "제2부 - 2.6 비임상시험자료요약문"),
        ("M2_7.yaml", "제2부 - 2.7 임상시험자료요약"),
    ]

    # 1. 전체 통합 PDF 생성
    print(f"\n{'='*80}")
    print(f"📄 GENERATING COMPLETE PDF")
    print(f"{'='*80}")
    complete_result = _generate_single_pdf(
        output_path,
        full_module_order,
        filename,
        "국제공통기술문서(CTD) - TM-5 용액"
    )

    if not complete_result["ok"]:
        return complete_result

    print(f"✅ Complete PDF generated: {complete_result['path']}")
    print(f"   Size: {complete_result['size']:,} bytes\n")

    # 2. Module 2 전용 PDF 생성
    print(f"{'='*80}")
    print(f"📄 GENERATING MODULE 2 PDF")
    print(f"{'='*80}")
    module2_filename = "CTD_Module2_Complete2.pdf"
    module2_result = _generate_single_pdf(
        output_path,
        module2_order,
        module2_filename,
        "국제공통기술문서(CTD) - 제2부 (Module 2)"
    )

    if module2_result["ok"]:
        print(f"✅ Module 2 PDF generated: {module2_result['path']}")
        print(f"   Size: {module2_result['size']:,} bytes\n")
    else:
        print(f"⚠️  Module 2 PDF generation failed: {module2_result.get('error', 'Unknown error')}\n")

    # 결과 반환 (두 PDF 모두 포함)
    return {
        "ok": True,
        "path": complete_result["path"],
        "size": complete_result["size"],
        "module2_path": module2_result.get("path") if module2_result["ok"] else None,
        "module2_size": module2_result.get("size") if module2_result["ok"] else None,
        "message": f"Generated 2 PDFs: {filename} and {module2_filename}"
    }


if __name__ == "__main__":
    # 테스트
    result = save_as_pdf(output_dir="../output")
    print("PDF save result:", result)
