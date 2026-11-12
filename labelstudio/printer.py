"""PT-E550W Raster Reference v1.02, with compressed 128-pin raster lines.

Windows RAW spooling and TCP acknowledgement are submission acknowledgements,
not physical-print confirmations. E550W does not support ESC i S polling.
"""
import contextlib
import ctypes
from ctypes import wintypes
import socket
import struct
from PIL import Image, ImageOps
from .models import TAPE


def usb_present():
    """Read current USB interface paths with SetupAPI, without opening a print job."""
    if not hasattr(ctypes,'WinDLL'):
        return None
    class GUID(ctypes.Structure):
        _fields_=[('Data1',wintypes.DWORD),('Data2',wintypes.WORD),('Data3',wintypes.WORD),('Data4',ctypes.c_ubyte*8)]
    class INTERFACE(ctypes.Structure):
        _fields_=[('cbSize',wintypes.DWORD),('InterfaceClassGuid',GUID),('Flags',wintypes.DWORD),('Reserved',ctypes.c_void_p)]
    guid=GUID(0xa5dcbf10,0x6530,0x11d2,(ctypes.c_ubyte*8)(0x90,0x1f,0x00,0xc0,0x4f,0xb9,0x51,0xed))
    api=ctypes.WinDLL('setupapi',use_last_error=True)
    api.SetupDiGetClassDevsW.argtypes=[ctypes.POINTER(GUID),wintypes.LPCWSTR,wintypes.HWND,wintypes.DWORD]
    api.SetupDiGetClassDevsW.restype=ctypes.c_void_p
    api.SetupDiEnumDeviceInterfaces.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(GUID),wintypes.DWORD,ctypes.POINTER(INTERFACE)]
    api.SetupDiGetDeviceInterfaceDetailW.argtypes=[ctypes.c_void_p,ctypes.POINTER(INTERFACE),ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
    api.SetupDiDestroyDeviceInfoList.argtypes=[ctypes.c_void_p]
    handle=api.SetupDiGetClassDevsW(ctypes.byref(guid),None,None,0x12) # PRESENT | DEVICEINTERFACE
    if handle==ctypes.c_void_p(-1).value:
        return None
    try:
        index=0
        while True:
            item=INTERFACE();item.cbSize=ctypes.sizeof(INTERFACE)
            if not api.SetupDiEnumDeviceInterfaces(handle,None,ctypes.byref(guid),index,ctypes.byref(item)):
                return False if ctypes.get_last_error()==259 else None
            needed=wintypes.DWORD()
            api.SetupDiGetDeviceInterfaceDetailW(handle,ctypes.byref(item),None,0,ctypes.byref(needed),None)
            buffer=ctypes.create_string_buffer(needed.value)
            ctypes.cast(buffer,ctypes.POINTER(wintypes.DWORD))[0]=8 if ctypes.sizeof(ctypes.c_void_p)==8 else 6
            if api.SetupDiGetDeviceInterfaceDetailW(handle,ctypes.byref(item),buffer,needed.value,None,None):
                path=ctypes.wstring_at(ctypes.addressof(buffer)+4).lower()
                if 'vid_04f9&pid_2060' in path:
                    return True
            index+=1
    finally:
        api.SetupDiDestroyDeviceInfoList(handle)


def printers():
    try:
        import win32print
        result=[]
        for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS, None, 2):
            result.append({'name':p['pPrinterName'],'driver':p['pDriverName'],'port':p['pPortName'],
                           'status':p['Status'],'supported':'brother' in p['pDriverName'].lower(),
                           'jobs':p['cJobs']})
        return result
    except Exception as exc:
        return []


def installed_drivers():
    try:
        import win32print
        return [item['pName'] for item in win32print.EnumPrinterDrivers(None,None,2)]
    except Exception:
        return []


