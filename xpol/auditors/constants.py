"""Constants for auditor cost estimates and thresholds."""

# Cost estimates (monthly, in USD)
# These are rough estimates and should be adjusted based on actual pricing
COST_ESTIMATES = {
    # Cloud Functions
    "cloud_function_idle": 5.0,  # Estimated monthly cost for idle function
    "cloud_function_memory_optimization": 8.0,  # Estimated savings from memory optimization
    "cloud_function_error_reduction": 10.0,  # Estimated savings from fixing errors
    
    # Cloud Run
    "cloud_run_idle": 10.0,  # Estimated monthly cost for idle service
    "cloud_run_cpu_optimization": 30.0,  # Estimated savings from CPU throttling
    "cloud_run_memory_optimization": 15.0,  # Estimated savings from memory reduction
    "cloud_run_min_instances_per_instance": 40.0,  # Estimated cost per min instance
    
    # Compute Engine
    "compute_stopped_disk_cost": 20.0,  # Estimated disk costs for stopped instances
    "compute_preemptible_savings": 100.0,  # Estimated savings from using preemptible VMs
    
    # Cloud SQL
    "cloud_sql_stopped": 50.0,  # Estimated cost for stopped instance
    "cloud_sql_idle": 100.0,  # Estimated cost for idle instance
    "cloud_sql_downsizing": 50.0,  # Estimated savings from downsizing
    
    # Storage
    "disk_storage_per_gb_monthly": 0.04,  # Standard disk storage cost per GB/month
    "static_ip_external_monthly": 7.0,  # Cost for unused external static IP
}

# Thresholds for recommendations
THRESHOLDS = {
    # Memory utilization thresholds
    "memory_utilization_low": 0.3,  # Below 30% utilization triggers recommendation
    "memory_utilization_very_low": 0.2,  # Below 20% utilization
    
    # CPU utilization thresholds
    "cpu_utilization_low": 10.0,  # Below 10% CPU utilization
    "cpu_utilization_very_low": 5.0,  # Below 5% CPU utilization
    
    # Error rate thresholds
    "error_rate_high": 5.0,  # Above 5% error rate triggers recommendation
    
    # Connection/utilization thresholds
    "connection_count_idle": 1.0,  # Average connections below 1.0
    
    # Invocation/request thresholds
    "invocations_idle": 0,  # Zero invocations considered idle
    "requests_idle": 0,  # Zero requests considered idle
}

# Memory optimization factors
MEMORY_OPTIMIZATION = {
    "recommended_reduction_factor": 0.5,  # Recommend reducing to 50% of current
    "minimum_memory_mb": 128,  # Minimum memory allocation (MB)
}

# Default regions and zones (can be overridden)
DEFAULT_REGIONS = [
    "us-central1",
    "us-east1",
    "us-west1",
    "europe-west1",
    "asia-east1"
]

DEFAULT_ZONES = [
    "us-central1-a",
    "us-central1-b",
    "us-east1-b",
    "us-west1-a",
    "europe-west1-b",
    "asia-east1-a"
]

# Cloud Functions specific regions
CLOUD_FUNCTIONS_DEFAULT_REGIONS = [
    "us-central1",
    "us-east1",
    "us-west1",
    "europe-west1"
]
