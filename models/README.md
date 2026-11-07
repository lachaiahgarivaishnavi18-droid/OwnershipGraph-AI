# Model artifacts

Run `python backend/train_model.py` to create anomaly.joblib and model_metadata.json.
The model uses reproducible synthetic feature vectors, never real crime labels.
Only load artifacts generated locally by a trusted operator: joblib uses pickle.
Model absence is a supported workflow state. No model metrics are fabricated.
