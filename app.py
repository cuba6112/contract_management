from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from datetime import datetime
import os
from models import db, Contract
from pdf_operations import extract_pdf_data, generate_pdf_report

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contracts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key-here'  # Required for flashing messages

# Initialize the database with the app
db.init_app(app)

def init_db():
    with app.app_context():
        db.create_all()

@app.route('/')
def index():
    sort_by = request.args.get('sort_by', 'expiration_date')
    order = request.args.get('order', 'asc')
    
    if order == 'asc':
        contracts = Contract.query.order_by(getattr(Contract, sort_by)).all()
    else:
        contracts = Contract.query.order_by(getattr(Contract, sort_by).desc()).all()
    
    return render_template('index.html', contracts=contracts)

@app.route('/add_contract', methods=['GET', 'POST'])
def add_contract():
    if request.method == 'POST':
        try:
            # Create contract with required fields
            contract = Contract(
                contract_name=request.form['contract_name'],
                value=float(request.form['value']),
                status=request.form['status'],
                notes=request.form['notes']
            )
            
            # Only set dates if status is not Pending or State Contract
            if request.form['status'] not in ['Pending', 'State Contract']:
                contract.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
                contract.expiration_date = datetime.strptime(request.form['expiration_date'], '%Y-%m-%d')
            
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
        try:
            contract.contract_name = request.form['contract_name']
            contract.status = request.form['status']
            
            # Handle dates based on status
            if contract.status in ['Pending', 'State Contract']:
                contract.start_date = None
                contract.expiration_date = None
            else:
                contract.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
                contract.expiration_date = datetime.strptime(request.form['expiration_date'], '%Y-%m-%d')
            
            contract.value = float(request.form['value'])
            contract.notes = request.form['notes']
            db.session.commit()
            flash('Contract updated successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error updating contract: {str(e)}', 'error')
            return redirect(url_for('edit_contract', id=id))
    return render_template('edit_contract.html', contract=contract)

@app.route('/delete_contract/<int:id>')
def delete_contract(id):
    try:
        contract = Contract.query.get_or_404(id)
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

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
