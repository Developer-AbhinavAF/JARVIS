"""web_automation — Web automation engine using Playwright.

Capabilities:
- Browser automation (Chrome, Firefox, Safari, Edge)
- Navigation and page control
- Element interaction (click, type, select)
- Form filling and submission
- Data extraction and scraping
- JavaScript execution
- Network interception
- Multi-tab management
- Screenshot and PDF generation
"""

from __future__ import annotations

import os
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class BrowserType(Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class PageState(Enum):
    """Page loading states."""
    LOAD = "load"
    DOMCONTENTLOADED = "domcontentloaded"
    NETWORKIDLE = "networkidle"


@dataclass
class BrowserConfig:
    """Browser configuration."""
    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = False
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    timeout: float = 30000.0
    slow_mo: float = 0.0
    user_agent: str = ""


@dataclass
class AutomationResult:
    """Result of web automation operation."""
    success: bool = False
    operation: str = ""
    url: str = ""
    title: str = ""
    content: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    screenshot_path: str = ""
    processing_time: float = 0.0
    error: str = ""


class WebAutomationEngine:
    """Web automation engine using Playwright."""
    
    def __init__(self, config: BrowserConfig = None):
        self._config = config or BrowserConfig()
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
        self._initialized = False
    
    async def _init_playwright(self) -> bool:
        """Initialize Playwright."""
        if self._initialized:
            return True
        
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._initialized = True
            logger.info("Playwright initialized")
            return True
        except ImportError:
            logger.error("Playwright not installed. Install with: pip install playwright")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            return False
    
    async def start_browser(self, config: BrowserConfig = None) -> bool:
        """Start browser with configuration."""
        if config:
            self._config = config
        
        if not await self._init_playwright():
            return False
        
        try:
            # Launch browser
            browser_type = getattr(self._playwright, self._config.browser_type.value)
            launch_args = {
                "headless": self._config.headless,
                "slow_mo": self._config.slow_mo
            }
            
            self._browser = await browser_type.launch(**launch_args)
            
            # Create context
            context_args = {
                "viewport": self._config.viewport,
                "user_agent": self._config.user_agent if self._config.user_agent else None
            }
            self._context = await self._browser.new_context(**{k: v for k, v in context_args.items() if v})
            
            # Create page
            self._page = await self._context.new_page()
            self._page.set_default_timeout(self._config.timeout)
            
            logger.info(f"Browser started: {self._config.browser_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return False
    
    async def close_browser(self) -> None:
        """Close browser and cleanup."""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self._initialized = False
            
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    async def navigate(self, url: str, wait_until: PageState = PageState.LOAD) -> AutomationResult:
        """Navigate to URL."""
        start_time = time.time()
        
        try:
            if not self._page:
                await self.start_browser()
            
            await self._page.goto(url, wait_until=wait_until.value)
            
            return AutomationResult(
                success=True,
                operation="navigate",
                url=self._page.url,
                title=await self._page.title(),
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return AutomationResult(
                success=False,
                operation="navigate",
                url=url,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def click(self, selector: str, timeout: float = None) -> AutomationResult:
        """Click element."""
        start_time = time.time()
        
        try:
            if not self._page:
                return AutomationResult(success=False, operation="click", error="No page active")
            
            await self._page.click(selector, timeout=timeout)
            
            return AutomationResult(
                success=True,
                operation="click",
                url=self._page.url,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return AutomationResult(
                success=False,
                operation="click",
                selector=selector,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def type_text(self, selector: str, text: str, delay: float = 0) -> AutomationResult:
        """Type text into element."""
        start_time = time.time()
        
        try:
            if not self._page:
                return AutomationResult(success=False, operation="type", error="No page active")
            
            await self._page.fill(selector, text)
            if delay > 0:
                await self._page.type(selector, text, delay=delay)
            
            return AutomationResult(
                success=True,
                operation="type",
                url=self._page.url,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Type failed: {e}")
            return AutomationResult(
                success=False,
                operation="type",
                selector=selector,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def select_option(self, selector: str, value: str) -> AutomationResult:
        """Select option from dropdown."""
        start_time = time.time()
        
        try:
            if not self._page:
                return AutomationResult(success=False, operation="select", error="No page active")
            
            await self._page.select_option(selector, value)
            
            return AutomationResult(
                success=True,
                operation="select",
                url=self._page.url,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Select failed: {e}")
            return AutomationResult(
                success=False,
                operation="select",
                selector=selector,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def get_text(self, selector: str) -> AutomationResult:
        """Get text content of element."""
        start_time = time.time()
        
        try:
            if not self._page:
                return AutomationResult(success=False, operation="get_text", error="No page active")
            
            text = await self._page.inner_text(selector)
            
            return AutomationResult(
                success=True,
                operation="get_text",
                content=text,
                url=self._page.url,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Get text failed: {e}")
            return AutomationResult(
                success=False,
                operation="get_text",
                selector=selector,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def get_attribute(self, selector: str, attribute: str) -> AutomationResult:
        """Get attribute of element."""
        start_time = time.time()
        
        try:
            if not self._page:
                return AutomationResult(success=False, operation="get_attribute", error="No page active")
            
            attr_value = await self._page.get_attribute(selector, attribute)
            
            return AutomationResult(
                success=True,
                operation="get_attribute",
                content=attr_value or "",
                url=self._page.url,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Get attribute failed: {e}")
            return AutomationResult(
                success=False,
                operation="get_attribute",
                selector=selector,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def screenshot(self, path: str = None, full_page: bool = False) -> AutomationResult:
        """Take screenshot of page."""
        start_time = time.time()
        
        try:
            if not self._page:
                return AutomationResult(success=False, operation="screenshot", error="No page active")
            
            if not path:
                timestamp = int(time.time())
                path = f"screenshot_{timestamp}.png"
            
            await self._page.screenshot(path=path, full_page=full_page)
            
            return AutomationResult(
                success=True,
                operation="screenshot",
                screenshot_path=path,
                url=self._page.url,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return AutomationResult(
                success=False,
                operation="screenshot",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def evaluate(self, script: str) -> AutomationResult:
        """Execute JavaScript in page."""
        start_time = time.time()
        
        try:
            if not self._page:
                return AutomationResult(success=False, operation="evaluate", error="No page active")
            
            result = await self._page.evaluate(script)
            
            return AutomationResult(
                success=True,
                operation="evaluate",
                data={"result": result},
                url=self._page.url,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Evaluate failed: {e}")
            return AutomationResult(
                success=False,
                operation="evaluate",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def wait_for_selector(self, selector: str, timeout: float = None) -> AutomationResult:
        """Wait for selector to appear."""
        start_time = time.time()
        
        try:
            if not self._page:
                return AutomationResult(success=False, operation="wait", error="No page active")
            
            await self._page.wait_for_selector(selector, timeout=timeout)
            
            return AutomationResult(
                success=True,
                operation="wait",
                url=self._page.url,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Wait failed: {e}")
            return AutomationResult(
                success=False,
                operation="wait",
                selector=selector,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def extract_links(self) -> AutomationResult:
        """Extract all links from page."""
        start_time = time.time()
        
        try:
            if not self._page:
                return AutomationResult(success=False, operation="extract_links", error="No page active")
            
            links = await self._page.eval_on_selector_all("a", "elements => elements.map(e => ({href: e.href, text: e.textContent}))")
            
            return AutomationResult(
                success=True,
                operation="extract_links",
                data={"links": links},
                url=self._page.url,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Extract links failed: {e}")
            return AutomationResult(
                success=False,
                operation="extract_links",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def fill_form(self, form_data: Dict[str, str]) -> AutomationResult:
        """Fill form with data."""
        start_time = time.time()
        
        try:
            if not self._page:
                return AutomationResult(success=False, operation="fill_form", error="No page active")
            
            for selector, value in form_data.items():
                await self._page.fill(selector, value)
            
            return AutomationResult(
                success=True,
                operation="fill_form",
                data={"filled_fields": list(form_data.keys())},
                url=self._page.url,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Fill form failed: {e}")
            return AutomationResult(
                success=False,
                operation="fill_form",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def search_google(self, query: str) -> AutomationResult:
        """Search Google and return results."""
        start_time = time.time()
        
        try:
            # Navigate to Google
            await self.navigate("https://google.com")
            
            # Fill search box
            await self.type_text("input[name='q']", query)
            
            # Submit search
            await self._page.press("input[name='q']", "Enter")
            
            # Wait for results
            await self.wait_for_selector(".g")
            
            # Extract results
            results = await self._page.eval_on_selector_all(".g", "elements => elements.map(e => ({title: e.querySelector('h3')?.textContent, link: e.querySelector('a')?.href}))")
            
            return AutomationResult(
                success=True,
                operation="google_search",
                data={"query": query, "results": results},
                url=self._page.url,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return AutomationResult(
                success=False,
                operation="google_search",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def new_tab(self, url: str = None) -> AutomationResult:
        """Open new tab."""
        start_time = time.time()
        
        try:
            if not self._context:
                return AutomationResult(success=False, operation="new_tab", error="No browser context")
            
            new_page = await self._context.new_page()
            
            if url:
                await new_page.goto(url)
            
            return AutomationResult(
                success=True,
                operation="new_tab",
                url=new_page.url if url else "",
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"New tab failed: {e}")
            return AutomationResult(
                success=False,
                operation="new_tab",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def get_page_info(self) -> Dict[str, Any]:
        """Get current page information."""
        if not self._page:
            return {}
        
        return {
            "url": self._page.url,
            "title": self._page.title(),
            "browser": self._config.browser_type.value,
            "headless": self._config.headless
        }


# Global web automation engine instance
web_automation_engine = WebAutomationEngine()