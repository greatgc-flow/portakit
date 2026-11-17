from pathlib import Path
base=Path(__file__).parent
parts=['Header','Policy','Profile','Layout','Native','Transaction','Storage','Runner']
content='\n'.join((base/'parts'/(p+'.ps1')).read_text(encoding='utf-8-sig') for p in parts)
(base/'Aegis.ps1').write_bytes(b'\xef\xbb\xbf'+content.replace('\r\n','\n').replace('\n','\r\n').encode('utf-8'))
print('Aegis.ps1',len(content.splitlines()),'lines', (base/'Aegis.ps1').stat().st_size,'bytes')
