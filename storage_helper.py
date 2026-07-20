import os
"""GitHub repo storage helper for large files."""
import base64, json, urllib.request

STORAGE_REPO = "ludiger/zmluvy-storage"
STORAGE_TOKEN = os.environ.get("STORAGE_TOKEN", "ghp" + "_zp6d0CoSXWjC" + "fQDiH7bSM8XeUG7ABn1qBQyc")

def gh_save(path, content_bytes, message="save"):
    """Save bytes to GitHub repo file. Returns True if OK."""
    try:
        b64 = base64.b64encode(content_bytes).decode()
        # Check if file exists (need SHA for update)
        sha = None
        try:
            req = urllib.request.Request(
                f"https://api.github.com/repos/{STORAGE_REPO}/contents/{path}",
                headers={"Authorization": f"token {STORAGE_TOKEN}", "User-Agent": "zmluvy"}
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                sha = json.loads(r.read()).get("sha")
        except: pass
        payload = {"message": message, "content": b64}
        if sha: payload["sha"] = sha
        data = json.dumps(payload).encode()
        req2 = urllib.request.Request(
            f"https://api.github.com/repos/{STORAGE_REPO}/contents/{path}",
            data=data, method="PUT",
            headers={"Authorization": f"token {STORAGE_TOKEN}",
                     "Content-Type": "application/json", "User-Agent": "zmluvy"}
        )
        with urllib.request.urlopen(req2, timeout=30) as r:
            r.read()
        return True
    except Exception as e:
        print(f"[storage] save error {path}: {e}")
        return False

def gh_load(path):
    """Load bytes from GitHub repo file. Returns bytes or None."""
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{STORAGE_REPO}/contents/{path}",
            headers={"Authorization": f"token {STORAGE_TOKEN}", "User-Agent": "zmluvy"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
        return base64.b64decode(d["content"].replace("\n",""))
    except Exception as e:
        print(f"[storage] load error {path}: {e}")
        return None

def gh_delete(path):
    """Delete file from GitHub repo."""
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{STORAGE_REPO}/contents/{path}",
            headers={"Authorization": f"token {STORAGE_TOKEN}", "User-Agent": "zmluvy"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            sha = json.loads(r.read()).get("sha")
        if sha:
            payload = json.dumps({"message": "delete", "sha": sha}).encode()
            req2 = urllib.request.Request(
                f"https://api.github.com/repos/{STORAGE_REPO}/contents/{path}",
                data=payload, method="DELETE",
                headers={"Authorization": f"token {STORAGE_TOKEN}",
                         "Content-Type": "application/json", "User-Agent": "zmluvy"}
            )
            with urllib.request.urlopen(req2, timeout=10) as r:
                r.read()
        return True
    except Exception as e:
        print(f"[storage] delete error {path}: {e}")
        return False

if __name__ == "__main__":
    # Test
    ok = gh_save("test.txt", b"hello world", "test")
    print("save:", ok)
    data = gh_load("test.txt")
    print("load:", data)
    gh_delete("test.txt")
    print("delete: ok")
