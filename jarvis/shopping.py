"""jarvis.shopping

Shopping assistant for JARVIS.
Search products on Flipkart, Amazon, Myntra, Meesho, and Shopsy.
Compare prices and ratings, return best deals.
"""

import re
import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

try:
    from web_browser import WebBrowser, init_web_browser, web_browser
    WEB_BROWSER_AVAILABLE = True
except ImportError:
    WEB_BROWSER_AVAILABLE = False
    logger.warning("Web browser not available. Shopping search will be limited.")

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class Product:
    """Product information."""
    name: str
    price: float
    original_price: Optional[float]
    discount: Optional[str]
    rating: float
    review_count: int
    platform: str
    link: str
    image: Optional[str]
    in_stock: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @property
    def value_score(self) -> float:
        """Calculate value score (higher is better)."""
        if self.price <= 0:
            return 0
        
        # Score based on rating and price
        # Higher rating = better, lower price = better
        rating_weight = 0.6
        price_weight = 0.4
        
        rating_score = (self.rating / 5.0) * rating_weight
        
        # For price, assume 10000 is baseline, lower is better
        price_score = min(1.0, 10000 / self.price) * price_weight if self.price > 0 else 0
        
        return (rating_score + price_score) * 100


@dataclass
class ShoppingResult:
    """Result from multiple platforms."""
    query: str
    products: List[Product]
    total_found: int
    platforms_searched: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "products": [p.to_dict() for p in self.products],
            "total_found": self.total_found,
            "platforms_searched": self.platforms_searched,
        }
    
    def get_best_deals(self, min_rating: float = 4.0, limit: int = 5) -> List[Product]:
        """Get best deals (4+ rating, lowest price)."""
        # Filter by rating
        filtered = [p for p in self.products if p.rating >= min_rating]
        
        # Sort by price
        filtered.sort(key=lambda x: (x.price, -x.rating))
        
        return filtered[:limit]


