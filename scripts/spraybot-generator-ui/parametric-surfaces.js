// Source-independent point/normal evaluation for parameter overlay rendering.
const add=(a,b)=>a.map((x,i)=>x+b[i]);
const sub=(a,b)=>a.map((x,i)=>x-b[i]);
const scale=(a,s)=>a.map(x=>x*s);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const unit=a=>{const n=Math.hypot(...a);if(n<1e-12)throw Error('Degenerate parametric normal');return scale(a,1/n);};
export function evaluateSurface(surface,u,v){
  const g=surface.geometry;
  if(['plane_rectangle','plane_triangle','csg_trimmed_face'].includes(surface.type))return [add(add(g.origin,scale(g.u,u)),scale(g.v,v)),g.normal];
  if(surface.type==='sweep_quad'){
    const [a,b,c,d]=g.corners,e=sub(b,a),f=sub(d,a),t=add(sub(a,b),sub(c,d));
    return [add(add(add(a,scale(e,u)),scale(f,v)),scale(t,u*v)),unit(cross(add(e,scale(t,v)),add(f,scale(t,u))))];
  }
  if(surface.type==='sweep_triangle'){
    const [a,b,c]=g.corners,x=sub(b,a),y=sub(c,a);return [add(add(a,scale(x,u)),scale(y,v)),unit(cross(x,y))];
  }
  if(surface.type==='sweep_cap'){
    const c=g.corners,n=c.length,center=scale(c.reduce(add,[0,0,0]),1/n),q=((v%1)+1)%1*n,i=Math.floor(q);
    const boundary=add(scale(c[i],1-(q-i)),scale(c[(i+1)%n],q-i));
    return [add(center,scale(sub(boundary,center),u)),g.normal];
  }
  if(['cylinder_side','disk'].includes(surface.type)){
    const radial=add(scale(g.radial_u,Math.cos(2*Math.PI*v)),scale(g.radial_v,Math.sin(2*Math.PI*v)));
    if(surface.type==='cylinder_side')return [add(add(g.origin,scale(g.axis,u*g.length_m)),scale(radial,g.radius_m)),unit(radial)];
    return [add(add(g.origin,scale(g.axis,g.axial_fraction*g.length_m)),scale(radial,u*g.radius_m)),scale(g.axis,g.normal_sign)];
  }
  throw Error(`Unsupported parametric surface: ${surface.type}`);
}
