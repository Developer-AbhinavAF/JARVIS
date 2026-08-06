# Security Policies

## Confirmation Requirements
- **Critical operations**: system_shutdown, system_sleep, delete_file
- **High risk**: file operations, system control
- **Medium risk**: network operations, automation
- **Low risk**: information queries

## Risk Levels
- **none**: Information queries, calculations
- **low**: File reads, basic system info
- **medium**: File writes, network requests
- **high**: File deletion, system control
- **critical**: System shutdown, destructive operations

## Safety Controls
- Never execute destructive operations without confirmation
- Validate all file paths before operations
- Sanitize URLs before opening
- Limit system control to safe operations

## Audit Trail
- Log all destructive operations
- Track tool usage patterns
- Monitor for suspicious activity
