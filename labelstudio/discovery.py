"""Read-only Windows PnP, SNMP identity and bounded IPv4 MAC discovery.

MAC resolution is only valid on the local link. A routed network needs a stable
DNS hostname or a DHCP reservation. A reachable TCP port is not printer identity.
"""
import concurrent.futures
import ctypes
import ipaddress
import json
import re
import socket
import struct
import subprocess
import threading
import time
from .profiles import detect_model

def powershell(script):
    result=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',
        "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); "+script],capture_output=True,
        timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),encoding='utf-8',errors='replace')
    if result.returncode:
        raise OSError(result.stderr.strip()[:500])
    value=json.loads(result.stdout.lstrip('\ufeff').strip() or '[]')
    return value if isinstance(value,list) else [value]

def interfaces():
    try:
        values=powershell("Get-NetIPAddress -AddressFamily IPv4 -AddressState Preferred | Where-Object {$_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'} | Select-Object IPAddress,PrefixLength,InterfaceAlias | ConvertTo-Json -Compress")
        result=[]
        for v in values:
            net=ipaddress.ip_network(f"{v['IPAddress']}/{v['PrefixLength']}",strict=False)
            # Offer a bounded local /24 inside larger subnets, never silently sweep an enterprise /16.
            scan=ipaddress.ip_network(f"{v['IPAddress']}/{max(24,net.prefixlen)}",strict=False)
            result.append(dict(address=v['IPAddress'],network=str(net),scan=str(scan),name=v['InterfaceAlias']))
        return result
    except Exception:
        return []

def usb_devices():
    try:
        values=powershell("Get-CimInstance Win32_PnPEntity | Where-Object {$_.PNPDeviceID -match 'VID_04F9' -and $_.Present -ne $false} | Select-Object Name,PNPDeviceID,ConfigManagerErrorCode,Service | ConvertTo-Json -Compress")
        pids={'2060':'PT-E550W','2062':'PT-P750W','20AF':'PT-P710BT'}
        result=[]
        for v in values:
            hardware=v.get('PNPDeviceID','')
            pid=re.search('PID_([0-9A-F]{4})',hardware,re.I)
            model=detect_model(v.get('Name','')) or (pids.get(pid[1].upper()) if pid else None)
            result.append(dict(model=model,name=v.get('Name'),hardware_id=hardware,connection='usb',
                driver_loaded=v.get('ConfigManagerErrorCode')==0 and bool(v.get('Service')),
                driver_error=v.get('ConfigManagerErrorCode')))
        return result
    except Exception as exc:
        return [dict(model=None,connection='usb',error=str(exc))]

def normalize_mac(value):
    if not re.fullmatch(r'[0-9a-f:.\-\s]+',value.lower()):
        raise ValueError('INVALID_MAC_ADDRESS')
    result=re.sub('[^0-9a-f]','',value.lower())
    if len(result)!=12 or not re.fullmatch('[0-9a-f]{12}',result):
        raise ValueError('INVALID_MAC_ADDRESS')
    return ':'.join(result[i:i+2] for i in range(0,12,2))

def arp(ip):
    if not hasattr(ctypes,'WinDLL'):
        return None
    api=ctypes.WinDLL('iphlpapi')
    api.SendARP.argtypes=[ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)]
    address=struct.unpack('<I',socket.inet_aton(ip))[0]
    buffer=(ctypes.c_ubyte*8)();size=ctypes.c_uint32(8)
    if api.SendARP(address,0,buffer,ctypes.byref(size))==0 and size.value==6:
        return ':'.join(f'{v:02x}' for v in buffer[:6])
    return None

def tlv(tag,value):
    size=len(value)
    return bytes([tag])+ (bytes([size]) if size<128 else b'\x81'+bytes([size]))+value

