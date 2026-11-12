import io
import math
import os
import re
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, features
from .formulas import interpolate
from .models import Label, TAPE

SCALE = 3
DPM = 180 / 25.4
FONT_DIR = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
SYSTEM_FONTS = {'Segoe UI': ('segoeui.ttf', 'segoeuib.ttf'), 'Arial': ('arial.ttf', 'arialbd.ttf'),
                'Tahoma': ('tahoma.ttf', 'tahomabd.ttf'), 'Consolas': ('consola.ttf', 'consolab.ttf'),
                'Times New Roman': ('times.ttf', 'timesbd.ttf')}


def get_font(name, size, bold, assets):
    if name in SYSTEM_FONTS:
        path = FONT_DIR / SYSTEM_FONTS[name][1 if bold else 0]
    else:
        path = assets(name, 'font')
    try:
        return ImageFont.truetype(io.BytesIO(Path(path).read_bytes()), max(1, round(size * 180 / 72 * SCALE)),
                                  layout_engine=ImageFont.Layout.RAQM if features.check_feature('raqm') else ImageFont.Layout.BASIC)
    except (OSError, KeyError):
        raise ValueError('FONT_NOT_FOUND:' + name)


def text_options(text, direction):
    if not features.check_feature('raqm'):
        return {}
    if direction == 'auto':
        direction = 'rtl' if re.search(r'[\u0600-\u08ff]', text) else 'ltr'
    return {'direction': direction}


