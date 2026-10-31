"""Cycloid disc geometry, kinematics and load sharing for the elbow reducer.

Fixed ring pins (zp) in the housing, discs with zc = zp - 1 lobes, output
pins through holes in the discs. All maths is plain numpy so calc.py and the
cad build use the exact same curves.

Conventions: housing frame, axis = z, angles in radians. Input (cam) angle
alpha puts disc A centre at e*(cos a, sin a); disc B sits at alpha + pi.
Both discs (and the output) turn by phi = -alpha / zc.
"""

import math

import numpy as np


def rot(a):
    """2x2 rotation matrix for angle a (rad)."""
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s], [s, c]])


def pin_path(r_pins, e, zc, n):
    """Ring-pin centre path seen from disc A (a closed curtate trochoid).

    returns (n, 2) points for the pin at housing angle 0, alpha 0..2*pi*zc.
    """
    a = np.linspace(0.0, 2 * math.pi * zc, n, endpoint=False)
    x = r_pins - e * np.cos(a)
    y = -e * np.sin(a)
    t = a / zc
    c, s = np.cos(t), np.sin(t)
    return np.stack([c * x - s * y, s * x + c * y], axis=1)


def outward_normals(pts):
    """Unit outward normals of a closed ccw polyline (central differences)."""
    d = np.roll(pts, -1, axis=0) - np.roll(pts, 1, axis=0)
    n = np.stack([d[:, 1], -d[:, 0]], axis=1)
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def signed_area(pts):
    """Polygon signed area (positive = counter-clockwise)."""
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def disc_profile(r_pins, e, r_pin, zc, n=4000, dr=0.0, rot_deg=0.0):
    """Disc outline in its own frame: pin path offset inward by r_pin + dr.

    dr > 0 is an equidistant relief (radial play against the pins).
    rot_deg turns the outline (disc B uses -180/zc).
    """
    q = pin_path(r_pins, e, zc, n)
    if signed_area(q) < 0:
        q = q[::-1]
    p = q - (r_pin + dr) * outward_normals(q)
    if rot_deg:
        p = p @ rot(math.radians(rot_deg)).T
    return p


def curvature(pts):
    """Signed curvature (1/mm, + = convex) of a closed ccw polyline (3-point circle)."""
    a, b, c = np.roll(pts, 1, axis=0), pts, np.roll(pts, -1, axis=0)
    ab, bc, ca = b - a, c - b, a - c
    cross = ab[:, 0] * bc[:, 1] - ab[:, 1] * bc[:, 0]
    la, lb, lc = (np.linalg.norm(v, axis=1) for v in (ab, bc, ca))
    return 2 * cross / (la * lb * lc)


def self_intersects(pts, stride=1):
    """True when the closed polyline crosses itself (cusp / undercut check)."""
    p = pts[::stride]
    a, b = p, np.roll(p, -1, axis=0)
    n = len(p)

    def cross(u, v):
        # z of the 2d cross product
        return u[..., 0] * v[..., 1] - u[..., 1] * v[..., 0]

    for i in range(n):
        # test segment i against all non-adjacent segments (vectorised)
        j = np.arange(i + 2, n - (1 if i == 0 else 0))
        if len(j) == 0:
            continue
        p1, p2, p3, p4 = a[i], b[i], a[j], b[j]
        d1 = cross(p4 - p3, p1 - p3)
        d2 = cross(p4 - p3, p2 - p3)
        d3 = cross(p2 - p1, p3 - p1)
        d4 = cross(p2 - p1, p4 - p1)
        if np.any((d1 * d2 < 0) & (d3 * d4 < 0)):
            return True
    return False


def point_to_polyline(qs, poly):
    """Distance and closest point index from each point in qs to a closed polyline.

    returns (dist (m,), idx (m,), closest points (m, 2)).
    """
    a = poly
    b = np.roll(poly, -1, axis=0)
    ab = b - a
    l2 = np.sum(ab * ab, axis=1)
    out_d, out_i, out_p = [], [], []
    for q in qs:
        t = np.clip(np.sum((q - a) * ab, axis=1) / l2, 0.0, 1.0)
        c = a + t[:, None] * ab
        d = np.linalg.norm(c - q, axis=1)
        k = int(np.argmin(d))
        out_d.append(d[k])
        out_i.append(k)
        out_p.append(c[k])
    return np.array(out_d), np.array(out_i), np.array(out_p)


def inside(qs, poly):
    """Even-odd point-in-polygon test for each point in qs."""
    x, y = poly[:, 0], poly[:, 1]
    x2, y2 = np.roll(x, -1), np.roll(y, -1)
    res = []
    for qx, qy in qs:
        cond = (y > qy) != (y2 > qy)
        xi = x + (qy - y) * (x2 - x) / np.where(y2 - y == 0, 1e-12, y2 - y)
        res.append(bool(np.sum(cond & (qx < xi)) % 2))
    return np.array(res)


