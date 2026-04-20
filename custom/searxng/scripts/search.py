#!/usr/bin/env python3
"""
SearXNG Search CLI
Usage: python3 search.py "query" [--num N] [--engines engine1,engine2] [--lang zh-CN]
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from typing import Optional

SEARXNG_URL = "http://192.168.31.147:9900"


def search(
    query: str,
    num_results: int = 5,
    engines: Optional[str] = None,
    language: Optional[str] = None,
    time_range: Optional[str] = None,
) -> dict:
    """Search using SearXNG API"""
    
    params = {
        "q": query,
        "format": "json",
    }
    
    if engines:
        params["engines"] = engines
    if language:
        params["language"] = language
    if time_range:
        params["time_range"] = time_range
    
    url = f"{SEARXNG_URL}/search?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "results": []}


def format_results(data: dict, num: int = 5) -> str:
    """Format search results for display"""
    
    if "error" in data:
        return f"Error: {data['error']}"
    
    results = data.get("results", [])[:num]
    
    if not results:
        return "No results found."
    
    output = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        url = r.get("url", "")
        content = r.get("content", "")[:300]
        engine = r.get("engine", "unknown")
        
        output.append(f"{i}. {title}")
        output.append(f"   URL: {url}")
        output.append(f"   Source: {engine}")
        output.append(f"   {content}...")
        output.append("")
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Search using SearXNG")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--num", "-n", type=int, default=5, help="Number of results")
    parser.add_argument("--engines", "-e", help="Comma-separated list of engines")
    parser.add_argument("--lang", "-l", default="zh-CN", help="Result language")
    parser.add_argument("--time", "-t", choices=["day", "week", "month", "year"], help="Time range")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON")
    
    args = parser.parse_args()
    
    data = search(
        query=args.query,
        num_results=args.num,
        engines=args.engines,
        language=args.lang,
        time_range=args.time,
    )
    
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(format_results(data, args.num))


if __name__ == "__main__":
    main()
