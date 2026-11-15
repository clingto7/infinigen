"""Keep one native ChairFactory recipe per source part in v6 bundles."""

from __future__ import annotations


_RECIPE_FIELDS = ('constructor', 'parameters', 'source_to_obj')


def _source(provenance):
    if provenance.get('primitive') == 'native_chair_constructor':
        return provenance
    if provenance.get('primitive') == 'source_cap_triangulation':
        return provenance.get('native_chair_source')
    return None


def compact(bundle):
    if bundle.get('schema') != 'spraybot.parametric.v3':
        raise ValueError('native chair requires source sweep patches')
    for part in bundle['parts']:
        recipe = None
        for surface in part['surfaces']:
            provenance = surface['provenance']
            source = _source(provenance)
            if source is None:
                raise ValueError('native chair part contains another primitive')
            current = {key: source[key] for key in _RECIPE_FIELDS}
            if recipe is None:
                recipe = current
            elif recipe != current:
                raise ValueError('native chair source part mixes constructor recipes')
            for key in _RECIPE_FIELDS:
                del source[key]
            source['recipe_scope'] = 'part'
        part['source_recipe'] = recipe
    bundle['schema'] = 'spraybot.parametric.v6'
    return bundle


def expand_surface(surface, recipe):
    if not isinstance(recipe, dict) or set(recipe) != set(_RECIPE_FIELDS):
        raise ValueError('native chair part lacks source recipe')
    clone = {**surface, 'provenance': {**surface['provenance']}}
    provenance = clone['provenance']
    source = _source(provenance)
    if source is None or source.get('recipe_scope') != 'part':
        raise ValueError('native chair surface lacks part recipe reference')
    if source is not provenance:
        source = {**source}
        provenance['native_chair_source'] = source
    if any(key in source for key in _RECIPE_FIELDS):
        raise ValueError('native chair surface duplicates source recipe')
    source.update(recipe)
    del source['recipe_scope']
    return clone
