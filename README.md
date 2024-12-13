# Contract Management System

A Flask-based web application for managing contracts, with features for importing PDF contracts, generating reports, and tracking contract status.

## Features

- Contract management (Add, Edit, Delete)
- PDF contract import
- PDF report generation
- Contract status tracking (Active, Pending, State Contract, Expired, Terminated)
- Sortable contract list
- Date handling based on contract status

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

## Installation

1. Clone or download this repository to your local machine:
```bash
git clone <repository-url>
cd contract-management-system
```

2. Create and activate a virtual environment (recommended):
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
python reset_db.py
```

## Running the Application

1. Start the Flask application:
```bash
python app.py
```

2. Open a web browser and navigate to:
```
http://localhost:5000
```

## Usage

1. **Adding Contracts**:
   - Click "Add Contract" button
   - Fill in contract details
   - For Pending or State Contract status, dates are optional

2. **Editing Contracts**:
   - Click "Edit" next to a contract
   - Modify contract details
   - Click "Save Changes"

3. **Deleting Contracts**:
   - Click "Delete" next to a contract

4. **Generating Reports**:
   - Click "Generate Report" to create a PDF report
   - Reports are sorted based on current view

## File Structure

```
contract-management-system/
├── app.py              # Main application file
├── models.py           # Database models
├── pdf_operations.py   # PDF handling functions
├── requirements.txt    # Project dependencies
├── reset_db.py        # Database initialization script
└── templates/         # HTML templates
    ├── index.html
    ├── add_contract.html
    └── edit_contract.html
```

## Troubleshooting

1. **Database Issues**:
   - Run `reset_db.py` to reset the database
   - Check file permissions in the application directory

2. **PDF Import Issues**:
   - Ensure PDF files are readable and not corrupted
   - Check PDF file permissions

3. **Installation Issues**:
   - Ensure Python and pip are correctly installed
   - Try creating a new virtual environment
   - Update pip: `pip install --upgrade pip`

## Support

For issues or questions, please create an issue in the repository or contact support.