def status(settings):
    items=printers()
    matches=[p for p in items if p['name']==settings.printer]
    drivers=installed_drivers()
    from .profiles import get_profile,detect_model
    model=settings.model
    profile=get_profile(model)
    driver_installed=any(detect_model(name)==model for name in drivers) if model!='Brother Windows driver' else any('brother' in name.lower() for name in drivers)
    present=usb_present() if settings.connection=='usb' else None
    info={'connection':settings.connection,'driver_installed':driver_installed,'drivers':drivers,'printers':items,'usb_present':present,
          'state':'unknown','detail':'SELECT_PRINTER','device_confirmed':False,'model':None,'configured_model':model,'profile':profile,'resolved_ip':settings.ip}
    if settings.connection=='wifi' and profile['transport']=='raster':
        from .discovery import resolve,probe
        try:
            settings=resolve(settings)
            info['resolved_ip']=settings.ip
        except ValueError as exc:
            info.update(state='offline',detail=str(exc))
            return info
        if not settings.ip:
            info['detail']='SET_PRINTER_IP'
        else:
            try:
                with socket.create_connection((settings.ip,settings.printer_port),timeout=2):
                    pass
                identity=probe(settings.ip,port=settings.printer_port)
                info.update(state='reachable',detail='TCP_REACHABLE',model=identity['model'],identity=identity)
                if identity['model'] and identity['model']!=model:
                    info.update(state='error',detail='PRINTER_MODEL_MISMATCH')
            except OSError:
                info.update(state='offline',detail='TCP_UNREACHABLE')
    elif matches:
        printer=matches[0]
        info['model']=detect_model(printer.get('driver',''))
        info['driver_installed']=True
        if not printer['supported']:
            info.update(state='error',detail='UNSUPPORTED_PRINTER')
        elif printer['status'] & (0x80 | 0x1000 | 0x2 | 0x4 | 0x8 | 0x10 | 0x40 | 0x800):
            info.update(state='offline',detail='WINDOWS_PRINTER_ERROR')
        elif info['model'] and info['model']!=model:
            info.update(state='error',detail='PRINTER_MODEL_MISMATCH')
        elif present and model=='PT-E550W':
            info.update(state='reachable',detail='USB_DEVICE_DETECTED')
        elif present is False and model=='PT-E550W' and settings.connection=='usb':
            info.update(state='offline',detail='USB_DEVICE_NOT_CONNECTED')
        else:
            info.update(state='unknown',detail='WINDOWS_READY_UNCONFIRMED')
    if settings.connection=='usb' and model=='PT-E550W' and present:
        info['model']='PT-E550W'
        if info['state']=='unknown':info.update(state='reachable',detail='USB_DEVICE_DETECTED')
    if settings.connection=='usb' and model!='PT-E550W':
        from .discovery import usb_devices
        detected=[v for v in usb_devices() if v.get('model')==model]
        info['usb_devices']=detected
        if detected:
            info['model']=model
            if info['state'] not in ('error','offline'):
                info.update(state='reachable',detail='USB_DEVICE_DETECTED')
    return info


def packbits(data):
    result=bytearray()
    i=0
    while i<len(data):
        repeat=1
        while i+repeat<len(data) and data[i+repeat]==data[i] and repeat<128:
            repeat+=1
        if repeat>=2:
            result.extend(((1-repeat)&255,data[i]))
            i+=repeat
        else:
            start=i
            i+=1
            while i<len(data) and i-start<128:
                if i+1<len(data) and data[i]==data[i+1]:
                    break
                i+=1
            result.append(i-start-1)
            result.extend(data[start:i])
    return bytes(result)


def raster_page(image, label, cut='full', first=True, last=True):
    from .profiles import get_profile
    profile=get_profile(label.model)
    if profile['transport']!='raster':raise ValueError('WINDOWS_DRIVER_TRANSPORT_REQUIRED')
    if cut not in profile['cuts']:raise ValueError('UNSUPPORTED_CUT_FOR_MODEL')
    printable, offset=TAPE[label.width]
    top=(image.height-printable)//2
    high=label.quality=='high'
    feed=28 if high else 14
    # Margins are visible in the preview and included in the physical label length.
    # The printer supplies these blank columns via ESC i d instead of raster data.
    image=image.crop((feed,0,image.width-feed,image.height))
    ink=ImageOps.invert(image.convert('L')).point(lambda p:255 if p>0 else 0,'1')
    ink=ink.crop((0,top,image.width,top+printable))
    # Transpose each image column into a 128-pin raster line; 1 means ink.
    head=Image.new('1',(128,image.width),0)
    head.paste(ink.transpose(Image.Transpose.TRANSPOSE),(offset,0))
    # Pack rows as MSB-first bytes in printer pin order.
    raw=head.tobytes()
    # The renderer already samples the feed axis at 360 dpi in high mode.
    # Duplicating those samples again would incorrectly double the physical length.
    lines=image.width
    flags=(0x40 if high else 0) | (0x04 if cut=='half' else 0) | (0x08 if last and cut=='full' else 0)
    out=bytearray(b'\x00'*100+b'\x1b@' if first else b'')
    out.extend(b'\x1bia\x01')
    # Width checked by printer; media kind omitted to permit TZe/HGe compatible tape.
    out.extend(b'\x1biz'+bytes([0x84,0,round(label.width),0])+struct.pack('<I',lines)+bytes([0 if first else 1,0]))
    out.extend(b'\x1biM'+bytes([0x40 if cut=='full' else 0]))
    if label.model!='PT-P710BT':
        out.extend(b'\x1biA\x01')
    out.extend(b'\x1biK'+bytes([flags]))
    out.extend(b'\x1bid'+struct.pack('<H',feed)+b'M\x02')
    for i in range(image.width):
        line=raw[i*16:i*16+16]
        packed=packbits(line)
        block=(b'Z' if not any(line) else b'G'+struct.pack('<H',len(packed))+packed)
        out.extend(block)
    out.extend(b'\x1a' if last else b'\x0c')
    return bytes(out)


