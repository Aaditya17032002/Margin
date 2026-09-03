"""One-shot Azure deployment smoke test. Prints status only — no secrets."""

from __future__ import annotations

import os

import httpx


def snippet(body: str, n: int = 280) -> str:
    return body.replace("\n", " ")[:n]


def main() -> None:
    ep = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    key = os.environ["AZURE_OPENAI_API_KEY"]
    ver = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    emb_key = os.environ.get("AZURE_EMBEDDING_API_KEY") or key
    emb_dep = os.environ.get("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
    extract = os.environ.get("AZURE_OPENAI_DEPLOYMENT_EXTRACT", "gpt-5.2")
    router = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    verifier = os.environ.get("AZURE_OPENAI_DEPLOYMENT_VERIFIER", "gpt-5.2")

    print("endpoint", ep)
    print("api_version", ver)
    print("deployments", {"router": router, "extract": extract, "verifier": verifier, "embed": emb_dep})
    print()

    url = f"{ep}/openai/models?api-version={ver}"
    r = httpx.get(url, headers={"api-key": key}, timeout=30)
    print(f"[{r.status_code}] list models (openai key)")
    if r.status_code == 200:
        data = r.json()
        ids = [m.get("id") for m in data.get("data", [])][:50]
        print("  models:", ids)
    else:
        print(" ", snippet(r.text, 200))

    r2 = httpx.get(url, headers={"api-key": emb_key}, timeout=30)
    print(f"[{r2.status_code}] list models (embedding key)")
    if r2.status_code == 200:
        data = r2.json()
        ids = [m.get("id") for m in data.get("data", [])][:50]
        print("  models:", ids)

    def chat(name: str, deployment: str, payload: dict) -> None:
        chat_url = f"{ep}/openai/deployments/{deployment}/chat/completions?api-version={ver}"
        resp = httpx.post(
            chat_url,
            headers={"api-key": key, "Content-Type": "application/json"},
            json=payload,
            timeout=90,
        )
        if resp.status_code == 200:
            msg = resp.json()["choices"][0].get("message", {})
            print(f"[{resp.status_code}] {name}: {msg.get('content')!r} finish={resp.json()['choices'][0].get('finish_reason')}")
        else:
            print(f"[{resp.status_code}] {name}: {snippet(resp.text)}")

    print("\n--- chat ---")
    chat(
        f"{router} max_tokens",
        router,
        {
            "messages": [{"role": "user", "content": "Reply with the single word OK"}],
            "max_tokens": 16,
            "temperature": 0,
        },
    )
    chat(
        f"{extract} max_tokens",
        extract,
        {
            "messages": [{"role": "user", "content": "Reply with the single word OK"}],
            "max_tokens": 16,
            "temperature": 0,
        },
    )
    chat(
        f"{extract} max_completion_tokens",
        extract,
        {
            "messages": [{"role": "user", "content": "Reply with the single word OK"}],
            "max_completion_tokens": 32,
        },
    )
    if verifier != extract:
        chat(
            f"{verifier} max_completion_tokens",
            verifier,
            {
                "messages": [{"role": "user", "content": "Reply with the single word OK"}],
                "max_completion_tokens": 32,
            },
        )

    print("\n--- embeddings ---")

    def embed(name: str, api_key: str, extra: dict) -> None:
        eurl = f"{ep}/openai/deployments/{emb_dep}/embeddings?api-version={ver}"
        resp = httpx.post(
            eurl,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json={"input": ["margin smoke test"], **extra},
            timeout=60,
        )
        if resp.status_code == 200:
            vec = resp.json()["data"][0]["embedding"]
            print(f"[{resp.status_code}] {name}: dim={len(vec)}")
        else:
            print(f"[{resp.status_code}] {name}: {snippet(resp.text)}")

    embed("openai-key default", key, {})
    embed("openai-key dim1536", key, {"dimensions": 1536})
    embed("embedding-key default", emb_key, {})
    embed("embedding-key dim1536", emb_key, {"dimensions": 1536})

    print("\n--- deep research ---")
    dr_ep = (os.environ.get("AZURE_DEEP_RESEARCH_ENDPOINT") or "").rstrip("/")
    dr_key = os.environ.get("AZURE_DEEP_RESEARCH_API_KEY") or ""
    print("endpoint_set", bool(dr_ep), "key_set", bool(dr_key))


if __name__ == "__main__":
    main()
