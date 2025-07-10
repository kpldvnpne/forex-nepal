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

        print("\nOpening all forex links concurrently...")
        print("=" * 50)

        # Function to open a single bank's forex page
        async def open_bank_forex(bank, index):
            bank_name = bank.get('name', 'Unknown Bank')
            bank_class = bank.get('class', 'Unknown')
            forex_url = bank.get('forex_page', '')

            if not forex_url:
                print(f"{index:2d}. {bank_name} ({bank_class}) - No forex URL provided")
                return {'bank': bank_name, 'class': bank_class, 'reason': 'No URL', 'status': 'failed'}

            try:
                print(f"{index:2d}. Opening: {bank_name} ({bank_class})")
                print(f"    URL: {forex_url}")

                # Open link in new tab using JavaScript
                await main_page.evaluate(f"window.open('{forex_url}', '_blank')")

                # Wait a moment for tab creation
                await asyncio.sleep(0.5)

                return {'bank': bank_name, 'class': bank_class, 'url': forex_url, 'status': 'opened'}

            except Exception as e:
                print(f"    Status: ✗ Error - {str(e)}")
                return {'bank': bank_name, 'class': bank_class, 'url': forex_url, 'reason': str(e), 'status': 'failed'}

        # Open all links concurrently
        tasks = []
        for i, bank in enumerate(banks, 1):
            task = open_bank_forex(bank, i)
            tasks.append(task)

        # Execute all tasks concurrently
        print(f"\nStarting concurrent opening of {len(tasks)} forex pages...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Wait for all tabs to be created
        print("\nWaiting for all tabs to be created...")
        await asyncio.sleep(3)

        # Get all pages and try to validate them
        all_pages = context.pages
        print(f"\nFound {len(all_pages)} total tabs (including main page)")

        # Process results
        for result in results:
            if isinstance(result, Exception):
                failed_links.append({'bank': 'Unknown', 'class': 'Unknown', 'reason': str(result), 'url': 'Unknown'})
            elif result['status'] == 'failed':
                failed_links.append(result)
            elif result['status'] == 'opened':
                successful_links.append(result)

        # Optional: Try to validate pages that were opened
        print("\nValidating opened pages...")
        validated_successful = []
        validated_failed = []

        # Skip the main page (index 0) and check the rest
        for i, page in enumerate(all_pages[1:], 1):
            try:
                # Wait for page to load with a shorter timeout for concurrent loading
                await page.wait_for_load_state('domcontentloaded', timeout=5000)
                current_url = page.url

                if current_url and not current_url.startswith('about:blank'):
                    print(f"    Tab {i}: ✓ Loaded - {current_url}")
                    validated_successful.append({'tab': i, 'url': current_url})
                else:
                    print(f"    Tab {i}: ✗ Failed to load properly")
                    validated_failed.append({'tab': i, 'reason': 'Blank or failed to load'})

            except Exception as e:
                print(f"    Tab {i}: ✗ Error - {str(e)}")
                validated_failed.append({'tab': i, 'reason': str(e)})

        print(f"\nValidation complete:")
        print(f"  Successfully loaded tabs: {len(validated_successful)}")
        print(f"  Failed to load tabs: {len(validated_failed)}")

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
