"""Migrate a dedicated cloud database; optionally seed synthetic demo records."""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.cloud import cloud_database_url,create_cloud_app
from alembic import command
from alembic.config import Config

def main():
    os.environ['DATABASE_URL']=cloud_database_url()
    cfg=Config(str(ROOT/'alembic.ini'))
    cfg.set_main_option('script_location',str(ROOT/'backend'/'migrations'))
    command.upgrade(cfg,'head')
    if os.getenv('DEMO_MODE','false').lower()=='true':
        from app.seed import seed
        with create_cloud_app().app_context(): seed()
    print('Cloud database migrated; synthetic seed applied only when DEMO_MODE=true.')

if __name__=='__main__': main()
