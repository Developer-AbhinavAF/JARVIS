# JARVIS Planning

## Simple Tasks

Simple, high-confidence tasks should execute directly.

Examples:

* open YouTube
* what time is it
* remember my name
* take a screenshot

Do not create unnecessary planning overhead for trivial requests.

## Complex Tasks

For complex requests:

1. Understand the desired outcome.
2. Identify required capabilities.
3. Determine dependencies.
4. Build an ordered execution plan.
5. Execute each step.
6. Verify each meaningful state transition.
7. Recover from failures when possible.
8. Continue or stop based on the resulting state.
9. Produce the final response.

## Multi-Step Example

User:

"Open YouTube, search Interstellar, and play the first result."

Plan:

1. Open/activate browser.
2. Open YouTube.
3. Verify YouTube.
4. Search Interstellar.
5. Verify results.
6. Identify first result.
7. Open/play result.
8. Verify playback.
9. Respond.

## Conditional Planning

When a task depends on state:

* inspect current state,
* choose the appropriate branch,
* execute,
* verify,
* continue.

## Iterative Operations

For collections:

* process each item,
* handle individual failures,
* preserve successful results,
* report meaningful partial failures.

## Planning and Tools

Planning should determine whether the task requires:

* direct conversation
* memory
* RAG
* a single tool
* multiple tools
* code generation
* desktop automation
* vision
* external APIs

Do not invoke unnecessary capabilities.

## Confidence

Simple high-confidence actions can execute immediately.

Ambiguous or potentially risky actions should require clarification or confirmation according to the safety policy.
