"""
Smart Healthcare Analytics — FastAPI prediction service.

Run locally:
    uvicorn app:app --reload
or:
    python app.py

Production:
    uvicorn app:app --host 0.0.0.0 --port $PORT

Interactive API docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import json
import math
import os
from datetime import date as Date, timedelta
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models"


# ---------------------------------------------------------------------------
# Load artifacts
# ---------------------------------------------------------------------------
def _load_json(filename: str) -> dict[str, Any]:
    path = MODEL_DIR / filename
    if not path.exists():
        raise RuntimeError(
            f"Missing metadata file: {path}. Run the notebooks in notebooks/ first."
        )
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _load_model(filename: str):
    path = MODEL_DIR / filename
    if not path.exists():
        raise RuntimeError(
            f"Missing model file: {path}. Run the notebooks in notebooks/ first."
        )
    return joblib.load(path)


DEMAND_META = _load_json("demand_meta.json")
NO_SHOW_META = _load_json("no_show_meta.json")
SEGMENTS_META = _load_json("segments_meta.json")

demand_model = _load_model("demand_linear.joblib")
logistic_model = _load_model("no_show_logistic.joblib")
tree_model = _load_model("no_show_tree.joblib")
segmentation_model = _load_model("patient_kmeans.joblib")

ALL_DEPARTMENTS = "All departments"
DEPARTMENTS = DEMAND_META["departments"]
DEPARTMENT_OPTIONS = [ALL_DEPARTMENTS, *DEPARTMENTS]
WEEKDAYS = NO_SHOW_META["options"]["weekdays"]
NEIGHBOURHOODS = NO_SHOW_META["options"]["neighbourhoods"]
AGE_GROUPS = NO_SHOW_META["options"]["age_groups"]
RISK_BANDS = NO_SHOW_META["risk_bands"]
RESOURCE_ASSUMPTIONS = DEMAND_META["resource_assumptions"]


def age_group(age: int) -> str:
    if age <= 17:
        return "0-17"
    if age <= 34:
        return "18-34"
    if age <= 49:
        return "35-49"
    if age <= 64:
        return "50-64"
    return "65+"


def validate_department(department: str) -> str:
    if department not in DEPARTMENT_OPTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown department '{department}'. Choose one of: {DEPARTMENT_OPTIONS}",
        )
    return department


def demand_feature_row(forecast_date: Date, department: str) -> pd.DataFrame:
    timestamp = pd.Timestamp(forecast_date)
    return pd.DataFrame(
        [
            {
                "department": department,
                "weekday": timestamp.day_name(),
                "month": timestamp.month_name(),
                "is_weekend": int(timestamp.dayofweek >= 5),
            }
        ]
    )


def predict_department(forecast_date: Date, department: str) -> float:
    row = demand_feature_row(forecast_date, department)
    prediction = float(demand_model.predict(row)[0])
    return max(0.0, prediction)


def resource_plan(patients: float) -> dict[str, int]:
    assumptions = RESOURCE_ASSUMPTIONS
    expected_admissions = patients * DEMAND_META["admission_rate"]
    return {
        "exam_rooms": max(1, math.ceil(patients * assumptions["exam_rooms_per_patient"])),
        "beds": max(1, math.ceil(expected_admissions * assumptions["bed_buffer"])),
        "doctors": max(1, math.ceil(patients / assumptions["patients_per_doctor"])),
        "nurses": max(1, math.ceil(patients / assumptions["patients_per_nurse"])),
        "support_staff": max(
            1, math.ceil(patients / assumptions["patients_per_support"])
        ),
    }


def build_demand_response(
    forecast_date: Date, department: str = ALL_DEPARTMENTS
) -> dict[str, Any]:
    department = validate_department(department)

    if department == ALL_DEPARTMENTS:
        department_predictions = {
            dept: predict_department(forecast_date, dept) for dept in DEPARTMENTS
        }
        predicted_patients = sum(department_predictions.values())
        residual_std = float(DEMAND_META["daily_total_residual_std"])
        department_breakdown = [
            {
                "department": dept,
                "expected_patients": round(value, 2),
                "share": round(value / predicted_patients, 3)
                if predicted_patients > 0
                else 0.0,
            }
            for dept, value in sorted(
                department_predictions.items(), key=lambda item: item[1], reverse=True
            )
        ]
        display_precision = 1
    else:
        predicted_patients = predict_department(forecast_date, department)
        residual_std = float(DEMAND_META["residual_std"])
        department_breakdown = [
            {
                "department": department,
                "expected_patients": round(predicted_patients, 2),
                "share": 1.0,
            }
        ]
        display_precision = 2

    margin = 1.96 * residual_std
    lower = max(0.0, predicted_patients - margin)
    upper = predicted_patients + margin
    expected_admissions = predicted_patients * DEMAND_META["admission_rate"]

    return {
        "forecast_date": forecast_date.isoformat(),
        "weekday": pd.Timestamp(forecast_date).day_name(),
        "department": department,
        "predicted_patients": round(predicted_patients, display_precision),
        "prediction_interval": [
            round(lower, display_precision),
            round(upper, display_precision),
        ],
        "expected_admissions": round(expected_admissions, display_precision),
        "resource_plan": resource_plan(predicted_patients),
        "department_breakdown": department_breakdown,
    }


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class DemandRequest(BaseModel):
    forecast_date: Date = Field(
        default_factory=Date.today, description="Date to forecast"
    )
    department: str = Field(
        default=ALL_DEPARTMENTS,
        description=f"One of {DEPARTMENT_OPTIONS}",
    )


class NoShowRequest(BaseModel):
    age: int = Field(ge=0, le=120, description="Patient age in years")
    gender: Literal["F", "M"] = "F"
    scholarship: int = Field(default=0, ge=0, le=1)
    hipertension: int = Field(default=0, ge=0, le=1)
    diabetes: int = Field(default=0, ge=0, le=1)
    alcoholism: int = Field(default=0, ge=0, le=1)
    handicap: int = Field(default=0, ge=0, le=4)
    sms_received: int = Field(default=1, ge=0, le=1)
    lead_time_days: int = Field(default=7, ge=0, le=365)
    weekday: str = "Monday"
    neighbourhood: str = "JARDIM DA PENHA"

    @field_validator("weekday")
    @classmethod
    def weekday_must_be_valid(cls, value: str) -> str:
        if value not in WEEKDAYS:
            raise ValueError(f"weekday must be one of {WEEKDAYS}")
        return value

    @field_validator("neighbourhood")
    @classmethod
    def neighbourhood_must_be_valid(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in NEIGHBOURHOODS:
            raise ValueError("Unknown neighbourhood. Use GET /options for valid values.")
        return normalized


class SegmentRequest(BaseModel):
    age: float = Field(default=40, ge=0, le=120)
    total_appointments: int = Field(default=2, ge=1, le=200)
    avg_lead_time_days: float = Field(default=7, ge=0, le=365)
    chronic_conditions: float = Field(default=0, ge=0, le=4)
    sms_rate: float = Field(default=0.5, ge=0, le=1)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Smart Healthcare Analytics API",
    version="1.0.0",
    description=(
        "Prediction service for hospital demand, appointment no-shows and patient segments. "
        "Models are trained in the notebooks and loaded from the models/ directory."
    ),
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "Smart Healthcare Analytics API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": [
            "/predict/demand",
            "/forecast/demand",
            "/predict/no-show",
            "/predict/segment",
            "/segments/summary",
            "/metadata",
            "/options",
        ],
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "models_loaded": {
            "demand": True,
            "no_show_logistic": True,
            "no_show_tree": True,
            "patient_kmeans": True,
        },
    }


@app.get("/options")
def options() -> dict[str, Any]:
    segments = [
        {
            "cluster": int(cluster_id),
            "label": profile["label"],
            "patients": profile["patients"],
            "share": profile["share"],
        }
        for cluster_id, profile in sorted(
            SEGMENTS_META["cluster_profiles"].items(),
            key=lambda item: item[1]["patients"],
            reverse=True,
        )
    ]
    return {
        "departments": DEPARTMENT_OPTIONS,
        "weekdays": WEEKDAYS,
        "neighbourhoods": NEIGHBOURHOODS,
        "genders": NO_SHOW_META["options"]["genders"],
        "age_groups": AGE_GROUPS,
        "segments": segments,
    }


@app.get("/metadata")
def metadata() -> dict[str, Any]:
    return {
        "demand": DEMAND_META,
        "no_show": NO_SHOW_META,
        "segments": SEGMENTS_META,
    }


@app.post("/predict/demand")
def predict_demand(request: DemandRequest) -> dict[str, Any]:
    try:
        return build_demand_response(request.forecast_date, request.department)
    except HTTPException:
        raise
    except Exception as error:  # pragma: no cover - defensive API boundary
        raise HTTPException(status_code=500, detail=f"Demand prediction failed: {error}")


@app.get("/forecast/demand")
def forecast_demand(
    start_date: Date | None = Query(default=None, description="First forecast date"),
    days: int = Query(default=14, ge=1, le=60),
    department: str = Query(default=ALL_DEPARTMENTS),
) -> dict[str, Any]:
    department = validate_department(department)
    start = start_date or Date.today()
    dates = [start + timedelta(days=offset) for offset in range(days)]
    try:
        forecast = [build_demand_response(day, department) for day in dates]
    except HTTPException:
        raise
    except Exception as error:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Demand forecast failed: {error}")

    peak = max(forecast, key=lambda row: row["predicted_patients"])
    total_patients = sum(row["predicted_patients"] for row in forecast)
    return {
        "department": department,
        "start_date": start.isoformat(),
        "days": days,
        "forecast": forecast,
        "summary": {
            "total_predicted_patients": round(total_patients, 1),
            "average_daily_patients": round(total_patients / len(forecast), 2),
            "peak_date": peak["forecast_date"],
            "peak_patients": peak["predicted_patients"],
        },
        "assumptions": {
            "resources": RESOURCE_ASSUMPTIONS,
            "admission_rate": round(DEMAND_META["admission_rate"], 3),
            "prediction_interval": "95% interval using training residuals",
        },
    }


@app.post("/predict/no-show")
def predict_no_show(request: NoShowRequest) -> dict[str, Any]:
    has_handicap = int(request.handicap > 0)
    chronic_conditions = (
        request.hipertension
        + request.diabetes
        + request.alcoholism
        + has_handicap
    )
    row = pd.DataFrame(
        [
            {
                "Age": request.age,
                "lead_time_days": request.lead_time_days,
                "Scholarship": request.scholarship,
                "Hipertension": request.hipertension,
                "Diabetes": request.diabetes,
                "Alcoholism": request.alcoholism,
                "SMS_received": request.sms_received,
                "has_handicap": has_handicap,
                "chronic_conditions": chronic_conditions,
                "is_same_day": int(request.lead_time_days == 0),
                "Gender": request.gender,
                "weekday": request.weekday,
                "Neighbourhood": request.neighbourhood,
                "age_group": age_group(request.age),
            }
        ]
    )

    try:
        logistic_probability = float(logistic_model.predict_proba(row)[0, 1])
        tree_probability = float(tree_model.predict_proba(row)[0, 1])
    except Exception as error:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"No-show prediction failed: {error}")

    logistic_threshold = float(NO_SHOW_META["thresholds"]["logistic"])
    tree_threshold = float(NO_SHOW_META["thresholds"]["tree"])
    logistic_prediction = (
        "Likely no-show"
        if logistic_probability >= logistic_threshold
        else "Likely attend"
    )
    tree_prediction = (
        "Likely no-show" if tree_probability >= tree_threshold else "Likely attend"
    )

    if logistic_probability >= float(RISK_BANDS["high_min"]):
        risk_level = "High"
        recommended_action = (
            "Call the patient 24-48 hours before the appointment, confirm transport, "
            "and offer rescheduling."
        )
    elif logistic_probability >= float(RISK_BANDS["low_max"]):
        risk_level = "Medium"
        recommended_action = (
            "Send an SMS reminder and make a confirmation call 48 hours before the visit."
        )
    else:
        risk_level = "Low"
        recommended_action = "Standard automated reminder is sufficient."

    models_agree = logistic_prediction == tree_prediction
    if not models_agree:
        recommended_action += " The two models disagree; prioritise a manual confirmation."

    return {
        "no_show_probability": round(logistic_probability, 4),
        "prediction": logistic_prediction,
        "risk_level": risk_level,
        "recommended_action": recommended_action,
        "threshold": logistic_threshold,
        "decision_tree_probability": round(tree_probability, 4),
        "decision_tree_prediction": tree_prediction,
        "models_agree": models_agree,
        "risk_bands": RISK_BANDS,
        "input_summary": {
            "age": request.age,
            "gender": request.gender,
            "lead_time_days": request.lead_time_days,
            "weekday": request.weekday,
            "neighbourhood": request.neighbourhood,
            "sms_received": request.sms_received,
            "chronic_conditions": chronic_conditions,
        },
    }


@app.post("/predict/segment")
def predict_segment(request: SegmentRequest) -> dict[str, Any]:
    row = pd.DataFrame(
        [
            {
                "age": request.age,
                "appointments": request.total_appointments,
                "avg_lead_time": request.avg_lead_time_days,
                "chronic_conditions": request.chronic_conditions,
                "sms_rate": request.sms_rate,
            }
        ]
    )
    try:
        cluster = int(segmentation_model.predict(row)[0])
        scaled = segmentation_model.named_steps["scaler"].transform(row)
        distances = segmentation_model.named_steps["kmeans"].transform(scaled)[0]
    except Exception as error:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {error}")

    profile = SEGMENTS_META["cluster_profiles"][str(cluster)]
    label = profile["label"]
    return {
        "cluster": cluster,
        "segment": label,
        "description": SEGMENTS_META["cluster_descriptions"][label],
        "profile": profile,
        "distance_to_centroid": round(float(distances[cluster]), 3),
        "segment_no_show_rate": profile["no_show_rate"],
    }


@app.get("/segments/summary")
def segments_summary() -> dict[str, Any]:
    segments = []
    for cluster_id, profile in sorted(
        SEGMENTS_META["cluster_profiles"].items(),
        key=lambda item: item[1]["patients"],
        reverse=True,
    ):
        segments.append(
            {
                "cluster": int(cluster_id),
                **profile,
                "description": SEGMENTS_META["cluster_descriptions"][profile["label"]],
            }
        )
    return {
        "model": SEGMENTS_META["model"],
        "k": SEGMENTS_META["k"],
        "n_patients": SEGMENTS_META["n_patients"],
        "silhouette": SEGMENTS_META["silhouette"],
        "features": SEGMENTS_META["features"],
        "overall_no_show_rate": SEGMENTS_META["overall_no_show_rate"],
        "segments": segments,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )
