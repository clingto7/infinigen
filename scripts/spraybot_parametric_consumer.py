#!/usr/bin/env python3
"""Source-independent sampler for the workpiece parametric candidate.

Standard library only. Reads no Infinigen code, mesh data, or prior samplers.
"""
import json
import math
import sys
from pathlib import Path

SPACING_M = 0.009999


def vector(value):
    if not isinstance(value, list) or len(value) != 3 or any(
        isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
        for x in value
    ):
        raise ValueError('Expected finite 3-vector')
    return value


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def scale(a, factor):
    return [factor * x for x in a]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    length = norm(a)
    if not math.isfinite(length) or length <= 1e-12:
        raise ValueError('Undefined normal')
    return scale(a, 1/length)


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def intervals(bound, minimum=1):
    if not math.isfinite(bound) or bound < 0:
        raise ValueError('Invalid surface dimension')
    return max(minimum, math.ceil(bound / SPACING_M))


def circular(x, y, theta):
    return add(scale(x, math.cos(theta)), scale(y, math.sin(theta)))


def section(data):
    return (vector(data['center']), vector(data['radial_u']), vector(data['radial_v']))


def sampler(surface):
    kind, g = surface['type'], surface['geometry']
    expected_domain = {'u': [0, 1], 'v': [0, 1]}
    if kind in ('plane_triangle','sweep_triangle'):
        expected_domain['constraint'] = 'u+v<=1'
    if surface['domain'] != expected_domain:
        raise ValueError('Unsupported parameter domain')
    if surface['periodic_v'] != (kind not in ('plane_rectangle', 'plane_triangle', 'sweep_quad', 'sweep_triangle')):
        raise ValueError('Wrong periodicity')
    if kind in ('plane_rectangle', 'plane_triangle'):
        o, x, y, n = (vector(g[k]) for k in ('origin', 'u', 'v', 'normal'))
        if norm(x) <= 0 or norm(y) <= 0 or abs(dot(x, y)) > 1e-6*norm(x)*norm(y):
            raise ValueError('Invalid plane basis')
        if abs(norm(n)-1) > 1e-5 or abs(dot(n,x)) > 1e-5*norm(x) or abs(dot(n,y)) > 1e-5*norm(y):
            raise ValueError('Invalid plane normal')
        nu, nv = intervals(norm(x)), intervals(norm(y))

        def evaluate(u, v):
            return add(add(o, scale(x, u)), scale(y, v)), n

    elif kind == 'sweep_triangle':
        a,b,c=(vector(p) for p in g['corners'])
        x,y=sub(b,a),sub(c,a)
        normal=unit(cross(x,y))
        nu,nv=intervals(norm(x)),intervals(norm(y))
        def evaluate(u,v):
            return add(add(a,scale(x,u)),scale(y,v)),normal

    elif kind in ('sweep_quad', 'sweep_cap'):
        corners = [vector(p) for p in g['corners']]
        n = unit(vector(g['normal']))
        if len(corners) < 3 or (kind == 'sweep_quad' and len(corners) != 4):
            raise ValueError('Invalid source sweep control points')
        if kind == 'sweep_quad':
            a,b,c,d = corners
            e,f,t = sub(b,a), sub(d,a), add(sub(a,b),sub(c,d))
            nu = intervals(max(norm(e),norm(sub(c,d))))
            nv = intervals(max(norm(f),norm(sub(c,b))))
            def evaluate(u,v):
                point = add(add(add(a,scale(e,u)),scale(f,v)),scale(t,u*v))
                normal = unit(cross(add(e,scale(t,v)),add(f,scale(t,u))))
                if dot(normal,n) <= 0:
                    raise ValueError('Folded source sweep cell')
                return point,normal
        else:
            center = scale([sum(p[i] for p in corners) for i in range(3)],1/len(corners))
            nu = intervals(max(norm(sub(p,center)) for p in corners))
            nv = len(corners)*intervals(max(norm(sub(corners[(i+1)%len(corners)],p)) for i,p in enumerate(corners)))
            def evaluate(u,v):
                q = (v % 1)*len(corners)
                index = int(q)
                edge = add(scale(corners[index],1-(q-index)),scale(corners[(index+1)%len(corners)],q-index))
                return add(center,scale(sub(edge,center),u)),n

    elif kind in ('cylinder_side', 'disk'):
        o, a, x, y = (vector(g[k]) for k in ('origin', 'axis', 'radial_u', 'radial_v'))
        r, length = g['radius_m'], g['length_m']
        if not all(isinstance(z, (int,float)) and not isinstance(z, bool) and math.isfinite(z) and z > 0 for z in (r,length)):
            raise ValueError('Invalid rod dimensions')
        if any(abs(norm(z)-1) > 1e-5 for z in (a,x,y)) or any(abs(dot(i,j)) > 1e-5 for i,j in ((a,x),(a,y),(x,y))):
            raise ValueError('Invalid rod frame')
        nv = intervals(2*math.pi*r*(norm(x)+norm(y)), minimum=3)
        if kind == 'cylinder_side':
            nu = intervals(length*norm(a))

            def evaluate(u, v):
                radial = circular(x, y, math.tau*v)
                return add(add(o, scale(a, u*length)), scale(radial, r)), unit(radial)
        else:
            fraction, sign = g['axial_fraction'], g['normal_sign']
            if fraction not in (0,1) or sign not in (-1,1):
                raise ValueError('Invalid disk position or normal sign')
            center = add(o, scale(a, fraction*length))
            normal = scale(a, sign)
            nu = intervals(r*(norm(x)+norm(y)))

            def evaluate(u, v):
                return add(center, scale(circular(x, y, math.tau*v), u*r)), normal

    elif kind == 'section_loft':
        if len(g['sections']) != 2 or g['orientation'] not in (-1,1):
            raise ValueError('Invalid loft sections or orientation')
        c0, x0, y0 = section(g['sections'][0])
        c1, x1, y1 = section(g['sections'][1])
        dc, dx, dy = sub(c1,c0), sub(x1,x0), sub(y1,y0)
        nu = intervals(norm(dc)+norm(dx)+norm(dy))
        nv = intervals(2*math.pi*max(norm(x0)+norm(y0), norm(x1)+norm(y1)), minimum=3)

        def evaluate(u, v):
            theta = math.tau*v
            x, y = add(x0,scale(dx,u)), add(y0,scale(dy,u))
            radial = circular(x,y,theta)
            point = add(add(c0,scale(dc,u)),radial)
            tu = add(dc,circular(dx,dy,theta))
            tt = add(scale(x,-math.sin(theta)),scale(y,math.cos(theta)))
            return point, scale(unit(cross(tt,tu)),g['orientation'])

    elif kind == 'section_disk':
        c,x,y = section(g['section'])
        normal = vector(g['normal'])
        if abs(norm(normal)-1)>1e-5:
            raise ValueError('Invalid disk normal')
        nu = intervals(norm(x)+norm(y))
        nv = intervals(2*math.pi*(norm(x)+norm(y)),minimum=3)

        def evaluate(u, v):
            return add(c,scale(circular(x,y,math.tau*v),u)),normal
    else:
        raise ValueError(f'Unsupported surface type: {kind}')
    return kind,nu,nv,evaluate


