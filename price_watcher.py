#!/usr/bin/env python3
"""
XREAL One Pro Price Watcher

Continuously monitors the XREAL One Pro product page for price changes.
Alerts when the price changes from the last known price.
"""

import argparse
import json
import logging
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def setup_logging(log_file: str | None = None) -> logging.Logger:
    """Configure logging for the price watcher."""
    logger = logging.getLogger("price_watcher")
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (if log file specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(console_format)
        logger.addHandler(file_handler)

    return logger


def load_config(config_path: str = "price_config.json") -> dict:
    """Load configuration from JSON file."""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_file.open() as f:
        return json.load(f)


def save_last_price(price: str, price_file: str = "last_price.json") -> None:
    """Save the last known price to a file."""
    with open(price_file, "w") as f:
        json.dump({"price": price}, f)


def load_last_price(price_file: str = "last_price.json") -> str | None:
    """Load the last known price from a file."""
    price_path = Path(price_file)
    if not price_path.exists():
        return None
    with price_path.open() as f:
        data = json.load(f)
        return data.get("price")


def extract_price(url: str, logger: logging.Logger) -> dict:
    """
    Extract the price from the product page.

    Returns:
        dict with keys:
            - 'price': str of the price found (e.g., "€549.00")
            - 'price_numeric': float of the numeric price value
            - 'error': str if there was an error fetching the page
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch page: {e}")
        return {"price": None, "price_numeric": None, "error": str(e)}

    soup = BeautifulSoup(response.text, "lxml")

    # Common price selectors for e-commerce sites
    price_selectors = [
        # Common class names for prices
        {"class_": re.compile(r"price", re.I)},
        {"class_": re.compile(r"product-price", re.I)},
        {"class_": re.compile(r"sale-price", re.I)},
        {"class_": re.compile(r"current-price", re.I)},
        # Meta tags
        {"property": "product:price:amount"},
        {"itemprop": "price"},
    ]

    price_text = None

    # Try to find price using various selectors
    for selector in price_selectors:
        elements = soup.find_all(attrs=selector)
        for elem in elements:
            text = elem.get_text(strip=True) if elem.get_text(strip=True) else elem.get("content", "")
            # Look for currency patterns (€, $, £, etc.)
            price_match = re.search(r"[€$£]\s*[\d.,]+|\d[\d.,]*\s*[€$£]", text)
            if price_match:
                price_text = price_match.group(0).strip()
                break
        if price_text:
            break

    # If still no price found, search for price patterns in page text
    if not price_text:
        page_text = soup.get_text(separator=" ", strip=True)
        # Look for prices with currency symbols (€, $, £)
        price_matches = re.findall(r"[€$£]\s*[\d.,]+", page_text)
        if price_matches:
            # Get the most likely product price (usually the first prominent one)
            price_text = price_matches[0]

    if not price_text:
        return {"price": None, "price_numeric": None, "error": "Could not find price on page"}

    # Extract numeric value - normalize by removing currency symbols and whitespace
    # then handle both European (1.234,56) and US (1,234.56) number formats
    clean_price = re.sub(r"[€$£\s]", "", price_text)
    # If there's both comma and period, determine format by last separator position
    if "," in clean_price and "." in clean_price:
        # European format: 1.234,56 -> last separator is comma (decimal)
        # US format: 1,234.56 -> last separator is period (decimal)
        last_comma = clean_price.rfind(",")
        last_period = clean_price.rfind(".")
        if last_comma > last_period:
            # European format - comma is decimal separator
            clean_price = clean_price.replace(".", "").replace(",", ".")
        else:
            # US format - period is decimal separator
            clean_price = clean_price.replace(",", "")
    elif "," in clean_price:
        # Could be European decimal (123,45) or US thousands (1,234)
        # Check if comma appears to be decimal separator (2 digits after)
        if re.search(r",\d{2}$", clean_price):
            clean_price = clean_price.replace(",", ".")
        else:
            clean_price = clean_price.replace(",", "")
    # Period only - treat as decimal separator (standard)

    try:
        price_numeric = float(clean_price)
    except ValueError:
        price_numeric = None

    return {"price": price_text, "price_numeric": price_numeric, "error": None}


def play_alert_sound(message: str) -> None:
    """
    Play an alert sound.

    Uses platform-specific methods:
    - macOS: Uses 'say' command for voice alert
    - All platforms: Terminal bell character
    """
    # Terminal bell works on most platforms
    print("\a" * 3)

    # On macOS, try the say command for voice alert
    if platform.system() == "Darwin":
        try:
            subprocess.run(
                ["say", message],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass  # Silently ignore if say command fails


def alert_price_change(
    product_name: str, url: str, old_price: str, new_price: str, play_sound: bool
) -> None:
    """Alert the user that the price has changed."""
    display_name = product_name[:40] if len(product_name) > 40 else product_name
    display_url = url[:50] + "..." if len(url) > 50 else url

    print("\n" + "=" * 70)
    print("💰 PRICE CHANGE ALERT! 💰")
    print("=" * 70)
    print(f"   Product: {display_name}")
    print(f"   Old Price: {old_price}")
    print(f"   New Price: {new_price}")
    print(f"   URL: {display_url}")
    print("=" * 70 + "\n")

    if play_sound:
        play_alert_sound(f"Price change detected for {product_name}! New price is {new_price}")


def run_price_watcher(config_path: str = "price_config.json") -> None:
    """Main loop to continuously monitor price."""
    config = load_config(config_path)

    url = config["url"]
    check_interval = config.get("check_interval_seconds", 300)
    product_name = config.get("product_name", "Product")
    notification_config = config.get("notification", {})
    price_file = config.get("price_file", "last_price.json")

    log_file = notification_config.get("log_file") if notification_config.get("enabled") else None
    play_sound = notification_config.get("sound", True)

    logger = setup_logging(log_file)

    logger.info(f"Starting price watcher for: {product_name}")
    logger.info(f"URL: {url}")
    logger.info(f"Check interval: {check_interval} seconds")
    logger.info("-" * 60)

    # Load last known price
    last_price = load_last_price(price_file)
    if last_price:
        logger.info(f"Last known price: {last_price}")
    else:
        logger.info("No previous price recorded. Will record current price.")

    check_count = 0

    while True:
        check_count += 1
        logger.info(f"Check #{check_count} - Checking price...")

        result = extract_price(url, logger)

        if result.get("error"):
            logger.warning(f"Error checking price: {result.get('error')}")
        elif result.get("price"):
            current_price = result["price"]
            logger.info(f"Current price: {current_price}")

            if last_price is None:
                # First time - just record the price
                logger.info(f"Recording initial price: {current_price}")
                save_last_price(current_price, price_file)
                last_price = current_price
            elif current_price != last_price:
                # Price changed!
                alert_price_change(product_name, url, last_price, current_price, play_sound)
                logger.info(f"🚨 PRICE CHANGED from {last_price} to {current_price}! 🚨")
                save_last_price(current_price, price_file)
                last_price = current_price
            else:
                logger.info("Price unchanged.")
        else:
            logger.warning("Could not determine price from page content.")

        # Wait before next check
        logger.info(f"Next check in {check_interval} seconds...")
        logger.info("-" * 60)

        try:
            time.sleep(check_interval)
        except KeyboardInterrupt:
            logger.info("Price watcher stopped by user.")
            break


def main() -> None:
    """Entry point for the price watcher."""
    parser = argparse.ArgumentParser(
        description="Monitor XREAL One Pro product page for price changes"
    )
    parser.add_argument(
        "-c",
        "--config",
        default="price_config.json",
        help="Path to configuration file (default: price_config.json)",
    )
    parser.add_argument(
        "--check-once",
        action="store_true",
        help="Check price once and exit",
    )

    args = parser.parse_args()

    if args.check_once:
        config = load_config(args.config)
        logger = setup_logging()
        result = extract_price(config["url"], logger)
        if result.get("price"):
            logger.info(f"Current price: {result['price']}")
            sys.exit(0)
        else:
            logger.error(f"Error: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    else:
        try:
            run_price_watcher(args.config)
        except KeyboardInterrupt:
            print("\nPrice watcher stopped.")
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