class Transport:
    def __init__(self,settings,name):
        self.settings,self.name=settings,name
        self.sock=None
        self.handle=None
        self.job_id=None

    def __enter__(self):
        from .profiles import get_profile
        if get_profile(self.settings.model)['transport']!='raster':
            raise ValueError('WINDOWS_DRIVER_TRANSPORT_REQUIRED')
        if self.settings.connection=='wifi':
            from .discovery import resolve
            self.settings=resolve(self.settings)
            if not self.settings.ip:raise ValueError('SET_PRINTER_IP')
            self.sock=socket.create_connection((self.settings.ip,self.settings.printer_port),timeout=self.settings.timeout)
            self.sock.settimeout(self.settings.timeout)
        else:
            import win32print
            from .profiles import detect_model
            selected=next((p for p in printers() if p['name']==self.settings.printer),None)
            if not selected or not selected['supported'] or detect_model(selected['driver'])!=self.settings.model:
                raise ValueError('SELECT_SUPPORTED_PRINTER')
            self.handle=win32print.OpenPrinter(self.settings.printer)
            try:self.job_id=win32print.StartDocPrinter(self.handle,1,(self.name,None,'RAW'))
            except Exception:
                win32print.ClosePrinter(self.handle);self.handle=None;raise
        return self

    def send(self,data):
        if self.sock:
            self.sock.sendall(data)
        else:
            import win32print
            win32print.StartPagePrinter(self.handle)
            try:
                sent=win32print.WritePrinter(self.handle,data)
                if sent!=len(data):
                    raise OSError('INCOMPLETE_WRITE')
            finally:
                win32print.EndPagePrinter(self.handle)

    def __exit__(self,typ,value,tb):
        if self.sock:
            self.sock.close()
        if self.handle:
            import win32print
            try:
                if typ:
                    win32print.AbortPrinter(self.handle)
                else:
                    win32print.EndDocPrinter(self.handle)
            finally:
                win32print.ClosePrinter(self.handle)


def cut_for(settings,end_record,end_file,last):
    if last:
        return settings.cut_end_file
    if end_file:
        # At a file boundary this takes precedence over record/page cuts.
        return settings.cut_between_files
    if end_record:
        return settings.cut_end_record
    return settings.cut_between_pages


class DriverTransport:
    """GDI submission through a Brother queue; private cutter/media properties stay in its driver."""
    def __init__(self,settings,name):self.settings,self.name=settings,name;self.dc=None
    def __enter__(self):
        import win32ui
        import win32print
        from .profiles import detect_model
        chosen=next((p for p in printers() if p['name']==self.settings.printer and p['supported']),None)
        if not chosen:raise ValueError('SELECT_SUPPORTED_PRINTER')
        found=detect_model(chosen['driver'])
        if self.settings.model!='Brother Windows driver' and found!=self.settings.model:
            raise ValueError('PRINTER_MODEL_MISMATCH')
        self.dc=win32ui.CreateDC();self.dc.CreatePrinterDC(self.settings.printer)
        self.dc.StartDoc(self.name);return self
    def send_image(self,image,meta):
        from PIL import ImageWin
        # Set physical paper dimensions before queueing with Driver Properties. Refuse clipping/scaling.
        dx,dy=self.dc.GetDeviceCaps(88),self.dc.GetDeviceCaps(90)
        width=round(meta['length_mm']*dx/25.4);height=round(meta['width_mm']*dy/25.4)
        printable_x,printable_y=self.dc.GetDeviceCaps(8),self.dc.GetDeviceCaps(10)
        # Driver orientation may put the feed direction on Y.
        if width>printable_x+2 or height>printable_y+2:
            if height<=printable_x+2 and width<=printable_y+2:
                image=image.transpose(Image.Transpose.ROTATE_90);width,height=height,width
            else:raise ValueError('SET_DRIVER_MEDIA_SIZE_BEFORE_PRINTING')
        self.dc.StartPage()
        try:ImageWin.Dib(image.convert('RGB')).draw(self.dc.GetHandleOutput(),(0,0,width,height))
        finally:self.dc.EndPage()
    def __exit__(self,typ,value,tb):
        if self.dc:
            try:
                if typ:self.dc.AbortDoc()
                else:self.dc.EndDoc()
            finally:self.dc.DeleteDC();self.dc=None
