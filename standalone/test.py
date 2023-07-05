import re

from playwright.sync_api import Page, expect


def test_voila_basics(page: Page):
    page.goto("http://localhost:8866/")
    
    # basic voila is loaded
    page.locator("body.theme-light").wait_for()
    # when jdaviz is loaded (button at the top left)
    page.locator("text=Import Data").wait_for()
