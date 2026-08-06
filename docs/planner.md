# Planner Layer Specification

## Overview
The Planner resides between RAG and Candidate Tool Search.

## Responsibilities
- Evaluate if tool execution is required.
- Determine if memory lookup is sufficient.
- Determine if RAG context is required.
- Determine if multi-step tool execution is required.
- Build execution plan and estimate confidence score.
- Select appropriate `BrainProfile`.
