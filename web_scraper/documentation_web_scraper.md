# 📄 Project Documentation — Web Scraper


## 1. Introduction

### 1.1 Purpose
The Web Scraper is a Python-based application that extracts data from any public website using BeautifulSoup4 and Requests. It supports multiple scraping modes and saves results in both CSV and JSON formats.

### 1.2 Project Scope
The scope of this project is to design and develop a General Purpose Web Scraper using Python with BeautifulSoup4 and Requests that enables users to scrape any public website for text, headings, links, images, and tables using multiple scraping modes, featuring a Tkinter desktop GUI with live console output, CSV and JSON data export, and a Flask web application deployed on Vercel.

### 1.3 Intended Audience
- Data analysts collecting web data
- Researchers gathering information
- Developers testing web scraping techniques
- Students learning web scraping


## 2. System Overview

The Web Scraper is built in three versions:

| Version | Technology | Platform |
|---|---|---|
| CLI | Python | Terminal |
| Desktop GUI | Python + Tkinter | Windows/Mac/Linux |
| Web App | Python + Flask | Browser (Vercel) |



## 3. Features & Functionality

### 3.1 Scraping Modes

| Mode | Description |
|---|---|
| 📄 All Text | Scrapes all h1-h6, p, li, a, td text content |
| 📰 Headings | Extracts H1 through H6 headings only |
| 🔗 All Links | Gets all hyperlinks with text and URL |
| 🖼️ All Images | Gets all images with src and alt text |
| 📊 Tables | Extracts all HTML tables as structured data |
| 🎯 Custom CSS | Scrape any element by CSS selector |
| 🔍 Summary | Page title, word count, link/image counts |
| 🕸️ Multi-page | Scrape multiple URLs in one session |

### 3.2 Output Formats
- 💾 CSV file — structured spreadsheet format
- 📋 JSON file — nested data format
- Both saved automatically to `scraped_data/` folder

### 3.3 GUI Features
- URL input bar
- Mode selection buttons
- Live output console
- Progress indicator
- Save Results button
- Open Output Folder button
- Live stats (items scraped, files saved, errors)



## 4. Technical Design

### 4.1 Architecture
```
User Interface (Tkinter/Flask/HTML)
        ↓
HTTP Request (Requests Library)
        ↓
HTML Parsing (BeautifulSoup4)
        ↓
Data Extraction (Python Functions)
        ↓
File Output (CSV + JSON)
```

### 4.2 HTTP Request Setup

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
response = requests.get(url, headers=HEADERS, timeout=15)
soup = BeautifulSoup(response.content, "html.parser")
```

### 4.3 Key Functions

| Function | Description |
|---|---|
| `fetch_soup()` | Makes HTTP request and returns BeautifulSoup object |
| `scrape_text()` | Extracts all text elements |
| `scrape_headings()` | Extracts H1-H6 headings |
| `scrape_links()` | Extracts all hyperlinks |
| `scrape_images()` | Extracts all image tags |
| `scrape_tables()` | Extracts all HTML tables |
| `scrape_custom()` | Extracts by CSS selector |
| `scrape_summary()` | Returns page metadata summary |
| `save_csv()` | Saves results to CSV file |
| `save_json()` | Saves results to JSON file |

### 4.4 Flask API Route

| Route | Method | Description |
|---|---|---|
| `/scraper` | GET | Load scraper page |
| `/scraper/run` | POST | Run scraping task |

**Request format:**
```json
{
  "url": "https://quotes.toscrape.com",
  "mode": "headings",
  "selector": ".title",
  "attr": "text"
}
```

**Response format:**
```json
{
  "results": [
    {"type": "H1", "value": "Quotes to Scrape"},
    {"type": "H2", "value": "Top Ten tags"}
  ]
}
```

### 4.5 CSS Selector Examples

```css
h1              → All H1 headings
.title          → Elements with class "title"
#main p         → Paragraphs inside #main
div.article     → Divs with class "article"
table tr td     → Table cells
a[href]         → All links with href
```

## 6. Testing

| Test Case | Input | Expected Output | Result |
|---|---|---|---|
| Valid URL | https://quotes.toscrape.com | Data scraped | ✅ Pass |
| Invalid URL | not-a-url | Error message shown | ✅ Pass |
| Headings mode | Valid URL | H1-H6 list returned | ✅ Pass |
| Links mode | Valid URL | All links extracted | ✅ Pass |
| Tables mode | URL with table | Table data extracted | ✅ Pass |
| Custom selector | .quote | Matching elements | ✅ Pass |
| Save CSV | Click save | CSV file created | ✅ Pass |
| Save JSON | Click save | JSON file created | ✅ Pass |
| No internet | Any URL | Connection error shown | ✅ Pass |


## 7. Error Handling

| Error | Handling |
|---|---|
| No internet | Shows connection error message |
| Invalid URL | Shows HTTP error message |
| Timeout | Shows timeout error after 15s |
| No elements found | Shows warning message |
| Permission denied | Shows access error |


## 8. Ethical Considerations

⚠️ **Important Guidelines:**
- Always check `robots.txt` before scraping
- Do not scrape websites that prohibit it
- Add delays between requests (polite scraping)
- Do not use for commercial data theft
- Respect website terms of service


## 9. Limitations

- Cannot scrape JavaScript-rendered pages (use Selenium for that)
- Cannot bypass login-protected pages
- Rate limited by website servers
- Some websites block scrapers by IP


## 10. Future Enhancements

- 🤖 Selenium integration for JavaScript pages
- 📅 Scheduled scraping (auto-run daily)
- 🔐 Proxy rotation support
- 📊 Data visualization of scraped data
- ☁️ Cloud storage for scraped results
- 📱 Mobile app version


## 11. Conclusion

The Web Scraper application delivers a powerful and flexible data extraction tool supporting 8 scraping modes and dual output formats. It demonstrates Python web scraping, HTTP handling, GUI development, REST API design, and file management skills gained during the CodeTech IT Solutions internship.



