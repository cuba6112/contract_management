from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Contract(db.Model):
    __tablename__ = 'contract'
    
    id = db.Column(db.Integer, primary_key=True)
    contract_number = db.Column(db.String(50), unique=True, nullable=False)
    contract_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    expiration_date = db.Column(db.Date, nullable=True)
    value = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Contract {self.contract_number}: {self.contract_name}>'
