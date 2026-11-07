"""Build React into Vercel's CDN directory, optionally initialize a new cloud DB."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--skip-install',action='store_true');args=parser.parse_args()
    if not args.skip_install:
        npx=shutil.which('npx')
        if not npx: raise RuntimeError('Vercel build requires Node.js with npx')
        subprocess.run([npx,'--yes','pnpm@11.25.0','--dir','frontend','install','--frozen-lockfile'],cwd=ROOT,check=True)
    node=shutil.which('node')
    if not node: raise RuntimeError('Node.js is required for the frontend build')
    subprocess.run([node,'node_modules/vite/bin/vite.js','build'],cwd=ROOT/'frontend',check=True)
    shutil.copytree(ROOT/'frontend'/'dist',ROOT/'public',dirs_exist_ok=True)
    if os.getenv('VERCEL_INITIALIZE_DATABASE','false').lower()=='true':
        subprocess.run([sys.executable,str(ROOT/'scripts'/'initialize_cloud.py')],cwd=ROOT,check=True)
    if os.getenv('VERCEL_UPDATE_DEMO_PASSWORD','false').lower()=='true':
        subprocess.run([sys.executable,str(ROOT/'scripts'/'update_demo_password.py')],cwd=ROOT,check=True)
    print('React build prepared in public/; Flask serves /api from index.py.')

if __name__=='__main__': main()
