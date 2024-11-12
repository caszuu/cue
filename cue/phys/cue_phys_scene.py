from dataclasses import dataclass
from .cue_phys_types import PhysRay, PhysRayHit, PhysAABB, PhysHalfPlanes

# a collection of colliders which can be tested agains at once

@dataclass(init=False, slots=True)
class PhysScene:
    def __init__(self) -> None:
        self.scene_aabbs = []
        self.scene_planes = []

    # == scene mutation api ==

    def add_coll(self, coll: PhysAABB | PhysHalfPlanes) -> None:
        if isinstance(coll, PhysAABB):
            self.scene_aabbs.append(coll)
        elif isinstance(coll, PhysHalfPlanes):
            self.scene_planes.append(coll)
        else:
            raise TypeError(f"unsupported collider type {type(coll)}")

    def remove_coll(self, coll: PhysAABB | PhysHalfPlanes) -> None:
        if isinstance(coll, PhysAABB):
            self.scene_aabbs.remove(coll)
        elif isinstance(coll, PhysHalfPlanes):
            self.scene_planes.remove(coll)
        else:
            raise TypeError(f"unsupported collider type {type(coll)}")

    # == scene test api ==

    # return first (distance wise) hit in the scene
    def first_hit(self, ray: PhysRay, tmax = float('inf')) -> PhysRayHit | None:
        closest_hit = None

        # aabb pass

        box_ray_cast = PhysAABB.ray_cast
        for box in self.scene_aabbs:
            hit = box_ray_cast(box, ray, tmax)
            
            if isinstance(hit, PhysRayHit):
                closest_hit = hit
                tmax = hit.tmin

        # plane pass

        plane_ray_cast = PhysHalfPlanes.ray_cast
        for plane in self.scene_planes:
            hit = plane_ray_cast(plane, ray, tmax)

            if isinstance(hit, PhysRayHit):
                closest_hit = hit
                tmax = hit.tmin

        return closest_hit

    # return all collider hits in the scene (returns an empty list on no hits)
    def all_hits(self, ray: PhysRay, tmax = float('inf')) -> list[PhysRayHit]:
        hits = []

        # aabb pass

        box_ray_cast = PhysAABB.ray_cast
        for box in self.scene_aabbs:
            hit = box_ray_cast(box, ray, tmax)
            
            if isinstance(hit, PhysRayHit):
                hits.append(hit)

        # plane pass

        plane_ray_cast = PhysHalfPlanes.ray_cast
        for plane in self.scene_planes:
            hit = plane_ray_cast(plane, ray, tmax)

            if isinstance(hit, PhysRayHit):
                hits.append(hit)

        return hits

    scene_aabbs: list[PhysAABB]
    scene_planes: list[PhysHalfPlanes]