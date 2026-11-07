"""Neural molds (author 2026-11-04): TripoSplat depth and SAM2 part masks, INVISIBLE to the model - the mesh stays ours.

Runs ONLY under the neural venv (python 3.12 + torch), never imported by the pipeline (python3.14): depth_map.py and
parts_fit.py call it as a subprocess through `command()`.

    <venv>/bin/python -I -u tools/blender/neural_molds.py splat <front_crop.png> <outdir>
        TripoSplat once on the front panel crop -> <outdir>/splat.ply, and orthographic z-buffer depth renders of the
        splat: depth-front.npy (camera on the figure's front), depth-left0.npy / depth-left180.npy (the two profiles;
        the caller keeps the one whose silhouette matches its left panel). Each .npy is nearness (larger = nearer),
        NaN off the splat. Raw TripoSplat axes: front camera on +x, image right = +y, up = +z.
    <venv>/bin/python -I -u tools/blender/neural_molds.py sam2 <job.json> <outdir>
        job = {"views": {view: {"crop": png path, "boxes": {part: [x0, y0, x1, y1] crop pixels}}}}: one SAM2 box
        prompt per part -> <outdir>/<view>/<part>.png (crop resolution) and <outdir>/scores.json.
"""
import json
import os
import pathlib
import sys
import time

NEURAL = pathlib.Path(os.environ.get("CF_NEURAL_DIR", "/private/tmp/claude-501/-Users-afa-Developer-arthur-castle-fight/"
                                     "62d500c7-b3c8-4fca-a5be-28ee7a695133/scratchpad/neural"))
RES = 1024              # depth render size (square)
MIN_OPACITY = 0.2


def run(argv, env, tries=2):
    """The neural subprocess under one machine-wide lock (NEURAL/gpu.lock): two MPS jobs at once blew the command buffer (n01D,
    roster-v6); a failed run is retried once after the lock is held again."""
    import fcntl
    import subprocess
    NEURAL.mkdir(parents=True, exist_ok=True)
    with open(NEURAL / "gpu.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for i in range(tries):
            done = subprocess.run(argv, env=env)
            if done.returncode == 0:
                return
            print(f"neural: exit {done.returncode}, " + ("retrying" if i + 1 < tries else "giving up"), flush=True)
        raise subprocess.CalledProcessError(done.returncode, argv)


def command(*args):
    """argv for the pipeline's subprocess call, and its env (HF cache, MPS fallback, offline)."""
    env = {**os.environ, "PYTORCH_ENABLE_MPS_FALLBACK": "1", "HF_HOME": str(NEURAL / "sam2_hf"), "HF_HUB_OFFLINE": "1"}
    return [str(NEURAL / "venv/bin/python"), "-I", "-u", str(pathlib.Path(__file__).resolve()), *map(str, args)], env


def zbuffer(u, v, near, res=RES, splat=1):
    """Orthographic z-buffer: (nearness map, NaN where no point). u, v in 0..1 (v down); nearest point wins."""
    import numpy as np
    img = np.full((res, res), -np.inf, np.float32)
    px = np.clip((u * (res - 1)).astype(int), 0, res - 1)
    py = np.clip((v * (res - 1)).astype(int), 0, res - 1)
    for ox in range(-splat, splat + 1):
        for oy in range(-splat, splat + 1):
            np.maximum.at(img, (np.clip(py + oy, 0, res - 1), np.clip(px + ox, 0, res - 1)), near)
    return np.where(np.isfinite(img), img, np.nan)


def splat(crop, out):
    import numpy as np
    import torch
    sys.path.insert(0, str(NEURAL / "triposplat_src/repo"))
    from triposplat import TripoSplatPipeline
    c = NEURAL / "triposplat_ckpts"
    t0 = time.time()
    pipe = TripoSplatPipeline(ckpt_path=f"{c}/diffusion_models/triposplat_fp16.safetensors",
                              decoder_path=f"{c}/vae/triposplat_vae_decoder_fp16.safetensors",
                              dinov3_path=f"{c}/clip_vision/dino_v3_vit_h.safetensors",
                              flux2_vae_encoder_path=f"{c}/vae/flux2-vae.safetensors",
                              rmbg_path=f"{c}/background_removal/birefnet.safetensors",
                              device="mps" if torch.backends.mps.is_available() else "cpu")
    g, prepared = pipe.run(str(crop), num_gaussians=262144, steps=20, show_progress=False)
    out.mkdir(parents=True, exist_ok=True)
    prepared.save(out / "prepared.png")
    g.save_ply(str(out / "splat.ply"))
    xyz = g.get_xyz.float().cpu().numpy()
    keep = g.get_opacity.float().cpu().numpy()[:, 0] > MIN_OPACITY
    xyz = xyz[keep]
    del pipe, g
    s = float(max(np.ptp(xyz, 0))) * 1.05
    c0 = (xyz.max(0) + xyz.min(0)) / 2
    p = (xyz - c0) / s + 0.5                          # 0..1 cube
    v = 1 - p[:, 2]                                   # image down = -z
    views = {"front": (p[:, 1], p[:, 0]),             # camera +x: right = +y, nearer = larger x
             "left0": (p[:, 0], -p[:, 1]),            # camera -y: right = +x, nearer = smaller y
             "left180": (1 - p[:, 0], p[:, 1])}       # camera +y: right = -x, nearer = larger y
    for name, (u, near) in views.items():
        d = zbuffer(u, v, near.astype(np.float32))
        np.save(out / f"depth-{name}.npy", d)
        lo, hi = np.nanpercentile(d, (1, 99))
        from PIL import Image
        Image.fromarray((np.nan_to_num((d - lo) / max(hi - lo, 1e-6), nan=0).clip(0, 1) * 255).astype(np.uint8)).save(out / f"depth-{name}.png")
    (out / "splat.json").write_text(json.dumps({"points": int(len(xyz)), "seconds": round(time.time() - t0, 1), "res": RES}))
    print(f"triposplat: {len(xyz)} gaussians, {time.time() - t0:.0f}s -> {out}")


def sam2(job, out):
    import numpy as np
    import torch
    from PIL import Image
    from transformers import Sam2Model, Sam2Processor
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    t0 = time.time()
    name = "facebook/sam2.1-hiera-large"
    model, proc = Sam2Model.from_pretrained(name).to(dev).eval(), Sam2Processor.from_pretrained(name)
    scores = {}
    for view, spec in json.loads(pathlib.Path(job).read_text())["views"].items():
        img = Image.open(spec["crop"]).convert("RGB")
        names, boxes = list(spec["boxes"]), list(spec["boxes"].values())
        (out / view).mkdir(parents=True, exist_ok=True)
        if not boxes:
            continue
        inputs = proc(images=img, input_boxes=[boxes], return_tensors="pt").to(dev)
        with torch.no_grad():
            res = model(**inputs, multimask_output=False)
        masks = proc.post_process_masks(res.pred_masks.cpu(), inputs["original_sizes"].cpu())[0]   # (parts, 1, H, W)
        iou = res.iou_scores.cpu().numpy().reshape(len(names), -1)[:, 0]
        for k, part in enumerate(names):
            m = np.asarray(masks[k, 0], bool)
            Image.fromarray(m.astype(np.uint8) * 255).save(out / view / f"{part.replace('/', '_')}.png")
            scores[f"{view}/{part}"] = {"iou_pred": round(float(iou[k]), 3), "area": int(m.sum())}
    (out / "scores.json").write_text(json.dumps(scores, indent=1))
    print(f"sam2: {len(scores)} part masks, {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    mode, a, b = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    {"splat": splat, "sam2": sam2}[mode](a, b)
