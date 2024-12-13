from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contract_name = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.DateTime)
    expiration_date = db.Column(db.DateTime)
    value = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(50), nullable=False, default='Active')
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<Contract {self.contract_name}>'
