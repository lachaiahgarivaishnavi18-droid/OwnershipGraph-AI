import os
from sqlalchemy.pool import NullPool
from . import create_app

def cloud_database_url():
    url=os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or ''
    for prefix in ['postgres://','postgresql://']:
        if url.startswith(prefix): url='postgresql+psycopg://'+url[len(prefix):]
    if not url.startswith('postgresql+psycopg://'):
        raise RuntimeError('Cloud deployment requires a persistent PostgreSQL DATABASE_URL or POSTGRES_URL')
    return url

def create_cloud_app():
    secret=os.getenv('JWT_SECRET_KEY','')
    if len(secret)<32: raise RuntimeError('Cloud deployment requires a stable JWT_SECRET_KEY of at least 32 characters')
    return create_app({
        'SQLALCHEMY_DATABASE_URI':cloud_database_url(),
        'JWT_SECRET_KEY':secret,
        'SQLALCHEMY_ENGINE_OPTIONS':{'poolclass':NullPool,'pool_pre_ping':True},
    })
