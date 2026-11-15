"""Independent consumer and validator checks for the versioned sweep contract."""
import copy
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from spraybot_parametric_consumer import sampler, consume
from spraybot_parametric_sweep_validate import validate_sweep
from infinigen2.workpieces.parametric_sweep import export_patches


def fixture():
    corners=[[0,0,0],[1,0,0],[1,1,0.02],[0,1,0]]
    surface={'id':'cell','type':'sweep_quad','domain':{'u':[0,1],'v':[0,1]},
             'periodic_v':False,'geometry':{'corners':corners,'normal':[0,0,1]},
             'provenance':{'primitive':'curve_to_mesh_with_uv','rail_indices':[1,1,2,2],
                           'profile_indices':[1,2,2,1]},
             'mesh_mapping':{'construction_triangle_ids':[0,1],'support_triangle_ids':[0,1]},
             'approximation':{'kind':'source_sweep_sections','mesh_distance_bound_m':0.005002}}
    return surface,np.asarray(corners)[[[0,1,2],[0,2,3]]]


class SweepContractTests(unittest.TestCase):
    def test_support_loop_box_source_bounds(self):
        surface, _ = fixture()
        corners = [[1, -.5, -.5], [1, .5, -.5],
                   [1, .5, .5], [1, -.5, .5]]
        surface['geometry'] = {'corners': corners, 'normal': [1, 0, 0]}
        surface['approximation']['mesh_distance_bound_m'] = 2e-6
        surface['provenance'] = {
            'primitive': 'support_loop_box_subdivision',
            'grid_addresses': [[8, 2, 2], [8, 3, 2], [8, 3, 3], [8, 2, 3]],
            'size_m': [2, 2, 2], 'support_loop_offset_m': [.1, .1, .1],
            'grid_resolution': [4, 4, 4], 'subdivision_level': 1,
            'source_center_m': [0, 0, 0], 'source_axes_m': np.eye(3).tolist(),
        }
        triangles = np.asarray(corners)[[[0, 1, 2], [0, 2, 3]]]
        validate_sweep(surface, triangles)
        surface['provenance']['size_m'] = [1.5, 2, 2]
        with self.assertRaisesRegex(ValueError, 'source envelope'):
            validate_sweep(surface, triangles)

    def test_bevel_checks_twisted_source_quad_surface(self):
        surface, triangles = fixture()
        surface['provenance'] = {
            'primitive':'source_bevel_quad', 'source_constructor':'drawer_body',
            'source_face_id':1, 'source_face_corners':surface['geometry']['corners'],
            'bevel_width_m':.001,
        }
        validate_sweep(surface, triangles)

    def test_uv_sphere_source_sections_reject_wrong_radii(self):
        corners = [[1,0,0],[0,1,0],[0,0,1]]
        normal = (np.ones(3) / np.sqrt(3)).tolist()
        surface = {'id':'sphere_cell', 'type':'sweep_triangle',
                   'domain':{'u':[0,1],'v':[0,1],'constraint':'u+v<=1'},
                   'periodic_v':False,
                   'geometry':{'corners':corners,'normal':normal},
                   'provenance':{'primitive':'uv_sphere_sections','center_m':[0,0,0],
                                 'axes_m':np.eye(3).tolist(),'segments':12,'rings':8,
                                 'source_face_id':1,'rail_indices':[1,2,2],
                                 'profile_indices':[1,2,3]},
                   'mesh_mapping':{'construction_triangle_ids':[0],
                                   'support_triangle_ids':[0]},
                   'approximation':{'kind':'source_sweep_sections',
                                    'mesh_distance_bound_m':2e-6}}
        validate_sweep(surface, np.asarray([corners]))
        surface['provenance']['axes_m'][0][0] = .5
        with self.assertRaisesRegex(ValueError, 'source radii'):
            validate_sweep(surface, np.asarray([corners]))

    def test_removed_degenerate_bevel_face_cannot_claim_final_triangles(self):
        corners = [[0,0,0],[1,0,0],[1,1,0],[0,1,0]]
        record = {'instance_id':1, 'transform':np.eye(4).tolist(),
                  'patches':[None, {'type':'sweep_quad', 'corners':corners,
                                    'source_rail_indices':[1,1,2,2],
                                    'source_profile_indices':[1,2,2,1]}]}
        triangles = np.asarray(corners)[[[0,1,2],[0,2,3]]]
        surfaces = export_patches(record,np.array([0,1]),np.array([2,2]),triangles)
        self.assertEqual(len(surfaces),1)
        with self.assertRaisesRegex(ValueError, 'degenerate bevel face'):
            export_patches(record,np.array([0,1]),np.array([1,2]),triangles)

    def test_removed_bevel_facet_does_not_require_final_triangles(self):
        corners = [[0,0,0],[1,0,0],[1,1,0],[0,1,0]]
        patch = {'type':'sweep_quad', 'corners':corners,
                 'source_rail_indices':[1,1,2,2],
                 'source_profile_indices':[1,2,2,1],
                 'bevel_source_face_id':1,
                 'bevel_source_corners':corners,
                 'bevel_source_primitive':'chair_dining_back',
                 'bevel_width_m':.01}
        record = {'instance_id':1, 'transform':np.eye(4).tolist(),
                  'patches':[patch, patch]}
        triangles = np.asarray(corners)[[[0,1,2],[0,2,3]]]
        surfaces = export_patches(record,np.array([0,1]),np.array([2,2]),triangles)
        self.assertEqual(len(surfaces),1)
        self.assertEqual(surfaces[0]['provenance']['source_constructor'], 'chair_dining_back')

    def test_removed_assembled_source_patch_requires_explicit_contract(self):
        corners = [[0,0,0],[1,0,0],[1,1,0],[0,1,0]]
        patch = {'type':'sweep_quad', 'corners':corners,
                 'source_rail_indices':[1,1,2,2],
                 'source_profile_indices':[1,2,2,1]}
        record = {'instance_id':1, 'transform':np.eye(4).tolist(),
                  'patches':[patch, patch]}
        triangles = np.asarray(corners)[[[0,1,2],[0,2,3]]]
        with self.assertRaisesRegex(ValueError, 'source sweep patch lost'):
            export_patches(record,np.array([0,1]),np.array([2,2]),triangles)
        record['allow_removed_source_patches'] = True
        surfaces = export_patches(record,np.array([0,1]),np.array([2,2]),triangles)
        self.assertEqual(len(surfaces),1)
        self.assertEqual(surfaces[0]['mesh_mapping']['construction_triangle_ids'],[0,1])

    def test_source_cap_triangles_retain_parent_corner_lineage(self):
        corners = [[0,0,0],[1,0,0],[1,1,0],[0,1,0]]
        record = {'instance_id':1, 'transform':np.eye(4).tolist(),
                  'triangulate_source_caps':True,
                  'patches':[{'type':'sweep_cap', 'corners':corners,
                              'source_rail_indices':[1,1,1,1],
                              'source_profile_indices':[1,2,3,4]}]}
        triangles = np.asarray(corners)[[[0,1,2],[0,2,3]]]
        surfaces = export_patches(record,np.array([0,1]),np.array([1,1]),triangles)
        self.assertEqual(len(surfaces),2)
        for surface in surfaces:
            validate_sweep(surface, triangles)
        surfaces[0]['provenance']['source_corner_indices'] = [0,2,3]
        with self.assertRaisesRegex(ValueError, 'source cap triangulation'):
            validate_sweep(surfaces[0], triangles)

    def test_window_source_requires_constructor_controls_and_frame_bounds(self):
        surface, triangles = fixture()
        surface['provenance'] = {
            'primitive':'window_frame_source',
            'source_constructor':'_window_geometry',
            'component':1, 'source_face_id':7,
            'source_to_obj':np.eye(4).tolist(),
            'parameters':{
                'dimensions':[3.0,3.0,3.0],
                'top_profile_height':0.0, 'bottom_profile_height':0.0,
                'frame_width':0.04, 'sub_frame_width':0.02,
                'sub_frame_thickness':0.03,
                'shutter_width':0.04, 'shutter_thickness':0.005,
                'shutter_interval':0.05, 'shutter_rotation':0.0,
                'panel_h_amount':2, 'panel_v_amount':2,
                'sub_panel_h_amount':2, 'sub_panel_v_amount':2,
                'shutter':False,
            },
        }
        validate_sweep(surface, triangles)
        surface['provenance']['parameters']['dimensions'] = [0.1,0.1,0.1]
        with self.assertRaisesRegex(ValueError, 'source dimensions'):
            validate_sweep(surface, triangles)

    def test_source_quad_can_change_diagonal_after_assembly(self):
        corners = [[0,0,0],[1,0,0],[1,1,0],[0,1,0]]
        record = {'instance_id':1, 'transform':np.eye(4).tolist(),
                  'patches':[{'type':'sweep_split_quad', 'corners':corners,
                              'source_rail_indices':[1,1,2,2],
                              'source_profile_indices':[1,2,2,1],
                              'splits':[{'corners':[corners[i] for i in tri]}
                                        for tri in ((0,1,3),(1,2,3))]}]}
        triangles = np.asarray(corners)[[[0,1,2],[0,2,3]]]
        surfaces = export_patches(record,np.array([0,1]),np.array([1,1]),triangles)
        self.assertEqual(len(surfaces),2)
        self.assertEqual([s['mesh_mapping']['construction_triangle_ids'] for s in surfaces],[[0],[1]])
        for surface in surfaces:
            validate_sweep(surface, triangles)

    def test_bevel_patch_requires_source_face_and_width(self):
        surface, triangles = fixture()
        surface['provenance'] = {'primitive': 'storage_cell_shelf_bevel',
            'source_face_id': 7, 'source_face_corners': [[0,0,0],[1,0,0],[1,1,0],[0,1,0]],
            'bevel_width_m': .03}
        validate_sweep(surface, triangles)
        surface['provenance']['bevel_width_m'] = .001
        with self.assertRaisesRegex(ValueError, 'exceeds source width'):
            validate_sweep(surface, triangles)

    def test_shared_bevel_patch_names_its_source_constructor(self):
        surface, triangles = fixture()
        surface['provenance'] = {'primitive': 'source_bevel_quad',
            'source_constructor': 'chair_dining_seat', 'source_face_id': 7,
            'source_face_corners': [[0,0,0],[1,0,0],[1,1,0],[0,1,0]],
            'bevel_width_m': .03}
        validate_sweep(surface, triangles)
        del surface['provenance']['source_constructor']
        with self.assertRaisesRegex(ValueError, 'invalid bevel source provenance'):
            validate_sweep(surface, triangles)

    def test_welded_source_quad_triangle_provenance(self):
        surface, _ = fixture()
        corners = [[0,0,0], [1,0,0], [1,.5,0]]
        surface['type'] = 'sweep_triangle'
        surface['domain']['constraint'] = 'u+v<=1'
        surface['geometry']['corners'] = corners
        surface['provenance'] = {
            'primitive': 'curve_to_mesh_with_uv',
            'rail_indices': [2.,2.,3.], 'profile_indices': [8.,9.,9.],
            'source_quad_split': True,
            'source_quad_rail_indices': [2.,2.,3.,3.],
            'source_quad_profile_indices': [8.,9.,9.,8.],
        }
        surface['mesh_mapping'] = {'construction_triangle_ids':[0], 'support_triangle_ids':[0]}
        surface['approximation']['mesh_distance_bound_m'] = 2e-6
        validate_sweep(surface, np.asarray([corners]))
        surface['provenance']['source_quad_profile_indices'] = [8.,8.,8.,8.]
        with self.assertRaisesRegex(ValueError, 'source quad split'):
            validate_sweep(surface, np.asarray([corners]))

    def test_ruled_grid_uses_same_bilinear_consumer(self):
        surface, triangles = fixture()
        surface['provenance'] = {'primitive': 'ruled_grid_extrusion',
                                 'grid_addresses': [[1,1,1],[2,1,1],[2,2,1],[1,2,1]]}
        validate_sweep(surface, triangles)
        _, _, _, evaluate = sampler(surface)
        np.testing.assert_allclose(evaluate(.5,.5)[0], [.5,.5,.005])

    def test_ruled_grid_rejects_cut_or_interpolated_lineage(self):
        for addresses in (
            [[1,1,1],[3,1,1],[3,2,1],[1,2,1]],
            [[1,1,1],[1.5,1,1],[1.5,2,1],[1,2,1]],
            [[1,1,1],[2,1,1],[2,2,2],[1,2,1]],
        ):
            with self.subTest(addresses=addresses):
                surface, triangles = fixture()
                surface['provenance'] = {'primitive': 'ruled_grid_extrusion',
                                         'grid_addresses': addresses}
                with self.assertRaisesRegex(ValueError, 'ruled-grid'):
                    validate_sweep(surface, triangles)

    def test_twisted_cell_point_and_normal(self):
        surface, triangles=fixture()
        ids,angle=validate_sweep(surface,triangles)
        self.assertEqual(ids,[0,1]);self.assertGreater(angle,0)
        _,_,_,evaluate=sampler(surface)
        point,normal=evaluate(.5,.5)
        np.testing.assert_allclose(point,[.5,.5,.005])
        np.testing.assert_allclose(normal,np.asarray([-.01,-.01,1])/np.linalg.norm([-.01,-.01,1]))

    def test_error_bound_is_not_a_license_to_move_controls(self):
        surface,triangles=fixture()
        triangles[0,0,2]=.001
        with self.assertRaisesRegex(ValueError,'vertices disagree'):
            validate_sweep(surface,triangles)

    def test_missing_half_cell_fails(self):
        surface,triangles=fixture()
        surface['mesh_mapping']={'construction_triangle_ids':[0],'support_triangle_ids':[0]}
        with self.assertRaisesRegex(ValueError,'coverage'):
            validate_sweep(surface,triangles)

    def test_false_error_bound_fails(self):
        surface,triangles=fixture()
        surface['approximation']['mesh_distance_bound_m']=1
        with self.assertRaisesRegex(ValueError,'bound'):
            validate_sweep(surface,triangles)

    def test_reversed_mesh_fails(self):
        surface,triangles=fixture()
        with self.assertRaisesRegex(ValueError,'orientation'):
            validate_sweep(surface,triangles[:,::-1])

    def test_convex_cap(self):
        surface,triangles=fixture()
        corners=np.asarray(surface['geometry']['corners']);corners[:,2]=0
        surface['geometry']['corners']=corners.tolist();surface['type']='sweep_cap';surface['periodic_v']=True
        surface['provenance']['rail_indices']=[1,1,1,1]
        surface['approximation']['mesh_distance_bound_m']=2e-6
        validate_sweep(surface,corners[[[0,1,2],[0,2,3]]])
        _,_,_,evaluate=sampler(surface)
        np.testing.assert_allclose(evaluate(0,.9)[0],[.5,.5,0])
        np.testing.assert_allclose(evaluate(1,0)[0],[0,0,0])

    def test_collapsed_sweep_pole(self):
        surface,_=fixture()
        corners=[[0,0,0],[1,0,0],[.5,1,0]]
        surface['type']='sweep_triangle'
        surface['domain']['constraint']='u+v<=1'
        surface['geometry']['corners']=corners
        surface['provenance']['rail_indices']=[1.5,1.,2.]
        surface['provenance']['profile_indices']=[1.,2.,2.]
        surface['mesh_mapping']={'construction_triangle_ids':[0],'support_triangle_ids':[0]}
        surface['approximation']['mesh_distance_bound_m']=2e-6
        validate_sweep(surface,np.asarray([corners]))
        _,_,_,evaluate=sampler(surface)
        np.testing.assert_allclose(evaluate(.2,.3)[0],[.35,.3,0])

    def test_small_cap_allows_source_coordinate_rounding(self):
        surface,_=fixture()
        corners=[[0,0,0],[0.002,0,0],[0.001,0.001,0]]
        surface['type']='sweep_triangle'
        surface['domain']['constraint']='u+v<=1'
        surface['geometry']['corners']=corners
        surface['provenance']['rail_indices']=[1.5,1.,2.]
        surface['provenance']['profile_indices']=[1.,2.,2.]
        surface['mesh_mapping']={'construction_triangle_ids':[0],'support_triangle_ids':[0]}
        surface['approximation']['mesh_distance_bound_m']=2e-6
        rounded=np.asarray([corners],dtype=float)
        rounded[0,2,1]-=1e-7
        validate_sweep(surface,rounded)

    def test_version_requires_v3(self):
        surface,_=fixture()
        bundle={'schema':'spraybot.parametric-candidate.v2','unit':'m','frame':'exported_obj_axes_origin',
                'parts':[{'id':'base','surfaces':[surface]}]}
        with self.assertRaisesRegex(ValueError,'schema version'):
            consume(bundle)
        bundle['schema']='spraybot.parametric-candidate.v3'
        self.assertGreater(len(consume(bundle)),0)


if __name__=='__main__':
    unittest.main()
