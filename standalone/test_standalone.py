import re

from playwright.sync_api import Page, expect


def test_solara_basics(page: Page):
    page.goto("http://localhost:8765/")

    # when jdaviz is loaded (button at the top left)
    page.locator("text=Welcome to Jdaviz").wait_for()
