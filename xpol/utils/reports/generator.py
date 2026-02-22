"""PDF report generation utilities."""

import os
from datetime import datetime
from typing import List, Dict, Optional
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image as RLImage,
)

from ...types import DashboardData, AuditResult, OptimizationRecommendation
from ..helpers import format_currency, format_percentage, calculate_percentage_change
from ..visualizations import ChartGenerator


def get_pdf_styles():
    """Get styled paragraph styles for PDF."""
    styles = getSampleStyleSheet()
    
    # Title style
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a73e8'),
        spaceAfter=30,
        alignment=1,  # Center
    ))
    
    # Chapter style
    styles.add(ParagraphStyle(
        name='CustomChapter',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a73e8'),
        spaceAfter=12,
        spaceBefore=12,
        backgroundColor=colors.HexColor('#e8f0fe'),
    ))
    
    # Section style
    styles.add(ParagraphStyle(
        name='CustomSection',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1a73e8'),
        spaceAfter=10,
        spaceBefore=10,
    ))
    
    return styles


class ReportGenerator:
    """Generate PDF reports for FinOps dashboard."""
    
    def __init__(self, output_dir: str = "."):
        """Initialize report generator.
        
        Args:
            output_dir: Output directory for reports
        """
        self.output_dir = output_dir
        self.chart_generator = ChartGenerator()
        self.styles = get_pdf_styles()
    
    def generate_report(
        self,
        data: DashboardData,
        output_filename: str = "gcp-finops-report.pdf"
    ) -> str:
        """Generate complete PDF report.
        
        Args:
            data: Dashboard data
            output_filename: Output PDF filename (full path or filename)
        
        Returns:
            Path to generated PDF
        """
        # If output_filename is already a full path, use it; otherwise join with output_dir
        if os.path.isabs(output_filename):
            output_path = output_filename
        else:
            output_path = os.path.join(self.output_dir, output_filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch,
        )
        
        # Build story (content)
        story = []
        
        # Add header
        story.append(Paragraph("GCP FinOps Dashboard Report", self.styles['CustomTitle']))
        story.append(Paragraph(f"Project: {data.project_id}", self.styles['Normal']))
        story.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 0.3*inch))
        
        # Executive Summary
        self._add_executive_summary(story, data)
        
        # Cost Summary
        self._add_cost_summary(story, data)
        
        # Service Breakdown
        self._add_service_breakdown(story, data.service_costs)
        
        # Budget Alerts
        if data.budget_alerts:
            self._add_budget_alerts(story, data.budget_alerts)
        
        # Audit Results
        self._add_audit_results(story, data.audit_results)
        
        # Recommendations
        self._add_recommendations(story, data.recommendations)
        
        # Add charts
        self._add_charts(story, data)
        
        # Build PDF
        doc.build(story)
        
        return output_path
    
    def _add_executive_summary(self, story: List, data: DashboardData) -> None:
        """Add executive summary section."""
        story.append(Paragraph("Executive Summary", self.styles['CustomChapter']))
        
        change = calculate_percentage_change(data.current_month_cost, data.last_month_cost)
        change_text = "increased" if change > 0 else "decreased" if change < 0 else "remained stable"
        
        summary_text = (
            f"This report provides a comprehensive analysis of GCP costs and optimization "
            f"opportunities for project '{data.project_id}'. "
            f"<br/><br/>"
            f"Current month spending: <b>{format_currency(data.current_month_cost)}</b> "
            f"({change_text} by {format_percentage(abs(change))} from last month). "
            f"<br/><br/>"
            f"Total potential monthly savings identified: <b>{format_currency(data.total_potential_savings)}</b> "
            f"({format_currency(data.total_potential_savings * 12)}/year)."
        )
        
        story.append(Paragraph(summary_text, self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
    
    def _add_cost_summary(self, story: List, data: DashboardData) -> None:
        """Add cost summary section."""
        story.append(Paragraph("Cost Summary", self.styles['CustomChapter']))
        
        change = calculate_percentage_change(data.current_month_cost, data.last_month_cost)
        
        # Create table data
        table_data = [
            [Paragraph("<b>Metric</b>", self.styles['Normal']), 
             Paragraph("<b>Value</b>", self.styles['Normal'])],
            ["Current Month", format_currency(data.current_month_cost)],
            ["Last Month", format_currency(data.last_month_cost)],
            ["Change", f"{'+' if change > 0 else ''}{format_percentage(change)}"],
            ["Year-to-Date", format_currency(data.ytd_cost)],
        ]
        
        # Create table
        table = Table(table_data, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f0fe')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
    
    def _add_service_breakdown(self, story: List, service_costs: Dict[str, float]) -> None:
        """Add service breakdown section."""
        if not service_costs:
            return
        
        story.append(Paragraph("Service Cost Breakdown", self.styles['CustomChapter']))
        
        total = sum(service_costs.values())
        
        # Create table data
        table_data = [
            [Paragraph("<b>#</b>", self.styles['Normal']),
             Paragraph("<b>Service</b>", self.styles['Normal']),
             Paragraph("<b>Cost</b>", self.styles['Normal']),
             Paragraph("<b>% of Total</b>", self.styles['Normal'])]
        ]
        
        for i, (service, cost) in enumerate(sorted(service_costs.items(), key=lambda x: x[1], reverse=True), 1):
            percentage = (cost / total) * 100 if total > 0 else 0
            # Truncate long service names and wrap in Paragraph for proper wrapping
            service_name = service[:60] if len(service) > 60 else service
            table_data.append([
                str(i),
                Paragraph(service_name, self.styles['Normal']),
                format_currency(cost),
                format_percentage(percentage)
            ])
        
        # Create table with proper column widths
        table = Table(table_data, colWidths=[0.4*inch, 3.5*inch, 1.3*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f0fe')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # # column centered
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),    # Service column left
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),  # Cost and % columns right
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
    
    def _add_audit_results(self, story: List, audit_results: Dict[str, AuditResult]) -> None:
        """Add audit results section."""
        if not audit_results:
            return
        
        story.append(Paragraph("Resource Audit Summary", self.styles['CustomChapter']))
        
        # Create table data
        table_data = [
            [Paragraph("<b>Resource Type</b>", self.styles['Normal']),
             Paragraph("<b>Total</b>", self.styles['Normal']),
             Paragraph("<b>Untag</b>", self.styles['Normal']),
             Paragraph("<b>Idle</b>", self.styles['Normal']),
             Paragraph("<b>Savings/mo</b>", self.styles['Normal'])]
        ]
        
        for resource_type, result in audit_results.items():
            resource_name = resource_type.replace("_", " ").title()
            if len(resource_name) > 30:
                resource_name = resource_name[:27] + "..."
            
            table_data.append([
                Paragraph(resource_name, self.styles['Normal']),
                str(result.total_count),
                str(result.untagged_count),
                str(result.idle_count),
                format_currency(result.potential_monthly_savings)
            ])
        
        # Create table with proper column widths
        table = Table(table_data, colWidths=[2.2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1.6*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f0fe')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),     # Resource Type column left
            ('ALIGN', (1, 0), (3, -1), 'CENTER'),   # Count columns centered
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),    # Savings column right
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
    
    def _add_budget_alerts(self, story: List, alerts) -> None:
        """Add budget alerts section."""
        if not alerts:
            return
        
        # Filter to only show triggered alerts
        triggered_alerts = [a for a in alerts if a.spend_percentage >= a.threshold_percent]
        if not triggered_alerts:
            return
        
        story.append(Paragraph("Budget Alerts", self.styles['CustomChapter']))
        
        # Create table data
        table_data = [
            [Paragraph("<b>Budget Name</b>", self.styles['Normal']),
             Paragraph("<b>Threshold</b>", self.styles['Normal']),
             Paragraph("<b>Current Spend</b>", self.styles['Normal']),
             Paragraph("<b>Budget Amount</b>", self.styles['Normal']),
             Paragraph("<b>Status</b>", self.styles['Normal'])]
        ]
        
        for alert in triggered_alerts:
            status = "BREACHED" if alert.is_breached else "WARNING" if alert.spend_percentage >= 90 else "ALERT"
            status_color = colors.HexColor('#ea4335') if alert.is_breached else colors.HexColor('#fbbc04') if alert.spend_percentage >= 90 else colors.HexColor('#34a853')
            
            table_data.append([
                Paragraph(alert.budget_name[:40], self.styles['Normal']),
                f"{alert.threshold_percent:.0f}%",
                format_currency(alert.current_spend),
                format_currency(alert.budget_amount),
                Paragraph(f"<font color='{status_color.hexval()}'>{status}</font>", self.styles['Normal'])
            ])
        
        # Create table
        table = Table(table_data, colWidths=[2*inch, 1*inch, 1.2*inch, 1.2*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f0fe')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),     # Budget Name column left
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),     # Threshold column centered
            ('ALIGN', (2, 0), (3, -1), 'RIGHT'),     # Cost columns right
            ('ALIGN', (4, 0), (4, -1), 'CENTER'),    # Status column centered
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
    
    def _add_recommendations(self, story: List, recommendations: List[OptimizationRecommendation]) -> None:
        """Add recommendations section."""
        if not recommendations:
            return
        
        story.append(PageBreak())
        story.append(Paragraph("Optimization Recommendations", self.styles['CustomChapter']))
        
        # Sort by savings
        sorted_recs = sorted(recommendations, key=lambda r: r.potential_monthly_savings, reverse=True)
        
        for i, rec in enumerate(sorted_recs[:20], 1):  # Top 20 recommendations
            # Section title
            story.append(Paragraph(
                f"{i}. {rec.resource_name} ({rec.region})",
                self.styles['CustomSection']
            ))
            
            # Issue and recommendation
            issue_text = f"<b>Issue:</b> {rec.issue}"
            rec_text = f"<b>Recommendation:</b> {rec.recommendation}"
            savings_text = f"<b>Potential Savings:</b> {format_currency(rec.potential_monthly_savings)}/month"
            
            story.append(Paragraph(issue_text, self.styles['Normal']))
            story.append(Paragraph(rec_text, self.styles['Normal']))
            story.append(Paragraph(savings_text, self.styles['Normal']))
            story.append(Spacer(1, 0.15*inch))
    
    def _add_charts(self, story: List, data: DashboardData) -> None:
        """Add charts to PDF."""
        story.append(PageBreak())
        story.append(Paragraph("Cost Visualizations", self.styles['CustomChapter']))
        
        # Get absolute path for output directory
        output_dir_abs = os.path.abspath(self.output_dir)
        
        # Service breakdown pie chart
        if data.service_costs:
            chart_path = None
            try:
                fig = self.chart_generator.create_service_breakdown_chart(data.service_costs)
                chart_path = os.path.join(output_dir_abs, "temp_service_chart.png")
                fig.write_image(chart_path, width=800, height=500)
                
                if os.path.exists(chart_path):
                    # Load image into memory to avoid file access issues
                    with open(chart_path, 'rb') as img_file:
                        img_data = img_file.read()
                    
                    img_buffer = BytesIO(img_data)
                    img = RLImage(img_buffer, width=6*inch, height=3.75*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.2*inch))
            except Exception as e:
                # If chart generation fails, add a note instead
                story.append(Paragraph(
                    f"<i>Service breakdown chart could not be generated: {str(e)}</i>",
                    self.styles['Normal']
                ))
                story.append(Spacer(1, 0.2*inch))
            finally:
                # Clean up temp file
                if chart_path and os.path.exists(chart_path):
                    try:
                        os.remove(chart_path)
                    except:
                        pass
        
        # Savings chart
        if data.audit_results:
            chart_path = None
            try:
                story.append(PageBreak())
                fig = self.chart_generator.create_savings_chart(data.audit_results)
                chart_path = os.path.join(output_dir_abs, "temp_savings_chart.png")
                fig.write_image(chart_path, width=800, height=500)
                
                if os.path.exists(chart_path):
                    # Load image into memory to avoid file access issues
                    with open(chart_path, 'rb') as img_file:
                        img_data = img_file.read()
                    
                    img_buffer = BytesIO(img_data)
                    img = RLImage(img_buffer, width=6*inch, height=3.75*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.2*inch))
            except Exception as e:
                # If chart generation fails, add a note instead
                story.append(Paragraph(
                    f"<i>Savings chart could not be generated: {str(e)}</i>",
                    self.styles['Normal']
                ))
                story.append(Spacer(1, 0.2*inch))
            finally:
                # Clean up temp file
                if chart_path and os.path.exists(chart_path):
                    try:
                        os.remove(chart_path)
                    except:
                        pass
