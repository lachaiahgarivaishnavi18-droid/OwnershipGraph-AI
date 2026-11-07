import io
import pytest
from app.cloud import cloud_database_url,create_cloud_app

def test_cloud_requires_persistent_database(monkeypatch):
    monkeypatch.delenv('DATABASE_URL',raising=False);monkeypatch.delenv('POSTGRES_URL',raising=False)
    with pytest.raises(RuntimeError,match='persistent PostgreSQL'): cloud_database_url()
    monkeypatch.setenv('DATABASE_URL','sqlite:///local.db')
    with pytest.raises(RuntimeError,match='persistent PostgreSQL'): cloud_database_url()

def test_cloud_normalizes_managed_postgres_driver(monkeypatch):
    monkeypatch.delenv('DATABASE_URL',raising=False)
    monkeypatch.setenv('POSTGRES_URL','postgres://demo:secret@example.invalid/ownership?sslmode=require')
    assert cloud_database_url().startswith('postgresql+psycopg://')

def test_cloud_requires_stable_jwt_secret(monkeypatch):
    monkeypatch.delenv('JWT_SECRET_KEY',raising=False)
    with pytest.raises(RuntimeError,match='stable JWT_SECRET_KEY'): create_cloud_app()

def test_xlsx_import_without_pandas(client,headers):
    from openpyxl import Workbook
    book=Workbook();sheet=book.active
    sheet.append(['external_id','entity_name','entity_type','jurisdiction','source_id','synthetic'])
    sheet.append(['XLSX-DEMO','Synthetic Excel Record','COMPANY','Demo',1,True])
    stream=io.BytesIO();book.save(stream);stream.seek(0)
    response=client.post('/api/import/entities',data={'file':(stream,'entities.xlsx'),'dry_run':'false'},headers=headers)
    assert response.status_code==200,response.json
    assert response.json['imported']==1

def test_xlsx_rejects_duplicate_headers(client,headers):
    from openpyxl import Workbook
    book=Workbook();book.active.append(['source_id','source_id']);book.active.append([1,1])
    stream=io.BytesIO();book.save(stream);stream.seek(0)
    response=client.post('/api/import/entities',data={'file':(stream,'entities.xlsx')},headers=headers)
    assert response.status_code==422
    assert 'unique' in response.json['error']
