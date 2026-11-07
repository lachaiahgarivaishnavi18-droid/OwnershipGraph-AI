"""Vercel WSGI entrypoint. Local development still uses backend/run.py."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent/'backend'))
from app.cloud import create_cloud_app

app=create_cloud_app()
