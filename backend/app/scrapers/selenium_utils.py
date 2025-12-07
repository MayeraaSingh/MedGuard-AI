"""
MedGuard AI - Selenium Utilities
Helper functions for web scraping with Selenium
"""

import logging
from typing import Optional, List, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)


class SeleniumDriver:
    """Managed Selenium WebDriver with common configurations."""
    
    def __init__(self, headless: bool = True, timeout: int = 10):
        """
        Initialize Selenium driver.
        
        Args:
            headless: Run browser in headless mode
            timeout: Default timeout for waits (seconds)
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        
        logger.info(f"Initialized Selenium driver (headless={headless})")
    
    def start(self):
        """Start the WebDriver."""
        if self.driver:
            logger.warning("Driver already started")
            return
        
        try:
            options = Options()
            
            if self.headless:
                options.add_argument('--headless')
            
            # Common options for stability
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            # User agent to avoid detection
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(self.timeout)
            
            logger.info("WebDriver started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start WebDriver: {e}")
            raise
    
    def stop(self):
        """Stop the WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("WebDriver stopped")
            except Exception as e:
                logger.error(f"Error stopping WebDriver: {e}")
    
    def get(self, url: str):
        """Navigate to URL."""
        if not self.driver:
            self.start()
        
        logger.debug(f"Navigating to: {url}")
        self.driver.get(url)
        time.sleep(1)  # Brief pause for page load
    
    def get_page_source(self) -> str:
        """Get current page source."""
        if not self.driver:
            raise RuntimeError("Driver not started")
        
        return self.driver.page_source
    
    def get_soup(self) -> BeautifulSoup:
        """Get BeautifulSoup object of current page."""
        return BeautifulSoup(self.get_page_source(), 'html.parser')
    
    def wait_for_element(self, by: By, value: str, timeout: Optional[int] = None) -> bool:
        """
        Wait for element to be present.
        
        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Custom timeout (uses default if not provided)
            
        Returns:
            True if element found, False otherwise
        """
        if not self.driver:
            raise RuntimeError("Driver not started")
        
        timeout = timeout or self.timeout
        
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            logger.debug(f"Element found: {value}")
            return True
        except TimeoutException:
            logger.warning(f"Element not found: {value}")
            return False
    
    def find_element_safe(self, by: By, value: str) -> Optional[Any]:
        """
        Safely find element without throwing exception.
        
        Args:
            by: Selenium By locator type
            value: Locator value
            
        Returns:
            Element if found, None otherwise
        """
        if not self.driver:
            raise RuntimeError("Driver not started")
        
        try:
            return self.driver.find_element(by, value)
        except NoSuchElementException:
            return None
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def wait_for_element(driver: webdriver.Chrome, by: By, value: str, timeout: int = 10) -> bool:
    """
    Wait for element to be present.
    
    Args:
        driver: Selenium WebDriver
        by: Selenium By locator type
        value: Locator value
        timeout: Timeout in seconds
        
    Returns:
        True if element found, False otherwise
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return True
    except TimeoutException:
        return False


def extract_table_data(soup: BeautifulSoup, table_selector: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract data from HTML table.
    
    Args:
        soup: BeautifulSoup object
        table_selector: CSS selector for table (finds first table if None)
        
    Returns:
        List of dictionaries with table data
    """
    if table_selector:
        table = soup.select_one(table_selector)
    else:
        table = soup.find('table')
    
    if not table:
        logger.warning("No table found")
        return []
    
    rows = []
    headers = []
    
    # Extract headers
    header_row = table.find('thead')
    if header_row:
        headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
    else:
        # Try first row
        first_row = table.find('tr')
        if first_row:
            headers = [th.get_text(strip=True) for th in first_row.find_all(['th', 'td'])]
    
    # Extract data rows
    tbody = table.find('tbody') or table
    for tr in tbody.find_all('tr'):
        cells = tr.find_all(['td', 'th'])
        
        if not cells:
            continue
        
        if headers:
            row_data = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    row_data[headers[i]] = cell.get_text(strip=True)
        else:
            row_data = {f'col_{i}': cell.get_text(strip=True) for i, cell in enumerate(cells)}
        
        rows.append(row_data)
    
    logger.debug(f"Extracted {len(rows)} rows from table")
    return rows


def take_screenshot(driver: webdriver.Chrome, filepath: str):
    """
    Take screenshot of current page.
    
    Args:
        driver: Selenium WebDriver
        filepath: Path to save screenshot
    """
    try:
        driver.save_screenshot(filepath)
        logger.info(f"Screenshot saved: {filepath}")
    except Exception as e:
        logger.error(f"Screenshot error: {e}")


def scroll_to_bottom(driver: webdriver.Chrome, pause_time: float = 0.5):
    """
    Scroll to bottom of page (useful for infinite scroll).
    
    Args:
        driver: Selenium WebDriver
        pause_time: Pause between scrolls
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)
        
        # Check if reached bottom
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        
        last_height = new_height


def handle_captcha_wait(driver: webdriver.Chrome, timeout: int = 60):
    """
    Wait for user to manually solve CAPTCHA.
    
    Args:
        driver: Selenium WebDriver
        timeout: Maximum wait time
    """
    logger.warning("CAPTCHA detected. Please solve manually...")
    time.sleep(timeout)
