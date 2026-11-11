# Northstar Bank — Banking Web Application

A responsive educational banking web app built with **HTML, CSS, JavaScript, Python (Flask), and SQLite**.

## Features
- Responsive landing page, account registration, login, and dashboard
- Automatically generated 16-digit Luhn-valid card numbers
- PINs stored as password hashes (Werkzeug)
- Balance enquiry
- Deposit and withdrawal
- Transfers between accounts, with both balances and transaction records updated atomically
- Recent activity and transaction history
- Account closure
- Parameterized SQL queries, server-side validation, and session-based authentication
- CSRF token validation for form submissions

## Requirements
- Python 3.9+
- VS Code (recommended)
- No database installation required; SQLite is included with Python

## Run on Windows (VS Code)
1. Extract the ZIP file.
2. In VS Code, choose **File → Open Folder** and select `Banking-Web-Application`.
3. Open **Terminal → New Terminal**.
4. Create a virtual environment (recommended):

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt terminal or run:

   ```powershell
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe app.py
   ```

5. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

6. Start the app:

   ```powershell
   python app.py
   ```

7. Open the local address shown in the terminal, normally `http://127.0.0.1:5000`.

## First test
1. Choose **Open an account**.
2. Enter a name and a 4-digit PIN twice.
3. Save the generated 16-digit card number.
4. Log in with the card number and PIN.
5. Create a second demo account in another browser/private window to test transfers.
6. Deposit into the first account, then transfer to the second account.
7. Log in to the second account to confirm the received amount.

## Database
The app creates `banking_web.db` automatically in this folder on first run. It contains `accounts` and `transactions` tables.

## Important limitations
This is a learning/demo project. It does not connect to a real bank, payment network, or financial institution and must not be used to store real funds or sensitive financial data. It has not undergone a professional security audit. Before any public deployment, set a strong random `SECRET_KEY`, disable Flask debug mode, use HTTPS, add rate limiting and stronger account recovery controls, and arrange a security review.

If this project is adapted from another repository, review its license and retain required attribution. Describe only work you personally understand and can demonstrate.
