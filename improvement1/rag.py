"""Improvement 1: Docling extraction and hierarchical parent-child retrieval.

All parser, chunker, embedder, index, retrieval, context-packing, and generation
code for this method lives in this folder.
"""
from __future__ import annotations

import gc
import json
import math
import re
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PDF_DIR=ROOT/"financebench"/"pdfs"
DATA_DIR=ROOT/"data"
ELEMENT_DIR=ROOT/"improvement1"/"elements"
INDEX_DIR=ROOT/"improvement1"/"indexes"
MODEL_DIR=ROOT/"improvement1"/"models"/"huggingface"
PARSER_ID="docling-tableformer-accurate-cuda-textlayer"

def docs():
    return [s.strip() for s in (DATA_DIR/"subset.txt").read_text(encoding="utf-8-sig").splitlines() if s.strip()]

def questions():
    path=DATA_DIR/"questions.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

def parse_docling(pdf: Path):
    import os
    MODEL_DIR.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault("HF_HOME",str(MODEL_DIR))
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.accelerator_options import AcceleratorDevice,AcceleratorOptions
    from docling.datamodel.pipeline_options import PdfPipelineOptions,TableFormerMode
    from docling.document_converter import DocumentConverter,PdfFormatOption
    options=PdfPipelineOptions(do_ocr=False,do_table_structure=True)
    options.table_structure_options.mode=TableFormerMode.ACCURATE
    options.accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CUDA)
    converter=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=options)})
    import torch
    with torch.inference_mode(),torch.autocast(device_type="cuda",dtype=torch.float16):
        document=converter.convert(str(pdf)).document
    by_page={}
    for item,_level in document.iterate_items():
        label=str(getattr(item,"label","")).split(".")[-1].lower()
        provenance=getattr(item,"prov",[]) or []
        page=int(getattr(provenance[0],"page_no",1) or 1) if provenance else 1
        if "table" in label:
            try: text=item.export_to_markdown(doc=document)
            except Exception: text=str(getattr(item,"text","") or "")
            kind="Table"
        else:
            text=str(getattr(item,"text","") or "").strip()
            kind="Title" if label in {"section_header","title"} else "NarrativeText"
        if text.strip(): by_page.setdefault(page,[]).append({"type":kind,"text":text.strip(),"page_number":page})
    from pypdf import PdfReader
    page_count=len(PdfReader(str(pdf)).pages)
    return [{"page_number":p,"text":"\n".join(e["text"] for e in by_page.get(p,[])),"elements":by_page.get(p,[])} for p in range(1,page_count+1)]

def complete_page_slots(doc_name: str,data):
    from pypdf import PdfReader
    count=len(PdfReader(str(PDF_DIR/f"{doc_name}.pdf")).pages)
    pages={int(page["page_number"]):page for page in data.get("pages",[])}
    complete=[pages.get(p,{"page_number":p,"text":"","elements":[]}) for p in range(1,count+1)]
    changed=len(complete)!=len(data.get("pages",[])) or any(p not in pages for p in range(1,count+1))
    data["pages"]=complete; data["page_count"]=count
    return data,changed

def load_or_parse(doc_name: str):
    ELEMENT_DIR.mkdir(parents=True,exist_ok=True)
    path=ELEMENT_DIR/f"{doc_name}.json"
    if path.exists():
        data,changed=complete_page_slots(doc_name,json.loads(path.read_text(encoding="utf-8")))
        if data.get("parser")==PARSER_ID:
            if changed: path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
            return data
    pdf=PDF_DIR/f"{doc_name}.pdf"
    if not pdf.exists(): raise FileNotFoundError(pdf)
    pages=parse_docling(pdf)
    import torch
    gc.collect()
    if torch.cuda.is_available(): torch.cuda.empty_cache(); torch.cuda.ipc_collect()
    data={"doc_name":doc_name,"parser":PARSER_ID,"pages":pages}
    data,_=complete_page_slots(doc_name,data)
    path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
    return data

