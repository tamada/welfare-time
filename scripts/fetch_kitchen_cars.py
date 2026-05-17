import asyncio
import argparse
import sys
from playwright.async_api import async_playwright

async def fetch_kitchen_cars(output_path=None):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        url = "https://schedule.mellow.jp/ss_web/markets/KqTl8N"
        
        # JSレンダリングを完了させるために十分な時間を待機
        await page.goto(url)
        await page.wait_for_timeout(5000) 
        
        # 完全にレンダリングされたHTMLコンテンツを取得
        content = await page.content()
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            sys.stdout.write(content)
        
        await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch kitchen car schedule HTML")
    parser.add_argument("-o", "--output", help="Output file path (optional, otherwise stdout)")
    args = parser.parse_args()
    
    asyncio.run(fetch_kitchen_cars(args.output))
