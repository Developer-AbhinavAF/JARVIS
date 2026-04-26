"""jarvis.web_browser

Web browser automation for JARVIS.
Visit pages, extract content, search within pages, and take screenshots.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, urljoin
import re

logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available. Web browsing will be limited.")

# Fallback: requests + beautifulsoup
try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class PageContent:
    """Content extracted from a web page."""
    url: str
    title: str
    text: str
    links: List[Dict[str, str]]
    headings: List[str]
    images: List[str]
    metadata: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResult:
    """Search result within a page."""
    query: str
    matches: List[Dict[str, Any]]
    total_matches: int
    page_url: str
    page_title: str


class WebBrowser:
    """Web browser for JARVIS."""
    
    def __init__(self, headless: bool = True):
        """Initialize web browser.
        
        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.current_url: Optional[str] = None
        
        logger.info("WebBrowser initialized")
    
    async def _ensure_browser(self):
        """Ensure browser is launched."""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        
        if not self.browser:
            try:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(headless=self.headless)
                self.page = await self.browser.new_page()
                logger.info("Browser launched")
            except Exception as e:
                logger.exception(f"Failed to launch browser: {e}")
                return False
        
        return True
    
    async def visit_page(self, url: str, wait_for: str = "networkidle") -> Optional[PageContent]:
        """Visit a web page and extract content.
        
        Args:
            url: URL to visit
            wait_for: When to consider page loaded (load, domcontentloaded, networkidle)
            
        Returns:
            PageContent object or None if failed
        """
        logger.info(f"Visiting: {url}")
        
        # Try Playwright first
        if PLAYWRIGHT_AVAILABLE and await self._ensure_browser():
            try:
                await self.page.goto(url, wait_until=wait_for)
                self.current_url = self.page.url
                
                # Extract content
                title = await self.page.title()
                
                # Get main text content
                text = await self.page.evaluate("""() => {
                    // Remove script and style elements
                    const scripts = document.querySelectorAll('script, style, nav, footer, header, aside');
                    scripts.forEach(el => el.remove());
                    
                    // Get main content or body
                    const main = document.querySelector('main, article, [role="main"], .content, #content');
                    const content = main || document.body;
                    return content.innerText;
                }""")
                
                # Get links
                links = await self.page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                        text: a.innerText.trim(),
                        href: a.href
                    })).filter(a => a.text.length > 0);
                }""")
                
                # Get headings
                headings = await self.page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('h1, h2, h3')).map(h => h.innerText.trim());
                }""")
                
                # Get metadata
                metadata = await self.page.evaluate("""() => {
                    const meta = {};
                    document.querySelectorAll('meta').forEach(m => {
                        const name = m.getAttribute('name') || m.getAttribute('property');
                        const content = m.getAttribute('content');
                        if (name && content) meta[name] = content;
                    });
                    return meta;
                }""")
                
                return PageContent(
                    url=self.current_url,
                    title=title,
                    text=text[:50000],  # Limit text length
                    links=links[:50],   # Limit links
                    headings=headings[:20],
                    images=[],  # Can be added if needed
                    metadata=metadata,
                )
                
            except Exception as e:
                logger.exception(f"Playwright failed: {e}")
                # Fall through to requests fallback
        
        # Fallback: Use requests + BeautifulSoup
        if REQUESTS_AVAILABLE:
            return await self._visit_with_requests(url)
        
        return None
    
    async def _visit_with_requests(self, url: str) -> Optional[PageContent]:
        """Fallback method using requests."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator='\n', strip=True)
            
            # Get title
            title = soup.title.string if soup.title else "No title"
            
            # Get links
            links = []
            for a in soup.find_all('a', href=True)[:50]:
                href = urljoin(url, a['href'])
                text_link = a.get_text(strip=True)
                if text_link:
                    links.append({"text": text_link, "href": href})
            
            # Get headings
            headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])[:20]]
            
            # Get metadata
            metadata = {}
            for meta in soup.find_all('meta'):
                name = meta.get('name') or meta.get('property')
                content = meta.get('content')
                if name and content:
                    metadata[name] = content
            
            return PageContent(
                url=url,
                title=title,
                text=text[:50000],
                links=links,
                headings=headings,
                images=[],
                metadata=metadata,
            )
            
        except Exception as e:
            logger.exception(f"Requests fallback failed: {e}")
            return None
    
    async def search_in_page(self, url: str, query: str) -> SearchResult:
        """Search for specific content within a page.
        
        Args:
            url: URL to search in
            query: Search query
            
        Returns:
            SearchResult with matches
        """
        page_content = await self.visit_page(url)
        
        if not page_content:
            return SearchResult(
                query=query,
                matches=[],
                total_matches=0,
                page_url=url,
                page_title="Error loading page"
            )
        
        # Search in text
        text = page_content.text.lower()
        query_lower = query.lower()
        matches = []
        
        # Find all occurrences
        start = 0
        while True:
            idx = text.find(query_lower, start)
            if idx == -1:
                break
            
            # Get context around match
            context_start = max(0, idx - 100)
            context_end = min(len(text), idx + len(query) + 100)
            context = page_content.text[context_start:context_end]
            
            matches.append({
                "context": context.strip(),
                "position": idx,
            })
            
            start = idx + len(query)
        
        # Also search in headings
        for heading in page_content.headings:
            if query_lower in heading.lower():
                matches.append({
                    "context": f"Heading: {heading}",
                    "position": -1,
                })
        
        return SearchResult(
            query=query,
            matches=matches,
            total_matches=len(matches),
            page_url=page_content.url,
            page_title=page_content.title,
        )
    
    async def extract_article(self, url: str) -> Optional[str]:
        """Extract article content from a page (like Readability mode).
        
        Args:
            url: URL to extract from
            
        Returns:
            Clean article text
        """
        page_content = await self.visit_page(url)
        
        if not page_content:
            return None
        
        # Try to identify main content
        text = page_content.text
        
        # Remove common boilerplate patterns
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip very short lines that might be navigation
            if len(line) < 20 and not line.endswith('.'):
                continue
            # Skip common non-content
            if any(skip in line.lower() for skip in ['cookie', 'privacy policy', 'terms of use', 'sign up', 'log in']):
                continue
            cleaned_lines.append(line)
        
        return '\n\n'.join(cleaned_lines[:100])  # Limit to ~100 paragraphs
    
    async def take_screenshot(self, url: str, output_path: str, full_page: bool = True) -> bool:
        """Take a screenshot of a page.
        
        Args:
            url: URL to screenshot
            output_path: Path to save screenshot
            full_page: Whether to capture full page or just viewport
            
        Returns:
            True if successful
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available for screenshots")
            return False
        
        if not await self._ensure_browser():
            return False
        
        try:
            await self.page.goto(url, wait_until="networkidle")
            await self.page.screenshot(path=output_path, full_page=full_page)
            logger.info(f"Screenshot saved: {output_path}")
            return True
        except Exception as e:
            logger.exception(f"Screenshot failed: {e}")
            return False
    
    async def close(self):
        """Close browser and cleanup."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        
        logger.info("Browser closed")
    
    def format_content_for_display(self, content: PageContent, max_length: int = 3000) -> str:
        """Format page content for display."""
        lines = [
            f"🌐 **{content.title}**",
            f"   {content.url}",
            "",
        ]
        
        # Add main headings
        if content.headings:
            lines.append("📑 **Outline:**")
            for h in content.headings[:10]:
                lines.append(f"  • {h}")
            lines.append("")
        
        # Add main content
        text = content.text[:max_length]
        if len(content.text) > max_length:
            text += "... [truncated]"
        
        lines.extend(["📝 **Content:**", text, ""])
        
        # Add relevant links
        if content.links:
            lines.append("🔗 **Key Links:**")
            for link in content.links[:10]:
                lines.append(f"  • [{link['text'][:50]}]({link['href']})")
        
        return "\n".join(lines)


# Global instance
web_browser: Optional[WebBrowser] = None


def init_web_browser(headless: bool = True):
    """Initialize global web browser."""
    global web_browser
    web_browser = WebBrowser(headless)
    return web_browser


async def visit_page(url: str) -> Optional[PageContent]:
    """Visit a web page."""
    if not web_browser:
        init_web_browser()
    return await web_browser.visit_page(url)


async def search_in_page(url: str, query: str) -> SearchResult:
    """Search within a page."""
    if not web_browser:
        init_web_browser()
    return await web_browser.search_in_page(url, query)


async def extract_article(url: str) -> Optional[str]:
    """Extract article from page."""
    if not web_browser:
        init_web_browser()
    return await web_browser.extract_article(url)


def tool_web_visit(url: str) -> str:
    """Tool: Visit web page (for LLM)."""
    import asyncio
    
    if not web_browser:
        init_web_browser()
    
    try:
        content = asyncio.run(visit_page(url))
        if content:
            return web_browser.format_content_for_display(content)
        return "Failed to visit page"
    except Exception as e:
        return f"Error: {str(e)}"


def tool_web_search(url: str, query: str) -> str:
    """Tool: Search within page (for LLM)."""
    import asyncio
    
    if not web_browser:
        init_web_browser()
    
    try:
        result = asyncio.run(search_in_page(url, query))
        
        if result.total_matches == 0:
            return f"No matches found for '{query}' on {result.page_title}"
        
        lines = [
            f"🔍 Found {result.total_matches} matches for '{query}' on **{result.page_title}**",
            "",
        ]
        
        for i, match in enumerate(result.matches[:5], 1):
            lines.append(f"**Match {i}:**")
            lines.append(f"```")
            lines.append(match['context'])
            lines.append(f"```")
            lines.append("")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {str(e)}"


WEB_BROWSER_REGISTRY = {
    "web_visit": tool_web_visit,
    "web_search": tool_web_search,
}
