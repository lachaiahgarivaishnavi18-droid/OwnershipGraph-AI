"""Explicit operator update for the three synthetic demo accounts only."""
import os
from flask import current_app
from werkzeug.security import generate_password_hash
from .models import db,User,Audit

def update_demo_password():
    if not current_app.config['DEMO_MODE']: raise ValueError('Demo-account updates require DEMO_MODE=true')
    password=os.getenv('DEMO_PASSWORD','')
    if not 8<=len(password)<=128: raise ValueError('DEMO_PASSWORD must contain 8–128 characters')
    count=0
    for username,role in [('analyst','analyst'),('reviewer','reviewer'),('admin','administrator')]:
        user=db.session.query(User).filter_by(username=username,email=f'{username}@demo.invalid',role=role).first()
        if not user: raise ValueError(f'Expected synthetic demo account not found: {username}')
        user.password_hash=generate_password_hash(password)
        db.session.add(Audit(action='demo_password_updated',resource_type='user',resource_id=user.id,details={'synthetic_demo_account':True}))
        count+=1
    db.session.commit()
    return count
