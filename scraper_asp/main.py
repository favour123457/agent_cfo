from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import markdownify
import uvicorn

app = FastAPI(
    title="Deep-Dive Web Scraper ASP",
    description="An Agent Service Provider that extracts clean, structured data from any website.",
    version="1.0.0"
)

# Allow CORS for our frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScrapeRequest(BaseModel):
    url: str
    extract_markdown: bool = True
    wait_for_timeout: int = 1000 # wait for 1 second by default to let JS load

class ScrapeResponse(BaseModel):
    url: str
    title: str
    content: str
    status: str

@app.post("/api/scrape", response_model=ScrapeResponse)
async def scrape_url(request: ScrapeRequest):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Go to URL and wait until network is mostly idle
            await page.goto(request.url, wait_until="networkidle", timeout=15000)
            
            # Additional wait for dynamic content if specified
            if request.wait_for_timeout > 0:
                await page.wait_for_timeout(request.wait_for_timeout)
            
            html_content = await page.content()
            title = await page.title()
            await browser.close()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script, style, and svg elements to reduce noise
            for script_or_style in soup(["script", "style", "noscript", "svg"]):
                script_or_style.decompose()
                
            clean_html = str(soup)
            
            if request.extract_markdown:
                content = markdownify.markdownify(clean_html, heading_style="ATX")
            else:
                content = soup.get_text(separator='\n', strip=True)
                
            return ScrapeResponse(
                url=request.url,
                title=title,
                content=content.strip(),
                status="success"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
