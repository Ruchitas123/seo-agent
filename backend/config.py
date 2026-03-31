"""
Central config — loads from a .env file (if present) then environment variables.

Create a .env file in this directory:
    SERPAPI_KEY=your_key_here

That's it — no export needed.
"""

import os
import pathlib

# Auto-load .env from the project root (same dir as this file)
_env_path = pathlib.Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        _k = _k.strip()
        _v = _v.strip().strip('"').strip("'")
        if _k and _k not in os.environ:   # don't override real env vars
            os.environ[_k] = _v

def _require(var: str) -> str:
    value = os.environ.get(var)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{var}' is not set.\n"
            f"Run: export {var}='your_value_here'"
        )
    return value

SERPAPI_KEY = _require("SERPAPI_KEY")

# Tuning constants — change via env vars if needed
SERP_NUM             = int(os.environ.get("SERP_NUM", "10"))
REQUEST_TIMEOUT      = int(os.environ.get("REQUEST_TIMEOUT", "15"))
SLEEP_BETWEEN_SCRAPES = float(os.environ.get("SLEEP_BETWEEN_SCRAPES", "0.5"))
TOP_UNI_LIMIT        = int(os.environ.get("TOP_UNI_LIMIT", "50"))
TOP_BI_LIMIT         = int(os.environ.get("TOP_BI_LIMIT", "25"))
BIGRAM_MIN_COUNT     = int(os.environ.get("BIGRAM_MIN_COUNT", "2"))
MIN_SCRAPED_WORDS    = int(os.environ.get("MIN_SCRAPED_WORDS", "100"))
MAX_HEADING_LENGTH   = int(os.environ.get("MAX_HEADING_LENGTH", "120"))

STOPWORDS = {
    "the","and","for","that","this","with","from","have","are","was","were",
    "has","its","not","but","all","can","will","been","more","also","than",
    "when","into","your","our","their","they","them","there","then","what",
    "which","about","would","could","should","other","these","those","each",
    "some","such","very","just","over","only","both","most","many","much",
    "any","may","did","how","who","one","two","use","get","set","let","put",
    "out","new","see","way","per","via","ago","yet","you","its","—","-","|",
    "here","a","an","in","of","to","is","it","be","at","by","or","on","do",
    "as","we","he","she","so","if","up","no","me","my","us","am","go","re",
    "i","s","t","d","ll","ve","m","https","http","www","com","org","html",
    "like","feel","make","give","work","time","since","part","allow","used",
    "different","where","through","it's","i'm","you're","we're","don't",
    "isn't","aren't","wasn't","weren't","hasn't","haven't","hadn't","won't",
}
