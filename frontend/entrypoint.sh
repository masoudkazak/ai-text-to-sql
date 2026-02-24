#!/usr/bin/env sh
set -eu

exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0
