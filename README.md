# MoneyMatters 💰

Personal finance tracker that aggregates transactions from multiple financial accounts. Built as a Mint alternative after its discontinuation.

## Features (Current)

- ✅ Import Chase credit card transactions from CSV
- ✅ SQLite database storage
- ✅ Account-type aware summaries (credit cards vs bank accounts)
- ✅ Duplicate transaction detection
- ✅ Transaction history tracking

## Planned Features

- [ ] Auto-categorization of transactions
- [ ] Monthly spending reports
- [ ] Spending trends and visualizations
- [ ] Multi-bank support
- [ ] Net worth tracking
- [ ] Budget tracking
- [ ] Command-line dashboard

## Setup
```bash
# Clone repo
git clone https://github.com/ModulasKhwaait/moneyMatters.git
cd moneyMatters

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

## Usage

1. Export your Chase transactions as CSV
2. Place CSV in `data/raw/` folder
3. Run importer:
```bash
python src/importer.py
```

## Privacy & Security

⚠️ **Important:** This tool stores your financial data locally. Never commit your actual transaction data to GitHub!

- All transaction files in `data/` are gitignored
- Database files are gitignored
- Only code is shared publicly

## Project Structure
```
moneyMatters/
├── src/
│   ├── database.py    # Database operations
│   ├── importer.py    # CSV import logic
│   ├── categorizer.py # (Coming soon)
│   └── reporter.py    # (Coming soon)
├── data/
│   ├── raw/          # CSV imports (gitignored)
│   └── finance.db    # SQLite database (gitignored)
└── reports/          # Generated reports
```

## Tech Stack

- Python 3.9+
- SQLite (database)
- Pandas (data processing)
- (More to come...)

---

**Status:** 🚧 Work in Progress - Built for personal use as a Mint replacement