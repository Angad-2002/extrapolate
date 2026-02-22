"""Budget service for Google Cloud Billing Budgets API integration."""

from typing import List, Optional, Dict, Any
from google.cloud.billing import budgets_v1
from google.api_core import exceptions
from xpol.types import BudgetInfo, BudgetAlert
from xpol.utils.visualizations import print_error, print_warning
from xpol.services.base import get_default_credentials


class BudgetService:
    """Service for interacting with GCP Billing Budgets API."""
    
    def __init__(self, credentials=None):
        """Initialize budget service.
        
        Args:
            credentials: GCP credentials (defaults to application default)
        """
        self.credentials = get_default_credentials(credentials)
        self._client: Optional[budgets_v1.BudgetServiceClient] = None
    
    @property
    def client(self) -> budgets_v1.BudgetServiceClient:
        """Get Budget Service client."""
        if self._client is None:
            self._client = budgets_v1.BudgetServiceClient(
                credentials=self.credentials
            )
        return self._client
    
    def get_billing_account_id(self, project_id: str) -> Optional[str]:
        """Get billing account ID for a project.
        
        Args:
            project_id: GCP project ID
            
        Returns:
            Billing account ID (e.g., '01ABCD-2EFGH3-4IJKL5') or None if not found
        """
        try:
            from google.cloud import resourcemanager_v3
            
            # Get project info
            projects_client = resourcemanager_v3.ProjectsClient(
                credentials=self.credentials
            )
            project_name = f"projects/{project_id}"
            
            try:
                project = projects_client.get_project(name=project_name)
                # Project billing info is in project.project_id, but we need billing account
                # We'll use the Cloud Billing API instead
                from google.cloud import billing_v1
                billing_client = billing_v1.CloudBillingClient(
                    credentials=self.credentials
                )
                
                project_name_billing = f"projects/{project_id}"
                try:
                    billing_info = billing_client.get_project_billing_info(
                        name=project_name_billing
                    )
                    if billing_info.billing_account_name:
                        # Extract billing account ID from name
                        # Format: billingAccounts/01ABCD-2EFGH3-4IJKL5
                        return billing_info.billing_account_name.split('/')[-1]
                except exceptions.NotFound:
                    print_warning(f"Project {project_id} does not have a billing account linked")
                    return None
                    
            except exceptions.NotFound:
                print_error(f"Project {project_id} not found")
                return None
                
        except Exception as e:
            print_error(f"Failed to get billing account for project {project_id}: {str(e)}")
            return None
    
    def list_budgets(self, billing_account_id: str) -> List[BudgetInfo]:
        """List all budgets for a billing account.
        
        Args:
            billing_account_id: Billing account ID (e.g., '01ABCD-2EFGH3-4IJKL5')
            
        Returns:
            List of BudgetInfo objects
        """
        budgets = []
        parent = f"billingAccounts/{billing_account_id}"
        
        try:
            request = budgets_v1.ListBudgetsRequest(parent=parent)
            response = self.client.list_budgets(request=request)
            
            for budget in response:
                # Extract budget amount
                amount = 0.0
                currency = "USD"
                if budget.amount.specified_amount:
                    amount = float(budget.amount.specified_amount.units)
                    currency = budget.amount.specified_amount.currency_code
                elif budget.amount.last_period_amount:
                    # Last period amount - we'll need to fetch actual amount
                    amount = 0.0
                
                # Extract threshold rules
                threshold_rules = []
                for rule in budget.threshold_rules:
                    threshold_rules.append({
                        "threshold_percent": float(rule.threshold_percent),
                        "spend_basis": rule.spend_basis.name if rule.spend_basis else None
                    })
                
                # Extract projects
                projects = []
                if budget.budget_filter:
                    if budget.budget_filter.projects:
                        for project in budget.budget_filter.projects:
                            # Format: projects/123456789
                            projects.append(project.split('/')[-1])
                
                budget_info = BudgetInfo(
                    budget_id=budget.name.split('/')[-1],
                    display_name=budget.display_name,
                    billing_account_id=billing_account_id,
                    amount=amount,
                    currency=currency,
                    threshold_rules=threshold_rules,
                    projects=projects,
                    created_time=budget.create_time.isoformat() if budget.create_time else None,
                    updated_time=budget.update_time.isoformat() if budget.update_time else None
                )
                budgets.append(budget_info)
                
        except exceptions.PermissionDenied:
            print_error(f"Permission denied: Cannot access budgets for billing account {billing_account_id}")
        except Exception as e:
            print_error(f"Failed to list budgets: {str(e)}")
        
        return budgets
    
    def get_budget_alerts(
        self,
        project_id: str,
        billing_account_id: Optional[str] = None
    ) -> List[BudgetAlert]:
        """Get budget alerts for a project.
        
        Args:
            project_id: GCP project ID
            billing_account_id: Optional billing account ID (will be fetched if not provided)
            
        Returns:
            List of BudgetAlert objects
        """
        if billing_account_id is None:
            billing_account_id = self.get_billing_account_id(project_id)
            if billing_account_id is None:
                return []
        
        budgets = self.list_budgets(billing_account_id)
        alerts = []
        
        # Filter budgets that apply to this project
        project_budgets = [
            b for b in budgets
            if not b.projects or project_id in b.projects
        ]
        
        # For each budget, check if thresholds are breached
        # Note: We'll need actual spend from BigQuery to determine breaches
        # This method returns budget info that can be checked against actual spend
        for budget in project_budgets:
            # We'll create alerts based on threshold rules
            # Actual breach detection will be done by comparing with actual spend
            for rule in budget.threshold_rules:
                threshold_percent = rule.get("threshold_percent", 0.0)
                
                # Create a placeholder alert - actual spend will be filled in later
                alert = BudgetAlert(
                    budget_id=budget.budget_id,
                    budget_name=budget.display_name,
                    project_id=project_id,
                    billing_account_id=billing_account_id,
                    threshold_percent=threshold_percent,
                    current_spend=0.0,  # Will be filled by caller
                    budget_amount=budget.amount,
                    spend_percentage=0.0,  # Will be calculated by caller
                    is_breached=False  # Will be determined by caller
                )
                alerts.append(alert)
        
        return alerts
    
    def check_budget_breaches(
        self,
        project_id: str,
        current_spend: float,
        billing_account_id: Optional[str] = None
    ) -> List[BudgetAlert]:
        """Check if budgets are breached for a project.
        
        Args:
            project_id: GCP project ID
            current_spend: Current month spend for the project
            billing_account_id: Optional billing account ID
            
        Returns:
            List of BudgetAlert objects with breach information
        """
        alerts = self.get_budget_alerts(project_id, billing_account_id)
        
        # Update alerts with actual spend and breach status
        for alert in alerts:
            alert.current_spend = current_spend
            if alert.budget_amount > 0:
                alert.spend_percentage = (current_spend / alert.budget_amount) * 100.0
                # Check if threshold is breached
                alert.is_breached = alert.spend_percentage >= alert.threshold_percent
            else:
                alert.spend_percentage = 0.0
                alert.is_breached = False
        
        # Filter to only return alerts where threshold is reached or breached
        return [
            alert for alert in alerts
            if alert.spend_percentage >= alert.threshold_percent
        ]
