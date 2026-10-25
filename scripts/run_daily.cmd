@echo off
rem Daily ingestion wrapper for Windows Task Scheduler.
rem Runs from the project root with the venv Python and appends output to logs\ingest.log.
cd /d "%~dp0.."
if not exist logs mkdir logs
".venv\Scripts\python.exe" -m ingest.run >> "logs\ingest.log" 2>&1
