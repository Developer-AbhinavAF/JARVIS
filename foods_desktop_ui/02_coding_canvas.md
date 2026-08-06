# Coding and Canvas Integration

The web interface includes a Canvas code editor for writing and editing code.

## Code Generation Guidelines

When generating code:

1. **Language Selection**: Choose appropriate language based on context
   - Python for general scripting and automation
   - JavaScript for web-related tasks
   - HTML/CSS for web pages
   - PowerShell for Windows automation
   - Batch for simple Windows scripts

2. **Code Quality**:
   - Write clean, readable code
   - Add helpful comments
   - Follow language conventions
   - Include error handling
   - Use meaningful variable names

3. **File Management**:
   - Suggest appropriate file extensions
   - Consider user's environment (Windows)
   - Provide save locations
   - Handle file permissions

4. **Testing Considerations**:
   - Consider edge cases
   - Handle user input validation
   - Include error messages
   - Test mentally before suggesting

## Canvas Features

- Syntax highlighting
- Multiple language support
- Code completion (basic)
- File save/load
- Copy/paste functionality

## Code Examples

### Python Script
```python
import os
import sys

def main():
    """Main function for script execution."""
    print("Script started")
    # Your code here
    print("Script completed")

if __name__ == "__main__":
    main()
```

### PowerShell Script
```powershell
# PowerShell script
param($Path)

if (Test-Path $Path) {
    Write-Host "Path exists: $Path"
} else {
    Write-Host "Path not found: $Path"
}
```

## Best Practices

1. Start with clear goal statement
2. Write modular, reusable functions
3. Add docstrings/comments
4. Handle errors gracefully
5. Test critical paths
6. Provide usage instructions
