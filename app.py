from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from datetime import datetime
import os
from models import db, Contract
from pdf_operations import extract_pdf_data, generate_pdf_report

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contracts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    search_field = request.args.get('search_field', '')
    search_term = request.args.get('search_term', '')
    sort_by = request.args.get('sort_by', 'expiration_date')
    order = request.args.get('order', 'asc')
    
    query = Contract.query
    
    if search_term and search_field:
        if search_field == 'contract_number':
            query = query.filter(Contract.contract_number.ilike(f'%{search_term}%'))
        elif search_field == 'contract_name':
            query = query.filter(Contract.contract_name.ilike(f'%{search_term}%'))
        elif search_field == 'status':
            query = query.filter(Contract.status.ilike(f'%{search_term}%'))
        elif search_field == 'value':
            try:
                value = float(search_term)
                query = query.filter(Contract.value == value)
            except ValueError:
                flash('Please enter a valid number for value search', 'error')
        elif search_field == 'notes':
            query = query.filter(Contract.notes.ilike(f'%{search_term}%'))
    
    if order == 'asc':
        query = query.order_by(getattr(Contract, sort_by))
    else:
        query = query.order_by(getattr(Contract, sort_by).desc())
    
    contracts = query.all()
    return render_template('index.html', 
                         contracts=contracts,
                         search_field=search_field,
                         search_term=search_term,
                         title="Hudson County Correctional Facility",
                         page_title="Contract Management System")

@app.route('/add_contract', methods=['GET', 'POST'])
def add_contract():
    if request.method == 'POST':
        contract_number = request.form.get('contract_number', '').strip()
        contract_name = request.form.get('contract_name', '').strip()
        start_date = request.form.get('start_date')
        expiration_date = request.form.get('expiration_date')
        value = request.form.get('value')
        status = request.form.get('status')
        notes = request.form.get('notes')

        # Validate contract number
        if not contract_number:
            flash('Contract number is required', 'error')
            return redirect(url_for('add_contract'))

        # Check if contract number already exists
        existing_contract = Contract.query.filter_by(contract_number=contract_number).first()
        if existing_contract:
            flash('This contract number already exists in the database', 'error')
            return redirect(url_for('add_contract'))

        try:
            # Convert dates if they're not empty
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
            expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d').date() if expiration_date else None
            
            contract = Contract(
                contract_number=contract_number,
                contract_name=contract_name,
                start_date=start_date,
                expiration_date=expiration_date,
                value=float(value),
                status=status,
                notes=notes
            )
            db.session.add(contract)
            db.session.commit()
            flash('Contract added successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error adding contract: {str(e)}', 'error')
            return redirect(url_for('add_contract'))

    return render_template('add_contract.html')

@app.route('/edit_contract/<int:id>', methods=['GET', 'POST'])
def edit_contract(id):
    contract = Contract.query.get_or_404(id)
    if request.method == 'POST':
        new_contract_number = request.form.get('contract_number', '').strip()
        
        # Validate contract number
        if not new_contract_number:
            flash('Contract number is required', 'error')
            return redirect(url_for('edit_contract', id=id))

        # Check if new contract number already exists (excluding current contract)
        existing_contract = Contract.query.filter(
            Contract.contract_number == new_contract_number,
            Contract.id != id
        ).first()
        
        if existing_contract:
            flash('This contract number is already used by another contract', 'error')
            return redirect(url_for('edit_contract', id=id))

        try:
            contract.contract_number = new_contract_number
            contract.contract_name = request.form.get('contract_name', '').strip()
            start_date = request.form.get('start_date')
            expiration_date = request.form.get('expiration_date')
            contract.start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
            contract.expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d').date() if expiration_date else None
            contract.value = float(request.form.get('value'))
            contract.status = request.form.get('status')
            contract.notes = request.form.get('notes')
            
            db.session.commit()
            flash('Contract updated successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error updating contract: {str(e)}', 'error')
            return redirect(url_for('edit_contract', id=id))

    return render_template('edit_contract.html', contract=contract)

@app.route('/delete_contract/<int:id>')
def delete_contract(id):
    contract = Contract.query.get_or_404(id)
    try:
        db.session.delete(contract)
        db.session.commit()
        flash('Contract deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting contract: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/import_pdf')
def import_pdf():
    try:
        pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Contract_hccc.pdf')
        if not os.path.exists(pdf_path):
            flash(f'PDF file not found at: {pdf_path}', 'error')
            return redirect(url_for('index'))
        
        extract_pdf_data(pdf_path)
        flash('PDF imported successfully!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error importing PDF: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/generate_report')
def generate_report():
    try:
        sort_by = request.args.get('sort_by', 'expiration_date')
        order = request.args.get('order', 'asc')
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'contract_report.pdf')
        generate_pdf_report(output_path, sort_by=sort_by, order=order, active_only=active_only)
        
        return send_file(output_path, as_attachment=True, download_name='contract_report.pdf')
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/search')
def search():
    search_term = request.args.get('query', '').strip()
    search_field = request.args.get('field', 'contract_name')
    
    if not search_term:
        return redirect(url_for('index'))
    
    # Create the base query
    query = Contract.query
    
    # Apply search filter based on the selected field
    if search_field == 'contract_number':
        query = query.filter(Contract.contract_number.ilike(f'%{search_term}%'))
    elif search_field == 'contract_name':
        query = query.filter(Contract.contract_name.ilike(f'%{search_term}%'))
    elif search_field == 'status':
        query = query.filter(Contract.status.ilike(f'%{search_term}%'))
    elif search_field == 'value':
        try:
            search_value = float(search_term)
            query = query.filter(Contract.value == search_value)
        except ValueError:
            flash('Please enter a valid number for value search', 'error')
            return redirect(url_for('index'))
    elif search_field == 'notes':
        query = query.filter(Contract.notes.ilike(f'%{search_term}%'))
    
    # Execute the query
    contracts = query.all()
    
    # Flash a message if no results found
    if not contracts:
        flash(f'No contracts found matching "{search_term}" in {search_field}', 'info')
    
    return render_template('index.html', 
                         contracts=contracts, 
                         search_term=search_term, 
                         search_field=search_field)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
