from playwright.sync_api import Page


def test_solara_basics(page: Page):
    page.goto("http://localhost:8765/", wait_until="commit")
    page.locator('text=Load Local File').wait_for()

