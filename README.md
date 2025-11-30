# Black-Friday-watcher

A monitoring tool suite to watch XREAL product pages for stock availability and price changes during Black Friday sales.

## Features

### Stock Watcher (`stock_watcher.py`)
- 🔄 Continuous monitoring of the XREAL One product page for stock availability
- 🔔 Alerts when stock becomes available (sound + visual notification)
- 📝 Logging of all stock checks
- ⚙️ Configurable check intervals and stock indicators
- 🛑 Graceful shutdown with Ctrl+C

### Price Watcher (`price_watcher.py`)
- 💰 Continuous monitoring of the XREAL One Pro product page for price changes
- 🔔 Alerts when price changes (sound + visual notification)
- 📝 Logging of all price checks
- 💾 Persists last known price to detect changes across restarts
- ⚙️ Configurable check intervals

## Target URLs

- **Stock Watcher**: https://eu.shop.xreal.com/en-nl/products/xreal-one
- **Price Watcher**: https://eu.shop.xreal.com/en-nl/products/xreal-one-pro

## Requirements

- Python 3.10+
- Required packages listed in `requirements.txt`

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/Wadelz/Black-Friday-watcher.git
   cd Black-Friday-watcher
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Stock Watcher

#### Continuous Monitoring

Run the stock watcher to continuously monitor for stock availability:

```bash
python stock_watcher.py
```

#### Single Check

Check the stock status once and exit:

```bash
python stock_watcher.py --check-once
```

Exit codes for single check:
- `0` - Product is in stock
- `1` - Product is out of stock
- `2` - Unknown status or error

#### Custom Configuration

Use a custom configuration file:

```bash
python stock_watcher.py -c /path/to/custom-config.json
```

### Price Watcher

#### Continuous Monitoring

Run the price watcher to continuously monitor for price changes:

```bash
python price_watcher.py
```

#### Single Check

Check the current price once and exit:

```bash
python price_watcher.py --check-once
```

#### Custom Configuration

Use a custom configuration file:

```bash
python price_watcher.py -c /path/to/custom-price-config.json
```

### Running Both Watchers

To run both watchers simultaneously, open two terminal windows:

```bash
# Terminal 1 - Stock watcher for XREAL One
python stock_watcher.py

# Terminal 2 - Price watcher for XREAL One Pro
python price_watcher.py
```

## Configuration

### Stock Watcher Configuration

Edit `config.json` to customize the stock monitoring behavior:

```json
{
    "url": "https://eu.shop.xreal.com/en-nl/products/xreal-one",
    "check_interval_seconds": 60,
    "product_name": "XREAL One",
    "stock_indicators": {
        "out_of_stock": ["out of stock", "sold out", "unavailable", "notify me"],
        "in_stock": ["add to cart", "buy now", "add to bag", "in stock"]
    },
    "notification": {
        "enabled": true,
        "sound": true,
        "log_file": "stock_alerts.log"
    }
}
```

#### Stock Watcher Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `url` | Product page URL to monitor | XREAL One page |
| `check_interval_seconds` | Seconds between checks | 60 |
| `product_name` | Name shown in alerts | XREAL One |
| `stock_indicators.out_of_stock` | Text patterns indicating out of stock (case-insensitive) | Various |
| `stock_indicators.in_stock` | Text patterns indicating availability (case-insensitive) | Various |
| `notification.enabled` | Enable logging to file | true |
| `notification.sound` | Play sound on stock alert | true |
| `notification.log_file` | Log file path | stock_alerts.log |

### Price Watcher Configuration

Edit `price_config.json` to customize the price monitoring behavior:

```json
{
    "url": "https://eu.shop.xreal.com/en-nl/products/xreal-one-pro",
    "check_interval_seconds": 300,
    "product_name": "XREAL One Pro",
    "price_file": "last_price.json",
    "notification": {
        "enabled": true,
        "sound": true,
        "log_file": "price_alerts.log"
    }
}
```

#### Price Watcher Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `url` | Product page URL to monitor | XREAL One Pro page |
| `check_interval_seconds` | Seconds between checks | 300 |
| `product_name` | Name shown in alerts | XREAL One Pro |
| `price_file` | File to persist last known price | last_price.json |
| `notification.enabled` | Enable logging to file | true |
| `notification.sound` | Play sound on price change | true |
| `notification.log_file` | Log file path | price_alerts.log |

## Running in Background

### Linux/macOS

Use `nohup` to run in background:

```bash
nohup python stock_watcher.py > output.log 2>&1 &
```

Or use `screen` or `tmux` for persistent sessions.

### Windows

Use Task Scheduler or run in a minimized terminal.

## Tips for Black Friday

1. **Reduce check interval**: Set `check_interval_seconds` to 30 or less during peak sale times
2. **Keep terminal visible**: Keep the terminal window visible so you can see alerts immediately
3. **Enable sound**: Make sure `notification.sound` is `true` and your system volume is on
4. **Be ready**: Have the product page open in your browser, logged into your account with payment ready

## Troubleshooting

### "Could not resolve host" or connection errors
- Check your internet connection
- The website might be blocking requests; try increasing `check_interval_seconds`
- Some networks/VPNs may block the connection

### "UNKNOWN - Could not determine stock status"
- The page structure may have changed
- Check the page manually and update `stock_indicators` in config

## License

MIT License
