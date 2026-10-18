"""Render a 1080x1920 photo montage with Ken Burns motion + Chinese captions, piped to ffmpeg."""
import subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

UP = "/root/.claude/uploads/a609566a-2b23-563a-a009-6629ddc5605b/"
W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
out, audio = sys.argv[1], sys.argv[2]

# (image, seconds, caption, zoom from->to, pan dx)
SCENES = [
    # last weekend: studio session
    ("63b7d228-image.jpg", 3.4, "上个周末 · 灯光机位就位", (1.00, 1.07), 0.0),
    ("ddb510f1-image.jpg", 3.6, "第一位事业型妈妈", (1.08, 1.00), 0.03),
    # this weekend: living-room session
    ("7e12a5fc-image.jpg", 3.4, "这个周末 · 换到家里的客厅", (1.00, 1.08), 0.0),
    ("e8c9d316-image.jpg", 3.4, "第二位事业型妈妈", (1.08, 1.00), 0.03),
    ("921bc74b-image.jpg", 3.6, "聊到停不下来", (1.00, 1.07), -0.03),
]
END = 3.4   # end card duration
FOLLOW = "3a563be0-image.png"  # 1080x1920 follow card, shown last
FOLLOW_DUR = 3.2
XF = 0.6    # crossfade

def font(sz): return ImageFont.truetype(FONT, sz)

def prep(name):
    im = ImageOps.exif_transpose(Image.open(UP + name)).convert("RGB")
    bg = ImageOps.fit(im, (W, H)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (28, 22, 18)), 0.45)
    return im, bg

def text_center(d, y, s, sz, fill, stroke=0, sfill=(0, 0, 0)):
    f = font(sz)
    w = d.textlength(s, font=f)
    d.text(((W - w) / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill)

def ease(x): return x * x * (3 - 2 * x)

PHOTO_TOP, BOX_W, BOX_H = 620, 1000, 900

def frame(im, bg, t, dur, zoom, dx):
    p = ease(min(max(t / dur, 0), 1))
    z = zoom[0] + (zoom[1] - zoom[0]) * p
    PHOTO_W = min(BOX_W, int(BOX_H * im.width / im.height))
    ph = int(PHOTO_W * im.height / im.width)
    px = (W - PHOTO_W) // 2
    # crop window in source coords (subpixel via affine transform)
    cw, ch = im.width / z, im.height / z
    cx = im.width / 2 + dx * im.width * (p - 0.5)
    x0, y0 = cx - cw / 2, (im.height - ch) / 2
    sx = cw / PHOTO_W
    photo = im.transform((PHOTO_W, ph), Image.AFFINE, (sx, 0, x0, 0, sx, y0), Image.BICUBIC)
    f = bg.copy()
    # soft shadow + white border
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([px + 6, PHOTO_TOP + 16, px + PHOTO_W + 6, PHOTO_TOP + ph + 16], fill=(0, 0, 0, 140))
    f.paste(sh.filter(ImageFilter.GaussianBlur(18)), (0, 0), sh.filter(ImageFilter.GaussianBlur(18)))
    ImageDraw.Draw(f).rectangle([px - 8, PHOTO_TOP - 8, px + PHOTO_W + 7, PHOTO_TOP + ph + 7], fill=(250, 244, 234))
    f.paste(photo, (px, PHOTO_TOP))
    return f, PHOTO_TOP + ph

def overlay(f, photo_bottom, caption, t, title_alpha):
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    a = int(255 * title_alpha)
    text_center(d, 250, "连续两个周末", 64, (255, 214, 160, a), 1, (60, 30, 10, a))
    text_center(d, 345, "采访了两位事业型妈妈", 92, (255, 255, 255, a), 3, (60, 30, 10, a))
    d.rounded_rectangle([W/2 - 70, 480, W/2 + 70, 488], 4, fill=(232, 128, 72, a))
    ca = int(255 * ease(min(max((t - 0.25) / 0.5, 0), 1)))
    lift = int(24 * (1 - ca / 255))
    text_center(d, photo_bottom + 60 + lift, caption, 60, (255, 255, 255, ca), 2, (40, 20, 10, ca))
    text_center(d, H - 210, "散养Pie  ·  播客录制花絮", 44, (255, 236, 210, 220))
    return Image.alpha_composite(f.convert("RGBA"), o).convert("RGB")

def end_card(bg, t):
    f = bg.copy().convert("RGBA")
    dark = Image.new("RGBA", (W, H), (20, 14, 10, int(150 * ease(min(t / 0.6, 1)))))
    f = Image.alpha_composite(f, dark)
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(o)
    def a(delay): return int(255 * ease(min(max((t - delay) / 0.6, 0), 1)))
    text_center(d, 700, "是妈妈，", 110, (255, 255, 255, a(0.2)), 3, (40, 20, 10, a(0.2)))
    text_center(d, 850, "也是她自己", 110, (255, 214, 160, a(0.6)), 3, (40, 20, 10, a(0.6)))
    d.rounded_rectangle([W/2 - 70, 1030, W/2 + 70, 1038], 4, fill=(232, 128, 72, a(1.0)))
    text_center(d, 1090, "两期对谈 · 即将上线", 58, (255, 255, 255, a(1.0)))
    text_center(d, H - 210, "散养Pie  ·  播客录制花絮", 44, (255, 236, 210, 220))
    return Image.alpha_composite(f, o).convert("RGB")

prepped = [prep(s[0]) for s in SCENES]
starts, t0 = [], 0.0
for s in SCENES:
    starts.append(t0); t0 += s[1] - XF
end_start = t0
follow_start = end_start + END - XF
total = follow_start + FOLLOW_DUR
follow_im = Image.open(UP + FOLLOW).convert("RGB").resize((W, H))

def follow_card(t):
    z = 1.04 - 0.04 * ease(min(t / FOLLOW_DUR, 1))
    cw, ch = W / z, H / z
    return follow_im.transform((W, H), Image.AFFINE, (1 / z, 0, (W - cw) / 2, 0, 1 / z, (H - ch) / 2), Image.BICUBIC)

def render_scene(i, t):
    name, dur, cap, zoom, dx = SCENES[i]
    im, bg = prepped[i]
    lt = t - starts[i]
    f, pb = frame(im, bg, lt, dur, zoom, dx)
    title_alpha = ease(min(t / 0.8, 1))
    return overlay(f, pb, cap, lt, title_alpha)

ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio, "-map", "0:v", "-map", "1:a",
    "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)

nf = int(total * FPS)
for k in range(nf):
    t = k / FPS
    active = [i for i in range(len(SCENES)) if starts[i] <= t < starts[i] + SCENES[i][1]]
    if t >= follow_start:
        img = follow_card(t - follow_start)
        if t < end_start + END:
            img = Image.blend(end_card(prepped[-1][1], t - end_start), img, ease((t - follow_start) / XF))
    elif t >= end_start:
        img = end_card(prepped[-1][1], t - end_start)
        # crossfade from last scene into end card
        last = len(SCENES) - 1
        if t < starts[last] + SCENES[last][1]:
            img = Image.blend(render_scene(last, t), img, (t - end_start) / XF)
    elif len(active) == 2:
        a, b = active
        img = Image.blend(render_scene(a, t), render_scene(b, t), ease((t - starts[b]) / XF))
    else:
        img = render_scene(active[0], t)
    ff.stdin.write(img.tobytes())
ff.stdin.close(); ff.wait()
print("done", total, "s")
