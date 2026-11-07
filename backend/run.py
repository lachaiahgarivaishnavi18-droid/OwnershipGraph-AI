import os
from app import create_app
from app.models import db
from app.seed import seed

app=create_app()
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('--seed',action='store_true'); parser.add_argument('--port',type=int,default=5055)
    args=parser.parse_args()
    if args.seed:
        if not app.config['DEMO_MODE']: raise RuntimeError('Demo seed requires DEMO_MODE=true')
        with app.app_context(): db.create_all(); seed()
    app.run(host='127.0.0.1',port=args.port,debug=False)
