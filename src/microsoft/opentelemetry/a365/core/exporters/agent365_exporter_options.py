# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Configuration for Agent365 exporter.

Vendored from microsoft-agents-a365-observability-core exporters/agent365_exporter_options.py.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from microsoft.opentelemetry.a365.core.exporters.utils import DEFAULT_MAX_PAYLOAD_BYTES


class Agent365ExporterOptions:
    """Configuration for Agent365Exporter.

    Only cluster_category and token_resolver are required for core operation.
    """

    def __init__(
        self,
        cluster_category: str = "prod",
        token_resolver: Optional[Callable[[str, str], Optional[str]]] = None,
        use_s2s_endpoint: bool = False,
        max_queue_size: int = 2048,
        scheduled_delay_ms: int = 5000,
        exporter_timeout_ms: int = 30000,
        max_export_batch_size: int = 512,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
    ):
        """
        Args:
            cluster_category: Cluster region argument. Defaults to 'prod'.
            token_resolver: Callable(agent_id, tenant_id) -> token string or None.
            use_s2s_endpoint: Use the S2S endpoint instead of standard endpoint.
            max_queue_size: Maximum queue size for the batch processor.
            scheduled_delay_ms: Delay between export batches (ms).
            exporter_timeout_ms: Timeout for the export operation (ms).
            max_export_batch_size: Maximum batch size for export operations.
            max_payload_bytes: Upper bound on HTTP request body size in bytes. The exporter
                splits per-identity batches into sub-batches whose estimated size stays under
                this limit, providing headroom under the A365 1 MB server limit. Default is
                900_000 (~100 KB headroom for estimator error and JSON envelope overhead).
        """
        self.cluster_category = cluster_category
        self.token_resolver = token_resolver
        self.use_s2s_endpoint = use_s2s_endpoint
        self.max_queue_size = max_queue_size
        self.scheduled_delay_ms = scheduled_delay_ms
        self.exporter_timeout_ms = exporter_timeout_ms
        self.max_export_batch_size = max_export_batch_size
        self.max_payload_bytes = max_payload_bytes
