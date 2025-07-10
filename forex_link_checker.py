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

        # Track successful and failed links
        successful_links = []
        failed_links = []

        print("\nOpening forex links...")
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
                # Create a new page (tab) for each bank
                page = await context.new_page()

                print(f"{i:2d}. Opening: {bank_name} ({bank_class})")
                print(f"    URL: {forex_url}")

                # Navigate to the forex page
                response = await page.goto(forex_url, timeout=10000)  # 10 second timeout

                # Check if the page loaded successfully
                if response and response.status < 400:
                    print(f"    Status: ✓ Loaded successfully (HTTP {response.status})")
                    successful_links.append({'bank': bank_name, 'class': bank_class, 'url': forex_url})
                else:
                    print(f"    Status: ✗ Failed to load (HTTP {response.status if response else 'No response'})")
                    failed_links.append({'bank': bank_name, 'class': bank_class, 'url': forex_url, 'reason': f'HTTP {response.status if response else "No response"}'})

                # Wait a bit before opening the next link
                await asyncio.sleep(2)

            except Exception as e:
                print(f"    Status: ✗ Error - {str(e)}")
                failed_links.append({'bank': bank_name, 'class': bank_class, 'url': forex_url, 'reason': str(e)})

                # Close the page if it was created but failed
                try:
                    await page.close()
                except:
                    pass

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