def csg_strokes(part_id, surface):
    """Raster the Boolean trim loops in the recorded source-face plane."""
    g, domain = surface['geometry'], surface['domain']
    origin, axis_u, axis_v, normal = (vector(g[key]) for key in ('origin', 'u', 'v', 'normal'))
    if (domain.get('u') != [0, 1] or domain.get('v') != [0, 1]
        or surface.get('periodic_v') is not False or
        abs(norm(normal) - 1) > 1e-5):
        raise ValueError('Invalid CSG trimmed face domain')
    loops = domain['loops']
    if not loops:
        raise ValueError('CSG trimmed face has no loops')
    count = intervals(norm(axis_u))
    result = []
    scanlines = {(i + 0.5) / count for i in range(count)}
    for loop in loops:
        if loop.get('role') == 'outer':
            values = [point[0] for point in loop['points']]
            scanlines.add((min(values) + max(values)) * 0.5)
    for u in sorted(scanlines):
        crossings = []
        for loop in loops:
            points = loop['points']
            for a, b in zip(points, points[1:] + points[:1]):
                if (a[0] <= u < b[0]) or (b[0] <= u < a[0]):
                    crossings.append(a[1] + (u - a[0]) * (b[1] - a[1]) / (b[0] - a[0]))
        crossings.sort()
        if len(crossings) % 2:
            raise ValueError('CSG trim scanline has odd intersections')
        for start, end in zip(crossings[::2], crossings[1::2]):
            if end - start < 1e-10:
                continue
            steps = intervals((end - start) * norm(axis_v))
            stroke = {'part_id': part_id, 'surface_id': surface['id'],
                      'points': [], 'normals': [], 'parameters': []}
            for j in range(steps + 1):
                v = start + (end - start) * j / steps
                stroke['points'].append(add(add(origin, scale(axis_u, u)), scale(axis_v, v)))
                stroke['normals'].append(normal)
                stroke['parameters'].append([u, v])
            result.append(stroke)
    if not result:
        raise ValueError('CSG trimmed face produced no trajectory samples')
    return result


