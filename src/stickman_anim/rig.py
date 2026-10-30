"""2D Articulated Skeleton Rig, Poses, IK, Lip-Sync, and Crowds for stickman_anim.

Provides:
- Analytic 2-bone Inverse Kinematics (IK) for natural arm and leg bending.
- 12+ named poses & procedural actions (walk, run, wave, point, type, sit, shrug, jump, celebrate, fail, hold, hand-off, think).
- Facing directions (left, right, front) and prop attach points.
- Eye look-at targeting and audio amplitude-driven mouth movement.
- Emotes, speech/thought bubbles, character archetypes (human, robot, dog, cat, server_bot), and crowd generator.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, Optional, List, Union
from PIL import ImageDraw, ImageFont
from .paths import Point, dist, lerp_pt


def get_default_font(size: int = 11):
    try:
        from .lib import font
        return font(size)
    except Exception:
        return ImageFont.load_default()



def solve_2bone_ik(
    root: Point,
    target: Point,
    l1: float = 24.0,
    l2: float = 22.0,
    bend_dir: int = 1  # 1 = outward/down, -1 = inward/up
) -> Point:
    """
    Analytic 2-bone Inverse Kinematics solver using the Law of Cosines.
    Returns the exact mid-joint (elbow or knee) coordinate.
    """
    dx = target[0] - root[0]
    dy = target[1] - root[1]
    d = math.hypot(dx, dy)

    # Fully stretched / unreachable
    if d >= (l1 + l2):
        frac = l1 / max(1e-4, d)
        return (root[0] + dx * frac, root[1] + dy * frac)

    # Target too close to root
    d = max(abs(l1 - l2) + 1e-3, d)

    # Angle of baseline
    base_ang = math.atan2(dy, dx)

    # Law of cosines for angle at root joint
    cos_q1 = (l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d)
    q1 = math.acos(max(-1.0, min(1.0, cos_q1)))

    joint_ang = base_ang + bend_dir * q1
    return (
        root[0] + l1 * math.cos(joint_ang),
        root[1] + l1 * math.sin(joint_ang),
    )


@dataclass
class Pose:
    """Full body joint targets and angles."""
    torso_tilt: float = 0.0          # degrees
    head_tilt: float = 0.0
    hip_offset: Point = (0.0, 0.0)
    hand_l: Optional[Point] = None   # None = natural rest
    hand_r: Optional[Point] = None
    foot_l: Optional[Point] = None
    foot_r: Optional[Point] = None
    elbow_bend_l: int = -1
    elbow_bend_r: int = 1
    knee_bend_l: int = 1
    knee_bend_r: int = 1


def get_action_pose(action: str, t: float = 0.0, facing: str = "right") -> Pose:
    """
    Generate procedural continuous poses for named actions.
    t is typically frame index or cyclic phase.
    """
    p = Pose()
    act = action.lower()
    sgn = 1.0 if facing == "right" else -1.0

    if act == "walk":
        phase = t * 0.4
        p.torso_tilt = 4.0 * sgn
        p.hip_offset = (0.0, -abs(math.sin(phase)) * 3.0)
        p.foot_l = (-math.sin(phase) * 16.0 * sgn, -max(0.0, math.cos(phase)) * 6.0)
        p.foot_r = (math.sin(phase) * 16.0 * sgn, -max(0.0, -math.cos(phase)) * 6.0)
        p.hand_l = (math.sin(phase) * 14.0 * sgn, 18.0)
        p.hand_r = (-math.sin(phase) * 14.0 * sgn, 18.0)

    elif act == "run":
        phase = t * 0.6
        p.torso_tilt = 14.0 * sgn
        p.hip_offset = (0.0, -abs(math.sin(phase)) * 6.0)
        p.foot_l = (-math.sin(phase) * 26.0 * sgn, -max(0.0, math.cos(phase)) * 12.0)
        p.foot_r = (math.sin(phase) * 26.0 * sgn, -max(0.0, -math.cos(phase)) * 12.0)
        p.hand_l = (math.sin(phase) * 22.0 * sgn, -6.0)
        p.hand_r = (-math.sin(phase) * 22.0 * sgn, -6.0)

    elif act == "wave":
        p.hand_l = (-10.0 * sgn, 20.0)
        wave_dx = math.sin(t * 0.6) * 12.0
        p.hand_r = (18.0 * sgn + wave_dx, -44.0)

    elif act == "point":
        p.torso_tilt = 4.0 * sgn
        p.hand_l = (-8.0 * sgn, 20.0)
        p.hand_r = (38.0 * sgn, -12.0)

    elif act == "type":
        wig = 3.0 if (int(t) % 2) else 0.0
        p.torso_tilt = 6.0 * sgn
        p.hand_l = (14.0 * sgn, 6.0 - wig)
        p.hand_r = (24.0 * sgn, 6.0 + wig)

    elif act == "sit":
        p.torso_tilt = 2.0
        p.hip_offset = (0.0, 16.0)
        p.foot_l = (18.0 * sgn, 16.0)
        p.foot_r = (22.0 * sgn, 16.0)
        p.hand_l = (12.0 * sgn, 10.0)
        p.hand_r = (16.0 * sgn, 10.0)

    elif act == "shrug":
        p.torso_tilt = 0.0
        p.hand_l = (-20.0, -8.0)
        p.hand_r = (20.0, -8.0)
        p.head_tilt = math.sin(t * 0.2) * 5.0

    elif act == "jump":
        p.hip_offset = (0.0, -22.0)
        p.foot_l = (-8.0, -8.0)
        p.foot_r = (8.0, -8.0)
        p.hand_l = (-22.0, -36.0)
        p.hand_r = (22.0, -36.0)

    elif act == "celebrate":
        cheer_w = math.sin(t * 0.5) * 6.0
        p.hand_l = (-20.0 + cheer_w, -46.0)
        p.hand_r = (20.0 - cheer_w, -46.0)

    elif act == "fail":
        p.torso_tilt = 16.0
        p.head_tilt = 22.0
        p.hand_l = (-4.0, 6.0)
        p.hand_r = (4.0, 6.0)

    elif act == "hold":
        p.hand_l = (14.0 * sgn, 4.0)
        p.hand_r = (18.0 * sgn, 0.0)

    elif act == "hand_off":
        p.torso_tilt = 10.0 * sgn
        p.hand_r = (36.0 * sgn, -4.0)
        p.hand_l = (-6.0 * sgn, 18.0)

    elif act == "think":
        p.torso_tilt = -4.0 * sgn
        p.head_tilt = -10.0 * sgn
        p.hand_l = (4.0 * sgn, -24.0)  # Hand to chin
        p.hand_r = (-8.0 * sgn, 18.0)

    return p


class Character:
    """Articulated stick figure or agent with 2-bone IK and attachments."""
    def __init__(
        self,
        kind: str = "human",           # 'human', 'robot', 'dog', 'cat', 'server_bot'
        scale: float = 1.0,
        facing: str = "right",         # 'right', 'left', 'front'
        accessories: Optional[List[str]] = None,
        props: Optional[Dict[str, Any]] = None,
    ):
        self.kind = kind.lower()
        self.scale = scale
        self.facing = facing
        self.accessories = set(accessories or [])
        self.props = props or {}  # slot -> name or path
        self.look_at: Optional[Point] = None
        self.expression: str = "neutral"
        self.mouth_open: float = 0.0   # 0.0 (closed) to 1.0 (open)

    def draw(
        self,
        frame_obj: Any,
        cx: float,
        floor_y: float,
        action: str = "idle",
        t: float = 0.0,
        hl: Optional[Point] = None,
        hr: Optional[Point] = None,
        col: Optional[Tuple[int, int, int]] = None,
    ) -> None:
        """Render character using forward kinematics + analytic 2-bone IK."""
        c = frame_obj
        col = col or (245, 245, 245)
        s = self.scale
        sgn = 1.0 if self.facing == "right" else (-1.0 if self.facing == "left" else 0.0)

        pose = get_action_pose(action, t=t, facing=self.facing)
        if hl is not None:
            pose.hand_l = (hl[0] - cx, hl[1] - (floor_y - 66 * s))
        if hr is not None:
            pose.hand_r = (hr[0] - cx, hr[1] - (floor_y - 66 * s))

        # Root hip position
        hip_x = cx + pose.hip_offset[0] * s
        hip_y = floor_y - 42.0 * s + pose.hip_offset[1] * s

        # Shoulders position
        tilt_rad = math.radians(pose.torso_tilt)
        torso_len = 26.0 * s
        sh_x = hip_x + torso_len * math.sin(tilt_rad)
        sh_y = hip_y - torso_len * math.cos(tilt_rad)

        # Head position
        neck_len = 16.0 * s
        head_rad = math.radians(pose.torso_tilt + pose.head_tilt)
        head_x = sh_x + neck_len * math.sin(head_rad)
        head_y = sh_y - neck_len * math.cos(head_rad)

        # 1. Torso
        c.line((hip_x, hip_y), (sh_x, sh_y), col=col, w=2.6 * s)

        # 2. Legs with 2-Bone IK
        l_leg1, l_leg2 = 20.0 * s, 20.0 * s
        default_foot_l = (hip_x - 9.0 * s, floor_y)
        default_foot_r = (hip_x + 9.0 * s, floor_y)

        target_fl = (hip_x + pose.foot_l[0] * s, floor_y + pose.foot_l[1] * s) if pose.foot_l else default_foot_l
        target_fr = (hip_x + pose.foot_r[0] * s, floor_y + pose.foot_r[1] * s) if pose.foot_r else default_foot_r

        knee_l = solve_2bone_ik((hip_x, hip_y), target_fl, l_leg1, l_leg2, bend_dir=pose.knee_bend_l)
        knee_r = solve_2bone_ik((hip_x, hip_y), target_fr, l_leg1, l_leg2, bend_dir=pose.knee_bend_r)

        c.line((hip_x, hip_y), knee_l, col=col, w=2.4 * s)
        c.line(knee_l, target_fl, col=col, w=2.4 * s)
        c.line((hip_x, hip_y), knee_r, col=col, w=2.4 * s)
        c.line(knee_r, target_fr, col=col, w=2.4 * s)

        # Feet feet-lines
        foot_dx = 8.0 * s * (1.0 if self.facing != "left" else -1.0)
        c.line(target_fl, (target_fl[0] + foot_dx, target_fl[1]), col=col, w=2.2 * s)
        c.line(target_fr, (target_fr[0] + foot_dx, target_fr[1]), col=col, w=2.2 * s)

        # 3. Head & Face Rendering
        if self.kind == "robot":
            # Robot square head + antenna + mouth grille
            hw = 11.0 * s
            c.rect((head_x - hw, head_y - hw), (head_x + hw, head_y + hw), col=col, w=2.6 * s)
            # Antenna
            c.line((head_x, head_y - hw), (head_x, head_y - hw - 8.0 * s), col=col, w=2.0 * s)
            c.circle((head_x, head_y - hw - 10.0 * s), 2.4 * s, col=(80, 220, 255), fill=True)
            # Eyes with look_at targeting
            eye_off_x = 0.0
            eye_off_y = 0.0
            if self.look_at:
                ang = math.atan2(self.look_at[1] - head_y, self.look_at[0] - head_x)
                eye_off_x = math.cos(ang) * 2.0 * s
                eye_off_y = math.sin(ang) * 1.5 * s

            eye_col = (80, 220, 255) if self.expression != "dead" else (255, 95, 95)
            c.circle((head_x - 4.5 * s + eye_off_x, head_y - 2.0 * s + eye_off_y), 2.2 * s, col=eye_col, fill=True)
            c.circle((head_x + 4.5 * s + eye_off_x, head_y - 2.0 * s + eye_off_y), 2.2 * s, col=eye_col, fill=True)

            # Mouth (amplitude-driven lip-sync)
            if self.mouth_open > 0.1:
                mh = max(1.5, 6.0 * self.mouth_open * s)
                c.rect((head_x - 5.0 * s, head_y + 4.0 * s), (head_x + 5.0 * s, head_y + 4.0 * s + mh), col=col, w=1.5 * s)
            else:
                c.line((head_x - 5.0 * s, head_y + 5.0 * s), (head_x + 5.0 * s, head_y + 5.0 * s), col=col, w=1.8 * s)

        elif self.kind == "server_bot":
            # Server rack on legs
            rw, rh = 16.0 * s, 26.0 * s
            c.rect((head_x - rw, head_y - rh / 2.0), (head_x + rw, head_y + rh / 2.0), col=col, w=2.6 * s)
            c.line((head_x - rw + 4.0, head_y), (head_x + rw - 4.0, head_y), col=(80, 220, 255), w=2.0 * s)
            c.circle((head_x + rw - 6.0, head_y - 6.0), 2.0 * s, col=(90, 255, 140), fill=True)

        else:
            # Human round head
            hr_rad = 10.0 * s
            c.circle((head_x, head_y), hr_rad, col=col, w=2.6 * s)

            # Glasses
            if "glasses" in self.accessories or self.kind == "human":
                c.circle((head_x - 4.0 * s, head_y - 1.0 * s), 3.5 * s, col=col, w=1.5 * s)
                c.circle((head_x + 4.0 * s, head_y - 1.0 * s), 3.5 * s, col=col, w=1.5 * s)
                c.line((head_x - 1.0 * s, head_y - 1.0 * s), (head_x + 1.0 * s, head_y - 1.0 * s), col=col, w=1.5 * s)

            # Eyes
            eye_off_x, eye_off_y = 0.0, 0.0
            if self.look_at:
                ang = math.atan2(self.look_at[1] - head_y, self.look_at[0] - head_x)
                eye_off_x = math.cos(ang) * 1.8 * s
                eye_off_y = math.sin(ang) * 1.2 * s
            c.circle((head_x - 4.0 * s + eye_off_x, head_y - 1.0 * s + eye_off_y), 1.2 * s, col=col, fill=True)
            c.circle((head_x + 4.0 * s + eye_off_x, head_y - 1.0 * s + eye_off_y), 1.2 * s, col=col, fill=True)

            # Mouth (amplitude lip-sync or expression)
            if self.mouth_open > 0.15:
                # Open oval mouth
                c.circle((head_x, head_y + 4.5 * s), 2.5 * s * self.mouth_open, col=col, w=1.5 * s)
            elif self.expression == "happy":
                c.poly([(head_x - 4.0 * s, head_y + 4.0 * s), (head_x, head_y + 6.5 * s), (head_x + 4.0 * s, head_y + 4.0 * s)], col=(90, 255, 140), w=1.8 * s, close=False)
            elif self.expression == "sad":
                c.poly([(head_x - 4.0 * s, head_y + 6.0 * s), (head_x, head_y + 3.5 * s), (head_x + 4.0 * s, head_y + 6.0 * s)], col=col, w=1.8 * s, close=False)

        # 4. Accessories (hats, crown, headphones, tie, cape)
        if "hat" in self.accessories:
            c.line((head_x - 14.0 * s, head_y - 9.0 * s), (head_x + 14.0 * s, head_y - 9.0 * s), col=col, w=2.4 * s)
            c.rect((head_x - 8.0 * s, head_y - 18.0 * s), (head_x + 8.0 * s, head_y - 9.0 * s), col=col, w=2.2 * s)
        elif "crown" in self.accessories:
            c.poly([(head_x - 9.0 * s, head_y - 10.0 * s), (head_x - 9.0 * s, head_y - 18.0 * s),
                    (head_x - 4.0 * s, head_y - 13.0 * s), (head_x, head_y - 19.0 * s),
                    (head_x + 4.0 * s, head_y - 13.0 * s), (head_x + 9.0 * s, head_y - 18.0 * s),
                    (head_x + 9.0 * s, head_y - 10.0 * s)], col=(255, 230, 0), w=2.0 * s, close=True)
        if "headphones" in self.accessories:
            c.circle((head_x - 11.0 * s, head_y), 3.5 * s, col=(80, 220, 255), fill=True)
            c.circle((head_x + 11.0 * s, head_y), 3.5 * s, col=(80, 220, 255), fill=True)
            # Band over head
            p_band = [(head_x - 11.0 * s, head_y), (head_x, head_y - 14.0 * s), (head_x + 11.0 * s, head_y)]
            c.poly(p_band, col=(80, 220, 255), w=2.0 * s, close=False)
        if "tie" in self.accessories:
            c.poly([(sh_x - 2.0 * s, sh_y + 2.0 * s), (sh_x + 2.0 * s, sh_y + 2.0 * s),
                    (sh_x + 3.0 * s, sh_y + 16.0 * s), (sh_x, sh_y + 20.0 * s),
                    (sh_x - 3.0 * s, sh_y + 16.0 * s)], col=(255, 95, 95), w=1.8 * s, close=True)

        # 5. Arms with 2-Bone IK
        l_arm1, l_arm2 = 18.0 * s, 18.0 * s
        default_hand_l = (sh_x - 10.0 * s, sh_y + 24.0 * s)
        default_hand_r = (sh_x + 10.0 * s, sh_y + 24.0 * s)

        target_hl = (sh_x + pose.hand_l[0] * s, sh_y + pose.hand_l[1] * s) if pose.hand_l else default_hand_l
        target_hr = (sh_x + pose.hand_r[0] * s, sh_y + pose.hand_r[1] * s) if pose.hand_r else default_hand_r

        elbow_l = solve_2bone_ik((sh_x, sh_y), target_hl, l_arm1, l_arm2, bend_dir=pose.elbow_bend_l)
        elbow_r = solve_2bone_ik((sh_x, sh_y), target_hr, l_arm1, l_arm2, bend_dir=pose.elbow_bend_r)

        c.line((sh_x, sh_y), elbow_l, col=col, w=2.4 * s)
        c.line(elbow_l, target_hl, col=col, w=2.4 * s)
        c.line((sh_x, sh_y), elbow_r, col=col, w=2.4 * s)
        c.line(elbow_r, target_hr, col=col, w=2.4 * s)

        # 6. Attached Props (e.g. coffee, laptop, sword, phone)
        for slot, prop_name in self.props.items():
            pos = target_hr if "right" in slot else target_hl
            if prop_name == "coffee":
                c.icon("coffee", (pos[0], pos[1] - 8.0 * s), size=int(18 * s), col=col)
            elif prop_name == "phone":
                c.icon("smartphone", (pos[0], pos[1] - 8.0 * s), size=int(18 * s), col=(80, 220, 255))
            elif prop_name == "laptop":
                c.rect((pos[0] - 10.0 * s, pos[1] - 4.0 * s), (pos[0] + 10.0 * s, pos[1] + 2.0 * s), col=col, w=2.0 * s)
                c.line((pos[0] - 8.0 * s, pos[1] - 4.0 * s), (pos[0] - 4.0 * s, pos[1] - 14.0 * s), col=(80, 220, 255), w=2.0 * s)


# ------------------------------------------------------------------ Emotes & Speech Bubbles
def draw_emote(frame_obj: Any, xy: Point, kind: str = "!", col: Optional[Tuple[int, int, int]] = None) -> None:
    """Draw comic emotion indicators over a character's head."""
    c = frame_obj
    x, y = xy
    k = kind.strip()
    if k == "!":
        col = col or (255, 230, 0)
        c.line((x, y - 14), (x, y - 4), col=col, w=2.8)
        c.circle((x, y), 1.5, col=col, fill=True)
    elif k == "?":
        col = col or (80, 220, 255)
        c.poly([(x - 5, y - 14), (x + 3, y - 14), (x + 4, y - 9), (x, y - 6), (x, y - 3)], col=col, w=2.4, close=False)
        c.circle((x, y), 1.5, col=col, fill=True)
    elif k == "heart":
        col = col or (255, 95, 95)
        c.poly([(x, y - 6), (x - 6, y - 12), (x - 3, y - 15), (x, y - 12), (x + 3, y - 15), (x + 6, y - 12)], col=col, w=2.2, close=True)
    elif k in ("sweat", "drop"):
        col = col or (80, 220, 255)
        c.poly([(x, y - 10), (x + 4, y - 4), (x, y), (x - 4, y - 4)], col=col, w=2.0, close=True)
    elif k in ("zzz", "sleep"):
        col = col or (180, 180, 190)
        fnt = get_default_font(10)
        c.text((x, y - 10), "Z", fnt, col=col)
        c.text((x + 8, y - 18), "z", fnt, col=col)


