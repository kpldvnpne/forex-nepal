import json
import asyncio
from playwright.async_api import async_playwright
import time

async def open_bank_pages(json_file_path):
    """
    Opens all bank forex pages from nepal_banks.json in separate tabs
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
        # Launch Chromium browser
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
                await context.pages[-1].evaluate(f"window.open('{bank['forex_page']}', '_blank', 'noopener,noreferrer')")

                print(f"Successfully opened {bank['name']} with developer tools")

            except Exception as e:
                print(f"Error opening {bank['name']}: {str(e)}")

        # Create tasks for all banks
        for bank in banks:
          await open_page(bank)

        for page in context.pages:
          print('Waiting for document to load')
          await page.wait_for_load_state('domcontentloaded')

        while len(context.pages) != 26:
          print(f'Not enough pages loaded. Only loaded {len(context.pages)} Waiting 1 more second ...')
          time.sleep(1)

        print(f"{len(context.pages)}, {len(context.background_pages)}")

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
