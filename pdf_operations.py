import pdfplumber
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
    """Generate a PDF report of contracts."""
    if contracts is None:
        query = Contract.query
        if active_only:
            query = query.filter_by(status='Active')
            
        if order == 'asc':
            contracts = query.order_by(getattr(Contract, sort_by)).all()
        else:
            contracts = query.order_by(getattr(Contract, sort_by).desc()).all()

    # Use landscape orientation for better fit
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=20,
        alignment=1  # Center alignment
    )
    elements.append(Paragraph('Contract Report', title_style))
    
    # Add report metadata
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.gray,
        alignment=1  # Center alignment
    )
    elements.append(Paragraph(f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', meta_style))
    elements.append(Paragraph(f'Sorted by: {sort_by.replace("_", " ").title()} ({order})', meta_style))
    elements.append(Spacer(1, 20))

    # Calculate column widths based on content
    contract_name_width = 180  # Slightly reduced to give more space to dates
    date_width = 95  # Increased for better header fit
    value_width = 100  # Enough for currency values
    status_width = 80  # Enough for status
    
    # Create header style for wrapping
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=colors.whitesmoke,
        alignment=1,  # Center alignment
        spaceAfter=0,
        spaceBefore=0,
    )
    
    # Create table data with wrapped headers
    data = [[
        Paragraph('Contract Name', header_style),
        Paragraph('Start Date', header_style),
        Paragraph('Expiration<br/>Date', header_style),  # Add line break in header
        Paragraph('Value', header_style),
        Paragraph('Status', header_style)
    ]]
    
    for contract in contracts:
        data.append([
            Paragraph(contract.contract_name, styles['Normal']),  # Wrap contract names
            contract.start_date.strftime('%Y-%m-%d') if contract.start_date else '',
            contract.expiration_date.strftime('%Y-%m-%d') if contract.expiration_date else '',
            f'${contract.value:,.2f}',
            contract.status
        ])

    # Create table with specific column widths
    table = Table(data, repeatRows=1, colWidths=[
        contract_name_width, date_width, date_width, value_width, status_width
    ])
    
    # Enhanced table styling
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Content styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),  # Center all content
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        
        # Grid styling
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2c3e50')),
        
        # Column-specific styling
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Left-align contract names
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Right-align values
        
        # Alternating row colors
        *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9f9f9')) for i in range(2, len(data), 2)]
    ]))
    
    elements.append(table)
    
    # Add footer
    elements.append(Spacer(1, 20))
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        alignment=1
    )
    elements.append(Paragraph('End of Report', footer_style))

    # Build PDF
    doc.build(elements)
