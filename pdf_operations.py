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

def generate_pdf_report(output_path, contracts=None, sort_by='expiration_date', order='asc', active_only=False, report_type=None):
    """Generate a PDF report of contracts."""
    # Use landscape orientation for more width
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=1,  # Center alignment
        spaceAfter=20
    )
    title = "Hudson County Correctional Facility - Contract Report"
    elements.append(Paragraph(title, title_style))
    
    if report_type == 'simplified':
        # Simplified report with only contract name, dates, and value
        data = [['Contract Name', 'Start Date', 'Expiration Date', 'Value']]
        
        # Query all contracts if not provided
        if contracts is None:
            from app import Contract
            query = Contract.query
            
            # Apply sorting
            if sort_by == 'expiration_date':
                if order == 'asc':
                    query = query.order_by(Contract.expiration_date.asc())
                else:
                    query = query.order_by(Contract.expiration_date.desc())
            
            if active_only:
                query = query.filter(Contract.status == 'Active')
            
            contracts = query.all()
        
        for contract in contracts:
            # Create Paragraph for contract name to enable proper wrapping
            contract_name = Paragraph(
                contract.contract_name,
                ParagraphStyle(
                    'ContractName',
                    fontSize=10,
                    leading=12,  # Line spacing
                    spaceBefore=0,
                    spaceAfter=0,
                )
            )
            data.append([
                contract_name,  # Use Paragraph object instead of plain text
                contract.start_date.strftime('%Y-%m-%d') if contract.start_date else '',
                contract.expiration_date.strftime('%Y-%m-%d') if contract.expiration_date else '',
                "${:,.2f}".format(contract.value) if contract.value else ''
            ])
        
        # Create table with specific column widths
        available_width = doc.width  # Use full available width
        col_widths = [available_width * 0.5, available_width * 0.15, available_width * 0.15, available_width * 0.2]
        table = Table(data, colWidths=col_widths, repeatRows=1)  # repeatRows=1 makes header repeat on each page
        
        # Style the table to match the example
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.85, 0.85, 0.85)),  # Light gray
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Content style
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Left align contract names
            ('ALIGN', (1, 1), (2, -1), 'CENTER'),  # Center align dates
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),   # Right align values
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.grey),  # Slightly thicker line below header
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            
            # Text wrapping and alignment
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically center all content
        ]))
        
        # Add table to elements
        elements.append(table)
        
        # Build the PDF
        doc.build(elements)
    else:
        # Full report with all details
        data = [['Contract #', 'Contract Name', 'Start Date', 'Expiration Date', 'Value', 'Status', 'Notes']]
        for contract in contracts:
            data.append([
                contract.contract_number,
                contract.contract_name,
                contract.start_date.strftime('%Y-%m-%d') if contract.start_date else '',
                contract.expiration_date.strftime('%Y-%m-%d') if contract.expiration_date else '',
                "${:,.2f}".format(contract.value) if contract.value else '',
                contract.status,
                contract.notes if contract.notes else ''
            ])
        
        # Create the table with appropriate styling
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
    
        elements.append(table)
        doc.build(elements)
