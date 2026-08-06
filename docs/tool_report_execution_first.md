# Execution-first tool report

The fast registry currently exposes contracts for `get_time`, `calculate`, `open_url`, `open_app`, `take_screenshot`, `recall_memory`, and `save_memory`.

Each contract includes description, arguments, example, aliases, risk, and verification. The default `get_time` tool is locally verified. The desktop/browser/screenshot tools intentionally fail closed until a host injects an observable verification provider; this replaces the previous unconditional-success behavior.
