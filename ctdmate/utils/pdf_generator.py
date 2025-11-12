# ctdmate/utils/pdf_generator.py
from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import yaml
import json

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class CTDPDFGenerator:
    """CTD 문서를 PDF로 생성하는 유틸리티"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_pdf(
        self,
        result: Dict[str, Any],
        filename: Optional[str] = None
    ) -> str:
        """CTD 결과를 PDF로 생성"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"CTD_Document_{timestamp}.pdf"

        pdf_path = self.output_dir / filename
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        # 스타일 정의
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c5f7c'),
            spaceAfter=30,
            alignment=TA_CENTER,
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#3d7a99'),
            spaceAfter=12,
            spaceBefore=12,
        )
        normal_style = styles['Normal']

        # 문서 빌드
        story = []

        # 제목
        story.append(Paragraph("CTD Document Generation Report", title_style))
        story.append(Spacer(1, 0.5*cm))

        # 메타 정보
        meta_data = [
            ["Generation Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["Status:", "Success" if result.get("ok") else "Failed"],
        ]

        if result.get("plan"):
            plan = result["plan"]
            meta_data.append(["Section:", plan.get("section", "N/A")])
            meta_data.append(["Format:", plan.get("output_format", "N/A")])

        meta_table = Table(meta_data, colWidths=[5*cm, 10*cm])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.5*cm))

        # 파싱 결과
        if result.get("parse"):
            story.append(Paragraph("1. File Parsing Results", heading_style))
            parse_data = result["parse"]
            if parse_data.get("results"):
                for i, res in enumerate(parse_data["results"], 1):
                    story.append(Paragraph(f"File {i}: {res.get('input', 'N/A')}", normal_style))
                    story.append(Paragraph(f"Pages: {res.get('pages', 0)}", normal_style))
                    story.append(Paragraph(f"Status: {res.get('status', 'N/A')}", normal_style))
                    story.append(Spacer(1, 0.3*cm))
            story.append(Spacer(1, 0.5*cm))

        # 검증 결과
        if result.get("validate"):
            story.append(Paragraph("2. Document Validation Results", heading_style))
            val_data = result["validate"]

            val_summary = [
                ["Validation Status:", "Passed" if val_data.get("pass") else "Failed"],
            ]

            if val_data.get("metrics"):
                metrics = val_data["metrics"]
                val_summary.append(["Score:", f"{metrics.get('score', 0):.2f}"])
                val_summary.append(["Completeness:", f"{metrics.get('completeness', 0):.2f}"])
                val_summary.append(["Compliance:", f"{metrics.get('compliance', 0):.2f}"])

            val_table = Table(val_summary, colWidths=[5*cm, 10*cm])
            val_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ]))
            story.append(val_table)
            story.append(Spacer(1, 0.3*cm))

            # 누락 항목
            if val_data.get("missing_required"):
                story.append(Paragraph("Missing Required Items:", normal_style))
                for item in val_data["missing_required"]:
                    story.append(Paragraph(f"• {item}", normal_style))
                story.append(Spacer(1, 0.3*cm))

            story.append(Spacer(1, 0.5*cm))

        # 생성 결과
        if result.get("generate"):
            story.append(Paragraph("3. Generated CTD Content", heading_style))
            gen_data = result["generate"]

            if gen_data.get("text"):
                text_content = gen_data["text"][:2000]  # 처음 2000자만
                if len(gen_data["text"]) > 2000:
                    text_content += "..."

                # 여러 줄로 나누어 표시
                for line in text_content.split('\n'):
                    if line.strip():
                        story.append(Paragraph(line, normal_style))

            story.append(Spacer(1, 0.5*cm))

            # 생성 메트릭
            if gen_data.get("gen_metrics"):
                story.append(Paragraph("Generation Metrics:", normal_style))
                metrics = gen_data["gen_metrics"]
                for key, value in metrics.items():
                    story.append(Paragraph(f"• {key}: {value}", normal_style))

        # 추적 정보
        if result.get("trace"):
            story.append(PageBreak())
            story.append(Paragraph("Processing Trace", heading_style))

            trace_data = []
            for i, step in enumerate(result["trace"], 1):
                trace_data.append([
                    str(i),
                    step.get("state", "N/A"),
                    "✓" if step.get("ok") else "✗"
                ])

            trace_table = Table(trace_data, colWidths=[2*cm, 8*cm, 2*cm])
            trace_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5f7c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            story.append(trace_table)

        # PDF 생성
        doc.build(story)
        return str(pdf_path)
