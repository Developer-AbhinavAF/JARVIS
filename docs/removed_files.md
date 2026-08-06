# Removed files

No repository file was deleted by this refactor.

Reason: the audit found extensive pre-existing user-owned deletions and modifications. Deleting the legacy modules without a clean ownership baseline could destroy work. The active startup path no longer imports them; deletion should follow after the LLM fallback is migrated and the user approves removal of the identified legacy surface.
