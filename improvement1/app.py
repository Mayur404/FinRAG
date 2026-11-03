"""Improvement 1 CLI and local Web UI."""
from __future__ import annotations
import argparse
import json
from http.server import BaseHTTPRequestHandler,HTTPServer
from urllib.parse import parse_qs,urlparse
from . import rag

def main():
    import sys
    if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8",errors="replace")
    parser=argparse.ArgumentParser(prog="finpaper")
    commands=parser.add_subparsers(dest="command",required=True)
    ingest=commands.add_parser("ingest"); ingest.add_argument("--doc-name",action="append"); ingest.add_argument("--all",action="store_true")
    ask=commands.add_parser("ask"); ask.add_argument("--doc-name",required=True); ask.add_argument("--question",required=True); ask.add_argument("--no-llm",action="store_true")
    serve=commands.add_parser("serve"); serve.add_argument("--port",type=int,default=8765)
    args=parser.parse_args()
    if args.command=="ingest":
        names=args.doc_name or rag.docs()
        created=0
        for name in names:
            print(f"Ingesting {name} [Improvement 1]",flush=True)
            created+=bool(rag.ingest(name))
        print(f"Completed {len(names)} filings ({created} newly ingested; cached indexes reused)")
    elif args.command=="ask":
        hits,meta=rag.retrieve(args.doc_name,args.question)
        sources=rag.pack_context(hits,meta["chunks"])
        answer="Retrieval complete; LLM generation was skipped." if args.no_llm else rag.generate(args.question,sources)
        print(json.dumps({"answer":answer,"sources":[{"rank":s["rank"],"page":s["page"],"kind":s["kind"],"text":s["text"]} for s in sources]},ensure_ascii=False,indent=2))
    else:
        run_server(args.port)

def run_server(port):
    print("Warming BGE and Ollama models before accepting questions...",flush=True)
    try:
        rag.warm_models()
        print("Models are warm; serving questions.",flush=True)
    except Exception as exc:
        print(f"Model warm-up unavailable ({exc}); first question will load models.",flush=True)
    class Handler(BaseHTTPRequestHandler):
        def _json(self,data,status=200):
            body=json.dumps(data,ensure_ascii=False).encode()
            self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            if self.path=="/":
                html='''<!doctype html><meta charset="utf-8"><title>FinanceBench · Improvement 1</title>
<style>body{font:15px system-ui;max-width:1000px;margin:2rem auto;color:#172033}textarea{width:100%;height:7rem;padding:.7rem}select,button{padding:.55rem;margin:.4rem 0}pre{white-space:pre-wrap;background:#f3f4f6;padding:1rem;border-radius:8px}.row{display:flex;gap:1rem;align-items:center}details{border:1px solid #ddd;padding:.5rem;margin:.5rem 0}</style>
<h1>FinanceBench RAG</h1><p>Improvement 1 · Docling + hierarchical parent-child retrieval</p>
<p id="elapsed" aria-live="polite" style="color:#64748b;font-size:.9rem"></p>
<script>
(() => {
  const label = document.getElementById('elapsed');
  let started = 0;
  document.addEventListener('submit', () => { started = performance.now(); label.textContent = 'Answering…'; }, true);
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const t0 = performance.now();
    const response = await originalFetch(...args);
    if (started) {
      const seconds = (performance.now() - started) / 1000;
      label.textContent = `Elapsed: ${seconds.toFixed(2)} seconds`;
      started = 0;
    } else if (String(args[0]).includes('ask')) {
      label.textContent = `Elapsed: ${((performance.now() - t0) / 1000).toFixed(2)} seconds`;
    }
    return response;
  };
})();
</script>
<div class="row"><label>Report <select id="doc">'''+''.join(f'<option>{name}</option>' for name in rag.docs())+'''</select></label>
<label>Benchmark question <select id="sample"><option value="">Choose a question</option></select></label></div>
<textarea id="question" placeholder="Ask a question about the selected filing"></textarea><br><button onclick="ask()">Ask</button>
<h2>Answer</h2><pre id="answer"></pre><h2>Retrieved source context</h2><div id="sources"></div>
<script>async function loadQuestions(){let r=await fetch('/questions?doc='+encodeURIComponent(doc.value));let qs=await r.json();sample.innerHTML='<option value="">Choose a question</option>'+qs.map(x=>`<option>${x.question.replaceAll('&','&amp;').replaceAll('<','&lt;')}</option>`).join('')}doc.onchange=loadQuestions;sample.onchange=()=>question.value=sample.value;loadQuestions();async function ask(){answer.textContent='Retrieving…';let r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({doc:doc.value,question:question.value})});let d=await r.json();answer.textContent=d.answer||d.error||'No response returned';sources.innerHTML=(d.sources||[]).map(s=>`<details><summary>#${s.rank} · Page ${s.page} · ${s.kind}</summary><pre>${s.text.replaceAll('&','&amp;').replaceAll('<','&lt;')}</pre></details>`).join('')}</script>'''
                data=html.encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
            elif self.path.startswith("/questions"):
                doc=parse_qs(urlparse(self.path).query).get("doc",[""])[0]
                self._json([q for q in rag.questions() if q.get("doc_name")==doc])
            else: self.send_error(404)
        def do_POST(self):
            if self.path!="/ask": self.send_error(404); return
            try:
                import time
                started=time.perf_counter()
                data=json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
                answer,sources=rag.answer(data["doc"],data["question"])
                self._json({"answer":answer,"elapsed_seconds":round(time.perf_counter()-started,2),"sources":[{k:s[k] for k in ("rank","page","kind","text")} for s in sources]})
            except Exception as exc: self._json({"error":str(exc)},500)
        def log_message(self,*_args): pass
    print(f"Improvement 1 UI: http://127.0.0.1:{port}",flush=True)
    HTTPServer(("127.0.0.1",port),Handler).serve_forever()

if __name__=="__main__": main()
