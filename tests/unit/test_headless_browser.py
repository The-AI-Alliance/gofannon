import pytest
from gofannon.headless_browser.headless_browser_get import HeadlessBrowserGet

def test_headless_browser_get():
    # Initialize the HeadlessBrowserGet tool.
    browser_get = HeadlessBrowserGet()
    # This is a really old sample page I made, anything could be better
    url = "https://app-template-37928.web.app"
    page_source = browser_get.fn(url)
    # Check that the fetched page source contains expected content.
    assert "home works!" in page_source