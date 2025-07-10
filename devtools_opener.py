import json
import asyncio
from playwright.async_api import async_playwright

async def open_bank_pages(json_file_path):
    """
    Opens all bank forex pages from nepal_banks.json in separate tabs
    with developer tools opened for each page.
    """

    # Load the JSON file
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{json_file_path}'.")
        return

    banks = data.get('banks', [])

    if not banks:
        print("No banks found in the JSON file.")
        return

    print(f"Found {len(banks)} banks. Opening forex pages...")

    async with async_playwright() as p:
        # Launch Firefox browser
        browser = await p.chromium.launch(
            headless=False,  # Keep browser visible
            devtools=True    # Enable developer tools
        )

        # Create a new browser context
        context = await browser.new_context()

        # Create the first page to act as our main tab
        main_page = await context.new_page()

        async def open_page(bank):
            """Open a single bank's forex page with developer tools"""
            try:
                # Create a new page (tab)
                # page = await context.new_page()

                # Navigate to the forex page
                print(f"Opening {bank['name']} - {bank['forex_page']}")
                print(f"window.open('{bank['forex_page']}', '_blank')")
                await main_page.evaluate(f"window.open('{bank['forex_page']}', '_blank')")

                page = context.pages[0]
                # Open developer tools
                await page.evaluate("() => { if (window.chrome && window.chrome.devtools) { window.chrome.devtools.panels.create('Custom', 'icon.png', 'panel.html'); } }")

                # Alternative method to open dev tools (keyboard shortcut)
                await page.keyboard.press('F12')

                print(f"Successfully opened {bank['name']} with developer tools")

            except Exception as e:
                print(f"Error opening {bank['name']}: {str(e)}")

        # Create tasks for all banks
        for bank in banks:
            if bank.get('forex_page'):  # Only process banks with forex_page
                await open_page(bank)
            else:
                print(f"Skipping {bank.get('name', 'Unknown')} - no forex_page found")

        print("Press Enter to close the browser...")
        input()  # Wait for user input before closing

        # Close the browser
        await browser.close()

async def main():
    """Main function to run the program"""
    json_file_path = "nepal_banks.json"
    await open_bank_pages(json_file_path)

if __name__ == "__main__":
    # Run the async function
    asyncio.run(main())
