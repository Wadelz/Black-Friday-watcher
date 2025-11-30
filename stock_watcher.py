#!/usr/bin/env python3
"""
XREAL One Stock Watcher

Continuously monitors the XREAL One product page for stock availability changes.
Alerts when the product becomes available (add to cart is enabled).
"""

import argparse
import json
import logging
import platform
import subprocess
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def setup_logging(log_file: str | None = None) -> logging.Logger:
    """Configure logging for the stock watcher."""
    logger = logging.getLogger("stock_watcher")
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


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_file.open() as f:
        return json.load(f)


def check_stock_status(
    url: str, stock_indicators: dict, logger: logging.Logger
) -> dict:
    """
    Check the stock status of the product page.

    Returns:
        dict with keys:
            - 'available': bool indicating if product is in stock
            - 'status': str describing the status found
            - 'page_text': str of relevant page content (for debugging)
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
        return {"available": None, "status": "error", "page_text": "", "error": str(e)}

    soup = BeautifulSoup(response.text, "lxml")

    # Get all text content and button elements
    page_text = soup.get_text(separator=" ", strip=True).lower()

    # Also check for specific button elements
    buttons = soup.find_all(["button", "a", "input"], class_=True)
    button_texts = " ".join(
        [btn.get_text(strip=True).lower() for btn in buttons if btn.get_text(strip=True)]
    )

    combined_text = page_text + " " + button_texts

    # Check for in-stock indicators first (higher priority)
    for indicator in stock_indicators.get("in_stock", []):
        if indicator.lower() in combined_text:
            return {
                "available": True,
                "status": f"IN STOCK - Found: '{indicator}'",
                "page_text": combined_text[:500],
                "error": None,
            }

    # Check for out-of-stock indicators
    for indicator in stock_indicators.get("out_of_stock", []):
        if indicator.lower() in combined_text:
            return {
                "available": False,
                "status": f"OUT OF STOCK - Found: '{indicator}'",
                "page_text": combined_text[:500],
                "error": None,
            }

    # Unknown status
    return {
        "available": None,
        "status": "UNKNOWN - Could not determine stock status",
        "page_text": combined_text[:500],
        "error": None,
    }


def play_alert_sound() -> None:
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
                ["say", "Alert! XREAL One is now in stock!"],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass  # Silently ignore if say command fails


def alert_stock_available(product_name: str, url: str, play_sound: bool) -> None:
    """Alert the user that stock is available."""
    # Truncate product name and URL to fit in alert box
    display_name = product_name[:40] if len(product_name) > 40 else product_name
    display_url = url[:50] + "..." if len(url) > 50 else url

    print("\n" + "=" * 70)
    print("🎉 STOCK ALERT! 🎉")
    print("=" * 70)
    print(f"   {display_name} IS NOW AVAILABLE!")
    print(f"   Quick! Go to: {display_url}")
    print("=" * 70 + "\n")

    if play_sound:
        play_alert_sound()


def run_stock_watcher(config_path: str = "config.json") -> None:
    """Main loop to continuously monitor stock status."""
    config = load_config(config_path)

    url = config["url"]
    check_interval = config.get("check_interval_seconds", 60)
    product_name = config.get("product_name", "Product")
    stock_indicators = config.get("stock_indicators", {})
    notification_config = config.get("notification", {})

    log_file = notification_config.get("log_file") if notification_config.get("enabled") else None
    play_sound = notification_config.get("sound", True)

    logger = setup_logging(log_file)

    logger.info(f"Starting stock watcher for: {product_name}")
    logger.info(f"URL: {url}")
    logger.info(f"Check interval: {check_interval} seconds")
    logger.info("-" * 60)

    last_status = None
    check_count = 0

    while True:
        check_count += 1
        logger.info(f"Check #{check_count} - Checking stock status...")

        result = check_stock_status(url, stock_indicators, logger)

        current_status = result["status"]
        logger.info(f"Status: {current_status}")

        # Alert if stock becomes available
        if result["available"] is True:
            alert_stock_available(product_name, url, play_sound)
            logger.info("🚨 STOCK AVAILABLE - CHECK THE WEBSITE NOW! 🚨")

            # If status changed from not available to available
            if last_status is not None and last_status.get("available") is not True:
                logger.info("STATUS CHANGED: Product is now IN STOCK!")

        elif result["available"] is False:
            logger.info("Product is still out of stock. Will check again...")

        elif result["available"] is None and result.get("error"):
            logger.warning(f"Error checking status: {result.get('error')}")

        else:
            logger.warning("Could not determine stock status from page content.")

        last_status = result

        # Wait before next check
        logger.info(f"Next check in {check_interval} seconds...")
        logger.info("-" * 60)

        try:
            time.sleep(check_interval)
        except KeyboardInterrupt:
            logger.info("Stock watcher stopped by user.")
            break


def main() -> None:
    """Entry point for the stock watcher."""
    parser = argparse.ArgumentParser(
        description="Monitor XREAL One product page for stock availability"
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)",
    )
    parser.add_argument(
        "--check-once",
        action="store_true",
        help="Check stock status once and exit",
    )

    args = parser.parse_args()

    if args.check_once:
        config = load_config(args.config)
        logger = setup_logging()
        result = check_stock_status(
            config["url"], config.get("stock_indicators", {}), logger
        )
        logger.info(f"Stock status: {result['status']}")
        if result["available"] is True:
            sys.exit(0)  # In stock
        elif result["available"] is False:
            sys.exit(1)  # Out of stock
        else:
            sys.exit(2)  # Unknown/error
    else:
        try:
            run_stock_watcher(args.config)
        except KeyboardInterrupt:
            print("\nStock watcher stopped.")
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
