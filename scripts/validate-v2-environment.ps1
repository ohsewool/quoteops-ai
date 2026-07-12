param(
    [ValidateSet("local", "test", "staging", "production")]
    [string]$Environment = "local",
    [switch]$RequireDatabase
)

$ErrorActionPreference = "Stop"

function Test-EnvironmentVariable([string]$Name) {
    return -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name))
}

$required = @("QUOTEOPS_DATABASE_URL", "QUOTEOPS_CORS_ORIGINS")
if ($RequireDatabase) {
    $required += "QUOTEOPS_DATABASE_URL"
}

foreach ($name in $required | Select-Object -Unique) {
    if (-not (Test-EnvironmentVariable $name)) {
        throw "Required V2 environment variable is not configured: $name"
    }
}

if ($Environment -in @("staging", "production")) {
    foreach ($name in @("QUOTEOPS_AUTH_SECRET")) {
        if (-not (Test-EnvironmentVariable $name)) {
            throw "Required production-like V2 environment variable is not configured: $name"
        }
    }
    if (([Environment]::GetEnvironmentVariable("QUOTEOPS_DEMO_ENABLED")) -eq "true") {
        throw "Demo mode is prohibited in staging and production"
    }
}

Write-Output "V2 environment policy validated for $Environment. Sensitive values were not printed."
