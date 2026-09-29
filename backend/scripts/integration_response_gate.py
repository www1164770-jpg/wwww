"""Explicit response barrier for the isolated local integration runner only.

Write control.json under artifacts/local-integration/gates; release a held
response by creating <id>.release. No product routes, auth bypass or fake body.
"""
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from flask import request
from flask_jwt_extended import get_jwt_identity


def install(app, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    claimed = set()
    sequence = 0

    def record(kind, **fields):
        nonlocal sequence
        with lock:
            sequence += 1
            row = dict(sequence=sequence, kind=kind, at=datetime.now(timezone.utc).isoformat(), **fields)
            with (directory/'events.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False)+'\n')
        return row

    @app.after_request
    def gate(response):
        if not request.path.startswith('/api/'):
            return response
        try:
            account = get_jwt_identity()
        except RuntimeError:
            account = None
        fields = dict(path=request.path, method=request.method, account=account,
                      career=request.args.get('career_code') or request.args.get('career'), status=response.status_code)
        control = directory/'control.json'
        rules = json.loads(control.read_text(encoding='utf-8')) if control.exists() else []
        chosen = None
        with lock:
            for rule in rules:
                ident = rule['id']
                if not ident.replace('-', '').replace('_', '').isalnum():
                    raise ValueError('invalid gate ID')
                if ident not in claimed and all(fields.get(k)==v for k,v in rule.items() if k != 'id'):
                    claimed.add(ident); chosen=ident; break
        if chosen:
            row=record('held', gate=chosen, **fields)
            (directory/(chosen+'.held.json')).write_text(json.dumps(row),encoding='utf-8')
            deadline=time.monotonic()+300
            while not (directory/(chosen+'.release')).exists() and time.monotonic()<deadline:
                time.sleep(.05)
            released=(directory/(chosen+'.release')).exists()
            record('released' if released else 'expired', gate=chosen, **fields)
            if not released:
                return {'error':'isolated_test_gate_expired'},504
        record('sent', gate=chosen, **fields)
        return response
