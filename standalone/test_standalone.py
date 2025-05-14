import re

from playwright.sync_api import Page, expect


def test_solara_basics(page: Page):
    page.goto("http://localhost:8765/")

    # when jdaviz is loaded (button at the top left)
    page.locator("text=Welcome to Jdaviz").wait_for()

    # clear the input, so that all the tiles can be clicked
    page.locator("input").fill("")

    page.locator("text=Cubeviz").click()
    # make sure cubeviz load properly
    page.locator("text=Import data").wait_for()
