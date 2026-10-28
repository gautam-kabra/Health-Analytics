# Smart Healthcare Analytics

End-to-end healthcare operations analytics project combining four machine-learning techniques with a FastAPI prediction service and a Streamlit dashboard.

**Live dashboard:** <https://health-analyticss.streamlit.app/>

| Task | Technique | Dataset |
|---|---|---|
| Department-level patient demand estimation | Linear Regression | Patient-flow records |
| Appointment no-show risk | Logistic Regression (calibrated) | Medical appointments | 
| Appointment classification / rules | Decision Tree | Medical appointments |
| Patient segmentation | K-Means | Patient-level appointment history |

## What it does

- **Demand forecast** — estimates expected patient volume for each hospital department on a selected date, aggregates department estimates into a hospital total, and converts demand into a simple resource plan (exam rooms, beds, doctors, nurses, support staff).
- **No-show risk** — scores an appointment with a calibrated Logistic Regression and compares the result with a Decision Tree. Returns a risk band and an outreach recommendation.
- **Patient segments** — groups 62k patients by age, appointment frequency, booking lead time, chronic conditions and SMS contact rate, then profiles each segment's no-show rate.

> Segmentation uses patient-level appointment history because the patient-flow extract contains only one visit per patient; appointment history provides the repeat-utilisation and engagement signals needed for operational segments.

## Project structure

```text
health_analytics/
├── data/
│   ├── appointments.csv          # copy of KaggleV2-May-2016.csv
│   └── patient_flow.csv          # copy of healthcare_analytics_patient_flow_data.csv
├── notebooks/
│   ├── 01_demand_forecasting.ipynb
│   ├── 02_no_show_models.ipynb
│   └── 03_patient_segmentation.ipynb
├── models/
│   ├── demand_linear.joblib
│   ├── no_show_logistic.joblib
│   ├── no_show_tree.joblib
│   ├── patient_kmeans.joblib
│   └── *_meta.json               # metrics, thresholds and UI options
├── .streamlit/
│   └── config.toml               # dark theme and client settings
├── app.py                        # FastAPI prediction service
├── dashboard.py                  # Streamlit frontend
├── requirements.txt
├── render.yaml                   # Render API blueprint
├── .gitignore
└── README.md
```

The original dataset archives remain untouched in `archive (2)/` and `archive (3)/`; the notebooks use clean copies in `data/`.

## Quickstart

### 1. Install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Start the prediction API

From the project root:

```powershell
uvicorn app:app --reload
```

- API: <http://127.0.0.1:8000>
- Swagger docs: <http://127.0.0.1:8000/docs>

### 3. Start the dashboard

In a second terminal, with the API still running:

```powershell
streamlit run dashboard.py
```

