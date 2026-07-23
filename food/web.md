# JARVIS Web Automation System

## Web Automation Architecture

### Primary Tool: Playwright
- Modern browser automation
- Multi-browser support (Chrome, Firefox, Safari, Edge)
- Real user interactions
- Network interception
- JavaScript execution

### Automation Capabilities

### Navigation
- Navigate to URLs
- Handle redirects
- Wait for page load
- Handle dynamic content
- Manage history

### Element Interaction
- Click elements
- Type in forms
- Select options
- Upload files
- Drag and drop

### Data Extraction
- Extract text
- Get attributes
- Scrape data
- Handle tables
- Parse JSON

### Form Operations
- Fill forms
- Submit forms
- Handle validation
- Multi-step forms
- File uploads

## Playwright Integration

### Browser Configuration
```python
playwright_config = {
    "browser": "chromium",  # chromium, firefox, webkit
    "headless": False,  # Show browser
    "viewport": {"width": 1920, "height": 1080},
    "timeout": 30000,
    "slow_mo": 0,  # Slow down for debugging
}
```

### Page Operations
```python
# Navigate
page.goto("https://example.com")

# Wait for element
page.wait_for_selector("#button")

# Click element
page.click("#button")

# Type text
page.fill("#input", "text")

# Get text
text = page.text_content("#element")

# Screenshot
page.screenshot(path="screenshot.png")
```

## Web Automation Patterns

### Search Pattern
```python
# Navigate to search engine
page.goto("https://google.com")

# Enter search query
page.fill("input[name='q']", "search term")

# Submit search
page.press("input[name='q']", "Enter")

# Wait for results
page.wait_for_selector(".g")

# Extract results
results = page.query_selector_all(".g")
```

### Login Pattern
```python
# Navigate to login page
page.goto("https://example.com/login")

# Fill credentials
page.fill("#username", "user")
page.fill("#password", "pass")

# Submit form
page.click("#login-button")

# Wait for login success
page.wait_for_url("**/dashboard")
```

### Form Filling Pattern
```python
# Navigate to form
page.goto("https://example.com/form")

# Fill fields
page.fill("#name", "John Doe")
page.fill("#email", "john@example.com")
page.select_option("#country", "US")

# Upload file
page.set_input_files("#file", "document.pdf")

# Submit form
page.click("#submit")

# Wait for confirmation
page.wait_for_selector(".success")
```

### Data Scraping Pattern
```python
# Navigate to page
page.goto("https://example.com/data")

# Wait for data to load
page.wait_for_selector(".data-item")

# Extract data
items = page.query_selector_all(".data-item")
data = []
for item in items:
    data.append({
        "title": item.query_selector(".title").text_content(),
        "price": item.query_selector(".price").text_content(),
    })

# Save data
save_data(data)
```

## Website-Specific Automation

### YouTube Automation
```python
# Search YouTube
page.goto("https://youtube.com")
page.fill("input[name='search_query']", "search term")
page.press("input[name='search_query']", "Enter")

# Click video
page.click("a#video-title")

# Wait for video to load
page.wait_for_selector(".html5-video-player")

# Get video info
title = page.title()
url = page.url
```

### GitHub Automation
```python
# Navigate to repository
page.goto("https://github.com/user/repo")

# Click file
page.click(".js-navigation-open")

# Get file content
content = page.text_content(".file-content")

# Clone repository
page.click("#clone-branch-or-tag")
page.click(".js-copy-clipboard")
```

### Google Search Automation
```python
# Search Google
page.goto("https://google.com")
page.fill("input[name='q']", "search term")
page.press("input[name='q']", "Enter")

# Get results
results = page.query_selector_all(".g")
for result in results:
    title = result.query_selector("h3").text_content()
    link = result.query_selector("a").get_attribute("href")
    print(f"{title}: {link}")
```

## Advanced Features

### Network Interception
```python
# Intercept network requests
def handle_route(route):
    route.continue_()

page.route("**/*", handle_route)

# Wait for specific response
with page.expect_response("**/api/data") as response_info:
    page.click("#load-data")
response = response_info.value
data = response.json()
```

### JavaScript Execution
```python
# Execute JavaScript
result = page.evaluate("() => document.title")

# Execute with arguments
result = page.evaluate("(a, b) => a + b", 2, 3)

# Execute in element context
element = page.query_selector("#element")
result = element.evaluate("(el) => el.textContent")
```

### Handle Dynamic Content
```python
# Wait for element to appear
page.wait_for_selector(".dynamic-element")

# Wait for navigation
page.wait_for_load_state("networkidle")

# Wait for specific condition
page.wait_for_function("() => document.readyState === 'complete'")
```

### Multi-Tab Operations
```python
# Open new tab
new_page = page.context.new_page()

# Switch between tabs
page.bring_to_front()

# Get all tabs
pages = page.context.pages
```

## Error Handling

### Timeout Handling
```python
try:
    page.click("#button", timeout=5000)
except Exception as e:
    print(f"Timeout: {e}")
    # Handle timeout
```

### Element Not Found
```python
if page.query_selector("#element"):
    page.click("#element")
else:
    print("Element not found")
```

### Navigation Errors
```python
try:
    page.goto("https://example.com")
except Exception as e:
    print(f"Navigation failed: {e}")
    # Handle error
```

## Verification

### Action Verification
```python
# Verify click worked
page.click("#button")
assert page.is_visible("#success-message")

# Verify navigation
page.goto("https://example.com")
assert page.url == "https://example.com"

# Verify form submission
page.fill("#input", "text")
page.click("#submit")
assert page.is_visible(".success")
```

### State Verification
```python
# Verify element exists
assert page.is_visible("#element")

# Verify element text
assert page.text_content("#element") == "expected text"

# Verify element attribute
assert page.get_attribute("#element", "href") == "expected"
```

## Performance Optimization

### Efficient Selectors
- Use specific selectors
- Avoid XPath when possible
- Use data attributes
- Cache selectors
- Use stable selectors

### Parallel Operations
```python
# Multiple pages
context = browser.new_context()
pages = [context.new_page() for _ in range(5)]

# Parallel actions
for page in pages:
    asyncio.create_task(page.goto(url))
```

### Resource Management
```python
# Close pages when done
page.close()

# Close browser when done
browser.close()

# Clear cookies
context.clear_cookies()
```

## Security Considerations

### Sensitive Data
- Don't log passwords
- Secure credential storage
- Use environment variables
- Clear sensitive data
- No credential leakage

### Anti-Bot Detection
- Use realistic user agents
- Add delays between actions
- Handle CAPTCHAs
- Respect rate limits
- Use residential proxies

### Privacy
- User consent required
- Clear data collection
- No tracking
- Data deletion
- Transparency

## Web Automation Use Cases

### Testing
- Automated testing
- Form validation
- Link checking
- Performance testing
- Cross-browser testing

### Data Collection
- Web scraping
- Price monitoring
- News aggregation
- Social media monitoring
- Research data collection

### Workflow Automation
- Form submissions
- Report generation
- Data entry
- Account management
- Scheduled tasks

### Integration
- API testing
- Third-party integration
- Data synchronization
- System monitoring
- Automated reporting