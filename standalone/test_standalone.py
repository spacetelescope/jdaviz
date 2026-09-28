from playwright.sync_api import Page


def test_solara_basics(page: Page):

    page.goto("http://localhost:8765/")
    page.locator('text=Welcome to Jdaviz!').wait_for()


def test_solara_astroquery_gaia(page: Page):

    print('Testing Astroquery with Gaia loads')

    page.goto("http://localhost:8765/")
    page.locator('text=Welcome to Jdaviz!').wait_for()

    # when jdaviz is loaded, click launch
    page.locator('img[alt="Launch Jdaviz"]').click()

    # find the string text "Source"
    page.locator(".v-input", has_text="Source").click()

    print('Dropdown found sucessfully')

    # wait for dropdown menu
    dropdown_menu = page.get_by_role("listbox")
    dropdown_menu.wait_for(state="visible")

    # Select "astroquery" from dropdown
    target_option = dropdown_menu.get_by_role("option", name="astroquery")
    target_option.wait_for(state="visible")
    target_option.click()

    print("astroquery selected")

    # change parameters: coordinates
    source = page.get_by_label("Source/Coordinates")
    source.wait_for()
    source.click()
    source.fill("259.37380294, 43.20553169")

    # change parameters: radius
    radius_field = page.get_by_label("Radius")
    radius_field.fill("1")

    # change parameters: unit -> arcmin
    page.locator(".v-input", has_text="Unit").click()
    dropdown_menu = page.get_by_role("listbox")
    dropdown_menu.wait_for(state="visible")
    target_option = dropdown_menu.get_by_role("option", name="arcmin")
    target_option.wait_for(state="visible")
    target_option.click()

    # change parameters: Telescope -> Gaia
    page.locator(".v-input", has_text="Telescope").click()
    dropdown_menu = page.get_by_role("listbox")
    dropdown_menu.wait_for(state="visible")
    target_option = dropdown_menu.get_by_role("option", name="Gaia")
    target_option.wait_for(state="visible")
    target_option.click()

    # Set Max Results to a small number to keep test quick
    max_results = page.get_by_label("Max Results")
    max_results.fill("2")

    print("All parameters filled in.")

    # click the Query Archive button
    page.locator("text=Query Archive").first.click()

    print("Queried Gaia sucessfully")

    # # wait for table information to appear in the Query Results section
    # table_cols = page.get_by_text("Select Additional Columns", exact=True)
    # table_cols.scroll_into_view_if_needed()
    # table_cols.wait_for(timeout=60_000)

    # select format as catalog
    page.locator(".v-input", has_text="Format").click()
    dropdown_menu = page.get_by_role("listbox")
    dropdown_menu.wait_for(state="visible")
    target_option = dropdown_menu.get_by_role("option", name="Catalog")
    target_option.wait_for(state="visible")
    target_option.click()

    # import table as scatter plot
    import_table = page.get_by_role("button", name="Import")
    # import_table.scroll_into_view_if_needed()
    import_table.first.click()

    print('Imported Catalog sucessfully.')

    # check logger to make sure catalog loaded successfully.
    page.locator('button').nth(3).click()
    page.locator("text=Logger").first.click()
    table_success = page.locator('.v-alert__content',
                                 has_text="Data 'Catalog' successfully added.")
    table_success.wait_for()

    print("Found logger message showing catalog loaded")