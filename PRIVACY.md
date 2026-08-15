# Privacy

The research plugin is a local, single-user tool. It does not call external LLM APIs, run a hosted service, or send telemetry.

Research entries, indexes, linked-project registries, verifier logs, and extract caches are written on the user's machine under the configured research roots. Defaults are `~/dev/research/` for both content and index data.

When the host agent performs web research, network access and source fetching are handled by the host agent runtime, not by this plugin's Python scripts.
