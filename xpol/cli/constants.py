"""CLI status code constants following standard Unix exit codes."""

# Standard exit codes (following sysexits.h)
EX_OK = 0              # Success
EX_GENERAL = 1         # General error
EX_USAGE = 64          # Command line usage error
EX_DATAERR = 65        # Data format error
EX_NOINPUT = 66        # Cannot open input
EX_NOUSER = 67         # Addressee unknown
EX_NOHOST = 68         # Host name unknown
EX_UNAVAILABLE = 69   # Service unavailable
EX_SOFTWARE = 70      # Internal software error
EX_OSERR = 71         # System error (e.g., can't fork)
EX_OSFILE = 72        # Critical OS file missing
EX_CANTCREAT = 73     # Can't create (user) output file
EX_IOERR = 74         # Input/output error
EX_TEMPFAIL = 75      # Temp failure; user is invited to retry
EX_PROTOCOL = 76      # Remote error in protocol
EX_NOPERM = 77        # Permission denied
EX_CONFIG = 78         # Configuration error

# GCP-specific error codes (using range 80-99)
EX_GCP_AUTH = 80      # GCP authentication error
EX_GCP_PERMISSION = 81 # GCP permission denied
EX_GCP_NOT_FOUND = 82 # GCP resource not found
EX_GCP_QUOTA = 83     # GCP quota exceeded
EX_GCP_API = 84       # GCP API error
EX_BIGQUERY = 85      # BigQuery error
EX_MONITORING = 86    # Cloud Monitoring error

