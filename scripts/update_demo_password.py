"""Run once during an explicitly requested demo-password update."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.cloud import create_cloud_app
from app.demo_accounts import update_demo_password

if __name__=='__main__':
    with create_cloud_app().app_context():
        count=update_demo_password()
        print(f'Updated {count} synthetic demo accounts; other accounts were not modified.')
