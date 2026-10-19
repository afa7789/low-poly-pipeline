#!/usr/bin/env python3
"""Send one prompt file to the ppq image endpoint and save the result as <stem>.jpg.

    python3 generate.py prompts/unit-n01X.txt
    python3 generate.py prompts/building-h09B.txt --out draft3 --dry-run
    python3 generate.py prompts/unit-n00U.txt --model nano-banana-2-1 --resolution 2K
    python3 generate.py draft2/prompts/00-template-rts.txt --image draft2/n01X.jpg \
        --out draft2 --name n01X-rts            # RTS 3/4 view drawn from the approved sheet

Key resolution order: $PPQ_API_KEY, then provider.ppq.options.apiKey in
~/.config/opencode/opencode.json. Never write the key into a file under this folder.

Endpoint: POST https://api.ppq.ai/v1/images/generations
Models verified on this gateway (2026-10-18, GET /v1/models?type=image):
  nano-banana-2-1  $0.046  2K, best panel comprehension -- the default here
  krea-2-turbo     $0.013  1K, silhouette sheets with a real shadow, no colour read
  flux-2-pro       $0.029  ignores panel wording, repeats one viewpoint
  flux-kontext-pro / flux-2-pro-i2i: broken on this gateway (502 / 400), do not use
  nano-banana-2-1-edit  $0.051  image-to-image (--image): same unit, new camera -- verified
                                2026-10-19 on the n01X RTS view
"""
import argparse
import base64
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://api.ppq.ai/v1/images/generations"


def api_key():
    key = os.environ.get("PPQ_API_KEY")
    if key:
        return key
    cfg = pathlib.Path.home() / ".config" / "opencode" / "opencode.json"
    if cfg.exists():
        return json.loads(cfg.read_text())["provider"]["ppq"]["options"]["apiKey"]
    sys.exit("no PPQ_API_KEY in the environment and no opencode.json to read it from")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt_file", type=pathlib.Path)
    ap.add_argument("--model", default="nano-banana-2-1")
    ap.add_argument("--resolution", default="2K")
    ap.add_argument("--aspect", default="1:1")
    ap.add_argument("--out", type=pathlib.Path, default=None, help="output directory (default: the prompt file's folder)")
    ap.add_argument("--name", default=None, help="output stem (default: the prompt file's stem minus its prefix)")
    ap.add_argument("--image", type=pathlib.Path, default=None,
                    help="reference image (the approved sheet); switches to the edit model")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.image and args.model == "nano-banana-2-1":
        args.model = "nano-banana-2-1-edit"

    prompt = args.prompt_file.read_text().strip()
    out = args.out or args.prompt_file.parent
    stem = args.name or args.prompt_file.stem.split("-", 1)[-1]
    dest = out / f"{stem}.jpg"

    payload = {"model": args.model, "prompt": prompt, "aspect_ratio": args.aspect,
               "resolution": args.resolution, "n": 1}
    if args.image:
        small = subprocess.run(["magick", str(args.image), "-resize", "1024x1024", "-quality", "88",
                                "jpg:-"], check=True, capture_output=True).stdout
        payload["image_url"] = "data:image/jpeg;base64," + base64.b64encode(small).decode()
    if args.dry_run:
        shown = {**payload, "prompt": f"<{len(prompt)} chars>"}
        if "image_url" in shown:
            shown["image_url"] = f"<{len(shown['image_url'])} chars>"
        print(json.dumps(shown, indent=1))
        print("would write:", dest)
        return

    req = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {api_key()}",
                                          "Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=400))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:400]}")
    out.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(r["data"][0]["url"], dest)
    print(f"{args.model} -> {dest}  {dest.stat().st_size} bytes  cost={r.get('cost')}")


if __name__ == "__main__":
    main()
