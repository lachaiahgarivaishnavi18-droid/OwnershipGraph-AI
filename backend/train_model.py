"""Reproducible synthetic-only anomaly experiment, with held-out novelty summary."""
from pathlib import Path
import json
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split

def train():
    rng=np.random.default_rng(42)
    x=np.column_stack([rng.integers(0,7,600),rng.integers(0,10,600),rng.binomial(1,.1,600),rng.integers(0,5,600),rng.uniform(0,1,600),rng.integers(0,6,600),rng.integers(0,15,600)])
    train_x,test_x=train_test_split(x,test_size=.2,random_state=42)
    model=IsolationForest(n_estimators=160,random_state=42,contamination='auto').fit(train_x)
    scores=-model.score_samples(test_x)
    metadata={'version':'synthetic-isolation-1.0','seed':42,'training_rows':len(train_x),'held_out_rows':len(test_x),'held_out_score_mean':float(scores.mean()),'held_out_score_std':float(scores.std()),'training_data':'independent synthetic feature vectors; no crime labels','limitations':'No supervised accuracy, PR-AUC, ROC-AUC or calibration claims are possible without real validated labels. No operational validation.'}
    out=Path(__file__).resolve().parents[1]/'models'; out.mkdir(exist_ok=True)
    joblib.dump({'model':model,'metadata':metadata},out/'anomaly.joblib')
    (out/'model_metadata.json').write_text(json.dumps(metadata,indent=2))
    print(json.dumps(metadata,indent=2))
if __name__=='__main__': train()