class ShoppingAssistant:
    """Shopping assistant for e-commerce platforms."""
    
    PLATFORMS = {
        'amazon': {
            'name': 'Amazon',
            'search_url': 'https://www.amazon.in/s?k={query}',
            'base_url': 'https://www.amazon.in',
        },
        'flipkart': {
            'name': 'Flipkart',
            'search_url': 'https://www.flipkart.com/search?q={query}',
            'base_url': 'https://www.flipkart.com',
        },
        'myntra': {
            'name': 'Myntra',
            'search_url': 'https://www.myntra.com/{query}',
            'base_url': 'https://www.myntra.com',
        },
        'meesho': {
            'name': 'Meesho',
            'search_url': 'https://www.meesho.com/search?q={query}',
            'base_url': 'https://www.meesho.com',
        },
        'shopsy': {
            'name': 'Shopsy',
            'search_url': 'https://shopsy.in/search?q={query}',
            'base_url': 'https://shopsy.in',
        },
        'buyhatke': {
            'name': 'Buyhatke',
            'search_url': 'https://www.buyhatke.com/search?q={query}',
            'base_url': 'https://www.buyhatke.com',
        },
    }
    
    def __init__(self):
        """Initialize shopping assistant."""
        self.browser = None
        logger.info("ShoppingAssistant initialized")
    
    async def _ensure_browser(self):
        """Ensure web browser is available."""
        if not WEB_BROWSER_AVAILABLE:
            return False
        
        if not self.browser:
            self.browser = init_web_browser(headless=True)
        
        return True
    
    def _clean_price(self, price_text: str) -> float:
        """Extract numeric price from text."""
        if not price_text:
            return 0.0
        
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.]', '', price_text)
        try:
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0
    
    def _parse_rating(self, rating_text: str) -> float:
        """Parse rating from text."""
        if not rating_text:
            return 0.0
        
        # Extract first number
        match = re.search(r'(\d+\.?\d*)', rating_text)
        if match:
            try:
                rating = float(match.group(1))
                return min(5.0, rating)  # Cap at 5
            except:
                pass
        
        return 0.0
    
    async def search_amazon(self, query: str) -> List[Product]:
        """Search products on Amazon."""
        products = []
        
        try:
            if not await self._ensure_browser():
                return products
            
            url = self.PLATFORMS['amazon']['search_url'].format(query=quote_plus(query))
            content = await self.browser.visit_page(url)
            
            if not content:
                return products
            
            # Parse with BeautifulSoup for better extraction
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content.text, 'html.parser')
            
            # Find product containers (Amazon structure changes frequently)
            selectors = [
                '[data-component-type="s-search-result"]',
                '.s-result-item',
                '.a-section',
            ]
            
            for selector in selectors:
                items = soup.select(selector)[:10]  # Limit to 10
                
                for item in items:
                    try:
                        # Extract name
                        name_elem = item.select_one('h2 a span, .a-text-normal')
                        name = name_elem.get_text(strip=True) if name_elem else "Unknown"
                        
                        # Extract price
                        price_elem = item.select_one('.a-price .a-offscreen, .a-price-whole')
                        price_text = price_elem.get_text(strip=True) if price_elem else "0"
                        price = self._clean_price(price_text)
                        
                        # Extract rating
                        rating_elem = item.select_one('.a-icon-alt, .a-star-small')
                        rating_text = rating_elem.get_text(strip=True) if rating_elem else "0"
                        rating = self._parse_rating(rating_text)
                        
                        # Extract link
                        link_elem = item.select_one('h2 a')
                        link = ''
                        if link_elem and link_elem.get('href'):
                            link = 'https://amazon.in' + link_elem['href']
                        
                        # Extract reviews count
                        reviews_elem = item.select_one('a[href*="reviews"] span')
                        review_count = 0
                        if reviews_elem:
                            review_text = reviews_elem.get_text(strip=True)
                            review_count = int(re.sub(r'[^\d]', '', review_text) or 0)
                        
                        if name and price > 0:
                            products.append(Product(
                                name=name[:200],
                                price=price,
                                original_price=None,
                                discount=None,
                                rating=rating,
                                review_count=review_count,
                                platform='Amazon',
                                link=link,
                                image=None,
                                in_stock=True,
                            ))
                    except Exception as e:
                        logger.debug(f"Error parsing Amazon item: {e}")
                        continue
                
                if products:
                    break  # Found products with this selector
            
            logger.info(f"Amazon: Found {len(products)} products")
            
        except Exception as e:
            logger.exception(f"Amazon search failed: {e}")
        
        return products
    
    async def search_flipkart(self, query: str) -> List[Product]:
        """Search products on Flipkart."""
        products = []
        
        try:
            if not await self._ensure_browser():
                return products
            
            url = self.PLATFORMS['flipkart']['search_url'].format(query=quote_plus(query))
            content = await self.browser.visit_page(url)
            
            if not content:
                return products
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content.text, 'html.parser')
            
            # Try different selectors
            selectors = [
                '._1AtVbE',
                '._2kHMtA',
                '._4ddWXP',
            ]
            
            for selector in selectors:
                items = soup.select(selector)[:10]
                
                for item in items:
                    try:
                        # Name
                        name_elem = item.select_one('._4rR01T, .s1Q9rs, a[title]')
                        name = name_elem.get_text(strip=True) if name_elem else "Unknown"
                        if not name:
                            title_attr = name_elem.get('title') if name_elem else None
                            name = title_attr or "Unknown"
                        
                        # Price
                        price_elem = item.select_one('._30jeq3, ._8Vcv41, ._3I9_wc')
                        price_text = price_elem.get_text(strip=True) if price_elem else "0"
                        price = self._clean_price(price_text)
                        
                        # Original price
                        original_elem = item.select_one('._3I9_wc, ._27UcVY')
                        original_price = None
                        if original_elem:
                            original_price = self._clean_price(original_elem.get_text(strip=True))
                        
                        # Rating
                        rating_elem = item.select_one('._3LWZlK, ._2_R_DZ')
                        rating_text = rating_elem.get_text(strip=True) if rating_elem else "0"
                        rating = self._parse_rating(rating_text)
                        
                        # Link
                        link_elem = item.select_one('a[href]')
                        link = ''
                        if link_elem and link_elem.get('href'):
                            link = 'https://flipkart.com' + link_elem['href']
                        
                        # Reviews
                        reviews_elem = item.select_one('._2_R_DZ span')
                        review_count = 0
                        if reviews_elem:
                            review_text = reviews_elem.get_text(strip=True)
                            match = re.search(r'(\d+)', re.sub(r',', '', review_text))
                            if match:
                                review_count = int(match.group(1))
                        
                        if name and price > 0:
                            products.append(Product(
                                name=name[:200],
                                price=price,
                                original_price=original_price if original_price > price else None,
                                discount=None,
                                rating=rating,
                                review_count=review_count,
                                platform='Flipkart',
                                link=link,
                                image=None,
                                in_stock=True,
                            ))
                    except Exception as e:
                        logger.debug(f"Error parsing Flipkart item: {e}")
                        continue
                
                if products:
                    break
            
            logger.info(f"Flipkart: Found {len(products)} products")
            
        except Exception as e:
            logger.exception(f"Flipkart search failed: {e}")
        
        return products
    
    async def search_simple_platform(self, query: str, platform: str) -> List[Product]:
        """Simple search for platforms without complex parsing."""
        products = []
        
        try:
            if not await self._ensure_browser():
                return products
            
            url = self.PLATFORMS[platform]['search_url'].format(query=quote_plus(query))
            content = await self.browser.visit_page(url)
            
            if not content:
                return products
            
            # Simple extraction - just note that search was performed
            # These platforms often have anti-bot measures
            logger.info(f"{platform.capitalize()}: Search performed, manual browsing may be needed")
            
            # Add a placeholder product with link to search
            products.append(Product(
                name=f"Search results for '{query}' on {platform.capitalize()}",
                price=0,
                original_price=None,
                discount=None,
                rating=0,
                review_count=0,
                platform=platform.capitalize(),
                link=url,
                image=None,
                in_stock=True,
            ))
            
        except Exception as e:
            logger.exception(f"{platform} search failed: {e}")
        
        return products
    
    async def search_product(self, query: str, platforms: Optional[List[str]] = None) -> ShoppingResult:
        """Search product across multiple platforms.
        
        Args:
            query: Product to search for
            platforms: List of platforms to search (default: all)
            
        Returns:
            ShoppingResult with all products
        """
        if not platforms:
            platforms = ['amazon', 'flipkart', 'myntra', 'meesho', 'shopsy', 'buyhatke']
        
        all_products = []
        searched_platforms = []
        
        # Search each platform
        if 'amazon' in platforms:
            amazon_products = await self.search_amazon(query)
            all_products.extend(amazon_products)
            if amazon_products:
                searched_platforms.append('Amazon')
        
        if 'flipkart' in platforms:
            flipkart_products = await self.search_flipkart(query)
            all_products.extend(flipkart_products)
            if flipkart_products:
                searched_platforms.append('Flipkart')
        
        # Simple searches for other platforms
        for platform in ['myntra', 'meesho', 'shopsy']:
            if platform in platforms:
                products = await self.search_simple_platform(query, platform)
                all_products.extend(products)
                searched_platforms.append(platform.capitalize())
        
        # Buyhatke price comparison (always add link, don't search for products)
        if 'buyhatke' in platforms:
            searched_platforms.append('Buyhatke')
        
        return ShoppingResult(
            query=query,
            products=all_products,
            total_found=len(all_products),
            platforms_searched=searched_platforms,
        )
    
    def format_results(self, result: ShoppingResult, min_rating: float = 4.0, limit: int = 5) -> str:
        """Format shopping results for display."""
        lines = [
            f"🛒 **Shopping Results: {result.query}**",
            f"   Platforms searched: {', '.join(result.platforms_searched)}",
            f"   Total products found: {result.total_found}",
            "",
        ]
        
        # Get best deals
        best_deals = result.get_best_deals(min_rating=min_rating, limit=limit)
        
        if not best_deals:
            lines.extend([
                "⚠️ No products found with 4+ star rating.",
                "Showing all found products:",
                "",
            ])
            # Show top products regardless of rating
            sorted_products = sorted(result.products, key=lambda x: x.price)[:limit]
            best_deals = sorted_products
        else:
            lines.extend([
                f"✨ **Top {len(best_deals)} Deals (4+ ★ rating, lowest price):**",
                "",
            ])
        
        for i, product in enumerate(best_deals, 1):
            # Price display
            price_display = f"₹{product.price:,.0f}"
            if product.original_price and product.original_price > product.price:
                discount = ((product.original_price - product.price) / product.original_price) * 100
                price_display = f"₹{product.price:,.0f} ~~₹{product.original_price:,.0f}~~ (-{discount:.0f}%)"
            
            # Rating stars
            stars = "★" * int(product.rating) + "☆" * (5 - int(product.rating))
            
            lines.extend([
                f"**{i}. [{product.platform}] {product.name[:80]}**",
                f"   💰 {price_display}",
                f"   ⭐ {stars} ({product.rating:.1f}) - {product.review_count} reviews",
                f"   🔗 [View Product]({product.link})",
                "",
            ])
        
        if not best_deals:
            lines.append("❌ No products found. Please try a more specific search.")
        
        # Add Buyhatke price comparison link
        buyhatke_url = f"https://www.buyhatke.com/search?q={quote_plus(result.query)}"
        lines.extend([
            "",
            "📊 **[Compare Prices on Buyhatke]" + f"({buyhatke_url})**",
            "   💡 Buyhatke compares prices across all major platforms to find the best deals!",
        ])
        
        return "\n".join(lines)


# Global instance
shopping_assistant: Optional[ShoppingAssistant] = None


def init_shopping_assistant():
    """Initialize global shopping assistant."""
    global shopping_assistant
    shopping_assistant = ShoppingAssistant()
    return shopping_assistant


async def search_product(query: str, platforms: Optional[List[str]] = None) -> ShoppingResult:
    """Search for a product."""
    if not shopping_assistant:
        init_shopping_assistant()
    
    return await shopping_assistant.search_product(query, platforms)


def tool_shopping_search(query: str, platforms: str = "all") -> str:
    """Tool: Search for products (for LLM)."""
    import asyncio
    
    if not shopping_assistant:
        init_shopping_assistant()
    
    platform_list = None if platforms == "all" else platforms.split(',')
    
    try:
        result = asyncio.run(search_product(query, platform_list))
        return shopping_assistant.format_results(result)
    except Exception as e:
        return f"Error searching for products: {str(e)}"


def tool_compare_prices(query: str) -> str:
    """Tool: Compare prices across platforms."""
    return tool_shopping_search(query)


SHOPPING_REGISTRY = {
    "shopping_search": tool_shopping_search,
    "compare_prices": tool_compare_prices,
}
