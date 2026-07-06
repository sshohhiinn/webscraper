import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from bs4 import BeautifulSoup
import csv, json, os, datetime
from urllib.parse import urljoin, urlparse

# ── Config ───────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "scraped_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Colors ───────────────────────────────────────────────────────────
BG        = "#F0EFEA"
CARD      = "#FFFFFF"
SIDE      = "#1E1E2E"
SIDE_FG   = "#CDD6F4"
ACCENT    = "#534AB7"
ACCENT_LT = "#EEEDFE"
ACCENT_DK = "#3C3489"
TEXT      = "#1A1A18"
TEXT_S    = "#6B6B67"
TEXT_T    = "#9B9B96"
BORDER    = "#D0D0CC"
GREEN     = "#0F6E56"
RED       = "#A32D2D"
RED_BG    = "#FEECEC"
TERM_BG   = "#1E1E2E"
TERM_FG   = "#CDD6F4"

SCRAPE_MODES = [
    ("📄", "All Text Content"),
    ("📰", "Headings (H1-H6)"),
    ("🔗", "All Links"),
    ("🖼️",  "All Images"),
    ("📊", "Tables"),
    ("🎯", "Custom CSS Selector"),
    ("🔍", "Full Page Summary"),
]

# ── Helpers ──────────────────────────────────────────────────────────
def timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def safe_name(url):
    domain = urlparse(url).netloc.replace(".", "_").replace("-", "_")
    return f"{domain}_{timestamp()}"

