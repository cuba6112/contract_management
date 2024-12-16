# Contract Management System

A Flask-based web application for managing contracts, with features for importing PDF contracts, generating reports, and tracking contract status.

## Features

- Contract management (Add, Edit, Delete)
- PDF contract import
- PDF report generation with multiple options:
  - All contracts by expiration date (ascending/descending)
  - All contracts by value
  - All contracts by status
  - Active contracts by expiration date (ascending/descending)
- Contract status tracking (Active, Pending, State Contract, Expired, Terminated)
- Advanced search functionality:
  - Search by contract name (partial match)
  - Search by status
  - Search by value (exact match)
  - Search by notes (partial match)
- Sortable contract list
- Date handling based on contract status

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

## Installation

1. Clone or download this repository to your local machine:
```bash
git clone https://github.com/cuba6112/contract_management.git
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

### 1. Adding Contracts
   - Click "Add Contract" button
   - Fill in contract details
   - For Pending or State Contract status, dates are optional

### 2. Editing Contracts
   - Click "Edit" next to a contract
   - Modify contract details
   - Click "Save Changes"

### 3. Deleting Contracts
   - Click "Delete" next to a contract

### 4. Searching Contracts
   - Use the search bar at the top of the contract list
   - Select search field (Contract Name, Status, Value, or Notes)
   - Enter search term
   - Click "Search" or press Enter
   - Use "Clear Search" to return to full list

### 5. Generating Reports
   - Click "Generate Report" dropdown
   - Choose report type:
     - All Contracts by Expiration (Ascending)
     - All Contracts by Expiration (Descending)
     - All Contracts by Value
     - All Contracts by Status
     - Active Contracts by Expiration (Ascending)
     - Active Contracts by Expiration (Descending)

## File Structure

```
contract-management-system/
├── app.py              # Main application file with routes and search functionality
├── models.py           # Database models
├── pdf_operations.py   # PDF handling and report generation
├── requirements.txt    # Project dependencies
├── reset_db.py        # Database initialization script
└── templates/         # HTML templates
    ├── index.html     # Main page with search and list
    ├── add_contract.html
    └── edit_contract.html
```

## Development Notes

### Recent Changes
1. Added search functionality (2024-12-16):
   - Implemented case-insensitive search
   - Added multiple search fields
   - Added search result persistence
   - Integrated with existing UI

2. Added active-only report generation (2024-12-13):
   - New report options for active contracts
   - Sorting by expiration date
   - Improved report formatting

3. Added State Contract status (Previous update):
   - New contract status option
   - Modified date field handling
   - Updated forms and validation

### Database Schema
- Contracts table:
  - id (Primary Key)
  - contract_name (String)
  - start_date (Date, nullable)
  - expiration_date (Date, nullable)
  - value (Float)
  - status (String)
  - notes (Text, nullable)

## Troubleshooting

1. **Database Issues**:
   - Run `reset_db.py` to reset the database
   - Check file permissions in the application directory

2. **PDF Import Issues**:
   - Ensure PDF files are readable and not corrupted
   - Check PDF file permissions

3. **Search Issues**:
   - For value search, ensure you enter a valid number
   - Text searches are partial matches (contain the search term)
   - Status searches are case-insensitive

4. **Installation Issues**:
   - Ensure Python and pip are correctly installed
   - Try creating a new virtual environment
   - Update pip: `pip install --upgrade pip`

## Support

For issues or questions, please create an issue in the repository or contact support.

## Future Enhancements
- Advanced search with date ranges
- Multiple field search
- Export search results to PDF
- Search history
- Saved searches
