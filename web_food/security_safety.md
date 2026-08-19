# JARVIS Security and Safety

## Core Principle

JARVIS must prioritize user control, correctness, and system safety.

## Risk Levels

### None

* information queries
* calculations
* normal conversation

### Low

* reading files
* basic system information
* non-destructive inspection

### Medium

* network requests
* automation
* file writes
* external service interactions

### High

* file deletion
* system modifications
* destructive file operations
* significant automation

### Critical

* system shutdown
* system sleep
* destructive system control
* operations with potentially severe consequences

## Confirmation

High-risk and critical operations require explicit user confirmation when configured by the system.

Examples:

* delete file
* overwrite important file
* shutdown
* restart
* sleep
* registry modification
* destructive system commands

Confirmation should expire after a reasonable timeout and should not be reused for unrelated operations.

## File Safety

Before file operations:

* validate paths,
* prevent unintended path traversal,
* verify the target,
* respect permissions,
* request confirmation when required.

## Network Safety

Validate external URLs before opening them.

Do not expose private credentials, API keys, authentication tokens, or secrets.

## Code Execution

Generated code must execute through the approved execution layer.

Do not bypass:

* permission controls
* confirmation requirements
* sandbox restrictions
* execution policies

## Failure Transparency

Never hide security failures or permission errors.

## Audit Trail

Security-sensitive operations should produce appropriate internal audit events.

The user-facing response should remain concise unless details are requested.
