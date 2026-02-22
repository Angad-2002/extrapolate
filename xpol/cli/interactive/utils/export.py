"""Export utilities for saving reports in various formats."""

from typing import Optional, List
from datetime import datetime
from pathlib import Path
import re
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from xpol.utils.reports import ReportGenerator
from xpol.api.config import REPORTS_DIR

console = Console()

def prompt_save_and_export(data: "DashboardData", ai_content: Optional[str] = None, default_base: str = "xpol-report") -> None:
    """Ask user whether to save, and in which formats (txt/pdf).
    
    Args:
        data: Dashboard data
        ai_content: Optional AI-generated content to save (if None, saves dashboard summary)
        default_base: Default base filename
    """
    try:
        save = inquirer.confirm(
            message="Save output to file?",
            default=False,
        ).execute()
        if not save:
            return
        fmt = inquirer.select(
            message="Select format:",
            choices=[
                Choice(value="txt", name="Text (.txt)"),
                Choice(value="pdf", name="PDF (.pdf)"),
                Choice(value="both", name="Both"),
            ],
        ).execute()
        base = inquirer.text(
            message="Base filename (without extension):",
            default=default_base,
        ).execute()
        if not base:
            base = default_base
        
        # Use reports directory for all saved files
        if fmt in ("txt", "both"):
            txt_path = REPORTS_DIR / f"{base}.txt"
            # Save AI content if provided, otherwise save dashboard summary
            if ai_content:
                content = ai_content
            else:
                content = build_text_summary(data)
            txt_path.write_text(content or "", encoding="utf-8")
            console.print(f"[green]✓[/] Saved to [cyan]{txt_path.resolve()}[/]")
        if fmt in ("pdf", "both"):
            pdf_path = REPORTS_DIR / f"{base}.pdf"
            try:
                if ai_content:
                    # Generate simple PDF with AI content
                    generate_ai_pdf(ai_content, data, str(pdf_path))
                else:
                    # Generate full dashboard report
                    ReportGenerator(output_dir=str(REPORTS_DIR)).generate_report(data, str(pdf_path))
                console.print(f"[green]✓[/] Saved to [cyan]{pdf_path.resolve()}[/]")
            except Exception as e:
                console.print(f"[yellow]Could not generate PDF:[/yellow] {e}")
    except Exception as e:
        console.print(f"[yellow]Save skipped:[/yellow] {e}")

def build_text_summary(data: "DashboardData") -> str:
    """Build a plain-text summary from DashboardData."""
    lines: List[str] = []
    lines.append("GCP FinOps Summary")
    lines.append(f"Project: {data.project_id}")
    lines.append(f"Billing Period: {data.billing_month}")
    lines.append("")
    lines.append("Costs:")
    lines.append(f"  Current Month: ${data.current_month_cost:,.2f}")
    lines.append(f"  Last Month:   ${data.last_month_cost:,.2f}")
    lines.append(f"  YTD:          ${data.ytd_cost:,.2f}")
    lines.append("")
    if data.service_costs:
        lines.append("Top Services by Cost:")
        for svc, cost in sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)[:10]:
            lines.append(f"  - {svc}: ${cost:,.2f}")
        lines.append("")
    lines.append("Audit Summary:")
    if data.audit_results:
        for rtype, result in data.audit_results.items():
            lines.append(
                f"  - {rtype.replace('_',' ').title()}: total={result.total_count}, "
                f"untagged={result.untagged_count}, idle={result.idle_count}, "
                f"savings=${result.potential_monthly_savings:,.2f}"
            )
    else:
        lines.append("  (no audit results)")
    lines.append("")
    lines.append(f"Potential Monthly Savings: ${data.total_potential_savings:,.2f}")
    return "\n".join(lines)

def generate_ai_pdf(ai_content: str, data: "DashboardData", output_path: str) -> None:
    """Generate a simple PDF containing the AI-generated content."""
    # Create PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=1*inch,
        bottomMargin=0.75*inch,
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=12,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=8,
        spaceBefore=12,
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    
    # Build story (content)
    story = []
    
    # Add header
    story.append(Paragraph("GCP FinOps AI Report", title_style))
    story.append(Paragraph(f"Project: {data.project_id}", normal_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        normal_style
    ))
    story.append(Spacer(1, 0.3*inch))
    
    # Convert markdown to PDF paragraphs
    lines = ai_content.split('\n')
    current_paragraph = []
    
    for line in lines:
        line = line.strip()
        if not line:
            # Empty line - flush current paragraph
            if current_paragraph:
                text = ' '.join(current_paragraph)
                story.append(Paragraph(escape_html(text), normal_style))
                current_paragraph = []
            story.append(Spacer(1, 6))
        elif line.startswith('##'):
            # Heading level 2
            if current_paragraph:
                text = ' '.join(current_paragraph)
                story.append(Paragraph(escape_html(text), normal_style))
                current_paragraph = []
            heading_text = line.replace('##', '').strip()
            story.append(Paragraph(escape_html(heading_text), heading_style))
        elif line.startswith('#'):
            # Heading level 1
            if current_paragraph:
                text = ' '.join(current_paragraph)
                story.append(Paragraph(escape_html(text), normal_style))
                current_paragraph = []
            heading_text = line.replace('#', '').strip()
            story.append(Paragraph(escape_html(heading_text), title_style))
        elif line.startswith('- ') or line.startswith('* '):
            # Bullet point
            if current_paragraph:
                text = ' '.join(current_paragraph)
                story.append(Paragraph(escape_html(text), normal_style))
                current_paragraph = []
            bullet_text = line[2:].strip()
            story.append(Paragraph(f"• {escape_html(bullet_text)}", normal_style))
        elif line.startswith('1. ') or re.match(r'^\d+\.\s', line):
            # Numbered list
            if current_paragraph:
                text = ' '.join(current_paragraph)
                story.append(Paragraph(escape_html(text), normal_style))
                current_paragraph = []
            story.append(Paragraph(escape_html(line.strip()), normal_style))
        else:
            # Regular text
            current_paragraph.append(line)
    
    # Flush remaining paragraph
    if current_paragraph:
        text = ' '.join(current_paragraph)
        story.append(Paragraph(escape_html(text), normal_style))
    
    # Build PDF
    doc.build(story)

def escape_html(text: str) -> str:
    """Escape HTML special characters for PDF generation."""
    # Basic HTML escaping
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    # Handle bold markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Handle code blocks (simple)
    text = re.sub(r'`([^`]+)`', r'<font name="Courier">\1</font>', text)
    return text

