"""python3 -m unittest discover -s tests/tools/blender

L16-3: the MDX reader (bytes built here, no Blizzard file), the Hive stats, the GLB writer and the reference mode of review_pair."""
import pathlib
import struct
import sys
import tempfile
import unittest

try:
    import numpy as np
    from PIL import Image
except ImportError:
    raise unittest.SkipTest("numpy / Pillow are not installed")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender"))

import hive_sheet as HS  # noqa: E402
import mdx_inspect as MI  # noqa: E402
import review_pair as RP  # noqa: E402


def chunk(tag, payload):
    return tag + struct.pack("<I", len(payload)) + payload


def geoset(verts, uvs, tris, material):
    """One v800 geoset body with its size word."""
    n = len(verts)
    body = b"VRTX" + struct.pack("<I", n) + b"".join(struct.pack("<3f", *v) for v in verts)
    body += b"NRMS" + struct.pack("<I", n) + b"".join(struct.pack("<3f", 0, 0, 1) for _ in verts)
    body += b"PTYP" + struct.pack("<II", 1, 4) + b"PCNT" + struct.pack("<II", 1, len(tris) * 3)
    body += b"PVTX" + struct.pack("<I", len(tris) * 3) + struct.pack(f"<{len(tris) * 3}H", *sum(tris, ()))
    body += b"GNDX" + struct.pack("<I", n) + bytes(n) + b"MTGC" + struct.pack("<II", 1, n)
    body += b"MATS" + struct.pack("<II", 1, 0)
    body += struct.pack("<3I", material, 0, 0) + struct.pack("<7f", 1, 0, 0, 0, 1, 1, 1)
    body += struct.pack("<I", 0)                                    # no per-sequence extents
    body += b"UVAS" + struct.pack("<I", 1) + b"UVBS" + struct.pack("<I", n) + b"".join(struct.pack("<2f", *t) for t in uvs)
    return struct.pack("<I", len(body) + 4) + body


def geoa(gid, alpha, key=None):
    body = struct.pack("<fI3fI", alpha, 0, 1, 1, 1, gid)
    if key:
        body += b"KGAO" + struct.pack("<3I", 1, 0, 0xFFFFFFFF) + struct.pack("<if", *key)
    return struct.pack("<I", len(body) + 4) + body


def fake_mdx(hidden_by_track=False):
    quad = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
    uv = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    geos = geoset(quad, uv, [(0, 1, 2)], 0) + geoset(quad, uv, [(0, 1, 2)], 1)
    layer = lambda tex: struct.pack("<6If", 28, 0, 0, tex, 0xFFFFFFFF, 0, 1.0)   # noqa: E731
    mat = lambda tex: struct.pack("<3I", 48, 0, 0) + b"LAYS" + struct.pack("<I", 1) + layer(tex)   # noqa: E731
    texs = struct.pack("<I260sI", 0, b"Textures\\Foot.blp", 0) + struct.pack("<I260sI", 1, b"", 0)
    seqs = struct.pack("<80s2I", b"Stand", 100, 200).ljust(132, b"\0")
    ga = geoa(0, 1.0) + geoa(1, 1.0, (150, 0.0) if hidden_by_track else (900, 0.0))
    return (b"MDLX" + chunk(b"VERS", struct.pack("<I", 800)) + chunk(b"SEQS", seqs) + chunk(b"MTLS", mat(0) + mat(1))
            + chunk(b"TEXS", texs) + chunk(b"GEOS", geos) + chunk(b"GEOA", ga))


