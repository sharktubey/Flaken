@echo off
start /B python -m uvicorn registry.main:app --host 127.0.0.1 --port 8000
