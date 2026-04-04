#!/bin/bash
# Quick test runner for backend

cd /Users/zw/workspace/ClinicOS/backend
python3 -m pytest tests/test_prototype_e2e.py -x -q --tb=short 2>&1 | tail -60
