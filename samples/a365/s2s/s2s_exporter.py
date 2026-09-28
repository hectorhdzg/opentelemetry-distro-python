# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Sample: A365 Exporter with S2S (Service-to-Service) authentication

Demonstrates how to export A365 telemetry using the S2S endpoint with a
service-principal token resolver. The resolver performs the app-to-instance
exchange and acquires an application token for the A365 observability scope;
the deterministic scenario exercises every public manual observability scope.

Run this file directly from the repository root as documented in
samples/a365/s2s/README.md.
"""

import logging

from microsoft.opentelemetry import use_microsoft_opentelemetry

from sample_config import SampleConfig
from sample_scenario import emit_sample_telemetry
from token_resolver import build_s2s_token_resolver


def _configure_export_logging() -> None:
    """Surface exporter status and correlation IDs without duplicate handlers."""
    exporter_logger = logging.getLogger("microsoft.opentelemetry.a365.core.exporters.agent365_exporter")
    exporter_logger.setLevel(logging.DEBUG)
    exporter_logger.propagate = False
    handler_name = "a365-s2s-sample-export-logging"
    if any(getattr(handler, "name", None) == handler_name for handler in exporter_logger.handlers):
        return
    handler = logging.StreamHandler()
    handler.name = handler_name
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    exporter_logger.addHandler(handler)


def main() -> None:
    config = SampleConfig.load()
    _configure_export_logging()
    use_microsoft_opentelemetry(
        enable_a365=True,
        a365_use_s2s_endpoint=True,
        a365_token_resolver=build_s2s_token_resolver(config),
    )
    print("Telemetry configured for S2S export.\n")

    emit_sample_telemetry(
        config.create_agent_details(),
        config.create_user_details(),
        config.create_request(),
    )

    print(
        "\nDone. All spans have been recorded. They are flushed to the A365 "
        "batch span processor and exported on shutdown when "
        "ENABLE_A365_OBSERVABILITY_EXPORTER=true."
    )


if __name__ == "__main__":
    main()
