# Financial Fraud Detection Engine (Rule-Based)

Python-based tool designed to analyze financial transactions and detect potentially suspicious patterns using rule-based logic and behavioral analysis.

---

## Overview

This project simulates a basic fraud detection system similar to those used in financial institutions. It evaluates transactions using predefined rules and assigns a risk score based on detected anomalies.

The system is designed to be modular, testable, and easily extendable.

---

## Key Features

* Rule-based fraud detection engine
* Risk scoring system (low, medium, high)
* Detection of high-value transactions
* Detection of transactions outside allowed time windows
* Detection of transaction splitting (smurfing)
* Detection of recurring behavioral patterns
* Command-line interface (CLI)
* Automatic report generation (`informe.txt`)
* Unit testing with `unittest`

---

## Detection Rules

### Basic Rules

* Transaction amount greater than 3000€
* Transactions outside allowed hours (08:00 - 22:00)

### Advanced Behavioral Rules

* **Transaction Splitting (Smurfing):**
  Multiple small transactions within the same day indicating possible structuring

* **Recurring Patterns:**
  Similar transactions across different dates suggesting repetitive behavior

---

## Project Structure

```text
detector-transacciones-sospechosas/
│
├── main.py        # Entry point (CLI)
├── detector.py    # Core fraud detection logic
├── utils.py       # Data loading and reporting
├── config.py      # Configuration and thresholds
├── tests/         # Unit tests
│   └── test_detector.py
│
├── transacciones.csv
├── README.md
└── .gitignore
```

---

## Installation

No external dependencies required.

```bash
python --version
```

---

## Usage

Run with default dataset:

```bash
python main.py
```

Run with custom file:

```bash
python main.py --file transacciones.csv
```

---

## Example Output

The system generates:

* Console report
* File report (`informe.txt`)

Example detections:

* High-value transaction
* Out-of-hours activity
* Grouped suspicious transactions
* Recurrent behavioral patterns

---

## Running Tests

```bash
python -m unittest discover -s tests
```

Expected output:

```text
Ran X tests

OK
```

---

## Design Approach

The system follows a modular design:

* Separation of concerns (logic, config, IO)
* Rule-based scoring engine
* Extensible architecture for adding new fraud rules
* Testable components

---

## Future Improvements

* External configuration via JSON/YAML
* Machine learning-based anomaly detection
* Real-time processing
* Visualization dashboard
* API integration (FastAPI)
* False positive reduction mechanisms

---

## Use Cases

* Fraud detection simulation
* Financial data analysis
* Rule-based anomaly detection systems
* Educational projects in cybersecurity and fintech

---

## Author

Developed as a practical project focused on financial anomaly detection and backend system design.