def make_tree(doc_name: str,pages):
    company=doc_name.split("_")[0]
    form="10-K" if "10K" in doc_name else "10-Q" if "10Q" in doc_name else "8-K" if "8K" in doc_name else "Earnings release"
    year_match=re.search(r"20\d\d",doc_name); year=year_match.group(0) if year_match else "unknown"
    chunks=[]; parents=[]; section="Document"; section_number=0; seq=0; current=None; previous_narrative=""
    def new_section(title,page):
        nonlocal current,section_number
        section_number+=1
        current={"id":f"{doc_name}:s{section_number}","doc_name":doc_name,"kind":"Section","section":title,"page":page,"text":title}
        parents.append(current)
    for page in pages:
        for element in page["elements"]:
            text=element["text"].strip()
            if element["type"]=="Title":
                section=text[:180]; new_section(section,element["page_number"]); continue
            if current is None: new_section("Document",element["page_number"])
            if element["type"]=="Table":
                parent_id=f"{doc_name}:t{seq}"
                table_context=(previous_narrative[-600:]+"\n"+text).strip()
                parents.append({"id":parent_id,"doc_name":doc_name,"kind":"Table","section":section,"page":element["page_number"],"text":table_context})
                breadcrumb=f"[Company: {company} | Form: {form} | Year: {year} | Section: {section}]"
                chunks.append({"id":f"{doc_name}:h{seq}","parent_id":parent_id,"doc_name":doc_name,"kind":"Table","page":element["page_number"],"text":text,"search_text":breadcrumb+" "+text,"prev":None,"next":None})
                current["text"]+="\n"+text; previous_narrative=""; seq+=1; continue
            current["text"]+="\n"+text
            parent_id=current["id"]
            words=text.split()
            for start in range(0,len(words),180):
                leaf=" ".join(words[start:start+180])
                if not leaf: continue
                breadcrumb=f"[Company: {company} | Form: {form} | Year: {year} | Section: {section}]"
                previous=chunks[-1] if chunks and chunks[-1].get("parent_id")==parent_id else None
                node={"id":f"{doc_name}:h{seq}","parent_id":parent_id,"doc_name":doc_name,"kind":"NarrativeText","page":element["page_number"],"text":leaf,"search_text":breadcrumb+" "+leaf,"prev":previous["id"] if previous else None,"next":None}
                if previous: previous["next"]=node["id"]
                chunks.append(node); seq+=1
            previous_narrative=text
    return chunks,parents

_EMBEDDING_MODEL = None

def embed(texts):
    import os
    os.environ.setdefault("HF_HOME",str(MODEL_DIR))
    from sentence_transformers import SentenceTransformer
    import torch
    if not torch.cuda.is_available(): raise RuntimeError("Improvement 1 requires CUDA; install the project CUDA PyTorch build.")
    local= (MODEL_DIR/"hub"/"models--BAAI--bge-base-en-v1.5").exists()
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL=SentenceTransformer("BAAI/bge-base-en-v1.5",device="cuda:0",local_files_only=local)
        _EMBEDDING_MODEL.half()
    model=_EMBEDDING_MODEL
    vectors=model.encode(texts,batch_size=64,convert_to_numpy=True,show_progress_bar=len(texts)>1,normalize_embeddings=True)
    return vectors

