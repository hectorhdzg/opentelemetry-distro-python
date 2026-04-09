import os

# Exclude tests/azure_monitor from collection — these tests require
# azure-monitor-opentelemetry and related packages that are not
# installed as part of the base test dependencies.
collect_ignore = [os.path.join(os.path.dirname(__file__), "azure_monitor")]
