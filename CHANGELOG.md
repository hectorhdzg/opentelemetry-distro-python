# Release History

## 0.1.0b1 (2026-04-27)

### Features Added

- Ensure baggage properties propagate to child spans when the console exporter is chosen and A365 exporter is disabled
  ([#74](https://github.com/microsoft/opentelemetry-distro-python/pull/74))
- Disable web-framework / HTTP-client instrumentations
  (`django`, `fastapi`, `flask`, `psycopg2`, `requests`, `urllib`, `urllib3`)
  by default when A365 is enabled. GenAI instrumentations
  (`langchain`, `openai`, `openai_agents`, `semantic_kernel`,
  `agent_framework`) remain enabled. Users can override either default via
  `instrumentation_options`.
  ([#64](https://github.com/microsoft/opentelemetry-distro-python/pull/64))

### Bugs Fixed

- Fetch the distro version instead of the upstream core package
  ([#73](https://github.com/microsoft/opentelemetry-distro-python/pull/73))

## 0.1.0a4 (2026-04-24)

### Breaking Changes

- Remove tenant_id, agent_id from config options
  ([#59](https://github.com/microsoft/opentelemetry-distro-python/pull/59))

### Features Added

- `enable_azure_monitor` is off by default
  ([#60](https://github.com/microsoft/opentelemetry-distro-python/pull/60))
- Match Upstream Changes: Update scope value to support new exporter path
  ([#62](https://github.com/microsoft/opentelemetry-distro-python/pull/62))

## 0.1.0a3 (2026-04-22)

### Features Added

- Vendor A365 core observability code
  ([#47](https://github.com/microsoft/opentelemetry-distro-python/pull/47))
- Add agent framework and semantic kernel instrumentations
  ([#50](https://github.com/microsoft/opentelemetry-distro-python/pull/50))
- Add Spectra Collector sidecar support with graceful fallback
  ([#48](https://github.com/microsoft/opentelemetry-distro-python/pull/48))
- Add console exporter for traces, metrics, and logs
  ([#54](https://github.com/microsoft/opentelemetry-distro-python/pull/54))

## 0.1.0a2 (2026-04-20)

### Features Added

- Integrate A365 observability into distro
  ([#45](https://github.com/microsoft/opentelemetry-distro-python/pull/45))
- Support openai-v2 and openai-agents-v2
  ([#37](https://github.com/microsoft/opentelemetry-distro-python/pull/37))

### Other Changes

- Modify the logic to add providers when azure monitor config is disabled
  ([#24](https://github.com/microsoft/opentelemetry-distro-python/pull/24))


## 0.1.0a1 (2026-04-10)

### Features Added

- Add langchain instrumentation 
  ([#26](https://github.com/microsoft/opentelemetry-distro-python/pull/26))
- Add Microsoft Opentelemetry Distro Configuration
  ([#9](https://github.com/microsoft/opentelemetry-distro-python/pull/9))
- Add langchain samples
  ([#8](https://github.com/microsoft/opentelemetry-distro-python/pull/8))
- Add azure-monitor-opentelemetry distro source
  ([#7](https://github.com/microsoft/opentelemetry-distro-python/pull/7))
- Added `azure-monitor-opentelemetry` package source for Azure Monitor OpenTelemetry distro integration.
  ([#7](https://github.com/microsoft/opentelemetry-distro-python/pull/7))

### Other Changes

- Add support for local mypy, pylint, black checks
  ([#14](https://github.com/microsoft/opentelemetry-distro-python/pull/14))
- Add mypy and pyright checks
  ([#15](https://github.com/microsoft/opentelemetry-distro-python/pull/15))
- Fix lint and format on langchain samples
  ([#16](https://github.com/microsoft/opentelemetry-distro-python/pull/16))
- Update max length to 120
  ([#17](https://github.com/microsoft/opentelemetry-distro-python/pull/17))
- Add environment variables to README
  ([#12](https://github.com/microsoft/opentelemetry-distro-python/pull/12))
- Add PR build
  ([#10](https://github.com/microsoft/opentelemetry-distro-python/pull/10))
- Microsoft mandatory file
  ([#2](https://github.com/microsoft/opentelemetry-distro-python/pull/2))