def warm_models():
    """Load retrieval and generation weights before the UI accepts questions."""
    embed(["warmup query"])
    payload={"model":"qwen3.5:4b","prompt":"Reply OK.","stream":False,"think":False,
             "keep_alive":"30m","options":{"temperature":0,"num_predict":1,
             "num_ctx":16384,"num_gpu":99}}
    request=urllib.request.Request("http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=180) as response:
        response.read()

def ingest(doc_name: str):
    import numpy as np
    INDEX_DIR.mkdir(parents=True,exist_ok=True)
    stem=INDEX_DIR/doc_name
    if stem.with_suffix(".npy").exists() and stem.with_suffix(".json").exists():
        cached=json.loads(stem.with_suffix(".json").read_text(encoding="utf-8"))
        if cached.get("parser")==PARSER_ID:
            print(f"Index already exists for {doc_name}; keeping the cached Improvement 1 result.",flush=True)
            return False
    source=load_or_parse(doc_name)
    chunks,parents=make_tree(doc_name,source["pages"])
    if not chunks: raise RuntimeError(f"Docling produced no searchable elements for {doc_name}")
    vectors=embed([c["search_text"] for c in chunks])
    INDEX_DIR.mkdir(parents=True,exist_ok=True)
    np.save(stem.with_suffix(".npy"),np.asarray(vectors,dtype="float32"))
    metadata={"doc_name":doc_name,"parser":PARSER_ID,"model":"BAAI/bge-base-en-v1.5","normalized":True,"chunks":chunks,"parents":parents}
    stem.with_suffix(".json").write_text(json.dumps(metadata,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    return True

def retrieve(doc_name: str,question: str,top_k=10):
    import numpy as np
    path=INDEX_DIR/f"{doc_name}.json"
    metadata=json.loads(path.read_text(encoding="utf-8"))
    query="Represent this sentence for searching relevant passages: "+question
    # Reuse the same resident BGE model used during ingestion. Constructing a
    # SentenceTransformer here reloads several hundred MB of weights per query.
    vector=embed([query])[0]
    matrix=np.load(INDEX_DIR/f"{doc_name}.npy",mmap_mode="r")
    scores=(matrix@vector).tolist()
    candidates=sorted(range(len(scores)),key=lambda i:scores[i],reverse=True)[:50]
    leaves=[{**metadata["chunks"][i],"score":float(scores[i])} for i in candidates]
    grouped={}
    for leaf in leaves:
        group=grouped.setdefault(leaf["parent_id"],{"score":leaf["score"],"hits":[]})
        group["score"]=max(group["score"],leaf["score"]); group["hits"].append(leaf)
    parents={p["id"]:p for p in metadata["parents"]}
    ranked=sorted(grouped.items(),key=lambda kv:kv[1]["score"]+0.1*(len(kv[1]["hits"])-1),reverse=True)[:top_k]
    hits=[]
    for rank,(parent_id,group) in enumerate(ranked,1):
        best=group["hits"][0]
        hits.append({**best,"rank":rank,"score":group["score"]+0.1*(len(group["hits"])-1),"parent":parents[parent_id],"matched_children":group["hits"]})
    return hits,metadata

def pack_context(hits,chunks,budget=3000):
    by_id={c["id"]:c for c in chunks}; used=0; packed=[]
    token_estimate=lambda text: math.ceil(len(text)/3.5)
    for hit in hits:
        text=hit["parent"].get("text",hit["text"])
        cost=token_estimate(text)
        if used+cost<=budget:
            packed.append({**hit,"text":text}); used+=cost; continue
        matched=hit["matched_children"][0]
        adjacent=[by_id[k] for k in (matched.get("prev"),matched["id"],matched.get("next")) if k in by_id]
        fallback="\n".join(x["text"] for x in adjacent)
        sentences=re.split(r"(?<=[.!?])\s+",fallback.strip()); selected=[]
        for sentence in sentences:
            if used+token_estimate(" ".join(selected+[sentence]))>budget: break
            selected.append(sentence)
        clipped=" ".join(selected)
        if clipped: packed.append({**hit,"text":clipped}); used+=token_estimate(clipped)
        if used>=budget: break
    return packed

def generate(question,sources,model="qwen3.5:4b"):
    source_text="\n".join(f"{i} - {s['text']}" for i,s in enumerate(sources,1))
    prompt=("please answer the question below using the sources provided after the question. "
            "If the sources do not contain enough information, use your general knowledge to give the best answer you can, and be clear when you are uncertain. The sources are listed after \"Sources:\".\n"
            f"Question: {question}\nSources:\n{source_text}")
    body=json.dumps({"model":model,"prompt":prompt,"stream":False,"think":False,"keep_alive":"30m","options":{"temperature":0,"seed":0,"num_ctx":16384,"num_gpu":99,"num_predict":-1}}).encode()
    request=urllib.request.Request("http://127.0.0.1:11434/api/generate",data=body,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=300) as response: answer=json.loads(response.read()).get("response","")
    return re.sub(r"<think>.*?</think>","",answer,flags=re.S).strip()

def answer(doc_name: str,question: str):
    hits,metadata=retrieve(doc_name,question)
    sources=pack_context(hits,metadata["chunks"],3000)
    return generate(question,sources),sources
