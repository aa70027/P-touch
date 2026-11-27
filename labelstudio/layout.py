"""Center measured element geometry without changing text, fonts or barcode data."""
from PIL import ImageOps
from .models import Label
from .profiles import printable
from .render import DPM,SCALE,element_image

def center_label(label:Label,row:dict,assets,element_id=None,axis='width'):
    result=label.model_copy(deep=True)
    if axis not in ('width','page'):raise ValueError('INVALID_CENTER_AXIS')
    targets=result.elements if element_id is None else [e for e in result.elements if e.id==element_id]
    if not targets:raise ValueError('ELEMENT_NOT_FOUND')
    if element_id is not None and len(targets)!=1:raise ValueError('AMBIGUOUS_ELEMENT_ID')
    px=DPM*SCALE
    # Measure every panel cell, including formulas and the widest cell counter.
    rows=[row|{'#cell':i+1} for i in range(result.cells)] if result.kind in ('patch-panel','terminal-block') else [row]
    measured={}
    for element in result.elements:
        images=[element_image(element,cell,assets,result.persian_digits) for cell in rows]
        boxes=[ImageOps.invert(image.convert('L')).getbbox() or (0,0,image.width,image.height) for image in images]
        measured[id(element)]={'w':max(i.width for i in images)/px,'h':max(i.height for i in images)/px,
                               'top':min(b[1] for b in boxes)/px,'bottom':max(b[3] for b in boxes)/px}
    if result.kind!='cable-wrap':
        top=min(e.y+measured[id(e)]['top'] for e in targets)
        bottom=max(e.y+measured[id(e)]['bottom'] for e in targets)
        if bottom-top>printable(result.width,result.model)+.01:
            raise ValueError('CONTENT_TOO_TALL_TO_CENTER')
        shift=result.width/2-(top+bottom)/2
        if any(e.y+shift<-.001 or e.y+shift+measured[id(e)]['h']>result.width+.001 for e in targets):
            raise ValueError('ELEMENT_FRAME_TOO_TALL_TO_CENTER')
        for element in targets:element.y=round(max(0,element.y+shift),4)
    fixed_length=False
    if axis=='page':
        before=max(2,result.margin_before);after=max(2,result.margin_after)
        cell_length=max(4.4,before+max([e.x+measured[id(e)]['w'] for e in result.elements] or [10])+after) if result.auto_length else result.length
        if result.kind in ('patch-panel','terminal-block'):
            available=result.pitch
        else:
            # Freeze the current auto-sized side/page, so centering is stable on repeated clicks.
            if result.auto_length:
                if not 4.4<=cell_length<=1000:raise ValueError('LABEL_LENGTH_OUT_OF_RANGE')
                result.length=cell_length;result.auto_length=False;fixed_length=True
            available=cell_length-before-after
        left=min(e.x for e in targets);right=max(e.x+measured[id(e)]['w'] for e in targets)
        if right-left>available+.01:raise ValueError('CONTENT_TOO_WIDE_TO_CENTER')
        center=available/2 if result.kind in ('patch-panel','terminal-block') else cell_length/2-before
        shift=center-(left+right)/2
        if any(e.x+shift<-.001 or e.x+shift+measured[id(e)]['w']>available+.001 for e in targets):
            raise ValueError('CENTER_CONFLICTS_WITH_MARGINS')
        for element in targets:element.x=round(max(0,element.x+shift),4)
    return result,{'fixed_length':fixed_length,'centered_elements':[e.id for e in targets]}