def consume(bundle):
    if bundle.get('schema') not in ('spraybot.parametric-candidate.v1', 'spraybot.parametric.v1', 'spraybot.parametric-candidate.v2', 'spraybot.parametric.v2', 'spraybot.parametric-candidate.v3', 'spraybot.parametric.v3', 'spraybot.parametric-candidate.v4', 'spraybot.parametric.v4', 'spraybot.parametric-candidate.v5', 'spraybot.parametric.v5', 'spraybot.parametric-candidate.v6', 'spraybot.parametric.v6') or bundle.get('unit') != 'm' or bundle.get('frame') != 'exported_obj_axes_origin':
        raise ValueError('Unsupported bundle, unit or frame')
    strokes = []
    part_ids, surface_ids = set(),set()
    for part in bundle['parts']:
        pid=part['id']
        if pid in part_ids:
            raise ValueError('Duplicate part ID')
        part_ids.add(pid)
        for surface in part['surfaces']:
            allowed = {'plane_rectangle', 'cylinder_side', 'disk'}
            if bundle['schema'].endswith(('.v2', '.v3')):
                allowed.add('plane_triangle')
            if bundle['schema'].endswith(('.v3', '.v5', '.v6')):
                allowed.update({'sweep_quad','sweep_cap','sweep_triangle'})
            if bundle['schema'].endswith('.v4'):
                allowed.add('csg_trimmed_face')
            if surface['type'] not in allowed:
                raise ValueError('Unsupported surface type for schema version')
            sid=surface['id']
            if sid in surface_ids:
                raise ValueError('Duplicate surface ID')
            surface_ids.add(sid)
            if surface['type'] == 'csg_trimmed_face':
                strokes.extend(csg_strokes(pid, surface))
                continue
            kind,nu,nv,evaluate=sampler(surface)
            for i in range(nu+1):
                u=i/nu
                if kind in ('plane_triangle','sweep_triangle'):
                    count = 1 if i == nu else math.ceil(nv * (1-u)) + 1
                else:
                    count=1 if kind in ('disk','section_disk','sweep_cap') and i==0 else nv+1
                stroke={'part_id':pid,'surface_id':sid,'points':[],'normals':[],'parameters':[]}
                for j in range(count):
                    v=(1-u)*j/(count-1) if kind in ('plane_triangle','sweep_triangle') and count > 1 else (0 if kind in ('plane_triangle','sweep_triangle') else j/nv)
                    # Preserve the v=1 parameter while evaluating the seam at theta=0.
                    point,normal=evaluate(u,0 if kind not in ('plane_rectangle', 'plane_triangle', 'sweep_quad', 'sweep_triangle') and j==nv else v)
                    stroke['points'].append(point)
                    stroke['normals'].append(normal)
                    stroke['parameters'].append([u,v])
                strokes.append(stroke)
    return strokes


if __name__=='__main__':
    if len(sys.argv)!=3:
        raise SystemExit('Usage: spraybot_parametric_consumer.py PARAMETRIC.json PATHS.json')
    bundle=json.loads(Path(sys.argv[1]).read_text())
    Path(sys.argv[2]).write_text(json.dumps(consume(bundle),allow_nan=False,separators=(',',':'))+'\n')
