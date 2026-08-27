# Privacy

The research plugin is a local, single-user tool. It does not call external LLM APIs, run a hosted service, or send telemetry.

Research entries, indexes, linked-project registries, verifier logs, calculation receipts, run packets, extract caches, and bounded hook status records are written on the user's machine under the configured research roots. Defaults are `~/dev/research/` for both content and index data.

The local hook log stores the event time, edited research path, host class, exit code, and pass/fail status. It does not store prompt text, file contents, credentials, or network payloads. The plugin does not transmit this log.

When the host agent performs web research, network access and source fetching are handled by the host agent runtime, not by this plugin's Python scripts.
