"""Main LLM service that delegates to provider implementations."""

import os
from typing import Optional, Dict, Any, List, AsyncIterator
from xpol.services.llm.providers import PROVIDERS, get_available_providers, get_available_models
from xpol.services.llm.providers.base import BaseLLMProvider
from xpol.types import DashboardData, AuditResult, OptimizationRecommendation
from xpol.utils.helpers import calculate_percentage_change


class LLMService:
    """Service for AI-powered insights using multiple AI providers."""
    
    DEFAULT_PROVIDER = "groq"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    
    def __init__(self, provider: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the LLM service with specified provider."""
        # Get provider from parameter, environment variable, or use default
        self.provider_name = provider or os.getenv("AI_PROVIDER") or self.DEFAULT_PROVIDER
        
        # Validate provider
        if self.provider_name not in PROVIDERS:
            raise ValueError(f"Invalid provider '{self.provider_name}'. Available: {', '.join(PROVIDERS.keys())}")
        
        provider_config = PROVIDERS[self.provider_name]
        provider_class = provider_config["class"]
        
        if not provider_class.is_available():
            raise ValueError(f"Provider '{self.provider_name}' is not available. Install required package.")
        
        # Get API key from parameter or environment
        if self.provider_name == "groq":
            api_key_env = os.getenv("GROQ_API_KEY")
        elif self.provider_name == "openai":
            api_key_env = os.getenv("OPENAI_API_KEY")
        elif self.provider_name == "anthropic":
            api_key_env = os.getenv("ANTHROPIC_API_KEY")
        else:
            api_key_env = None
        
        self.api_key = api_key or api_key_env
        if not self.api_key:
            raise ValueError(
                f"{self.provider_name.upper()}_API_KEY not found. "
                "Set it as an environment variable or pass it to the constructor."
            )
        
        # Get model from parameter, environment variable, or use default
        self.model = model or os.getenv("AI_MODEL") or self.DEFAULT_MODEL
        
        # Validate model is available for this provider
        available_models = provider_class.get_models()
        if self.model not in available_models:
            print(f"Warning: Model '{self.model}' not in available models list for {self.provider_name}. Using anyway...")
        
        # Initialize provider
        self._provider: BaseLLMProvider = provider_class(self.api_key, self.model)
    
    @property
    def provider(self) -> str:
        """Get provider name."""
        return self.provider_name
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, Dict[str, Any]]:
        """Get list of available AI providers."""
        return get_available_providers()
    
    @classmethod
    def get_available_models(cls, provider: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get list of available models for a provider or all providers."""
        return get_available_models(provider)
    
    def _call_llm(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7, is_chat: bool = False) -> str:
        """Make a call to the configured AI provider's API."""
        try:
            if is_chat:
                # Enhanced system message for conversational chat mode
                system_message = """You are a friendly and knowledgeable FinOps assistant helping users understand their Google Cloud Platform (GCP) costs and resources. 

Your role:
- Answer questions naturally and conversationally
- When greeted (hi, hello, hey), respond warmly and offer help
- Provide clear, actionable insights based on the data provided
- Use bullet points and formatting to make information easy to read
- If asked about costs, resources, or optimizations, provide specific details from the data
- If the user asks something you can't answer from the data, be honest and helpful
- Maintain a professional yet friendly tone
- Be concise but thorough

Format your responses naturally, using markdown for better readability when helpful."""
            else:
                # Standard system message for other AI features
                system_message = "You are a FinOps expert analyzing Google Cloud Platform costs and resources. Provide clear, actionable insights and recommendations."
            
            return self._provider.call(
                prompt=prompt,
                system_message=system_message,
                max_tokens=max_tokens,
                temperature=temperature,
            )
                
        except Exception as e:
            return f"Error generating AI insights with {self.provider_name}: {str(e)}"

    CHAT_SYSTEM_MESSAGE = """You are a friendly and knowledgeable FinOps assistant helping users understand their Google Cloud Platform (GCP) costs and resources.

Your role:
- Answer questions naturally and conversationally
- When greeted (hi, hello, hey), respond warmly and offer help
- Provide clear, actionable insights based on the data provided
- Use bullet points and formatting to make information easy to read
- If asked about costs, resources, or optimizations, provide specific details from the data
- If the user asks something you can't answer from the data, be honest and helpful
- Maintain a professional yet friendly tone
- Be concise but thorough

Format your responses naturally, using markdown for better readability when helpful."""

    async def stream_chat(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream chat response from the configured provider."""
        msg = system_message or self.CHAT_SYSTEM_MESSAGE
        async for chunk in self._provider.stream(
            prompt=prompt,
            system_message=msg,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            if chunk:
                yield chunk

    async def stream_answer_question(
        self,
        question: str,
        data: DashboardData,
        context: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream answer to a natural language question about FinOps data."""
        service_costs_text = ""
        if data.service_costs:
            service_costs_text = "\n**Service Costs:**\n" + chr(10).join(
                [f"- {s}: ${c:,.2f}" for s, c in sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)]
            )
        else:
            service_costs_text = "\n**Service Costs:**\n- No services with costs recorded"

        base_context = f"""User Question: {question}

You have access to the following GCP FinOps data for this project:

**Cost Summary:**
- Current month: ${data.current_month_cost:,.2f}
- Last month: ${data.last_month_cost:,.2f}
- Year-to-date (YTD): ${data.ytd_cost:,.2f}
{service_costs_text}

**Resource Details:**
{self._format_detailed_resources(data)}

**Optimization Opportunities:**
{self._format_recommendations(data)}

**Potential Monthly Savings:** ${data.total_potential_savings:,.2f}/month

Please answer the user's question naturally and conversationally. If it's a greeting, respond warmly and offer to help. If they're asking about costs, resources, or optimizations, provide specific details from the data above. Use clear formatting with bullet points when listing items. Be helpful, accurate, and friendly."""
        full_context = f"{base_context}\n\n{context}" if context else base_context
        async for chunk in self.stream_chat(
            full_context,
            system_message=self.CHAT_SYSTEM_MESSAGE,
            max_tokens=600,
            temperature=0.6,
        ):
            yield chunk

    def analyze_dashboard_data(self, data: DashboardData) -> Dict[str, Any]:
        """Generate comprehensive AI analysis of dashboard data."""
        
        # Use helper function to avoid division by zero
        change_pct = calculate_percentage_change(data.current_month_cost, data.last_month_cost)
        
        # Get top 5 services by cost
        top_services = sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Count total issues
        total_issues = sum(
            len(result.issues) for result in data.audit_results.values()
        )
        
        # Build prompt
        prompt = f"""Analyze this GCP FinOps data and provide insights:

**Cost Overview:**
- Current month: ${data.current_month_cost:,.2f}
- Last month: ${data.last_month_cost:,.2f}
- Change: {change_pct:+.1f}%
- YTD: ${data.ytd_cost:,.2f}

**Top Services by Cost:**
{chr(10).join([f"- {service}: ${cost:,.2f}" for service, cost in top_services])}

**Resource Issues:**
- Total potential savings: ${data.total_potential_savings:,.2f}/month
- Total issues found: {total_issues}

**Audit Summary:**
{chr(10).join([f"- {result.resource_type}: {result.total_count} resources, {result.untagged_count} untagged, {result.idle_count} idle" for result in data.audit_results.values() if result.total_count > 0])}

Provide your analysis in markdown format:

## Key Insights

### Cost Trends & Patterns
[3 key insights about spending patterns and trends]

### Actionable Recommendations
1. **[Priority]: [Specific recommendation]**
   [Brief explanation of impact and implementation]

2. **[Priority]: [Specific recommendation]**
   [Brief explanation of impact and implementation]

3. **[Priority]: [Specific recommendation]**
   [Brief explanation of impact and implementation]

### Critical Alerts
[Any anomalies or concerns requiring immediate attention]

Be concise but specific."""
        
        response = self._call_llm(prompt, max_tokens=800, temperature=0.6)
        
        return {
            "analysis": response,
            "provider": self.provider_name,
            "model_used": self.model,
            "project_id": data.project_id,
            "billing_month": data.billing_month,
        }
    
    def explain_cost_spike(self, data: DashboardData) -> str:
        """Explain why costs increased or decreased."""
        
        # Use helper function to avoid division by zero
        change_pct = calculate_percentage_change(data.current_month_cost, data.last_month_cost)
        
        if abs(change_pct) < 5:
            return "Your costs are relatively stable compared to last month (change < 5%)."
        
        direction = "increased" if change_pct > 0 else "decreased"
        top_services = sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        prompt = f"""The GCP costs {direction} by {abs(change_pct):.1f}% this month.

**Current Costs:**
- This month: ${data.current_month_cost:,.2f}
- Last month: ${data.last_month_cost:,.2f}

**Top Services:**
{chr(10).join([f"- {service}: ${cost:,.2f}" for service, cost in top_services])}

**Resource Insights:**
- Idle resources: {sum(r.idle_count for r in data.audit_results.values())}
- Untagged resources: {sum(r.untagged_count for r in data.audit_results.values())}
- Over-provisioned: {sum(r.over_provisioned_count for r in data.audit_results.values())}

Explain in 2-3 sentences why the costs {direction} and what might be causing it. Be specific and actionable."""
        
        return self._call_llm(prompt, max_tokens=300, temperature=0.5)
    
    def generate_executive_summary(self, data: DashboardData) -> str:
        """Generate an executive summary for reports."""
        
        top_services = sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)[:3]
        
        prompt = f"""Generate a brief executive summary for this GCP FinOps report:

**Financial Overview:**
- Current month: ${data.current_month_cost:,.2f}
- YTD: ${data.ytd_cost:,.2f}
- Potential savings: ${data.total_potential_savings:,.2f}/month

**Top Services:**
{chr(10).join([f"- {service}: ${cost:,.2f}" for service, cost in top_services])}

**Optimization Opportunities:**
- {len(data.recommendations)} recommendations identified
- {sum(len(r.issues) for r in data.audit_results.values())} total issues

Format your response in markdown:

## Executive Summary

[Write a professional 3-4 sentence summary suitable for executives. Focus on business impact and key takeaways. Include specific dollar amounts and percentages where relevant.]

### Key Metrics
- **Current Monthly Spend:** ${data.current_month_cost:,.2f}
- **Potential Monthly Savings:** ${data.total_potential_savings:,.2f}
- **Optimization Opportunities:** {len(data.recommendations)} recommendations

### Next Steps
[Brief 1-2 sentence recommendation on immediate actions executives should take.]"""
        
        return self._call_llm(prompt, max_tokens=250, temperature=0.6)
    
    def answer_question(self, question: str, data: DashboardData, context: Optional[str] = None) -> str:
        """Answer a natural language question about the FinOps data with enhanced conversational prompts."""
        
        # Build detailed context from dashboard data
        service_costs_text = ""
        if data.service_costs:
            service_costs_text = "\n**Service Costs:**\n" + chr(10).join([f"- {service}: ${cost:,.2f}" for service, cost in sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)])
        else:
            service_costs_text = "\n**Service Costs:**\n- No services with costs recorded"
        
        # Build a more natural, conversational prompt
        base_context = f"""User Question: {question}

You have access to the following GCP FinOps data for this project:

**Cost Summary:**
- Current month: ${data.current_month_cost:,.2f}
- Last month: ${data.last_month_cost:,.2f}
- Year-to-date (YTD): ${data.ytd_cost:,.2f}
{service_costs_text}

**Resource Details:**
{self._format_detailed_resources(data)}

**Optimization Opportunities:**
{self._format_recommendations(data)}

**Potential Monthly Savings:** ${data.total_potential_savings:,.2f}/month

Please answer the user's question naturally and conversationally. If it's a greeting, respond warmly and offer to help. If they're asking about costs, resources, or optimizations, provide specific details from the data above. Use clear formatting with bullet points when listing items. Be helpful, accurate, and friendly."""
        
        # Add conversation history context if provided
        if context:
            full_context = f"{base_context}\n\n{context}"
        else:
            full_context = base_context
        
        # Use chat mode for natural conversations
        return self._call_llm(full_context, max_tokens=600, temperature=0.6, is_chat=True)
    
    def _format_detailed_resources(self, data: DashboardData) -> str:
        """Format detailed resource information for AI context."""
        if not data.audit_results:
            return "No detailed resource information available."
        
        formatted_resources = []
        for resource_type, result in data.audit_results.items():
            if result.total_count > 0:
                resource_info = f"**{result.resource_type.replace('_', ' ').title()}:**\n"
                resource_info += f"  - Total: {result.total_count}\n"
                resource_info += f"  - Idle: {result.idle_count}\n"
                resource_info += f"  - Untagged: {result.untagged_count}\n"
                resource_info += f"  - Over-provisioned: {result.over_provisioned_count}\n"
                resource_info += f"  - Potential monthly savings: ${result.potential_monthly_savings:,.2f}\n"
                
                if result.issues:
                    resource_info += f"  - Issues: {', '.join(result.issues)}\n"
                
                formatted_resources.append(resource_info)
        
        return "\n".join(formatted_resources) if formatted_resources else "No resources found."
    
    def _format_recommendations(self, data: DashboardData) -> str:
        """Format optimization recommendations for AI context."""
        if not data.recommendations:
            return "No specific recommendations available."
        
        formatted_recs = []
        for i, rec in enumerate(data.recommendations[:10], 1):  # Limit to top 10
            rec_info = f"{i}. **{rec.resource_type.replace('_', ' ').title()} - {rec.resource_name}**\n"
            rec_info += f"   - Region: {rec.region}\n"
            rec_info += f"   - Issue: {rec.issue}\n"
            rec_info += f"   - Recommendation: {rec.recommendation}\n"
            rec_info += f"   - Potential savings: ${rec.potential_monthly_savings:,.2f}/month\n"
            rec_info += f"   - Priority: {rec.priority}\n"
            if rec.details:
                rec_info += f"   - Details: {rec.details}\n"
            formatted_recs.append(rec_info)
        
        return "\n".join(formatted_recs)
    
    def prioritize_recommendations(self, recommendations: List[OptimizationRecommendation]) -> str:
        """Help prioritize which recommendations to act on first."""
        
        if not recommendations:
            return "No recommendations available to prioritize."
        
        # Get top 10 by savings
        top_recs = sorted(recommendations, key=lambda x: x.potential_monthly_savings, reverse=True)[:10]
        
        rec_list = "\n".join([
            f"- {rec.resource_type} '{rec.resource_name}': {rec.issue} (Savings: ${rec.potential_monthly_savings:,.2f}/mo, Priority: {rec.priority})"
            for rec in top_recs
        ])
        
        prompt = f"""Given these optimization recommendations, suggest which 3 should be prioritized and why:

{rec_list}

Consider:
1. Savings potential
2. Implementation difficulty
3. Business risk

Provide your response in the following markdown format:

## Here are the top 3 optimization recommendations to prioritize:

1. **[Resource Name]: [Brief Issue Description] (Savings: $X.XX/mo, Priority: [level])**
   [Detailed explanation of why this should be prioritized, including implementation difficulty and business risk assessment.]

2. **[Resource Name]: [Brief Issue Description] (Savings: $X.XX/mo, Priority: [level])**
   [Detailed explanation of why this should be prioritized, including implementation difficulty and business risk assessment.]

3. **[Resource Name]: [Brief Issue Description] (Savings: $X.XX/mo, Priority: [level])**
   [Detailed explanation of why this should be prioritized, including implementation difficulty and business risk assessment.]

[Concluding paragraph summarizing the overall prioritization strategy and expected outcomes.]"""
        
        return self._call_llm(prompt, max_tokens=500, temperature=0.6)
    
    def suggest_budget_alerts(self, data: DashboardData) -> str:
        """Suggest appropriate budget alerts based on spending patterns."""
        
        avg_monthly = data.ytd_cost / 10  # Approximate average
        
        prompt = f"""Based on this GCP spending pattern, suggest appropriate budget alerts in a well-formatted markdown structure:

**Current Costs:**
- This month: ${data.current_month_cost:,.2f}
- Average monthly (estimated): ${avg_monthly:,.2f}
- YTD: ${data.ytd_cost:,.2f}

**Top Services:**
{chr(10).join([f"- {service}: ${cost:,.2f}" for service, cost in sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)[:5]])}

Please format your response as a clear markdown document with:
1. A main heading "## Budget Recommendations"
2. A "Current Spending Overview" section with key metrics
3. A "Recommended Budget Thresholds" section with specific dollar amounts
4. A "Alert Configuration" section with percentages and thresholds
5. A "Service-Specific Budgets" section if applicable
6. A "Next Steps" section with actionable recommendations

Use proper markdown formatting with headers, bullet points, bold text, and code blocks for dollar amounts."""
        
        return self._call_llm(prompt, max_tokens=600, temperature=0.6)
    
    def analyze(self, data: DashboardData) -> str:
        """Generate comprehensive AI analysis of dashboard data."""
        
        # Use helper function to avoid division by zero
        change_pct = calculate_percentage_change(data.current_month_cost, data.last_month_cost)
        
        # Get top 5 services by cost
        top_services = sorted(data.service_costs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Count total issues
        total_issues = sum(
            len(result.issues) for result in data.audit_results.values()
        )
        
        # Build prompt
        prompt = f"""Provide a comprehensive analysis of this GCP FinOps data in a well-formatted markdown structure:

**Current Costs:**
- This month: ${data.current_month_cost:,.2f}
- Last month: ${data.last_month_cost:,.2f}
- Change: {change_pct:+.1f}%
- YTD: ${data.ytd_cost:,.2f}

**Top Services by Cost:**
{chr(10).join([f"- {service}: ${cost:,.2f}" for service, cost in top_services])}

**Resource Summary:**
{chr(10).join([f"- {result.resource_type}: {result.total_count} total, {result.idle_count} idle" for result in data.audit_results.values() if result.total_count > 0])}

**Total Issues Found:** {total_issues}
**Potential Monthly Savings:** ${data.total_potential_savings:,.2f}

Please format your response as a clear markdown document with:
1. A main heading "## Comprehensive GCP Analysis"
2. A "Cost Overview" section with key financial metrics
3. A "Resource Utilization" section with utilization patterns
4. A "Key Findings" section with important insights
5. A "Recommendations" section with actionable next steps
6. A "Risk Assessment" section highlighting potential issues

Use proper markdown formatting with headers, bullet points, bold text, and code blocks for metrics and dollar amounts."""
        
        return self._call_llm(prompt, max_tokens=800, temperature=0.6)
    
    def analyze_resource_utilization(self, audit_results: Dict[str, AuditResult]) -> str:
        """Analyze resource utilization patterns."""
        
        if not audit_results:
            return "No audit data available."
        
        summary = "\n".join([
            f"- {result.resource_type}: {result.total_count} total, {result.idle_count} idle ({result.idle_count/result.total_count*100:.1f}% idle)" if result.total_count > 0 else f"- {result.resource_type}: No resources"
            for result in audit_results.values()
        ])
        
        prompt = f"""Analyze these resource utilization patterns and format the response as a clear markdown document:

{summary}

Total potential savings from optimization: ${sum(r.potential_monthly_savings for r in audit_results.values()):,.2f}/month

Please format your response with:
1. A main heading "## Resource Utilization Analysis"
2. A "Current Resource Overview" section with key metrics
3. A "Utilization Assessment" section with overall findings
4. A "Priority Actions" section highlighting which resources need immediate attention
5. A "Optimization Opportunities" section with specific recommendations
6. A "Potential Savings" section with cost impact

Use proper markdown formatting with headers, bullet points, bold text, and code blocks for metrics and dollar amounts."""
        
        return self._call_llm(prompt, max_tokens=600, temperature=0.6)


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> Optional[LLMService]:
    """Get or create LLM service singleton."""
    global _llm_service
    
    if _llm_service is None:
        try:
            _llm_service = LLMService()
        except ValueError:
            # API key not configured
            return None
    
    return _llm_service


def refresh_llm_service() -> Optional[LLMService]:
    """Refresh the LLM service singleton with current environment variables."""
    global _llm_service
    
    # Reset the singleton to force recreation
    _llm_service = None
    
    # Create new instance with current environment
    try:
        _llm_service = LLMService()
        return _llm_service
    except ValueError:
        # API key not configured
        return None

