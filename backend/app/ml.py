import os
import json
from pathlib import Path
from .engine import network, ownership

FEATURES=['depth','shareholders','cycles','shared_connections','concentration','missing_records','cross_jurisdiction_links']

def features(target):
    n=network(target); o=ownership(target)
    return [n['max_depth'],len(o['owners']),len(n['cycles']),len(n['shared_connections']),n['concentration'],len(o['gaps']),n['cross_jurisdiction_links']]

def predict(target):
    path=Path(os.getenv('MODEL_PATH',str(Path(__file__).resolve().parents[2]/'models'/'anomaly.joblib')))
    if not path.exists(): return {'status':'unavailable','reason':'No validated anomaly model artifact available. Run backend/train_model.py for an experimental synthetic model.','model_version':None}
    import joblib
    bundle=joblib.load(path) # trusted, locally generated artifact only
    row=features(target)
    score=float(-bundle['model'].score_samples([row])[0])
    return {'status':'experimental','anomaly_score':score,'model_version':bundle['metadata']['version'],'training_data':'synthetic','features':dict(zip(FEATURES,row)),'explanation':'Isolation Forest novelty score, not a probability of criminal activity. Feature values are descriptive inputs, not causal attributions.','metadata':bundle['metadata']}
