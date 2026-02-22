"""Plotly chart generation utilities."""

from typing import Dict, List
import plotly.graph_objects as go

from xpol.types import AuditResult


class ChartGenerator:
    """Generate Plotly charts for reports."""
    
    @staticmethod
    def create_cost_trend_chart(monthly_data: List[tuple], service_name: str = "Total") -> go.Figure:
        """Create cost trend chart.
        
        Args:
            monthly_data: List of (month, cost) tuples
            service_name: Service name for chart title
        
        Returns:
            Plotly figure
        """
        if not monthly_data:
            return go.Figure()
        
        months = [m[0] for m in monthly_data]
        costs = [m[1] for m in monthly_data]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=months,
            y=costs,
            mode='lines+markers',
            name=service_name,
            line=dict(color='#00bfff', width=3),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title=f"{service_name} - Monthly Cost Trend",
            xaxis_title="Month",
            yaxis_title="Cost (USD)",
            template="plotly_white",
            hovermode='x unified'
        )
        
        return fig
    
    @staticmethod
    def create_service_breakdown_chart(service_costs: Dict[str, float]) -> go.Figure:
        """Create service cost breakdown pie chart.
        
        Args:
            service_costs: Dictionary of service names to costs
        
        Returns:
            Plotly figure
        """
        if not service_costs:
            return go.Figure()
        
        labels = list(service_costs.keys())
        values = list(service_costs.values())
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.3,
            textinfo='label+percent',
            textposition='outside'
        )])
        
        fig.update_layout(
            title="Cost Breakdown by Service",
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_savings_chart(audit_results: Dict[str, AuditResult]) -> go.Figure:
        """Create potential savings bar chart.
        
        Args:
            audit_results: Dictionary of audit results
        
        Returns:
            Plotly figure
        """
        if not audit_results:
            return go.Figure()
        
        resources = [r.replace("_", " ").title() for r in audit_results.keys()]
        savings = [result.potential_monthly_savings for result in audit_results.values()]
        
        fig = go.Figure(data=[go.Bar(
            x=resources,
            y=savings,
            marker_color='lightgreen'
        )])
        
        fig.update_layout(
            title="Potential Monthly Savings by Resource Type",
            xaxis_title="Resource Type",
            yaxis_title="Potential Savings (USD/month)",
            template="plotly_white"
        )
        
        return fig