Open the URL Streamlit prints (normally <http://localhost:8501>).

To point the dashboard at a different API host:

```powershell
$env:HEALTH_API_URL="http://127.0.0.1:8000"
streamlit run dashboard.py
```

The dashboard also reads `HEALTH_API_URL` from Streamlit secrets when the
environment variable is not set. The API URL is a deployment setting, not an
end-user control: the sidebar shows service status only.

## Deployment

The recommended setup is split: the FastAPI API runs on Render and the
Streamlit dashboard runs on Streamlit Community Cloud.

### 1. API on Render

`render.yaml` provisions the API only. Connect the repository to Render and
create a Blueprint from the repository root. The blueprint:

- starts the API with `uvicorn app:app --host 0.0.0.0 --port $PORT`;
- uses `/health` as the health check;
- pins Python to `3.14.8` (use `3.13.5` if a wheel is unavailable).

To configure the service manually, use:

| Setting | Value |
|---|---|
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app:app --host 0.0.0.0 --port $PORT` |
| Health check | `/health` |
| Plan | Free |

After deployment, verify:

```text
https://<api-service>.onrender.com/health
https://<api-service>.onrender.com/docs
```

### 2. Dashboard on Streamlit Community Cloud

1. Push the repository to GitHub.
2. In [Streamlit Community Cloud](https://share.streamlit.io), create a new app
   from the repository and set the main file to `dashboard.py`.
3. In **Advanced settings**, choose Python 3.13 or 3.14 and add the secret:

```toml
HEALTH_API_URL = "https://<api-service>.onrender.com"
```

4. Deploy. The sidebar should show the API as online once the service is awake.

Streamlit Community Cloud ignores `runtime.txt`; select the Python version in
the deployment dialog or the app's settings.

## Notebooks

The notebooks are pre-executed and contain EDA, feature engineering, model training, evaluation plots and artifact-saving code.

1. **01_demand_forecasting.ipynb**
   - Builds a date × department demand panel.
   - Trains a Linear Regression on department, weekday, month and weekend features.
   - Reports both department-day metrics and aggregated daily-total metrics.
   - Saves `demand_linear.joblib` and `demand_meta.json`.

2. **02_no_show_models.ipynb**
   - Cleans 110,526 appointment records and engineers lead time, age group, chronic-condition count and same-day flags.
   - Trains a sigmoid-calibrated Logistic Regression and a depth-6 Decision Tree.
   - Uses a validation split to choose the classification threshold, then evaluates on a held-out test set.
   - Saves both models and `no_show_meta.json`.

3. **03_patient_segmentation.ipynb**
   - Aggregates appointment records to one row per patient.
   - Selects `k = 4` using elbow/silhouette analysis.
   - Labels segments, profiles their no-show rates and saves `patient_kmeans.joblib` and `segments_meta.json`.

To retrain everything, open the notebooks in Jupyter (from the project root or from `notebooks/`) and run all cells. The notebooks locate the project root automatically and write artifacts into `models/`.

> Notebook execution needs JupyterLab (`pip install jupyterlab`); it is not required to run the API or dashboard, because the trained artifacts are already included.

> The included artifacts were trained with Python 3.14 and scikit-learn 1.9. If you use a different environment and see a model-loading warning, rerun the notebooks to rebuild the `.joblib` files.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Service and model status |
| GET | `/metadata` | Metrics, thresholds, EDA summaries and UI options |
| GET | `/options` | Departments, weekdays, neighbourhoods and segments |
| POST | `/predict/demand` | Single-date demand and resource plan |
| GET | `/forecast/demand?start_date=...&days=14&department=...` | Multi-day demand forecast |
| POST | `/predict/no-show` | No-show probability, risk band and action |
| POST | `/predict/segment` | Closest patient segment for a profile |
| GET | `/segments/summary` | Segment sizes, profiles and no-show rates |

Example requests:

```bash
curl -X POST http://127.0.0.1:8000/predict/demand \
  -H "Content-Type: application/json" \
  -d '{"forecast_date":"2026-11-02","department":"All departments"}'
```

```bash
curl -X POST http://127.0.0.1:8000/predict/no-show \
  -H "Content-Type: application/json" \
  -d '{
    "age": 62,
    "gender": "F",
    "scholarship": 0,
    "hipertension": 1,
    "diabetes": 0,
    "alcoholism": 0,
    "handicap": 0,
    "sms_received": 0,
    "lead_time_days": 12,
    "weekday": "Thursday",
    "neighbourhood": "JARDIM DA PENHA"
  }'
```

## Key results

| Model | Result |
|---|---|
| Linear Regression | Department-day R² ≈ 0.817; MAE ≈ 0.90 patients/department-day |
| Logistic Regression | ROC-AUC ≈ 0.721; recall ≈ 0.78 at the validation-selected threshold |
| Decision Tree | ROC-AUC ≈ 0.722; F1 ≈ 0.44 |
| K-Means | 4 segments, silhouette ≈ 0.344, 62,298 patients |

## Important notes

- **Demand signal:** department baselines are stable, but the aggregate daily total in this extract is noisy. The API therefore returns a 95% planning interval, and the dashboard shows the uncertainty rather than pretending the total is precise.
- **No-show probabilities are calibrated.** The binary threshold is tuned for recall because missed appointments are costly; it is not a clinical decision rule.
- **Segments are descriptive.** They describe utilisation and engagement, not causality, and should support — not replace — operational judgement.
- The models are trained on historical data from 2016 and 2023–2024. Revalidate before using them in a live clinical setting.
