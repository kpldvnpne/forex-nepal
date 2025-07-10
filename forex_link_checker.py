import json
import asyncio
from playwright.async_api import async_playwright
import time

async def check_forex_links(json_file_path):
    """
    Opens all forex links from the JSON file in Firefox browser tabs
    """

    # Load the JSON file
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: JSON file '{json_file_path}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{json_file_path}'.")
        return

    banks = data.get('banks', [])

    if not banks:
        print("No banks found in the JSON file.")
        return

    print(f"Found {len(banks)} banks in the JSON file.")
    print("Starting Firefox browser...")

    async with async_playwright() as p:
        # Launch Firefox browser
        browser = await p.firefox.launch(
            headless=False,  # Keep browser visible
            slow_mo=1000,    # Add slight delay for better visibility
        )

        # Create a new browser context
        context = await browser.new_context()

        # Create the first page to act as our main tab
        main_page = await context.new_page()

        # Track successful and failed links
        successful_links = []
        failed_links = []

        print("\nOpening forex links in new tabs...")
        print("=" * 50)

        for i, bank in enumerate(banks, 1):
            bank_name = bank.get('name', 'Unknown Bank')
            bank_class = bank.get('class', 'Unknown')
            forex_url = bank.get('forex_page', '')

            if not forex_url:
                print(f"{i:2d}. {bank_name} ({bank_class}) - No forex URL provided")
                failed_links.append({'bank': bank_name, 'class': bank_class, 'reason': 'No URL'})
                continue

            try:
                print(f"{i:2d}. Opening: {bank_name} ({bank_class})")
                print(f"    URL: {forex_url}")

                # Open link in new tab using JavaScript
                await main_page.evaluate(f"window.open('{forex_url}', '_blank')")

                # Wait for the new tab to be created
                await asyncio.sleep(1)

                # Get all pages (tabs) in the context
                pages = context.pages

                # Find the newly created tab (last one)
                if len(pages) > i:  # We have a new tab
                    new_tab = pages[-1]

                    # Wait for the page to load
                    try:
                        await new_tab.wait_for_load_state('networkidle', timeout=10000)

                        # Check the final URL to see if it loaded properly
                        current_url = new_tab.url

                        if current_url and not current_url.startswith('about:blank'):
                            print(f"    Status: ✓ Loaded successfully")
                            print(f"    Final URL: {current_url}")
                            successful_links.append({'bank': bank_name, 'class': bank_class, 'url': forex_url, 'final_url': current_url})
                        else:
                            print(f"    Status: ✗ Failed to load properly")
                            failed_links.append({'bank': bank_name, 'class': bank_class, 'url': forex_url, 'reason': 'Blank page or failed to load'})

                    except Exception as tab_error:
                        print(f"    Status: ✗ Error loading tab - {str(tab_error)}")
                        failed_links.append({'bank': bank_name, 'class': bank_class, 'url': forex_url, 'reason': str(tab_error)})

                else:
                    print(f"    Status: ✗ Failed to create new tab")
                    failed_links.append({'bank': bank_name, 'class': bank_class, 'url': forex_url, 'reason': 'Tab creation failed'})

                # Wait a bit before opening the next link
                await asyncio.sleep(2)

            except Exception as e:
                print(f"    Status: ✗ Error - {str(e)}")
                failed_links.append({'bank': bank_name, 'class': bank_class, 'url': forex_url, 'reason': str(e)})

        # Print summary
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"Total banks processed: {len(banks)}")
        print(f"Successfully loaded: {len(successful_links)}")
        print(f"Failed to load: {len(failed_links)}")

        if failed_links:
            print("\nFailed links:")
            for failed in failed_links:
                print(f"  - {failed['bank']} ({failed['class']}): {failed['reason']}")

        print(f"\nAll {len(successful_links)} working links are now open in Firefox tabs.")
        print("You can now manually verify each forex page.")
        print("Press Enter to close all tabs and exit...")

        # Wait for user input before closing
        input()

        # Close browser
        await browser.close()
        print("Browser closed. Goodbye!")

async def main():
    """
    Main function to run the forex link checker
    """
    # You can change this path to wherever you save the JSON file
    json_file_path = "nepal_banks.json"

    print("Nepal Banks Forex Link Checker")
    print("=" * 40)
    print(f"Looking for JSON file: {json_file_path}")

    # Check if custom path is needed
    custom_path = input(f"Press Enter to use '{json_file_path}' or type a different path: ").strip()
    if custom_path:
        json_file_path = custom_path

    await check_forex_links(json_file_path)

if __name__ == "__main__":
    print("Installing required packages...")
    print("Make sure you have installed: pip install playwright")
    print("And run: playwright install firefox")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
