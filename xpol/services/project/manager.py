"""Project manager for multi-project operations."""

from typing import List, Optional, Dict, Set
from google.cloud import resourcemanager_v3
from google.api_core import exceptions

from xpol.services.budget import BudgetService
from xpol.services.base import get_default_credentials
from xpol.types import ProjectData
from xpol.utils.visualizations import print_error, print_warning, print_progress


class ProjectManager:
    """Manager for handling multiple GCP projects."""
    
    def __init__(self, credentials=None):
        """Initialize project manager.
        
        Args:
            credentials: GCP credentials (defaults to application default)
        """
        self.credentials = get_default_credentials(credentials)
        self._projects_client: Optional[resourcemanager_v3.ProjectsClient] = None
        self.budget_service = BudgetService(credentials=credentials)
    
    @property
    def projects_client(self) -> resourcemanager_v3.ProjectsClient:
        """Get Resource Manager Projects client."""
        if self._projects_client is None:
            self._projects_client = resourcemanager_v3.ProjectsClient(
                credentials=self.credentials
            )
        return self._projects_client
    
    def get_available_projects(self) -> List[str]:
        """Get list of all available projects the user has access to.
        
        Returns:
            List of project IDs
        """
        project_ids = []
        try:
            request = resourcemanager_v3.ListProjectsRequest()
            page_result = self.projects_client.list_projects(request=request)
            
            for project in page_result:
                if project.state == resourcemanager_v3.Project.State.ACTIVE:
                    project_ids.append(project.project_id)
                
        except Exception as e:
            print_error(f"Failed to list projects: {str(e)}")
        
        return project_ids
    
    def get_billing_account_for_project(self, project_id: str) -> Optional[str]:
        """Get billing account ID for a project.
        
        Args:
            project_id: GCP project ID
            
        Returns:
            Billing account ID or None
        """
        return self.budget_service.get_billing_account_id(project_id)
    
    def group_projects_by_billing_account(
        self,
        project_ids: List[str]
    ) -> Dict[str, List[str]]:
        """Group projects by their billing account.
        
        Args:
            project_ids: List of project IDs
            
        Returns:
            Dictionary mapping billing account ID to list of project IDs
        """
        groups: Dict[str, List[str]] = {}
        no_billing: List[str] = []
        
        print_progress(f"Grouping {len(project_ids)} projects by billing account...")
        
        for project_id in project_ids:
            billing_account_id = self.get_billing_account_for_project(project_id)
            if billing_account_id:
                if billing_account_id not in groups:
                    groups[billing_account_id] = []
                groups[billing_account_id].append(project_id)
            else:
                no_billing.append(project_id)
        
        if no_billing:
            # Projects without billing accounts go into a special group
            groups["NO_BILLING"] = no_billing
            print_warning(f"{len(no_billing)} project(s) without billing accounts")
        
        print_progress(f"Grouped into {len(groups)} billing account(s)", done=True)
        return groups
    
    def validate_projects(self, project_ids: List[str]) -> List[str]:
        """Validate that projects exist and are accessible.
        
        Args:
            project_ids: List of project IDs to validate
            
        Returns:
            List of valid project IDs
        """
        valid_projects = []
        
        for project_id in project_ids:
            try:
                project_name = f"projects/{project_id}"
                project = self.projects_client.get_project(name=project_name)
                if project.state == resourcemanager_v3.Project.State.ACTIVE:
                    valid_projects.append(project_id)
                else:
                    print_warning(f"Project {project_id} is not active (state: {project.state.name})")
            except exceptions.NotFound:
                print_error(f"Project {project_id} not found")
            except exceptions.PermissionDenied:
                print_error(f"Permission denied for project {project_id}")
            except Exception as e:
                print_error(f"Error validating project {project_id}: {str(e)}")
        
        return valid_projects
    
    def initialize_projects(
        self,
        projects: Optional[List[str]] = None,
        all_projects: bool = False,
        combine: bool = False
    ) -> Dict[str, List[str]]:
        """Initialize and group projects based on flags.
        
        Args:
            projects: Optional list of specific project IDs
            all_projects: If True, use all available projects
            combine: If True, group projects by billing account
            
        Returns:
            Dictionary mapping billing account ID (or "SINGLE" for non-combined) to list of project IDs
        """
        if all_projects:
            # Get all available projects
            project_ids = self.get_available_projects()
            if not project_ids:
                print_error("No projects found or accessible")
                return {}
            print_progress(f"Found {len(project_ids)} accessible project(s)")
        elif projects:
            # Use specified projects
            project_ids = [p.strip() for p in projects]
            # Validate projects
            project_ids = self.validate_projects(project_ids)
            if not project_ids:
                print_error("No valid projects found")
                return {}
        else:
            # Default: use current project from gcloud config
            from google.auth import default as auth_default
            _, default_project = auth_default()
            if default_project:
                project_ids = [default_project]
                print_progress(f"Using default project: {default_project}")
            else:
                print_error("No project specified and no default project found")
                return {}
        
        if combine:
            # Group by billing account
            return self.group_projects_by_billing_account(project_ids)
        else:
            # Return as individual groups (one project per group)
            return {f"SINGLE_{pid}": [pid] for pid in project_ids}
    
    def create_project_data_list(
        self,
        project_groups: Dict[str, List[str]]
    ) -> List[ProjectData]:
        """Create ProjectData objects for all projects.
        
        Args:
            project_groups: Dictionary mapping billing account to project IDs
            
        Returns:
            List of ProjectData objects
        """
        project_data_list = []
        
        for billing_account_id, project_ids in project_groups.items():
            for project_id in project_ids:
                # Get billing account (skip if it's the NO_BILLING marker)
                actual_billing_account = None
                if billing_account_id != "NO_BILLING":
                    actual_billing_account = billing_account_id
                elif billing_account_id == "NO_BILLING":
                    # Try to get billing account for this specific project
                    actual_billing_account = self.get_billing_account_for_project(project_id)
                
                project_data = ProjectData(
                    project_id=project_id,
                    billing_account_id=actual_billing_account
                )
                project_data_list.append(project_data)
        
        return project_data_list