class Reducer:
    """Cycloid stage: ring pins, two discs at 180 deg, output pins."""

    def __init__(self, zp, r_pins, r_pin, e, dr, r_out, n_out, r_out_pin, r_out_hole, n=4000):
        """Store the stage geometry (mm) and build both disc outlines."""
        self.zp, self.zc = zp, zp - 1
        self.R, self.rp, self.e, self.dr = r_pins, r_pin, e, dr
        self.rw, self.nw, self.rwp, self.rwh = r_out, n_out, r_out_pin, r_out_hole
        self.prof = {
            "A": disc_profile(r_pins, e, r_pin, self.zc, n, dr, 0.0),
            "B": disc_profile(r_pins, e, r_pin, self.zc, n, dr, -180.0 / self.zc),
        }
        self.pins = np.array([[r_pins * math.cos(b), r_pins * math.sin(b)]
                              for b in (2 * math.pi * k / zp for k in range(zp))])
        self.holes = np.array([[r_out * math.cos(b), r_out * math.sin(b)]
                               for b in (2 * math.pi * k / n_out for k in range(n_out))])

    @property
    def lam(self):
        """Curtate (shortening) ratio e * zp / r_pins."""
        return self.e * self.zp / self.R

    def pose(self, alpha, disc):
        """(centre xy, rotation phi) of a disc for input angle alpha."""
        a = alpha + (math.pi if disc == "B" else 0.0)
        return self.e * np.array([math.cos(a), math.sin(a)]), -alpha / self.zc

    def to_disc(self, pts, alpha, disc):
        """Map housing-frame points into the disc frame."""
        c, phi = self.pose(alpha, disc)
        return (pts - c) @ rot(-phi).T

    def ring_clearance(self, alpha, disc):
        """Signed gap (mm) from every ring pin surface to the disc outline at alpha."""
        q = self.to_disc(self.pins, alpha, disc)
        d, _, _ = point_to_polyline(q, self.prof[disc])
        sign = np.where(inside(q, self.prof[disc]), -1.0, 1.0)
        return sign * d - self.rp

    def out_clearance(self, alpha, disc):
        """Radial gap (mm) between each output pin and its disc hole at alpha."""
        c, phi = self.pose(alpha, disc)
        w = self.holes @ rot(phi).T  # output pins turn with the carrier
        q = self.to_disc(w, alpha, disc)
        return self.rwh - self.rwp - np.linalg.norm(q - self.holes, axis=1)

    def max_radius(self, n_alpha=360):
        """Largest housing-frame radius any disc point reaches over one input turn."""
        best = 0.0
        for disc in ("A", "B"):
            p = self.prof[disc]
            for a in np.linspace(0, 2 * math.pi, n_alpha, endpoint=False):
                c, phi = self.pose(a, disc)
                h = p @ rot(phi).T + c
                best = max(best, float(np.max(np.linalg.norm(h, axis=1))))
        return best

    def loads(self, alpha, disc, t_disc):
        """Pin forces for output torque t_disc (n*m) carried by one disc.

        rigid-rotation model: approach at pin i is proportional to the lever
        arm of its contact normal about the disc centre, so F_i = T l_i / sum(l^2)
        over the pins that push the right way. returns a dict with ring and
        output pin forces (n), contact data and the eccentric bearing force (n).
        """
        c, phi = self.pose(alpha, disc)
        q = self.to_disc(self.pins, alpha, disc)
        _, idx, cp = point_to_polyline(q, self.prof[disc])
        n = (q - cp) / np.linalg.norm(q - cp, axis=1, keepdims=True)  # disc -> pin
        # force on disc from pin is -n; lever arm about disc centre (mm)
        lev = cp[:, 0] * (-n[:, 1]) - cp[:, 1] * (-n[:, 0])
        sgn = 1.0  # ring pins push the disc in +z torque (reaction to output)
        load = lev * sgn > 1e-9
        tnmm = t_disc * 1000.0
        f = np.zeros(len(q))
        f[load] = tnmm * lev[load] / np.sum(lev[load] ** 2)
        f_ring = (-n * f[:, None]).sum(axis=0)
        # output pins: disc hole wall pushes pin; pins resist with -z torque on disc
        w = self.holes @ rot(phi).T
        qw = self.to_disc(w, alpha, disc)
        u = (qw - self.holes) / np.linalg.norm(qw - self.holes, axis=1, keepdims=True)
        cw = self.holes + self.rwh * u  # contact point on hole wall (disc frame)
        lev_w = cw[:, 0] * u[:, 1] - cw[:, 1] * u[:, 0]  # torque arm of force +u on disc
        load_w = lev_w < -1e-9
        fw = np.zeros(len(qw))
        fw[load_w] = tnmm * (-lev_w[load_w]) / np.sum(lev_w[load_w] ** 2)
        f_out = (u * fw[:, None]).sum(axis=0)
        f_brg = -(f_ring + f_out)  # eccentric bearing force on disc (disc frame)
        kap = curvature(self.prof[disc])[idx]
        return dict(f_ring=f, ring_loaded=load, kappa=kap, contact=cp, normal=n, lev=lev,
                    f_out=fw, out_loaded=load_w, f_brg=float(np.linalg.norm(f_brg)),
                    f_brg_vec=f_brg, f_ring_sum=f_ring, f_out_sum=f_out)


def hertz_line(f, length, r_eq, e1, nu1, e2, nu2):
    """Peak hertz line-contact pressure (mpa) for force f (n) over length (mm)."""
    e_star = 1.0 / ((1 - nu1 ** 2) / e1 + (1 - nu2 ** 2) / e2)
    return math.sqrt(f * e_star / (math.pi * length * r_eq))
