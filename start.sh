#!/bin/bash
# Start script that handles PORT environment variable properly

# Use PORT if set by Railway, otherwise default to 8000
PORT=${PORT:-8000}

# Start uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