class TestMdx(unittest.TestCase):
    def read(self, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "m.mdx"
            path.write_bytes(fake_mdx(**kw))
            return MI.read_mdx(path)

    def test_geosets_uvs_materials_textures(self):
        m = self.read()
        self.assertEqual([len(g["faces"]) // 3 for g in m["geosets"]], [1, 1])
        self.assertEqual(m["geosets"][0]["vertices"][1][6:], (1.0, 0.0))
        self.assertEqual(m["geosets"][1]["material"], 1)
        self.assertEqual(m["materials"][1][0]["texture"], 1)
        self.assertEqual(m["textures"], [(0, "Textures\\Foot.blp"), (1, "")])

    def test_alpha_track_in_the_first_sequence_hides_a_geoset_one_outside_does_not(self):
        self.assertEqual([g["visible"] for g in self.read()["geosets"]], [True, True])
        self.assertEqual([g["visible"] for g in self.read(hidden_by_track=True)["geosets"]], [True, False])


class TestStats(unittest.TestCase):
    def test_ink_is_a_dark_line_next_to_light_texels_flat_colour_has_none(self):
        flat = Image.new("RGBA", (32, 32), (120, 90, 60, 255))
        self.assertEqual(HS.texture_stats(flat)["ink"], 0.0)
        lined = Image.new("RGBA", (32, 32), (200, 200, 200, 255))
        for y in range(32):
            lined.putpixel((16, y), (10, 10, 10, 255))
        st = HS.texture_stats(lined)
        self.assertGreater(st["ink"], 0.0)
        self.assertAlmostEqual(st["dark"], 1 / 32, places=3)

    def test_uv_mask_covers_only_the_sampled_texels(self):
        g = {"vertices": [(0, 0, 0, 0, 0, 1, 0.0, 0.0), (0, 0, 0, 0, 0, 1, 0.5, 0.0), (0, 0, 0, 0, 0, 1, 0.0, 0.5)], "faces": [0, 1, 2]}
        mask = HS.uv_mask([g], (64, 64))
        self.assertTrue(mask[2, 2])
        self.assertFalse(mask[60, 60])
        self.assertLess(mask.mean(), 0.2)

    def test_palette_counts_colours_with_a_share_and_their_luma_spread(self):
        centres = np.array([[0, 0, 0], [255, 255, 255], [10, 10, 10]], dtype=float)
        big, spread = HS.palette_stats(centres, np.array([0.5, 0.48, 0.02]))
        self.assertEqual(big, 2)
        self.assertGreater(spread, 0.9)

    def test_shape_stats_trim_a_stray_vertex(self):
        rng = np.random.default_rng(1)
        body = rng.uniform(0, 1, (2000, 3))
        stray = np.concatenate([body, [[0, 50, 0]]])
        s = HS.shape_stats(stray[:, 0], stray[:, 1], stray[:, 2])
        self.assertLess(s["H"], 1.1)


class TestGlb(unittest.TestCase):
    def test_build_glb_round_trips_geometry_and_names_a_texture_per_geoset(self):
        mdx = {"geosets": [{"vertices": [(0, 0, 0, 0, 0, 1, 0, 0), (10, 0, 0, 0, 0, 1, 1, 0), (0, 0, 20, 0, 0, 1, 0, 1)],
                            "faces": [0, 1, 2], "material": 0, "visible": True}],
               "materials": [[{"filter": 0, "texture": 0, "alpha": 1.0}]], "textures": [(0, "x.blp")]}
        with tempfile.TemporaryDirectory() as tmp:
            glb = pathlib.Path(tmp) / "m.glb"
            glb.write_bytes(HS.build_glb(mdx, {}))
            j, blob = HS.read_glb(glb)
        pos = HS.accessor(j, blob, j["meshes"][0]["primitives"][0]["attributes"]["POSITION"])
        self.assertAlmostEqual(float(np.ptp(pos[:, 1])), HS.HEIGHT, places=4)       # Y-up, scaled to HEIGHT
        self.assertEqual(len(j["materials"]), 1)
        self.assertNotIn("textures", j)                                              # the texture is not in the study set: no image, no crash


class TestReference(unittest.TestCase):
    def test_reference_prompt_asks_for_that_model_and_ask_vote_sends_it(self):
        self.assertIn("THAT real WC3 model", RP.PROMPT_REF)
        self.assertNotIn("THAT real WC3 model", RP.PROMPT)
        seen = []
        reply = '{"sheet":"left","artist":"left","wc3":"right","form":"left"}'
        vote = RP.ask_vote(lambda model, prompt, imgs: seen.append(prompt) or reply, "m", "img.png", prompt=RP.PROMPT_REF)
        self.assertEqual(seen, [RP.PROMPT_REF])
        self.assertEqual(vote["wc3"], "right")


if __name__ == "__main__":
    unittest.main()