def save_csv(data, fname):
    if not data: return None
    path = os.path.join(OUTPUT_DIR, fname + ".csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=data[0].keys())
        w.writeheader(); w.writerows(data)
    return path

def save_json(data, fname):
    if not data: return None
    path = os.path.join(OUTPUT_DIR, fname + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path

# ── Scraper Logic ────────────────────────────────────────────────────
def fetch_soup(url, log):
    try:
        log(f"🌐 Fetching: {url}", "info")
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        log(f"✅ Status: {r.status_code} OK", "success")
        return BeautifulSoup(r.content, "html.parser")
    except Exception as e:
        log(f"❌ Error: {e}", "error")
        return None

def scrape_text(url, log):
    soup = fetch_soup(url, log)
    if not soup: return []
    data = []
    for tag in ["h1","h2","h3","h4","p","li","a","td"]:
        for el in soup.find_all(tag):
            text = el.get_text(strip=True)
            if text and len(text) > 3:
                item = {"tag": tag, "text": text[:300], "url": url}
                if tag == "a" and el.get("href"):
                    item["href"] = urljoin(url, el["href"])
                data.append(item)
    log(f"📄 Found {len(data)} text elements", "success")
    return data

def scrape_headings(url, log):
    soup = fetch_soup(url, log)
    if not soup: return []
    data = []
    for level in range(1, 7):
        for h in soup.find_all(f"h{level}"):
            text = h.get_text(strip=True)
            if text:
                data.append({"level": f"H{level}", "text": text, "url": url})
                log(f"  H{level}: {text[:70]}", "normal")
    log(f"📰 Found {len(data)} headings", "success")
    return data

def scrape_links(url, log):
    soup = fetch_soup(url, log)
    if not soup: return []
    data = []; seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        if href not in seen and href.startswith("http"):
            seen.add(href)
            data.append({"text": a.get_text(strip=True)[:100] or "(no text)",
                         "url": href, "domain": urlparse(href).netloc, "source": url})
            log(f"  🔗 {a.get_text(strip=True)[:50]} → {href[:60]}", "normal")
    log(f"🔗 Found {len(data)} unique links", "success")
    return data

def scrape_images(url, log):
    soup = fetch_soup(url, log)
    if not soup: return []
    data = []
    for img in soup.find_all("img"):
        src = urljoin(url, img.get("src", ""))
        data.append({"src": src, "alt": img.get("alt","")[:100],
                     "width": img.get("width",""), "height": img.get("height",""),
                     "source": url})
        log(f"  🖼️  {img.get('alt','(no alt)')[:50]} → {src[:60]}", "normal")
    log(f"🖼️  Found {len(data)} images", "success")
    return data

def scrape_tables(url, log):
    soup = fetch_soup(url, log)
    if not soup: return []
    tables = soup.find_all("table")
    if not tables:
        log("⚠️  No tables found on this page.", "warning")
        return []
    all_data = []
    for t_idx, table in enumerate(tables, 1):
        rows  = table.find_all("tr")
        heads = [th.get_text(strip=True) for th in rows[0].find_all(["th","td"])] if rows else []
        if not heads: continue
        log(f"  📊 Table {t_idx}: {len(rows)-1} rows × {len(heads)} cols", "normal")
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all(["td","th"])]
            if cells:
                rd = dict(zip(heads, cells))
                rd["_table"] = t_idx; rd["_source"] = url
                all_data.append(rd)
    log(f"📊 Total {len(all_data)} table rows", "success")
    return all_data

def scrape_custom(url, selector, attr, log):
    soup = fetch_soup(url, log)
    if not soup: return []
    elements = soup.select(selector)
    if not elements:
        log(f"⚠️  No elements found for: {selector}", "warning")
        return []
    data = []
    for i, el in enumerate(elements, 1):
        val = el.get_text(strip=True) if attr == "text" else el.get(attr, "")
        if val:
            data.append({"index": i, "selector": selector,
                         "value": val[:300], "source": url})
            log(f"  [{i}] {val[:70]}", "normal")
    log(f"🎯 Found {len(data)} elements", "success")
    return data

def scrape_summary(url, log):
    soup = fetch_soup(url, log)
    if not soup: return []
    title    = soup.title.string.strip() if soup.title else "N/A"
    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc     = desc_tag["content"] if desc_tag else "N/A"
    headings = sum(len(soup.find_all(f"h{i}")) for i in range(1, 7))
    links    = len(soup.find_all("a", href=True))
    images   = len(soup.find_all("img"))
    tables   = len(soup.find_all("table"))
    paras    = len(soup.find_all("p"))
    words    = len(soup.get_text().split())
    log(f"  📌 Title      : {title[:70]}", "normal")
    log(f"  📝 Description: {desc[:80]}", "normal")
    log(f"  📰 Headings   : {headings}", "normal")
    log(f"  🔗 Links      : {links}", "normal")
    log(f"  🖼️  Images     : {images}", "normal")
    log(f"  📊 Tables     : {tables}", "normal")
    log(f"  📄 Paragraphs : {paras}", "normal")
    log(f"  📖 Words      : ~{words}", "normal")
    log("🔍 Summary complete!", "success")
    return [{"url":url,"title":title,"description":desc,
             "headings":headings,"links":links,"images":images,
             "tables":tables,"paragraphs":paras,"words":words}]

# ── GUI App ───────────────────────────────────────────────────────────
class ScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🕷️ Web Scraper")
        self.root.geometry("980x660")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.minsize(800, 560)

        # Center
        self.root.update_idletasks()
        w, h = 980, 660
        x = (self.root.winfo_screenwidth()  // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.mode_var    = tk.IntVar(value=6)
        self.selector_var = tk.StringVar(value=".title")
        self.attr_var    = tk.StringVar(value="text")
        self.running     = False

        self._styles()
        self._build_ui()

    def _styles(self):
        s = ttk.Style(); s.theme_use("clam")
        s.configure("TCombobox",
            fieldbackground="#F5F5F4", background="#F5F5F4",
            foreground=TEXT, bordercolor=BORDER,
            arrowcolor=TEXT_S, relief="flat", padding=6)
        s.configure("Vertical.TScrollbar",
            background=SIDE, troughcolor=SIDE,
            bordercolor=SIDE, arrowcolor="#6C7086", relief="flat")

    def _build_ui(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Sidebar
        side = tk.Frame(self.root, bg=SIDE, width=230)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        self._sidebar(side)

        # Main
        main = tk.Frame(self.root, bg=BG)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)
        self._main(main)

    # ── Sidebar ──────────────────────────────────────────────────────
    def _sidebar(self, p):
        tk.Label(p, text="🕷️  Web Scraper",
                 font=("Helvetica",15,"bold"),
                 bg=SIDE, fg=SIDE_FG).pack(anchor="w", padx=18, pady=(22,2))
        tk.Label(p, text="BeautifulSoup4 + Requests",
                 font=("Helvetica",9), bg=SIDE,
                 fg="#6C7086").pack(anchor="w", padx=18, pady=(0,14))

        tk.Frame(p, bg="#313244", height=1).pack(fill="x", padx=14, pady=4)

        # Stats
        sf = tk.Frame(p, bg=SIDE)
        sf.pack(fill="x", padx=12, pady=6)
        self._stat(sf, "Items Scraped", "0",  "#A6E3A1", "s_items")
        self._stat(sf, "Files Saved",   "0",  "#CDD6F4", "s_files")
        self._stat(sf, "Errors",        "0",  "#F38BA8", "s_errors")

        tk.Frame(p, bg="#313244", height=1).pack(fill="x", padx=14, pady=8)

        # Scrape mode buttons
        tk.Label(p, text="SCRAPE MODE",
                 font=("Helvetica",9,"bold"),
                 bg=SIDE, fg="#6C7086").pack(anchor="w", padx=18, pady=(0,6))

        self.mode_btns = {}
        for i, (icon, label) in enumerate(SCRAPE_MODES):
            f = tk.Frame(p, bg=SIDE, cursor="hand2")
            f.pack(fill="x", padx=12, pady=1)
            lbl = tk.Label(f, text=f"  {icon}  {label}",
                           font=("Helvetica",10), bg=SIDE,
                           fg="#6C7086", anchor="w", pady=5)
            lbl.pack(fill="x", padx=4)
            self.mode_btns[i] = lbl
            def click(idx=i): self.set_mode(idx)
            lbl.bind("<Button-1>", lambda e, idx=i: self.set_mode(idx))
            f.bind("<Button-1>",   lambda e, idx=i: self.set_mode(idx))
            def on_enter(e, l=lbl, idx=i):
                if self.mode_var.get() != idx: l.config(bg="#313244")
            def on_leave(e, l=lbl, idx=i):
                if self.mode_var.get() != idx: l.config(bg=SIDE)
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)

        self.mode_var.set(6)
        for i, lbl in self.mode_btns.items():
            lbl.config(bg=SIDE, fg="#6C7086")
        self.mode_btns[6].config(bg=ACCENT, fg="white")

        tk.Frame(p, bg="#313244", height=1).pack(fill="x", padx=14, pady=8)

        # Output folder button
        tk.Button(p, text="📁  Open Output Folder",
                  font=("Helvetica",10), relief="flat",
                  bg="#313244", fg=SIDE_FG, cursor="hand2",
                  activebackground=ACCENT, activeforeground="white",
                  command=self.open_folder).pack(fill="x", padx=14, ipady=7)

        tk.Label(p, text=f"Saves to:\n~/Documents/scraped_data",
                 font=("Helvetica",8), bg=SIDE,
                 fg="#6C7086", justify="left").pack(anchor="w", padx=16, pady=(8,0))

    def _stat(self, p, label, val, color, attr):
        f = tk.Frame(p, bg="#313244")
        f.pack(fill="x", pady=3)
        tk.Label(f, text=label, font=("Helvetica",9),
                 bg="#313244", fg="#6C7086").pack(side="left", padx=10, pady=6)
        lbl = tk.Label(f, text=val, font=("Helvetica",10,"bold"),
                       bg="#313244", fg=color)
        lbl.pack(side="right", padx=10)
        setattr(self, attr, lbl)

    def set_mode(self, idx):
        self.mode_var.set(idx)
        for i, lbl in self.mode_btns.items():
            if i == idx:
                lbl.config(bg=ACCENT, fg="white")
            else:
                lbl.config(bg=SIDE, fg="#6C7086")
        # Show/hide custom selector fields
        if idx == 5:
            self.custom_frame.grid()
        else:
            self.custom_frame.grid_remove()

    # ── Main Area ─────────────────────────────────────────────────────
    def _main(self, p):
        # URL bar
        url_frame = tk.Frame(p, bg=BG)
        url_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20,10))
        url_frame.columnconfigure(1, weight=1)

        tk.Label(url_frame, text="🌐 URL",
                 font=("Helvetica",11,"bold"),
                 bg=BG, fg=TEXT).grid(row=0, column=0, padx=(0,10))

        self.url_var = tk.StringVar(value="https://quotes.toscrape.com")
        url_entry = tk.Entry(url_frame, textvariable=self.url_var,
                             font=("Helvetica",12), relief="flat",
                             bg=CARD, fg=TEXT, insertbackground=TEXT,
                             highlightbackground=BORDER, highlightthickness=1)
        url_entry.grid(row=0, column=1, sticky="ew", ipady=9)

        self.scrape_btn = tk.Button(url_frame, text="▶  Scrape",
                  font=("Helvetica",11,"bold"),
                  bg=ACCENT, fg="white", relief="flat",
                  padx=18, pady=8, cursor="hand2",
                  activebackground=ACCENT_DK,
                  command=self.start_scrape)
        self.scrape_btn.grid(row=0, column=2, padx=(10,0))

        tk.Button(url_frame, text="🗑  Clear",
                  font=("Helvetica",10), relief="flat",
                  bg="#E8E7E2", fg=TEXT,
                  padx=12, pady=8, cursor="hand2",
                  command=self.clear_log).grid(row=0, column=3, padx=(6,0))

        # Custom selector (hidden by default)
        self.custom_frame = tk.Frame(p, bg=BG)
        self.custom_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0,8))
        self.custom_frame.columnconfigure(1, weight=1)
        self.custom_frame.grid_remove()

        tk.Label(self.custom_frame, text="CSS Selector:",
                 font=("Helvetica",10), bg=BG, fg=TEXT_S).grid(row=0, column=0, padx=(0,8))
        tk.Entry(self.custom_frame, textvariable=self.selector_var,
                 font=("Helvetica",11), relief="flat",
                 bg=CARD, fg=TEXT, insertbackground=TEXT,
                 highlightbackground=BORDER, highlightthickness=1,
                 width=25).grid(row=0, column=1, sticky="ew", ipady=6)

        tk.Label(self.custom_frame, text="  Attribute:",
                 font=("Helvetica",10), bg=BG, fg=TEXT_S).grid(row=0, column=2, padx=(12,6))
        attr_cb = ttk.Combobox(self.custom_frame, textvariable=self.attr_var,
                               values=["text","href","src","title","alt","data-id"],
                               state="readonly", font=("Helvetica",10), width=10)
        attr_cb.grid(row=0, column=3)

        # Terminal output
        log_frame = tk.Frame(p, bg=TERM_BG,
                             highlightbackground="#313244", highlightthickness=1)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0,10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # Header bar
        hdr = tk.Frame(log_frame, bg="#313244")
        hdr.pack(fill="x")
        tk.Label(hdr, text="  ● ● ●  Output Console",
                 font=("Helvetica",10), bg="#313244",
                 fg="#6C7086").pack(side="left", padx=8, pady=6)
        self.status_lbl = tk.Label(hdr, text="Ready",
                                    font=("Helvetica",9),
                                    bg="#313244", fg="#A6E3A1")
        self.status_lbl.pack(side="right", padx=12)

        self.log_box = scrolledtext.ScrolledText(
            log_frame, font=("Courier New",10),
            bg=TERM_BG, fg=TERM_FG,
            insertbackground=TERM_FG,
            relief="flat", state="disabled",
            padx=12, pady=8)
        self.log_box.pack(fill="both", expand=True)

        # Tag colors
        self.log_box.tag_config("info",    foreground="#89B4FA")
        self.log_box.tag_config("success", foreground="#A6E3A1")
        self.log_box.tag_config("error",   foreground="#F38BA8")
        self.log_box.tag_config("warning", foreground="#FAB387")
        self.log_box.tag_config("normal",  foreground="#CDD6F4")
        self.log_box.tag_config("save",    foreground="#CBA6F7")

        # Bottom bar
        bot = tk.Frame(p, bg=BG)
        bot.grid(row=3, column=0, sticky="ew", padx=20, pady=(0,14))
        bot.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(bot, mode="indeterminate",
                                         length=400)
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0,12))

        tk.Button(bot, text="💾 Save Results",
                  font=("Helvetica",10,"bold"),
                  bg=GREEN, fg="white", relief="flat",
                  padx=14, pady=6, cursor="hand2",
                  activebackground="#085041",
                  command=self.save_results).grid(row=0, column=1)

        self.last_data = []
        self.items_count  = 0
        self.files_count  = 0
        self.errors_count = 0

        self.log("🕷️  Web Scraper ready! Enter a URL and click ▶ Scrape", "success")
        self.log("💡 Try: https://quotes.toscrape.com", "info")

    # ── Logging ───────────────────────────────────────────────────────
    def log(self, msg, tag="normal"):
        self.log_box.config(state="normal")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {msg}\n", tag)
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")
        self.last_data = []
        self.log("🗑  Console cleared. Ready to scrape!", "info")

    # ── Scrape ────────────────────────────────────────────────────────
    def start_scrape(self):
        if self.running:
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a URL to scrape!")
            return
        if not url.startswith("http"):
            url = "https://" + url
            self.url_var.set(url)

        self.running = True
        self.scrape_btn.config(state="disabled", text="⏳ Scraping...")
        self.status_lbl.config(text="Scraping...", fg="#FAB387")
        self.progress.start(10)
        self.last_data = []

        thread = threading.Thread(target=self._scrape_thread, args=(url,), daemon=True)
        thread.start()

    def _scrape_thread(self, url):
        mode = self.mode_var.get()
        try:
            self.log(f"\n{'─'*50}", "normal")
            self.log(f"🚀 Starting: {SCRAPE_MODES[mode][0]} {SCRAPE_MODES[mode][1]}", "info")
            self.log(f"{'─'*50}", "normal")

            if   mode == 0: data = scrape_text(url, self.log)
            elif mode == 1: data = scrape_headings(url, self.log)
            elif mode == 2: data = scrape_links(url, self.log)
            elif mode == 3: data = scrape_images(url, self.log)
            elif mode == 4: data = scrape_tables(url, self.log)
            elif mode == 5:
                sel  = self.selector_var.get().strip()
                attr = self.attr_var.get().strip()
                data = scrape_custom(url, sel, attr, self.log)
            elif mode == 6: data = scrape_summary(url, self.log)
            else: data = []

            self.last_data = data or []
            self.items_count += len(self.last_data)
            if self.last_data:
                self.errors_count = max(0, self.errors_count)
            else:
                self.errors_count += 1

        except Exception as e:
            self.log(f"❌ Unexpected error: {e}", "error")
            self.errors_count += 1
            self.last_data = []
        finally:
            self.root.after(0, self._scrape_done)

    def _scrape_done(self):
        self.running = False
        self.progress.stop()
        self.scrape_btn.config(state="normal", text="▶  Scrape")
        self.s_items.config(text=str(self.items_count))
        self.s_errors.config(text=str(self.errors_count))
        if self.last_data:
            self.status_lbl.config(text=f"Done — {len(self.last_data)} items", fg="#A6E3A1")
            self.log(f"\n✅ Scraping complete! {len(self.last_data)} items found.", "success")
            self.log("💾 Click 'Save Results' to export as CSV & JSON", "info")
        else:
            self.status_lbl.config(text="No data found", fg="#F38BA8")

    # ── Save ──────────────────────────────────────────────────────────
    def save_results(self):
        if not self.last_data:
            messagebox.showinfo("No Data", "Nothing to save yet! Run a scrape first.")
            return
        url   = self.url_var.get()
        fname = safe_name(url) + f"_{SCRAPE_MODES[self.mode_var.get()][1].replace(' ','_').lower()}"
        csv_p  = save_csv(self.last_data, fname)
        json_p = save_json(self.last_data, fname)
        self.files_count += 2
        self.s_files.config(text=str(self.files_count))
        self.log(f"\n💾 Saved CSV  → {csv_p}", "save")
        self.log(f"💾 Saved JSON → {json_p}", "save")
        messagebox.showinfo("Saved! ✅",
            f"Files saved to:\n📄 {os.path.basename(csv_p)}\n📋 {os.path.basename(json_p)}\n\nFolder:\n{OUTPUT_DIR}")

    def open_folder(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.startfile(OUTPUT_DIR) if os.name == "nt" else os.system(f"open '{OUTPUT_DIR}'")

# ── Run ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.tk_setPalette(background=BG)
    ScraperApp(root)
    root.mainloop()
