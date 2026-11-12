"""Model capabilities. Raster transport is limited to the documented 128-pin family.

Other models use the installed Brother Windows driver and its media/cutter dialog.
No physical printer has been certified by the build machine.
"""
import re

PROJECT = 'https://github.com/aa70027/P-touch'
TAPE_180 = {3.5:(24,52),6:(32,48),9:(50,39),12:(70,29),18:(112,8),24:(128,0)}
TAPE_360 = {3.5:(48,248),6:(64,240),9:(106,219),12:(150,197),18:(234,155),24:(320,112),36:(454,45)}

def profile(name, slug, *, wifi=False, half=False, dpi=180, high=360, raster=False, widths=None):
    return dict(id=name, name=name, slug=slug, wifi=wifi, usb=True, half_cut=half,
                cuts=['full','half','none'] if half else ['full','none'], dpi=dpi, high_dpi=high,
                widths=widths or [3.5,6,9,12,18,24], transport='raster' if raster else 'driver',
                driver_controls=not raster, hardware_tested=False,
                download_url='https://support.brother.com/g/b/downloadtop.aspx?c=us&lang=en&prod='+slug)

PROFILES = [
    profile('PT-E550W','e550weus',wifi=True,half=True,raster=True),
    profile('PT-P750W','p750weus',wifi=True,half=True,raster=True),
    profile('PT-P710BT','p710bteus',raster=True),
    profile('PT-P700','p700eus'),
    profile('PT-P900W','p900weus',wifi=True,half=True,dpi=360,high=720,widths=[3.5,6,9,12,18,24,36]),
    profile('PT-P950NW','p950nweus',wifi=True,half=True,dpi=360,high=720,widths=[3.5,6,9,12,18,24,36]),
    profile('QL-800','lpql800eus',dpi=300,high=600,widths=[12,29,38,50,54,62]),
    profile('QL-810W','lpql810weus',wifi=True,dpi=300,high=600,widths=[12,29,38,50,54,62]),
    profile('QL-820NWB','lpql820nwbeus',wifi=True,dpi=300,high=600,widths=[12,29,38,50,54,62]),
    profile('Brother Windows driver','',wifi=True,dpi=300,high=300,widths=[3.5,6,9,12,18,24,29,36,38,50,54,62,102]),
]

def get_profile(name):
    for p in PROFILES:
        if p['id']==name:
            return p
    raise ValueError('UNKNOWN_PRINTER_MODEL')

def detect_model(text):
    normalized=re.sub('[^A-Z0-9]','',str(text).upper())
    # Longest names first so QL-820NWB cannot be confused with a prefix.
    return next((p['id'] for p in sorted(PROFILES[:-1],key=lambda p:-len(p['id']))
                 if re.sub('[^A-Z0-9]','',p['id']) in normalized),None)

def printable(width, model='PT-E550W'):
    p=get_profile(model)
    if width not in p['widths']:
        raise ValueError('UNSUPPORTED_TAPE_WIDTH_FOR_MODEL')
    if p['dpi']==180:
        return TAPE_180[width][0]/180*25.4
    if p['dpi']==360:
        return TAPE_360[width][0]/360*25.4
    # Driver media has model/roll-specific nonprintable margins; driver validates final bounds.
    return max(1,width-2)
