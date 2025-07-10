import json
import asyncio
from playwright.async_api import async_playwright
import time

import pytz
from datetime import datetime, timedelta
import re

def get_nepali_date(offset_days=0):
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    today = datetime.now(nepal_tz) - timedelta(days=offset_days)
    return today.strftime('%Y-%m-%d')

async def load_with_nepali_date(base_url, page):
    max_attempts = 5
    for i in range(max_attempts):
        nepali_date = get_nepali_date(i)
        url = re.sub(r"yyyy-mm-dd", nepali_date, base_url)
        print(f"Trying URL: {url}")
        await page.goto(url, wait_until='domcontentloaded')

        try:
            print("Searching for 'No record found' to see if we need to go back'")
            await page.get_by_text('No record found.').wait_for(timeout=3_000)
            print(f"❌ No table for date {nepali_date}, trying previous day...")
        except:
            print(f"✅ Table found for date {nepali_date}")
            return

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
        )

        # Create a new browser context
        context = await browser.new_context()

        async def open_page(bank):
            """Open a single bank's forex page with developer tools"""
            try:
                # TODO: Handle anti_robot
                if bank.get('anti_robot', False):
                    return

                # TODO: Handle parse whole page, I would need to either use the PDF or the whole page and let gemini parse it
                if bank.get('parse_whole_page', False):
                    return

                # Create a new page (tab)
                page = await context.new_page()

                # Navigate to the forex page
                forex_page = bank['forex_page']
                print(f"Opening {bank['name']} - {forex_page}")
                if bank.get('handle_date', False):
                    await load_with_nepali_date(forex_page, page)
                else:
                    await page.goto(forex_page, wait_until='domcontentloaded', timeout=60_000)
                if 'table' in bank and bank['table'] == True:
                    table = page.locator('css=table')
                    if 'table_index' in bank:
                        table = table.nth(bank['table_index'])
                    else:
                        table = table.nth(0)
                    print(await table.evaluate('el => el.outerHTML'))
                elif 'query_selector' in bank:
                    element = await page.wait_for_selector(bank['query_selector'], state='attached')
                    if not element:
                        raise Exception(f'Could not find {bank['query_selector']} in {forex_page}')
                    print(await element.evaluate('el => el.outerHTML'))
                elif 'api' in bank:
                    api = bank['api']
                    api = api.replace('yyyy-mm-dd', '')
                    response = await page.wait_for_event("response", lambda r: api in r.url, timeout=30_000)
                    json_data = await response.json()
                    print(json_data)
                elif 'select_link' in bank:
                    # Only made for Himalayan
                    link = await page.query_selector('a[href^="getRate.php"]')
                    if not link:
                        raise Exception('Could not find link')
                    await link.click()
                    await page.wait_for_load_state('domcontentloaded')

                    table = page.locator('css=table').nth(3)
                    print(await table.evaluate('el => el.outerHTML'))

                print(f"Successfully opened {bank['name']}")

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