def element_image(element, row, assets):
    px = DPM * SCALE
    text = interpolate(element.text, row)
    w, h = round(element.w * px), max(1, round(element.h * px))
    if element.type == 'text':
        font = get_font(element.font, element.size, element.bold, assets)
        opts = text_options(text, element.direction)
        if not features.check_feature('raqm'):
            import arabic_reshaper
            from bidi.algorithm import get_display
            reshaper = arabic_reshaper.ArabicReshaper(configuration={'delete_harakat': False, 'shift_harakat_position': True})
            base = {'rtl':'R','ltr':'L'}.get(element.direction)
            text = '\n'.join(get_display(reshaper.reshape(line),base_dir=base) for line in text.split('\n'))
        probe = ImageDraw.Draw(Image.new('L', (1, 1), 255))
        stroke = 1 if element.bold and element.font not in SYSTEM_FONTS else 0
        box = probe.multiline_textbbox((0, 0), text or ' ', font=font, spacing=2*SCALE, stroke_width=stroke, **opts)
        tw, th = math.ceil(box[2]-box[0]), math.ceil(box[3]-box[1])
        w = w or max(1, tw + 2*SCALE)
        if tw > w + 1 or th > h + 1:
            raise ValueError('TEXT_OVERFLOW:' + element.id)
        layer = Image.new('L', (max(1,w),h), 255)
        x = 0 if element.align == 'left' else (w-tw) if element.align == 'right' else (w-tw)//2
        y = (h-th)//2
        draw = ImageDraw.Draw(layer)
        draw.multiline_text((x-box[0], y-box[1]), text, fill=0, font=font, spacing=2*SCALE,
                            align=element.align, stroke_width=stroke, **opts)
        if element.underline and text:
            draw.line((x, min(h-1,y+th+SCALE), x+tw, min(h-1,y+th+SCALE)), fill=0, width=SCALE)
    elif element.type == 'image':
        if not element.asset:
            return Image.new('L', (max(1,w), h), 255)
        path = assets(element.asset, 'image')
        with Image.open(path) as raw:
            raw = ImageOps.exif_transpose(raw).convert('RGBA')
            background = Image.new('RGBA', raw.size, 'white')
            background.alpha_composite(raw)
            source = background.convert('L')
        if not w:
            w = max(1, round(h*source.width/source.height))
        layer = Image.new('L', (w,h),255)
        fitted = ImageOps.contain(source, (w,h), Image.Resampling.LANCZOS)
        layer.paste(fitted, ((w-fitted.width)//2,(h-fitted.height)//2))
    elif element.type in ('qr', 'barcode'):
        if not text:
            raise ValueError('EMPTY_CODE:' + element.id)
        if element.type == 'qr':
            import qrcode
            source = qrcode.make(text, border=4, box_size=1).convert('L')
            w = w or h
            if min(w,h) / SCALE < source.width*2:
                raise ValueError('CODE_TOO_SMALL')
        else:
            source = code128(text)
            w = w or source.width*SCALE
            if w / SCALE < source.width:
                raise ValueError('CODE_TOO_SMALL')
        layer = Image.new('L',(max(1,w),h),255)
        fitted = ImageOps.contain(source,(w,h),Image.Resampling.NEAREST)
        layer.paste(fitted,((w-fitted.width)//2,(h-fitted.height)//2))
    else:
        w = w or round(10*px)
        layer = Image.new('L',(max(1,w),h),255)
        draw = ImageDraw.Draw(layer)
        thickness = max(1,round(element.thickness*px))
        if element.type == 'line':
            draw.line((0,h//2,w,h//2),fill=0,width=thickness)
        else:
            draw.rectangle((0,0,w-1,h-1),outline=0,width=thickness)
    return layer.rotate(element.rotation, expand=True, fillcolor=255) if element.rotation else layer


# Code 128 subset B, ISO/IEC 15417 symbol widths (start B=104, stop=106).
CODE128 = ('212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 '
           '112232 122132 122231 113222 123122 123221 223211 221132 221231 213212 223112 312131 '
           '311222 321122 321221 312212 322112 322211 212123 212321 232121 111323 131123 131321 '
           '112313 132113 132311 211313 231113 231311 112133 112331 132131 113123 113321 133121 '
           '313121 211331 231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 '
           '314111 221411 431111 111224 111422 121124 121421 141122 141221 112214 112412 122114 '
           '122411 142112 142211 241211 221114 413111 241112 134111 111242 121142 121241 114212 '
           '124112 124211 411212 421112 421211 212141 214121 412121 111143 111341 131141 114113 '
           '114311 411113 411311 113141 114131 311141 411131 211412 211214 211232 2331112').split()


def code128(text):
    values = [ord(c)-32 for c in text]
    if any(v < 0 or v > 94 for v in values) or len(values)>200:
        raise ValueError('CODE128_ASCII_ONLY')
    symbols = [104] + values + [(104+sum((i+1)*v for i,v in enumerate(values))) % 103,106]
    widths = [int(c) for s in symbols for c in CODE128[s]]
    image = Image.new('L',(sum(widths)+20,40),255)
    draw, x, black = ImageDraw.Draw(image),10,True
    for width in widths:
        if black:
            draw.rectangle((x,0,x+width-1,39),fill=0)
        x += width
        black = not black
    return image


def render_label(label: Label, row: dict, assets):
    from .profiles import get_profile, printable as printable_mm
    profile=get_profile(label.model)
    print_mm=printable_mm(label.width,label.model)
    printable=round(print_mm*DPM)
    px = DPM*SCALE
    # Reserve the unavoidable 2 mm feed at each end inside the requested length.
    # Optional whitespace can be removed without pretending the cutter can reach the head.
    before=max(2,label.margin_before)
    after=max(2,label.margin_after)
    rendered = [(e,element_image(e,row,assets)) for e in label.elements]
    max_x = max([e.x + image.width/px for e,image in rendered] or [10])
    cell_length = max(4.4,before+max_x+after) if label.auto_length else label.length
    if label.kind in ('patch-panel', 'terminal-block'):
        cell_length = label.pitch
        minimum = label.cells*label.pitch + before + after
        length = minimum if label.auto_length else label.length
        if length < minimum:
            raise ValueError('PANEL_LENGTH_TOO_SHORT')
    elif label.kind in ('cable-flag', 'die-cut-flag'):
        length = 2*cell_length+label.cable_gap
    else:
        length = cell_length
    if not 4.4 <= length <= 1000:
        raise ValueError('LABEL_LENGTH_OUT_OF_RANGE')
    height = max(1,round(label.width*px))
    image = Image.new('L',(max(1,round(length*px)),height),255)
    if label.kind in ('cable-flag','die-cut-flag'):
        offsets = [(0,0),(cell_length+label.cable_gap,0)]
    elif label.kind in ('patch-panel','terminal-block'):
        offsets = [(i*label.pitch,0) for i in range(label.cells)]
    else:
        offsets = [(0,0)]
    for index,(ox,oy) in enumerate(offsets):
        cell_row = row | {'#cell': index+1}
        for element,source in rendered:
            if label.kind in ('patch-panel','terminal-block'):
                source = element_image(element,cell_row,assets)
            x, y = round((before+element.x+ox)*px),round((element.y+oy)*px)
            if label.kind == 'cable-wrap':
                # Repeat in the printable height with a consistent row spacing.
                printable = round(print_mm*DPM)
                top = (label.width-printable/DPM)/2
                step = printable/DPM/label.wrap_repeats
                if source.height/px > step:
                    raise ValueError('WRAP_TEXT_TOO_TALL')
                for repeat in range(label.wrap_repeats):
                    ry = round((top+repeat*step+(step-source.height/px)/2)*px)
                    if x+source.width>image.width:
                        raise ValueError('ELEMENT_OUTSIDE_LABEL:'+element.id)
                    image.paste(source,(x,ry))
            else:
                boundary = (ox+cell_length-after)*px if label.kind in ('cable-flag','die-cut-flag') else (before+ox+label.pitch)*px if label.kind in ('patch-panel','terminal-block') else image.width-after*px
                if x+source.width > boundary+1 or y+source.height > height+1:
                    raise ValueError('ELEMENT_OUTSIDE_LABEL:'+element.id)
                image.paste(source,(x,y))
    draw = ImageDraw.Draw(image)
    if label.kind in ('cable-flag','die-cut-flag'):
        center = round((cell_length+label.cable_gap/2)*px)
        if label.separator:
            from .models import Element
            sep = Element(id='separator',text=label.separator,x=0,y=0,size=7,h=min(label.width-2,8),align='center')
            part = element_image(sep,row,assets)
            if part.width > label.cable_gap*px:
                raise ValueError('SEPARATOR_TOO_WIDE')
            image.paste(part,(center-part.width//2,(height-part.height)//2))
        if label.separator_line:
            printable=round(print_mm*DPM)
            top=round((label.width-printable/DPM)*px/2)+SCALE
            draw.line((center,top,center,height-top-1),fill=0,width=SCALE)
    if label.kind in ('patch-panel','terminal-block') and label.separator_line:
        printable=round(print_mm*DPM)
        top=round((label.width-printable/DPM)*px/2)+SCALE
        for i in range(1,label.cells):
            x=round((before+i*label.pitch)*px)
            draw.line((x,top,x,height-top-1),fill=0,width=SCALE)
    if label.border:
        printable=round(print_mm*DPM)
        top=round((label.width-printable/DPM)*px/2)+SCALE
        draw.rectangle((round(2*px)+SCALE,top,image.width-round(2*px)-SCALE-1,height-top-1),outline=0,width=SCALE)
    if label.mirror:
        image = ImageOps.mirror(image)
    # Mechanical resolution is 180 dpi across tape, 180/360 dpi along its length.
    across=profile['dpi'];along=profile['high_dpi'] if label.quality=='high' else across
    image = image.resize((max(1,round(length*along/25.4)),round(label.width*across/25.4)),Image.Resampling.LANCZOS)
    image = image.point(lambda p: 0 if p < 160 else 255,'1')
    bbox = ImageOps.invert(image.convert('L')).getbbox()
    printable=round(print_mm*across/25.4)
    top=(image.height-printable)//2
    if bbox and (bbox[1]<top or bbox[3]>top+printable):
        raise ValueError('OUTSIDE_PRINTABLE_AREA')
    return image, {'length_mm':round(length,2),'width_mm':label.width,'printable_mm':round(print_mm,2),
                   'resolution':[along,across],'model':label.model,'driver_controls':profile['driver_controls'],
                   'hardware_feed_mm':4,'estimated_output_mm':round(max(24.5,length),2),
                   'actual_margin_before_mm':before,'actual_margin_after_mm':after,
                   'warnings':(['DIE_CUT_LAYOUT_ON_CONTINUOUS_TAPE'] if label.kind=='die-cut-flag' else []) + ['HARDWARE_FEED_ADDED']}


def png_bytes(image):
    stream=io.BytesIO()
    image.save(stream,format='PNG')
    return stream.getvalue()
