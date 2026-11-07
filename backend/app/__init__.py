import os
import secrets
from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException
from .models import db, Revoked

@event.listens_for(Engine,'connect')
def sqlite_fk(connection, record):
    if 'sqlite' in type(connection).__module__:
        connection.execute('PRAGMA foreign_keys=ON')

def create_app(config=None):
    app=Flask(__name__)
    app.json.sort_keys=False
    demo=os.getenv('DEMO_MODE','true').lower()=='true'
    secret=os.getenv('JWT_SECRET_KEY')
    if not demo and (not secret or len(secret)<32): raise RuntimeError('Production requires JWT_SECRET_KEY of at least 32 characters')
    app.config.update(SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL','sqlite:///ownershipgraph.db'),SQLALCHEMY_TRACK_MODIFICATIONS=False,JWT_SECRET_KEY=secret or secrets.token_hex(32),JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=1),MAX_CONTENT_LENGTH=5*1024*1024,DEMO_MODE=demo,JSON_SORT_KEYS=False)
    if config: app.config.update(config)
    app.config.setdefault('ALLOW_SELF_REGISTRATION',os.getenv('ALLOW_SELF_REGISTRATION',str(demo)).lower()=='true')
    db.init_app(app)
    jwt=JWTManager(app)
    @jwt.token_in_blocklist_loader
    def revoked(header,payload): return db.session.get(Revoked,payload['jti']) is not None
    CORS(app,resources={r'/api/*':{'origins':os.getenv('CORS_ORIGINS','http://localhost:5173').split(',')}})
    limiter=Limiter(get_remote_address,app=app,default_limits=['300 per minute'],storage_uri=os.getenv('RATE_LIMIT_STORAGE_URI','memory://'))
    app.extensions['ownershipgraph_rate_limiter']=limiter
    from .api import api
    app.register_blueprint(api,url_prefix='/api')
    app.view_functions['api.login']=limiter.limit('10 per minute')(app.view_functions['api.login'])
    app.view_functions['api.signup']=limiter.limit('5 per hour')(app.view_functions['api.signup'])
    @app.errorhandler(ValidationError)
    def validation(exc): return jsonify(error='Validation failed',details=exc.errors(include_url=False,include_context=False)),422
    @app.errorhandler(ValueError)
    def value(exc): return jsonify(error=str(exc)),422
    @app.errorhandler(IntegrityError)
    def integrity(exc):
        db.session.rollback(); return jsonify(error='Conflicting unique record or referenced record is in use'),409
    @app.errorhandler(HTTPException)
    def http(exc): return jsonify(error=exc.description),exc.code
    @app.errorhandler(Exception)
    def unexpected(exc):
        db.session.rollback()
        app.logger.error('Unhandled application error: %s',type(exc).__name__)
        return jsonify(error='An internal error occurred. Check the service logs and configuration.'),500
    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store'
        response.headers['X-Frame-Options']='DENY'
        return response
    return app
