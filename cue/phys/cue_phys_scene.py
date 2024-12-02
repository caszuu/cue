from dataclasses import dataclass
from .cue_phys_types import PhysRay, PhysRayHit, PhysAABB, PhysHalfPlanes

import numpy as np
from pygame.math import Vector3 as Vec3

# a collection of colliders which can be tested agains at once

@dataclass(init=False, slots=True)
class PhysScene:
    def __init__(self, sub_id: str = "") -> None:
        self.sub_id = sub_id
        self.reset()
    
    def reset(self) -> None:
        self.scene_aabbs = []
        self.scene_planes = []

        self.child_subscenes = {}
        self.sub_aabb = None

    # == scene mutation api ==

    def add_coll(self, coll: PhysAABB | PhysHalfPlanes) -> None:
        if not self.sub_id.startswith(self.sub_id):
            raise ValueError(f"wrong phys subscene. (local sub_id: {self.sub_id}; wanted sub_id: {coll.sub_id})")
        
        next_id = coll.sub_id[len(self.sub_id):]
        if next_id:
            # collider is in a child subscene, forward it

            next_sub_id = next_id.split('.', 1)[0] + '.'

            subscene = self.child_subscenes.get(next_sub_id, None)

            if subscene is None:
                subscene = PhysScene(self.sub_id + next_sub_id)
                self.child_subscenes[next_sub_id] = subscene

            subscene.add_coll(coll)

            self.sub_aabb = None # invalidate sub_aabb
            return

        # add collider to this scene

        if isinstance(coll, PhysAABB):
            self.scene_aabbs.append(coll)
        elif isinstance(coll, PhysHalfPlanes):
            self.scene_planes.append(coll)
        else:
            raise TypeError(f"unsupported collider type {type(coll)}")

        self.sub_aabb = None # invalidate sub_aabb

    def remove_coll(self, coll: PhysAABB | PhysHalfPlanes) -> None:
        if not self.sub_id.startswith(self.sub_id):
            raise ValueError(f"wrong phys subscene. (local sub_id: {self.sub_id}; wanted sub_id: {coll.sub_id})")
        
        next_id = coll.sub_id[len(self.sub_id):]
        if next_id:
            # collider is in a child subscene, forward it

            next_sub_id = next_id.split('.', 1)[0] + '.'

            subscene = self.child_subscenes[next_sub_id]
            subscene.remove_coll(coll)
            
            # cleanup child scene if empty
            if (not subscene.scene_aabbs) and (not subscene.scene_planes) and (not subscene.child_subscenes):
                self.child_subscenes.pop(next_sub_id)
            
            self.sub_aabb = None # invalidate sub_aabb
            return

        if isinstance(coll, PhysAABB):
            self.scene_aabbs.remove(coll)
        elif isinstance(coll, PhysHalfPlanes):
            self.scene_planes.remove(coll)
        else:
            raise TypeError(f"unsupported collider type {type(coll)}")

        self.sub_aabb = None # invalidate sub_aabb

    # update subscene global aabbs, needed after a collider update
    def update_coll(self, coll: PhysAABB | PhysHalfPlanes) -> None:
        if not self.sub_id.startswith(self.sub_id):
            raise ValueError(f"wrong phys subscene. (local sub_id: {self.sub_id}; wanted sub_id: {coll.sub_id})")

        next_id = coll.sub_id[len(self.sub_id):]
        if next_id:
            # collider is in a child subscene, forward it

            next_sub_id = next_id.split('.', 1)[0] + '.'

            subscene = self.child_subscenes[next_sub_id]
            subscene.update_coll(coll)
            
        self.sub_aabb = None # invalidate sub_aabb

    def _recalc_sub_aabb(self):
        if self.sub_aabb is not None:
            return

        min_points = []
        max_points = []

        # aabbs

        for box in self.scene_aabbs:
            min_points.append(box.points[0])
            max_points.append(box.points[1])

        # planes
        # TODO: add plane aabb calc

        # child subscenes

        for subscene in self.child_subscenes.values():
            subscene._recalc_sub_aabb()

            min_points.append(subscene.sub_aabb.points[0])
            max_points.append(subscene.sub_aabb.points[1])
        
        # calc final scene aabb

        if not min_points:
            # scene empty, make dummy aabb

            self.sub_aabb = PhysAABB.make(Vec3(), Vec3(), None)
            return

        min_buf = np.vstack(min_points)
        max_buf = np.vstack(max_points)

        self.sub_aabb = PhysAABB(points=np.array(((np.min(min_buf[:,0]), np.min(min_buf[:,1]), np.min(min_buf[:,2])), (np.max(max_buf[:,0]), np.max(max_buf[:,1]), np.max(max_buf[:,2]))), dtype=np.float32))

    # == scene test api ==

    # return first (distance wise) hit in the scene
    def first_hit(self, ray: PhysRay, tmax = float('inf')) -> PhysRayHit | None:
        closest_hit = None

        # subscene global aabb test
        self._recalc_sub_aabb()
        if self.sub_aabb.ray_cast(ray, tmax) is None:
            return None

        # aabb pass

        box_ray_cast = PhysAABB.ray_cast
        for box in self.scene_aabbs:
            hit = box_ray_cast(box, ray, tmax)
            
            if hit is not None:
                closest_hit = hit
                tmax = hit.tmin

        # plane pass

        plane_ray_cast = PhysHalfPlanes.ray_cast
        for plane in self.scene_planes:
            hit = plane_ray_cast(plane, ray, tmax)

            if hit is not None:
                closest_hit = hit
                tmax = hit.tmin

        # test child subscenes

        scene_first_hit = PhysScene.first_hit
        for subscene in self.child_subscenes.values():
            hit = scene_first_hit(subscene, ray, tmax)

            if hit is not None:
                closest_hit = hit
                tmax = hit.tmin

        return closest_hit

    # return all collider hits in the scene (returns an empty list on no hits)
    def all_hits(self, ray: PhysRay, tmax = float('inf')) -> list[PhysRayHit]:
        hits = []

        # subscene global aabb test
        self._recalc_sub_aabb()
        if self.sub_aabb.ray_cast(ray, tmax) is None:
            return []

        # aabb pass

        box_ray_cast = PhysAABB.ray_cast
        for box in self.scene_aabbs:
            hit = box_ray_cast(box, ray, tmax)
            
            if hit is not None:
                hits.append(hit)

        # plane pass

        plane_ray_cast = PhysHalfPlanes.ray_cast
        for plane in self.scene_planes:
            hit = plane_ray_cast(plane, ray, tmax)

            if hit is not None:
                hits.append(hit)

        # test child subscenes

        scene_all_hits = PhysScene.all_hits
        for subscene in self.child_subscenes.values():
            for hit in scene_all_hits(subscene, ray, tmax):
                hits.append(hit)

        return hits

    scene_aabbs: list[PhysAABB]
    scene_planes: list[PhysHalfPlanes]

    child_subscenes: dict[str, 'PhysScene']
    
    sub_id: str
    sub_aabb: PhysAABB | None