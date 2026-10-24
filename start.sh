#!/bin/sh
# Start the FastAPI backend and the Streamlit UI in one container.
# The UI talks to the API over localhost; only the UI port is public.
set -e

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for the API (sample documents are embedded on first start)
for i in $(seq 1 60); do
    if curl -sf http://localhost:8000/health/live > /dev/null; then
        break
    fi
    sleep 1
done

streamlit run streamlit_app/app.py \
    --server.port "${PORT:-7860}" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --browser.gatherUsageStats false &
UI_PID=$!

# Exit (and let the platform restart us) if either process dies
while kill -0 "$API_PID" 2>/dev/null && kill -0 "$UI_PID" 2>/dev/null; do
    sleep 5
done
exit 1
