from typing import Literal
from pydantic import BaseModel, Field, model_validator

Cut = Literal['full', 'half', 'none']
KINDS = ['general', 'cable-flag', 'cable-wrap', 'patch-panel', 'faceplate', 'die-cut-flag', 'terminal-block', 'heat-shrink']
TAPE = {3.5: (24, 52), 6: (32, 48), 9: (50, 39), 12: (70, 29), 18: (112, 8), 24: (128, 0)}


class Element(BaseModel):
    id: str = 'text1'
    type: Literal['text', 'image', 'line', 'rectangle', 'qr', 'barcode'] = 'text'
    x: float = Field(2, ge=0, le=1000)
    y: float = Field(3.5, ge=0, le=102)
    w: float = Field(0, ge=0, le=1000)
    h: float = Field(6, gt=0, le=102)
    text: str = Field('DC-{Rack}-{Port}', max_length=8000)
    font: str = 'Segoe UI'
    size: float = Field(12, ge=3, le=96)
    bold: bool = False
    underline: bool = False
    align: Literal['left', 'center', 'right'] = 'center'
    direction: Literal['auto', 'rtl', 'ltr'] = 'auto'
    rotation: Literal[0, 90, 180, 270] = 0
    asset: str = ''
    thickness: float = Field(0.2, ge=0.1, le=3)


class Label(BaseModel):
    model: str = 'PT-E550W'
    name: str = Field('Untitled', max_length=200)
    kind: Literal['general', 'cable-flag', 'cable-wrap', 'patch-panel', 'faceplate', 'die-cut-flag', 'terminal-block', 'heat-shrink'] = 'general'
    width: float = 24
    length: float = Field(65, ge=4.4, le=1000)
    auto_length: bool = True
    margin_before: float = Field(2, ge=0, le=127)
    margin_after: float = Field(2, ge=0, le=127)
    quality: Literal['standard', 'high'] = 'standard'
    mirror: bool = False
    repeat: int = Field(1, ge=1, le=10000)
    separator: str = Field(' | ', max_length=100)
    separator_line: bool = True
    cable_gap: float = Field(8, ge=0, le=100)
    wrap_repeats: int = Field(2, ge=1, le=10)
    cells: int = Field(6, ge=1, le=96)
    pitch: float = Field(12, ge=2, le=100)
    border: bool = False
    elements: list[Element] = Field(default_factory=lambda: [Element()], max_length=100)

    @model_validator(mode='after')
    def valid_tape(self):
        from .profiles import get_profile
        if self.width not in get_profile(self.model)['widths']:
            raise ValueError('UNSUPPORTED_TAPE_WIDTH')
        return self


class Document(BaseModel):
    name: str = Field('Untitled', min_length=1, max_length=200)
    pages: list[Label] = Field(default_factory=lambda: [Label()], min_length=1, max_length=100)
    rules: list[dict] = Field(default_factory=list, max_length=100)
    variables: dict = Field(default_factory=dict)


class Settings(BaseModel):
    model: str = 'PT-E550W'
    wifi_mode: Literal['infrastructure','direct'] = 'infrastructure'
    hostname: str = Field('',max_length=253,pattern=r'^[a-zA-Z0-9_.-]*$')
    mac: str = ''
    auto_ip: bool = False
    discovery_subnet: str = ''
    update_prerelease: bool = False
    connection: Literal['usb', 'wifi'] = 'usb'
    printer: str = ''
    ip: str = ''
    printer_port: int = Field(9100, ge=1, le=65535)
    port: int = Field(8765, ge=1024, le=65535)
    auto_start: bool = False
    language: Literal['fa', 'en', 'ar'] = 'fa'
    default_width: float = 24
    default_quality: Literal['standard', 'high'] = 'standard'
    cut_between_pages: Cut = 'half'
    cut_end_record: Cut = 'half'
    cut_between_files: Cut = 'full'
    cut_end_file: Cut = 'full'
    auth_enabled: bool = False
    timeout: int = Field(120, ge=10, le=600)
    log_retention_days: int = Field(90, ge=1, le=3650)

    @model_validator(mode='after')
    def validate(self):
        from .profiles import get_profile
        if self.default_width not in get_profile(self.model)['widths']:
            raise ValueError('UNSUPPORTED_TAPE_WIDTH')
        if self.connection=='wifi' and get_profile(self.model)['transport']=='raster' and not get_profile(self.model)['wifi']:
            raise ValueError('WIFI_NOT_SUPPORTED_BY_MODEL')
        if self.auto_ip and not self.mac:
            raise ValueError('MAC_REQUIRED_FOR_AUTO_IP')
        if self.mac:
            from .discovery import normalize_mac
            self.mac=normalize_mac(self.mac)
        if self.discovery_subnet:
            import ipaddress
            net=ipaddress.ip_network(self.discovery_subnet,strict=False)
            if net.version!=4 or net.num_addresses>1024 or not net.is_private:
                raise ValueError('SELECT_LOCAL_SUBNET_MAX_1024')
        if self.ip:
            import ipaddress
            ipaddress.ip_address(self.ip)
        return self


class ResourceIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: Literal['template', 'document', 'dataset']
    scope: Literal['private', 'shared', 'inherit'] = 'inherit'
    payload: dict


class PrintRequest(BaseModel):
    source: str | None = None
    sheets: list[str] | None = None
    encoding: str = 'utf-8-sig'
    delimiter: str | None = None
    record_from: int = Field(0,ge=0)
    record_to: int | None = Field(None,ge=1)
    documents: list[Document] = Field(min_length=1, max_length=100)
    records: list[dict] = Field(default_factory=lambda: [{}], min_length=1, max_length=100000)
    copies: int = Field(1, ge=1, le=10000)
    file_copies: int = Field(1, ge=1, le=10000)
    mode: Literal['continuous', 'confirm'] = 'continuous'
    simulation: bool = False
