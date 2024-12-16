import pdfplumber
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from models import Contract, db
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_text(text):
    """Clean and normalize text."""
    return ' '.join(text.split()).strip()

def parse_date(text):
    """Try to parse date from various formats."""
    date_formats = [
        '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%B %d, %Y',
        '%b %d, %Y', '%Y/%m/%d', '%d-%m-%Y', '%m-%d-%Y'
    ]
    
    # Remove any extra whitespace and common separators
    text = clean_text(text)
    
    for fmt in date_formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None

def parse_value(text):
    """Parse monetary value from text."""
    if not text or any(word in text.lower() for word in ['no', 'not', 'award', 'awarded', 'yet', 'available']):
        return 0.0
        
    # Remove currency symbols, commas, and whitespace
    text = text.replace('$', '').replace(',', '').strip()
    
    # Find any number in the text (including decimals)
    matches = re.findall(r'\d+\.?\d*', text)
    if matches:
        try:
            return float(matches[0])
        except (ValueError, TypeError):
            return 0.0
    return 0.0

def extract_pdf_data(pdf_path):
    """Extract contract data from PDF and store in database."""
    try:
        logger.info(f"Opening PDF file: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"Successfully opened PDF with {len(pdf.pages)} pages")
            
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                logger.info(f"\nRaw text from page {page_num + 1}:")
                logger.info(text)
                
                lines = text.split('\n')
                current_contract = None
                
                for line in lines:
                    line = clean_text(line)
                    logger.info(f"Processing line: {line}")
                    
                    # Skip header line and empty lines
                    if not line or line.startswith('#') or 'Contract Date Expiration Amount' in line:
                        continue
                        
                    # Try to parse contract data from the line
                    parts = line.split()
                    if len(parts) >= 4:  # We need at least contract number, dates, and amount
                        try:
                            # Extract contract number (first part is usually a number)
                            if parts[0].isdigit():
                                if current_contract:
                                    # Save previous contract if exists
                                    if current_contract.value is None:
                                        current_contract.value = 0.0
                                    db.session.add(current_contract)
                                    db.session.commit()
                                    logger.info(f"Successfully added contract: {current_contract.contract_name}")
                                
                                # Start new contract
                                current_contract = Contract()
                                current_contract.contract_name = ""
                                current_contract.value = 0.0  # Default value
                                contract_parts = []
                                amount_found = False
                                
                                # Process each part
                                for part in parts[1:]:  # Skip the contract number
                                    # Check if this part is a date
                                    date = parse_date(part)
                                    if date:
                                        if not current_contract.start_date:
                                            current_contract.start_date = date
                                        elif not current_contract.expiration_date:
                                            current_contract.expiration_date = date
                                        continue
                                    
                                    # Check if this part is an amount (handle special cases)
                                    if (part.startswith('$') or 
                                        part.replace(',', '').replace('.', '').isdigit()) and not amount_found:
                                        value = parse_value(part)
                                        current_contract.value = value if value is not None else 0.0
                                        amount_found = True
                                        continue
                                    
                                    # Handle special cases for amount
                                    if part.lower() in ['no', 'not', 'award', 'awarded', 'yet', 'available']:
                                        continue
                                    
                                    # If not date or amount, it's part of the contract name
                                    contract_parts.append(part)
                                
                                current_contract.contract_name = ' '.join(contract_parts)
                                current_contract.status = 'Active'
                                current_contract.contract_number = parts[0]
                        
                        except Exception as e:
                            logger.error(f"Error processing line: {line}")
                            logger.error(str(e))
                            continue
                    
                    # Handle continuation lines (additional contract name parts)
                    elif current_contract and not any(part.startswith('$') for part in parts):
                        if not any(word.lower() in ['yet', 'awarded', 'available'] for word in parts):
                            current_contract.contract_name += ' ' + line
                
                # Save the last contract if exists
                if current_contract:
                    if current_contract.value is None:
                        current_contract.value = 0.0
                    db.session.add(current_contract)
                    db.session.commit()
                    logger.info(f"Successfully added contract: {current_contract.contract_name}")
                    
        return True
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        db.session.rollback()
        return False

def generate_pdf_report(output_path, contracts=None, sort_by='expiration_date', order='asc', active_only=False):
    from app import Contract
    
    # If no contracts provided, query based on filters
    if contracts is None:
        query = Contract.query
        
        # Apply sorting
        if sort_by == 'expiration_date':
            if order == 'asc':
                query = query.order_by(Contract.expiration_date.asc())
            else:
                query = query.order_by(Contract.expiration_date.desc())
        elif sort_by == 'contract_number':
            if order == 'asc':
                query = query.order_by(Contract.contract_number.asc())
            else:
                query = query.order_by(Contract.contract_number.desc())
                
        contracts = query.all()

    doc = SimpleDocTemplate(output_path, pagesize=landscape(letter))
    elements = []
    
    # Add facility name and title
    styles = getSampleStyleSheet()
    facility_style = ParagraphStyle(
        'FacilityName',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=1,
        spaceAfter=5,
        leading=22
    )
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=1,
        spaceAfter=5,
        leading=20
    )
    
    # Set the title based on the report type
    title_text = "All Contracts Report by Expiration Date" if not active_only else "Active Contracts Report"
    
    facility = Paragraph("Hudson County Correctional Facility", facility_style)
    title = Paragraph(title_text, title_style)
    elements.append(facility)
    elements.append(Spacer(1, 2))
    elements.append(title)
    elements.append(Spacer(1, 2))
    
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=1,
        spaceAfter=10,
        leading=14
    )
    
    # Add date
    current_date = datetime.now().strftime("%B %d, %Y")
    date_paragraph = Paragraph(f"Generated on: {current_date}", date_style)
    elements.append(date_paragraph)
    elements.append(Spacer(1, 10))
    
    # Prepare data for table
    data = [['Contract #', 'Contract Name', 'Start Date', 'Exp. Date', 'Value ($)', 'Status']]
    
    for contract in contracts:
        # Format dates
        start_date = contract.start_date.strftime('%Y-%m-%d') if contract.start_date else ''
        exp_date = contract.expiration_date.strftime('%Y-%m-%d') if contract.expiration_date else ''
        
        # Format value with commas and 2 decimal places
        value = "{:,.2f}".format(contract.value) if contract.value else ''
        
        # Add row to data with wrapped contract name
        data.append([
            contract.contract_number,
            Paragraph(contract.contract_name, ParagraphStyle('contract_name', fontSize=11, leading=13)),
            start_date,
            exp_date,
            value,
            contract.status
        ])
    
    # Create table with adjusted column widths - increased Contract # width
    table = Table(data, colWidths=[1.0*inch, 3.7*inch, 1.1*inch, 1.1*inch, 1.3*inch, 1.3*inch])
    
    # Style the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center align all by default
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),     # Left align contract names
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),    # Right align values
        ('ALIGN', (5, 1), (5, -1), 'LEFT'),     # Left align status
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 13),      # Header font
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),     # Content font
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('WORDWRAP', (0, 0), (-1, -1), True),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('ROWHEIGHT', (0, 0), (-1, -1), 30),
    ])
    
    # Add alternating row colors - using a lighter grey
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.add('BACKGROUND', (0, i), (-1, i), colors.Color(0.9, 0.9, 0.9))
            
    table.setStyle(style)
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
