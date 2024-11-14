from dataclasses import dataclass

from pygame.math import Vector3 as Vec3
import numpy as np

# base cue types for the phys system

@dataclass(slots=True)
class PhysRay:
    o: np.ndarray # ray origin
    d: np.ndarray # ray direction
    d_inv: np.ndarray # inverse of ray dir

    b: np.ndarray # ray box (sized ray)

    @classmethod
    def make(cls, origin: Vec3, dir: Vec3, box: Vec3 = Vec3(0., 0., 0.)) -> 'PhysRay':
        return cls(
            o = np.array(origin, dtype=np.float32),
            d = np.array(dir, dtype=np.float32),
            d_inv = 1 / np.array(dir, dtype=np.float32),
            b = np.array(box / 2, dtype=np.float32),
        )

@dataclass(slots=True)
class PhysRayHit:
    pos: np.ndarray
    norm: np.ndarray

    tmin: float
    tout: float

# == aabb ==

aabb_normal_lookup_table = [
    np.array([1, 0, 0], dtype=np.float32),
    np.array([0, 1, 0], dtype=np.float32),
    np.array([0, 0, 1], dtype=np.float32),

    np.array([-1, 0, 0], dtype=np.float32),
    np.array([0, -1, 0], dtype=np.float32),
    np.array([0, 0, -1], dtype=np.float32),
]

EPSILON = np.float32(1e-5)

@dataclass(slots=True)
class PhysAABB:
    points: np.ndarray

    @classmethod
    def make(cls, pos: Vec3, size: Vec3) -> 'PhysAABB':
        return cls(
            points = np.array((pos - size / 2, pos + size / 2), dtype=np.float32)
        )

    def _find_hit_norm(self, ray_pos: np.ndarray, ray_dir: np.ndarray, ray_box: np.ndarray) -> np.ndarray:
        tmax = float('inf')
        face_index = None
        
        # min pass

        p0 = self.points[0] - ray_box
        for d in range(3):
            denom = np.dot(aabb_normal_lookup_table[d], ray_dir)
            if denom > EPSILON:
                t = np.dot(p0 - ray_pos, aabb_normal_lookup_table[d])
                if t >= -EPSILON and tmax > t:
                    tmax = t
                    face_index = d

        # max pass

        p0 = self.points[1] + ray_box
        for d in range(3, 6):
            denom = np.dot(aabb_normal_lookup_table[d], ray_dir)
            if denom > EPSILON:
                t = np.dot(p0 - ray_pos, aabb_normal_lookup_table[d])
                if t >= -EPSILON and tmax > t:
                    tmax = t
                    face_index = d

        # TODO: still encoutered when inside the aabb.. but why
        if face_index is None:
            face_index = 0

        return -aabb_normal_lookup_table[face_index]

    def ray_cast(self, ray: PhysRay, tmax: float) -> PhysRayHit | None:
        tmin = 0.
        tout = -float('inf')

        min_points = self.points[0] - ray.b
        max_points = self.points[1] + ray.b

        for d in range(3):
            t1 = (min_points[d] - ray.o[d]) * ray.d_inv[d]
            t2 = (max_points[d] - ray.o[d]) * ray.d_inv[d]
            
            tmin = max(tmin, min(t1, t2))
            tout = max(tout, min(t1, t2))
            tmax = min(tmax, max(t1, t2))

        if tmin < tmax:
            hit_pos = ray.o + ray.d * tmin
            return PhysRayHit(hit_pos, self._find_hit_norm(hit_pos, ray.d, ray.b), tmin, tout)

    def aabb_intersect(self, other_box: 'PhysAABB') -> bool:
        return all(self.points[0] <= other_box.points[1]) and all(self.points[1] >= other_box.points[0])

@dataclass(slots=True)
class PhysHalfPlanes:
    # 2-dim arrays -> array of 3D vecs
    plane_pos_buf: np.ndarray
    plane_dir_buf: np.ndarray

    plane_count: int

    # @classmethod
    # def make(cls, )

    def ray_cast(self, ray: PhysRay, tmax: float) -> PhysRayHit | None:
        return None