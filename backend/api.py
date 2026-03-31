"""
Flask REST API — Backend for the React dashboard
Exposes: POST /api/analyze
Run:     python3 api.py
"""

import dataclasses
import json
import queue
import threading
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=False)


def to_serializable(obj):
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    body = request.get_json()
    if not body:
        return jsonify({"error": "Request body required"}), 400

    raw_keyword = (body.get("keyword") or "").strip()
    url         = (body.get("url") or "").strip()

    if not raw_keyword or not url:
        return jsonify({"error": "keyword and url are required"}), 400

    geo = "us"

    # Comma = separate keywords → run once per keyword, merge gaps
    # Space  = one phrase      → run as-is
    keywords = [k.strip() for k in raw_keyword.split(",") if k.strip()]
    keyword  = keywords[0]   # primary keyword drives SERP/scraping; extras merged in gaps

    def generate():
        q             = queue.Queue()
        result_holder = [None]
        error_holder  = [None]

        def step_callback(n, desc):
            q.put(("progress", n, desc))

        def worker():
            try:
                from orchestrator import run_analysis
                from agents import serp_agent, autocomplete_agent, gap_agent

                # Run primary keyword (full pipeline)
                result = run_analysis(keyword, url, geo, on_step=step_callback)

                # For each extra comma-separated keyword, run SERP + gap only and merge
                for extra_kw in keywords[1:]:
                    step_callback(5, f'Adding gaps for extra keyword "{extra_kw}"...')
                    try:
                        extra_serp = serp_agent.run(extra_kw, geo)
                        extra_ac   = autocomplete_agent.run(extra_kw)
                        extra_gaps = gap_agent.run(
                            extra_serp, extra_ac,
                            result.competitor_pages, result.your_page, extra_kw
                        )
                        # Tag each extra gap with its source keyword and merge
                        existing_kws = {g.keyword for g in result.gaps}
                        for g in extra_gaps:
                            if g.keyword not in existing_kws:
                                g.sources = [f'[{extra_kw}] ' + s for s in g.sources]
                                result.gaps.append(g)
                                existing_kws.add(g.keyword)
                    except Exception as extra_err:
                        raise RuntimeError(f'Failed to process extra keyword "{extra_kw}": {extra_err}') from extra_err

                result_holder[0] = result
            except Exception as e:
                error_holder[0] = str(e)
            finally:
                q.put(("done", None, None))

        threading.Thread(target=worker, daemon=True).start()

        while True:
            msg_type, step, desc = q.get()
            if msg_type == "progress":
                yield f"data: {json.dumps({'type': 'progress', 'step': step, 'desc': desc})}\n\n"
            elif msg_type == "done":
                break

        if error_holder[0]:
            yield f"data: {json.dumps({'type': 'error', 'message': error_holder[0]})}\n\n"
        else:
            result_dict = dataclasses.asdict(result_holder[0])
            yield f"data: {json.dumps({'type': 'result', 'data': result_dict})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  SEO Keyword Gap Analyzer — API Server           ║")
    print("║  Running on http://localhost:8000                ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    app.run(host="0.0.0.0", port=8000, debug=False)
