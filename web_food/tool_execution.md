# JARVIS Tool Execution

## Core Rule

A tool call is not a successful result.

A tool is successful only when the requested external state has been positively verified.

## Execution Pipeline

For every actionable request:

User Request
→ Intent Detection
→ Tool / Method Selection
→ Plan if Required
→ Execute
→ Verify
→ Retry or Fallback if Required
→ Final Response

## Tool Selection

Prefer an existing specialized tool when one exists.

Examples:

* YouTube task → YouTube/browser capability
* Memory request → memory capability
* Screenshot → screenshot capability
* NASA images → NASA visual capability
* Application launch → application capability
* System information → system information capability

Do not create a new implementation when an existing reliable tool already performs the task.

## Candidate Tool Selection

The complete tool registry should not be unnecessarily exposed to the language model.

Candidate tools should be selected using:

* intent
* semantic similarity
* aliases
* capability
* required arguments
* risk level
* verification method

Only relevant candidate tool definitions should be provided for the decision.

## Tool Card

A tool definition should contain:

* Name
* Aliases
* Description
* Arguments
* Examples
* Risk Level
* Dependencies
* Verification Method

## Verification

Every action must define how success can be observed.

Examples:

Opening an application:

* Verify the expected process or window exists.

Opening a webpage:

* Verify the browser is running and the requested page/navigation state is reached.

Typing text:

* Verify the target application/window is active before and, when possible, after the action.

File creation:

* Verify the expected file exists.

File modification:

* Verify the expected content/state changed.

Screenshot:

* Verify a screenshot was successfully captured before claiming completion.

## Tool Chaining

For multi-step requests, preserve state between operations.

Example:

"Open YouTube, search for Interstellar, and play it."

Plan:

1. Open browser/YouTube.
2. Verify YouTube is available.
3. Search for Interstellar.
4. Verify search results.
5. Select the requested result.
6. Verify playback state.
7. Respond with the final result.

Do not claim the entire chain succeeded if an intermediate step failed.

## Context References

Resolve references using current state and conversation context.

Examples:

"Open YouTube."

Then:

"Search for Interstellar."

Then:

"Play the first one."

"The first one" refers to the most recently established search-result context.

## No Unnecessary Tool Use

Normal conversation must remain normal conversation.

User:

"Don't use your tools, just talk to me."

Correct behavior:
Respond conversationally without unrelated tool calls.

## Tool Failure

If a tool fails:

* report the failure honestly,
* preserve useful context,
* retry only when appropriate,
* use an alternative method when available,
* never fabricate success.

## Code-Based Fallback

When no specialized tool exists, JARVIS may generate code to perform the requested operation.

Example:

User:
"Open YouTube."

Possible fallback:

```python
import webbrowser
webbrowser.open("https://www.youtube.com")
```

The execution system runs the code only when permitted and then verifies that the requested result occurred.

Specialized tools remain preferred for common operations.

## Tool Output

Tool execution details should be represented internally through structured events.

The final conversational response should normally contain only the useful result.

Example:

Tool:
`open_webpage("https://youtube.com")`

Verified result:

"Opened YouTube."

Not:

"I am now invoking the browser tool and checking the browser process..."
