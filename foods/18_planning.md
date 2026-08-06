# Planning Strategies

## Single-Step Operations
- Direct tool execution for simple requests
- No planning needed for level 0-2 tasks
- Execute immediately on high confidence

## Multi-Step Operations
- Break complex tasks into sequential steps
- Identify dependencies between steps
- Handle failures in intermediate steps
- Maintain state across steps

## Conditional Planning
- Evaluate conditions before execution
- Branch based on system state
- Handle both success and failure paths
- Provide clear reasoning for choices

## Iterative Operations
- Process collections of items
- Apply operations to each item
- Collect and aggregate results
- Handle partial failures gracefully

## Error Recovery Planning
- Plan fallback operations
- Identify retry opportunities
- Limit retry attempts
- Implement circuit breakers
