from playwright.sync_api import Page


def test_solara_basics(page: Page):

    page.goto("http://localhost:8765/")
    page.locator('text=Welcome to Jdaviz!').wait_for()