def snmp_description(ip,timeout=.45):
    # SNMPv1 GET sysDescr.0; public read-only community. No writes or printer commands.
    request_id=int(time.time()*1000)&0x7fffffff
    oid=bytes([43,6,1,2,1,1,1,0])
    var=tlv(0x30,tlv(6,oid)+b'\x05\x00')
    pdu=tlv(0xa0,tlv(2,request_id.to_bytes(4,'big'))+b'\x02\x01\x00'*2+tlv(0x30,var))
    packet=tlv(0x30,b'\x02\x01\x00'+tlv(4,b'public')+pdu)
    def fields(raw):
        index=0
        while index<len(raw):
            tag=raw[index];length=raw[index+1];index+=2
            if length&128:
                n=length&127;length=int.from_bytes(raw[index:index+n],'big');index+=n
            if index+length>len(raw):
                raise ValueError('INVALID_SNMP_RESPONSE')
            value=raw[index:index+length];index+=length
            yield tag,value
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout);sock.sendto(packet,(ip,161));raw,_=sock.recvfrom(8192)
        top=list(fields(next(fields(raw))[1]));reply=top[2]
        if reply[0]!=0xa2:
            return None
        values=list(fields(reply[1]))
        if int.from_bytes(values[0][1],'big')!=request_id or int.from_bytes(values[1][1],'big')!=0:
            return None
        binding=list(fields(next(fields(values[3][1]))[1]))
        if binding[0]!=(6,oid) or binding[1][0]!=4:
            return None
        return binding[1][1].decode('utf-8',errors='replace')[:1000]
    except (OSError,ValueError,IndexError,StopIteration):
        return None

def probe(ip,mac=None,port=9100):
    description=snmp_description(ip)
    reachable=False
    try:
        with socket.create_connection((ip,port),timeout=.4):
            reachable=True
    except OSError:
        pass
    return dict(ip=ip,mac=mac,model=detect_model(description or ''),description=description,
                reachable=reachable,identity_verified=bool(description and 'brother' in description.lower()))

def validate_network(cidr):
    net=ipaddress.ip_network(cidr,strict=False)
    if net.version!=4 or net.num_addresses>1024 or not net.is_private or net.is_loopback or net.is_link_local:
        raise ValueError('SELECT_LOCAL_SUBNET_MAX_1024')
    local=interfaces()
    if not any(net.subnet_of(ipaddress.ip_network(v['network'])) for v in local):
        raise ValueError('MAC_SEARCH_REQUIRES_LOCAL_SUBNET')
    return net

def resolve(settings):
    """Resolve at job start. Never silently use a stale IP after a MAC mismatch."""
    if settings.connection!='wifi':
        return settings
    if settings.hostname:
        try:
            ip=socket.gethostbyname(settings.hostname)
        except OSError:
            raise ValueError('PRINTER_HOSTNAME_NOT_FOUND')
        if settings.mac and settings.auto_ip and arp(ip)!=normalize_mac(settings.mac):
            raise ValueError('PRINTER_MAC_MISMATCH')
        return settings.model_copy(update={'ip':ip})
    if not settings.auto_ip or not settings.mac:
        return settings
    target=normalize_mac(settings.mac)
    if settings.ip and arp(settings.ip)==target:
        return settings
    net=validate_network(settings.discovery_subnet)
    def find(ip):
        return str(ip) if arp(str(ip))==target else None
    with concurrent.futures.ThreadPoolExecutor(max_workers=48) as pool:
        found=[ip for ip in pool.map(find,net.hosts()) if ip]
    if len(found)!=1:
        raise ValueError('PRINTER_MAC_NOT_FOUND' if not found else 'AMBIGUOUS_PRINTER_MAC')
    return settings.model_copy(update={'ip':found[0]})

class Discovery:
    def __init__(self):
        self.lock=threading.Lock()
        self.state={'running':False,'progress':0,'results':[],'error':None}
    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.state))
    def start(self,cidr,mac='',port=9100):
        net=validate_network(cidr)
        target=normalize_mac(mac) if mac else ''
        with self.lock:
            if self.state['running']:
                raise ValueError('DISCOVERY_ALREADY_RUNNING')
            self.state=dict(running=True,progress=0,total=max(0,net.num_addresses-2),results=[],error=None)
        def work():
            try:
                def scan(ip):
                    ip=str(ip);found=arp(ip)
                    if not found or target and found!=target:
                        return None
                    info=probe(ip,found,port)
                    return info if target or info['identity_verified'] else None
                with concurrent.futures.ThreadPoolExecutor(max_workers=48) as pool:
                    for result in pool.map(scan,net.hosts()):
                        with self.lock:
                            self.state['progress']+=1
                            if result:self.state['results'].append(result)
            except Exception as exc:
                with self.lock:self.state['error']=str(exc)
            finally:
                with self.lock:self.state['running']=False
        threading.Thread(target=work,daemon=True,name='printer-discovery').start()
        return self.snapshot()
