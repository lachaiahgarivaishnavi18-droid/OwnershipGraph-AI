def test_trained_model_inference_is_experimental(app,tmp_path,monkeypatch):
    import joblib
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from app.ml import predict
    path=tmp_path/'model.joblib'
    model=IsolationForest(n_estimators=10,random_state=42).fit(np.random.default_rng(42).uniform(0,10,(30,7)))
    joblib.dump({'model':model,'metadata':{'version':'unit-test-synthetic'}},path)
    monkeypatch.setenv('MODEL_PATH',str(path))
    result=predict(1)
    assert result['status']=='experimental'
    assert 0<result['anomaly_score']<1
    assert result['training_data']=='synthetic'
    assert 'probability' in result['explanation']
