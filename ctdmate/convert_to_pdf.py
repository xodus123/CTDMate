#!/usr/bin/env python
"""YAML 파일들을 CTD 형식 PDF로 변환"""
import sys
from pathlib import Path
import yaml

# 프로젝트 루트를 Python path에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def yaml_to_markdown(yaml_file: Path) -> str:
    """YAML 파일을 마크다운으로 변환"""
    with open(yaml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # YAML 코드 블록 제거 (```yaml ... ```)
    if content.strip().startswith('```yaml'):
        lines = content.split('\n')
        # 첫 줄(```yaml)과 마지막 줄(```) 제거
        content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content

    # YAML을 파싱해서 보기 좋게 변환
    try:
        data = yaml.safe_load(content)
        return format_yaml_as_markdown(data)
    except:
        # YAML 파싱 실패시 원본 반환
        return content

def format_yaml_as_markdown(data, level=0) -> str:
    """YAML 데이터를 마크다운 형식으로 변환"""
    lines = []
    indent = "  " * level

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{indent}**{key}:**\n")
                lines.append(format_yaml_as_markdown(value, level + 1))
            elif isinstance(value, list):
                lines.append(f"{indent}**{key}:**\n")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(format_yaml_as_markdown(item, level + 1))
                    else:
                        lines.append(f"{indent}- {item}\n")
            else:
                lines.append(f"{indent}**{key}:** {value}\n")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                lines.append(format_yaml_as_markdown(item, level))
            else:
                lines.append(f"{indent}- {item}\n")
    else:
        lines.append(f"{indent}{data}\n")

    return "".join(lines)

def create_ctd_pdf(output_dir: Path, pdf_path: Path):
    """CTD YAML 파일들을 하나의 PDF로 통합"""

    # CTD 모듈 순서
    modules = [
        ("M1.yaml", "제1부 행정정보 및 처방정보"),
        ("M2_3.yaml", "제2부 - 2.3 품질평가자료요약"),
        ("M2_4.yaml", "제2부 - 2.4 비임상시험자료개요"),
        ("M2_5.yaml", "제2부 - 2.5 임상시험자료개요"),
        ("M2_6.yaml", "제2부 - 2.6 비임상시험자료요약문"),
        ("M2_7.yaml", "제2부 - 2.7 임상시험자료요약"),
    ]

    # 통합 마크다운 생성
    markdown_parts = []
    markdown_parts.append("# 국제공통기술문서(CTD) - TM-5 용액\n\n")
    markdown_parts.append("---\n\n")

    for filename, title in modules:
        file_path = output_dir / filename
        if file_path.exists():
            print(f"  ✓ {filename} 처리 중...")
            markdown_parts.append(f"\n\n# {title}\n\n")
            markdown_parts.append("---\n\n")

            # YAML 내용 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # ```yaml 코드 블록 제거
            if content.strip().startswith('```yaml'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content

            markdown_parts.append(content)
            markdown_parts.append("\n\n")
        else:
            print(f"  ⚠️  {filename} 파일을 찾을 수 없습니다.")

    full_markdown = "".join(markdown_parts)

    # PDF 생성
    print(f"\n[PDF 생성 중...]")
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.units import inch
        import os

        # 한글 폰트 등록 시도
        font_name = "Helvetica"
        font_path = os.getenv("PDF_TTF", "")

        if font_path and Path(font_path).exists():
            try:
                pdfmetrics.registerFont(TTFont("KoreanFont", font_path))
                font_name = "KoreanFont"
                print(f"  ✓ 한글 폰트 적용: {font_path}")
            except:
                print(f"  ⚠️  한글 폰트 로드 실패, 기본 폰트 사용")

        # PDF 문서 생성
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=50,
            rightMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        # 스타일 설정
        styles = getSampleStyleSheet()
        story = []

        # 마크다운을 줄 단위로 처리
        lines = full_markdown.split('\n')
        for line in lines:
            if not line.strip():
                story.append(Spacer(1, 0.1*inch))
                continue

            # 간단한 마크다운 처리
            if line.startswith('# '):
                # 제목
                text = line.replace('# ', '')
                para = Paragraph(f"<b>{text}</b>", styles['Title'])
                story.append(para)
                story.append(Spacer(1, 0.2*inch))
            elif line.startswith('## '):
                # 소제목
                text = line.replace('## ', '')
                para = Paragraph(f"<b>{text}</b>", styles['Heading1'])
                story.append(para)
                story.append(Spacer(1, 0.1*inch))
            elif line.startswith('### '):
                # 작은 제목
                text = line.replace('### ', '')
                para = Paragraph(f"<b>{text}</b>", styles['Heading2'])
                story.append(para)
            elif line.startswith('---'):
                # 구분선
                story.append(Spacer(1, 0.1*inch))
            else:
                # 일반 텍스트
                # 볼드 처리
                text = line.replace('**', '<b>', 1)
                if '<b>' in text:
                    text = text.replace('**', '</b>', 1)

                try:
                    para = Paragraph(text, styles['Normal'])
                    story.append(para)
                except:
                    # 특수문자 처리 실패시 원본 사용
                    pass

        # PDF 빌드
        doc.build(story)
        print(f"✅ PDF 생성 완료: {pdf_path}")
        print(f"   크기: {pdf_path.stat().st_size / 1024:.1f} KB")

    except Exception as e:
        print(f"❌ PDF 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

def main():
    """메인 함수"""
    print("=" * 70)
    print("CTD YAML → PDF 변환")
    print("=" * 70)

    # 경로 설정
    output_dir = PROJECT_ROOT / "ctdmate" / "output"
    pdf_path = output_dir / "CTD_Complete.pdf"

    if not output_dir.exists():
        print(f"❌ 오류: output 디렉토리를 찾을 수 없습니다: {output_dir}")
        return 1

    print(f"\n입력 디렉토리: {output_dir}")
    print(f"출력 PDF: {pdf_path}\n")

    # PDF 생성
    success = create_ctd_pdf(output_dir, pdf_path)

    print("\n" + "=" * 70)
    if success:
        print("변환 완료!")
        print(f"PDF 파일: {pdf_path}")
    else:
        print("변환 실패")
    print("=" * 70)

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
