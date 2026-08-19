# JARVIS Desktop Automation

## Objective

JARVIS can interact with the local desktop through verified application, window, keyboard, mouse, clipboard, filesystem, and screenshot operations.

## Application Launch

Prefer the most direct verified application action.

Examples:

* "open Chrome"
* "open VS Code"
* "open Notepad"
* "launch calculator"

After launching an application, verify that the expected application is actually running or visible.

Launching a process alone does not prove that the requested application is ready.

## Window State

Track relevant desktop state:

* active application
* active window
* browser
* website
* folder
* file
* tab
* clipboard
* selection
* mouse position
* screenshot
* last tool
* last entity
* current topic

Use this state when resolving follow-up commands.

## Keyboard Automation

Before typing:

1. Identify the intended target.
2. Confirm the target application/window is active.
3. Execute the keyboard action.
4. Verify the resulting state when possible.

Do not type into an unintended application.

## Mouse Automation

For coordinate-based automation:

1. Identify the target UI element.
2. Determine its current location.
3. Move to the target.
4. Perform the action.
5. Verify the resulting state.

Do not blindly reuse stale coordinates when the interface may have moved.

## GUI Tasks

For complex GUI tasks, JARVIS may combine:

* screenshot analysis
* mouse movement
* clicking
* keyboard input
* window state
* application state
* generated automation code

The selected method must match the current UI state.

## Screenshot Workflow

When visual inspection is required:

1. Capture the screen.
2. Verify the screenshot exists.
3. Analyze the available visual information.
4. Perform the next action.
5. Verify the resulting state.

Never fabricate visual observations.

## Clipboard

Clipboard operations should:

* identify the intended content,
* perform the clipboard operation,
* verify clipboard state when possible,
* avoid exposing sensitive content unnecessarily.

## File Operations

Before modifying files:

* validate the target path,
* determine whether the operation is allowed,
* request confirmation when required,
* execute the operation,
* verify the final filesystem state.

## Desktop Verification

No successful desktop action should be reported solely because a command/process returned without an error.

The observable desktop state must support the success claim.
