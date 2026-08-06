# Verification-First Pipeline Specification

## Pipeline Order
```
Plan -> Execute -> Verify -> Retry -> Fallback -> Natural Response
```

## State Verification Protocol
No tool action reports success without verifying state changes (e.g. process inspection for apps, file existence checks for file actions, audio output state for media).
