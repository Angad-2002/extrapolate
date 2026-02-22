"""Audit command module."""

from typing import Optional, List
import click
import logging
from google.api_core import exceptions as gcp_exceptions
from xpol.cli.utils.display import show_enhanced_progress, display_audit_results_table
from xpol.cli.commands.base import BaseCommand
from xpol.core import DashboardRunner
from xpol.utils.visualizations import DashboardVisualizer
from xpol.types import DashboardData, MultiProjectDashboardData
from xpol.cli.constants import (
    EX_OK, EX_GENERAL, EX_USAGE, EX_GCP_AUTH, EX_GCP_PERMISSION,
    EX_GCP_NOT_FOUND, EX_BIGQUERY, EX_MONITORING
)
from xpol.cli.exceptions import CLIException

logger = logging.getLogger(__name__)

class AuditCommand(BaseCommand):
    """Audit command implementation."""
    
    def __init__(
        self,
        project_id: Optional[str],
        billing_table_prefix: str,
        location: str,
        billing_dataset: Optional[str] = None,
        regions: Optional[List[str]] = None,
        hide_project_id: bool = False,
        projects: Optional[List[str]] = None,
        all_projects: bool = False,
        combine: bool = False,
    ):
        super().__init__(project_id, billing_table_prefix, location)
        self.regions = regions
        self.hide_project_id = hide_project_id
        self.projects = projects
        self.all_projects = all_projects
        self.combine = combine
        # Default billing dataset to project_id if not provided
        self.billing_dataset = billing_dataset or (f"{project_id}.billing_export" if project_id else None)
    
    def run(self) -> int:
        """Run the audit command.
        
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        # Determine if we're in multi-project mode
        is_multi_project = self.all_projects or (self.projects and len(self.projects) > 1)
        
        if is_multi_project:
            return self._run_multi_project_audit()
        else:
            return self._run_single_project_audit()
    
    def _run_single_project_audit(self) -> int:
        """Run audit for a single project.
        
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        if not self.project_id:
            from xpol.utils.visualizations import print_error
            print_error("Project ID is required for single-project audit")
            logger.error("Project ID is required for single-project audit")
            return EX_USAGE
        
        show_enhanced_progress("Initializing dashboard runner...")
        
        try:
            runner = DashboardRunner(
                project_id=self.project_id,
                billing_dataset=self.billing_dataset or f"{self.project_id}.billing_export",
                billing_table_prefix=self.billing_table_prefix,
                regions=self.regions,
                location=self.location,
                hide_project_id=self.hide_project_id
            )
            
            show_enhanced_progress("Running cost optimization audit...")
            data = runner.run()
            
            # Add budget alerts
            data = runner.add_budget_alerts(data)
            
            show_enhanced_progress("Displaying results...")
            visualizer = DashboardVisualizer()
            visualizer.display_dashboard(data)
            
            show_enhanced_progress("Audit complete!", done=True)
            return EX_OK
        except gcp_exceptions.PermissionDenied as e:
            from xpol.utils.visualizations import print_error
            print_error(f"Permission denied: {str(e)}")
            logger.error(f"Permission denied: {str(e)}", exc_info=True)
            return EX_GCP_PERMISSION
        except gcp_exceptions.NotFound as e:
            from xpol.utils.visualizations import print_error
            print_error(f"Resource not found: {str(e)}")
            logger.error(f"Resource not found: {str(e)}", exc_info=True)
            return EX_GCP_NOT_FOUND
        except gcp_exceptions.Unauthenticated as e:
            from xpol.utils.visualizations import print_error
            print_error(f"Authentication failed: {str(e)}")
            logger.error(f"Authentication failed: {str(e)}", exc_info=True)
            return EX_GCP_AUTH
        except Exception as e:
            from xpol.utils.visualizations import print_error
            print_error(f"Audit failed: {str(e)}")
            logger.error(f"Audit failed: {str(e)}", exc_info=True)
            return EX_GENERAL
    
    def _run_multi_project_audit(self) -> int:
        """Run audit for multiple projects.
        
        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        # For multi-project, we need at least one project to get billing_dataset
        # Use first project or default project
        default_project = self.project_id or (self.projects[0] if self.projects else None)
        if not default_project:
            try:
                from google.auth import default as auth_default
                _, default_project = auth_default()
            except Exception as e:
                logger.debug(f"Could not get default project from auth: {str(e)}")
        
        if not default_project:
            from xpol.utils.visualizations import print_error
            print_error("Cannot determine default project for multi-project audit")
            logger.error("Cannot determine default project for multi-project audit")
            return EX_USAGE
        
        show_enhanced_progress("Initializing multi-project dashboard runner...")
        
        try:
            # Use default project for billing dataset location
            runner = DashboardRunner(
                project_id=default_project,
                billing_dataset=self.billing_dataset or f"{default_project}.billing_export",
                billing_table_prefix=self.billing_table_prefix,
                regions=self.regions,
                location=self.location,
                hide_project_id=self.hide_project_id
            )
            
            show_enhanced_progress("Running multi-project cost analysis...")
            multi_data = runner.run_multi_project(
                projects=self.projects,
                all_projects=self.all_projects,
                combine=self.combine
            )
            
            show_enhanced_progress("Displaying multi-project results...")
            visualizer = DashboardVisualizer()
            visualizer.display_multi_project_dashboard(multi_data)
            
            show_enhanced_progress("Multi-project audit complete!", done=True)
            return EX_OK
        except gcp_exceptions.PermissionDenied as e:
            from xpol.utils.visualizations import print_error
            print_error(f"Permission denied: {str(e)}")
            logger.error(f"Permission denied: {str(e)}", exc_info=True)
            return EX_GCP_PERMISSION
        except gcp_exceptions.NotFound as e:
            from xpol.utils.visualizations import print_error
            print_error(f"Resource not found: {str(e)}")
            logger.error(f"Resource not found: {str(e)}", exc_info=True)
            return EX_GCP_NOT_FOUND
        except gcp_exceptions.Unauthenticated as e:
            from xpol.utils.visualizations import print_error
            print_error(f"Authentication failed: {str(e)}")
            logger.error(f"Authentication failed: {str(e)}", exc_info=True)
            return EX_GCP_AUTH
        except Exception as e:
            from xpol.utils.visualizations import print_error
            print_error(f"Multi-project audit failed: {str(e)}")
            logger.error(f"Multi-project audit failed: {str(e)}", exc_info=True)
            return EX_GENERAL

@click.command()
@BaseCommand.common_options
@click.option(
    "--billing-dataset",
    type=str,
    help="BigQuery billing dataset (e.g., 'project.dataset_name'). Defaults to '{project_id}.billing_export'",
)
@click.option(
    "--regions",
    type=str,
    help="Comma-separated list of regions to audit (e.g., 'us-central1,us-east1')",
)
@click.option(
    "--hide-project-id",
    is_flag=True,
    help="Hide project ID in output for security (useful for screenshots/demos)",
)
@click.option(
    "--projects",
    type=str,
    help="Comma-separated list of project IDs to audit (e.g., 'project1,project2,project3')",
)
@click.option(
    "--all",
    "all_projects",
    is_flag=True,
    help="Audit all accessible projects",
)
@click.option(
    "--combine",
    is_flag=True,
    help="Combine projects by billing account (use with --projects or --all)",
)
@click.pass_context
def audit(
    ctx: click.Context,
    project_id: Optional[str],
    billing_table_prefix: str,
    location: str,
    billing_dataset: Optional[str],
    regions: Optional[str],
    hide_project_id: bool,
    projects: Optional[str],
    all_projects: bool,
    combine: bool,
) -> None:
    """Run cost optimization audits and generate recommendations.
    
    Examples:
        # Single project audit
        xpol audit --project-id my-project
        
        # Multiple specific projects
        xpol audit --projects project1,project2,project3
        
        # All projects
        xpol audit --all
        
        # Combine projects by billing account
        xpol audit --all --combine
    """
    region_list = regions.split(",") if regions else None
    project_list = projects.split(",") if projects else None
    
    cmd = AuditCommand(
        project_id=project_id,
        billing_table_prefix=billing_table_prefix,
        location=location,
        billing_dataset=billing_dataset,
        regions=region_list,
        hide_project_id=hide_project_id,
        projects=project_list,
        all_projects=all_projects,
        combine=combine,
    )
    exit_code = cmd.run()
    if exit_code != EX_OK:
        raise CLIException(f"Audit failed with exit code {exit_code}", exit_code)
