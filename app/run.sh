#!/bin/bash
uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload &
rq worker --with-scheduler --url redis://valkey:6379 app.queue.worker
