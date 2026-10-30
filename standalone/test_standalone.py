from playwright.sync_api import Page


def test_solara_basics(page: Page):
    page.goto("http://localhost:8765/", wait_until="commit")
    print('Jdaviz Loaded')
    page.locator('text=Load Local File').wait_for()


def test_pysiaf_imported(page: Page):

    page.goto("http://localhost:8765/", wait_until="commit")
    print('Jdaviz Loaded')
    page.locator('text=Load Local File').wait_for()



    page.locator(".v-input", has_text="Source").click()

    print("Dropdown clicked successfully.")

    dropdown_menu = page.get_by_role("listbox")
    dropdown_menu.wait_for(state="visible")

    target_option = dropdown_menu.get_by_role("option", name="url")
    target_option.wait_for(state="visible")
    target_option.click()

    print('Selected URL')

    source = page.get_by_label("URL")
    source.wait_for()
    source.click()
    source.fill("mast:jwst/product/jw01334-o001_t001_niriss_clear-f150w_i2d.fits")

    page.get_by_text("Align by", exact=True)

    print('Image loaded')

    import_table = page.get_by_role("button", name="Import")
    import_table.first.click()

    print('Import sucessful')

    page.locator('button').nth(4).click()
    page.locator("text=Footprints").first.click()

    footprint_locator = page.get_by_text("Center RA/Dec", exact=True)
    footprint_locator.scroll_into_view_if_needed()

    print("Footprint plugin loaded")