def draw_speech_bubble(
    frame_obj: Any,
    speaker_xy: Point,
    text: str,
    box_w: float = 120.0,
    box_h: float = 40.0,
    thought: bool = False,
    progress: float = 1.0,
    col: Optional[Tuple[int, int, int]] = None
) -> None:
    """Render a hand-drawn speech or thought bubble pointing at speaker."""
    c = frame_obj
    col = col or (245, 245, 245)
    sx, sy = speaker_xy
    bx = sx - box_w / 2.0
    by = sy - box_h - 25.0

    if progress < 0.2:
        return

    scale = min(1.0, progress * 1.5)
    bw = box_w * scale
    bh = box_h * scale
    x0, y0 = sx - bw / 2.0, sy - bh - 25.0

    if not thought:
        # Speech bubble rect + tail
        c.rect((x0, y0), (x0 + bw, y0 + bh), col=col, w=2.2, jit=0.8)
        # Tail triangle pointing down to speaker
        tail = [(x0 + bw / 2.0 - 6, y0 + bh), (sx, sy - 8), (x0 + bw / 2.0 + 8, y0 + bh)]
        c.poly(tail, col=col, w=2.0, close=False)
    else:
        # Thought bubble with small bubbles leading up
        c.rect((x0, y0), (x0 + bw, y0 + bh), col=col, w=2.0, jit=1.2)
        c.circle((sx + 4, sy - 10), 2.2, col=col, fill=True)
        c.circle((sx + 8, sy - 18), 3.5, col=col, fill=True)

    if progress >= 0.7:
        fnt = get_default_font(10)
        c.text((x0 + bw / 2.0, y0 + bh / 2.0), text, fnt, col=col, anchor="mm")


def draw_crowd(
    frame_obj: Any,
    box: Tuple[float, float, float, float],
    count: int = 8,
    action: str = "celebrate",
    t: float = 0.0
) -> None:
    """Render a procedural crowd of stick figures with staggered animation phases."""
    c = frame_obj
    x, y, w, h = box
    slot_w = w / max(1, count)
    fl = y + h

    rng = random.Random(int(count * 1337))
    for i in range(count):
        cx = x + (i + 0.5) * slot_w + rng.uniform(-4.0, 4.0)
        char_scale = rng.uniform(0.75, 0.95)
        char_kind = "human" if (i % 3 != 0) else "robot"
        char = Character(kind=char_kind, scale=char_scale)
        # Stagger animation phase
        stagger_t = t + i * 2.5
        char.draw(c, cx, fl, action=action, t=stagger_t)
