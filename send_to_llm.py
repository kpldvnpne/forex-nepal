import json
import asyncio
from playwright.async_api import async_playwright
import time

import pytz
from datetime import datetime, timedelta, timezone
import re

from bs4 import BeautifulSoup

def get_nepali_date(offset_days=0):
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    today = datetime.now(nepal_tz) - timedelta(days=offset_days)
    return today.strftime('%Y-%m-%d')

def get_utc_now_iso_string() -> str:
    """
    Returns the current time in UTC as a standard ISO 8601 string.
    Example output: '2023-10-27T10:30:55.123456Z'
    """
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

def clean_html_for_llm(html_content: str) -> str:
    attributes_to_keep = ['href', 'src', 'colspan', 'rowspan']

    soup = BeautifulSoup(html_content, 'html.parser')

    # Iterate through all tags in the document
    for tag in soup.find_all(True):
        # Create a new dictionary of attributes, keeping only the safe ones
        safe_attrs = {}
        for attr, value in tag.attrs.items():
            if attr in attributes_to_keep:
                safe_attrs[attr] = value

        # Replace the tag's attributes with the filtered ones
        tag.attrs = safe_attrs

    # Return the "prettified" HTML, which is nicely indented
    return soup.prettify()

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

def create_prompt_from_template(
    data_to_insert: str,
    prompt_filepath: str = "prompt.txt",
    placeholder: str = "{PASTE_THE_BANK_DATA_HERE}"
) -> str:
    try:
        with open(prompt_filepath, 'r', encoding='utf-8') as f:
            template_string = f.read()
    except FileNotFoundError:
        print(f"Error: The prompt file was not found at '{prompt_filepath}'")
        raise

    final_prompt = template_string.replace(placeholder, data_to_insert)
    return final_prompt

import os
from typing import Optional, Dict, Any

import google.generativeai as genai
from dotenv import load_dotenv

def send_prompt_to_gemini(prompt: str) -> Optional[Dict[str, Any]]:
    # Load environment variables from the .env file
    load_dotenv()

    # 1. Get the API key from environment variables
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file or environment variables.")
        return None

    try:
        # 2. Configure the generative AI client
        genai.configure(api_key=api_key)

        # 3. Set up the model configuration
        # Crucially, we instruct the model to return its response as JSON.
        generation_config = {
            "response_mime_type": "application/json",
        }

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=generation_config
        )

        # 4. Send the prompt and get the response
        print("Sending prompt to Gemini...")
        response = model.generate_content(prompt)

        # 5. The response.text will be a JSON string, so we parse it
        return json.loads(response.text)

    except Exception as e:
        print(f"An error occurred while communicating with the Gemini API: {e}")
        return None

async def open_bank_pages(json_file_path, concurrent=False):
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
                    await page.goto(forex_page, wait_until='domcontentloaded', timeout=240_000)

                # Access content in different way
                html = None
                json_data = None
                if 'table' in bank and bank['table'] == True:
                    table = page.locator('css=table')
                    if 'table_index' in bank:
                        table = table.nth(bank['table_index'])
                    else:
                        table = table.nth(0)
                    html = await table.evaluate('el => el.outerHTML')

                elif 'query_selector' in bank:
                    element = await page.wait_for_selector(bank['query_selector'], state='attached')
                    if not element:
                        raise Exception(f'Could not find {bank['query_selector']} in {forex_page}')
                    html = (await element.evaluate('el => el.outerHTML'))

                elif 'api' in bank:
                    api = bank['api']
                    api = api.replace('yyyy-mm-dd', '')
                    response = await page.wait_for_event("response", lambda r: api in r.url, timeout=30_000)
                    json_data = await response.json()
                elif 'select_link' in bank:
                    # Only made for Himalayan
                    link = await page.query_selector('a[href^="getRate.php"]')
                    if not link:
                        raise Exception('Could not find link')
                    await link.click()
                    await page.wait_for_load_state('domcontentloaded')

                    table = page.locator('css=table').nth(3)
                    html = await table.evaluate('el => el.outerHTML')

                bank_data = None
                if html != None:
                    cleaned_html = clean_html_for_llm(html)
                    bank_data = cleaned_html
                elif json_data != None:
                    bank_data = json.dumps(json_data, indent=2)
                else:
                    raise Exception('Neither html nor json found')

                prompt = create_prompt_from_template(bank_data)
                print(prompt)

                output = send_prompt_to_gemini(prompt)
                output['bank_name'] = bank['name']
                output['source_url'] = bank['forex_page']
                output['fetch_datetime_utc'] = get_utc_now_iso_string()

                print(json.dumps(output, indent=2))

                print(f"Successfully opened {bank['name']}")

                return output

            except Exception as e:
                print(f"Error opening {bank['name']}: {str(e)}")

        # Create tasks for all banks
        if concurrent:
            tasks = []
            for bank in banks:
                tasks.append(open_page(bank))

            outputs = await asyncio.gather(*tasks)
        else:
            outputs = []
            for bank in banks:
                output = await open_page(bank)
                outputs.append(output)

        final_data = {
            "all_banks": outputs
        }

        utc_time = get_utc_now_iso_string()
        with open(f'rate_{utc_time}.json', 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=4)

        with open(f'ui/data/current_rate.json', 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=4)

        print("Press Enter to close the browser...")
        input()  # Wait for user input before closing

        # Close the browser
        await browser.close()

async def main():
    """Main function to run the program"""
    json_file_path = "nepal_banks.json"
    await open_bank_pages(json_file_path, concurrent=True)

if __name__ == "__main__":
    # Run the async function
    asyncio.run(main())
