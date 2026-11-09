"""Download the two Hugging Face files and check pinned checksums."""
import hashlib, os, urllib.request, yaml
BASE = "https://huggingface.co/datasets/defeatbeta/yahoo-finance-data/resolve/main/data/US/"
if __name__ == "__main__":
    cfg = yaml.safe_load(open("configs/default.yaml")); os.makedirs("data/raw", exist_ok=True)
    for f in ["stock_prices", "daily_treasury_yield"]:
        p = f"data/raw/{f}.parquet"
        if not os.path.exists(p):
            urllib.request.urlretrieve(BASE + f + ".parquet", p)
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        print(f, h, "OK" if h == cfg["sha256"][f] else "MISMATCH (mirror updated; results may differ)")
