# EXE Decompile Report

The EXE was unpacked as a PyInstaller Python 3.11 application. Four application bytecode files were recovered and decompiled with Decompyle++/pycdc.

| File | Lines | Incomplete markers |
| --- | ---: | ---: |
| `recovered_source\excel_library.py` | 520 | 5 |
| `recovered_source\hancom_library.py` | 28570 | 89 |
| `recovered_source\interface.py` | 61 | 10 |
| `recovered_source\main.py` | 3282 | 21 |

## Recovered Files

- `recovered_source\excel_library.py`
- `recovered_source\hancom_library.py`
- `recovered_source\interface.py`
- `recovered_source\main.py`

## Incomplete Areas

### recovered_source\excel_library.py

- line 30: class 엑셀
- line 213: class 엑셀
- line 299: class 엑셀
- line 453: class 엑셀
- line 518: class 엑셀

### recovered_source\hancom_library.py

- line 51: class 기본한컴
- line 828: class 기본한컴
- line 1460: class 기본한컴
- line 1530: class 기본한컴
- line 1680: class 기본한컴
- line 1783: class 기본한컴
- line 1852: class 기본한컴
- line 1879: class 기본한컴
- line 1889: class 기본한컴
- line 1895: class 기본한컴
- line 1920: class 기본한컴
- line 1937: class 기본한컴
- line 1945: class 기본한컴
- line 1957: class 기본한컴
- line 1968: class 기본한컴
- line 1977: class 기본한컴
- line 1986: class 기본한컴
- line 1995: class 기본한컴
- line 2004: class 기본한컴
- line 2013: class 기본한컴
- line 2027: class 기본한컴
- line 2182: class 기본한컴
- line 2187: class 기본한컴
- line 2192: class 기본한컴
- line 2197: class 기본한컴
- line 2202: class 기본한컴
- line 2207: class 기본한컴
- line 2212: class 기본한컴
- line 2251: class 기본한컴
- line 2256: class 기본한컴
- line 2442: class 기본한컴
- line 3427: class 기본한컴
- line 4156: class 기본한컴
- line 4166: class 기본한컴
- line 4398: class 기본한컴
- line 4588: class 기본한컴
- line 4593: class 기본한컴
- line 4598: class 기본한컴
- line 4603: class 기본한컴
- line 5638: class 기본한컴
- line 6389: class 기본한컴
- line 7554: class 기본한컴
- line 7743: class 기본한컴
- line 10105: class 기본한컴
- line 11392: class 기본한컴
- line 11405: class 기본한컴
- line 11417: class 기본한컴
- line 12887: class 기본한컴
- line 12932: class 기본한컴
- line 14125: class 기본한컴
- line 14381: class 기본한컴
- line 14422: class 기본한컴
- line 14427: class 기본한컴
- line 14432: class 기본한컴
- line 14437: class 기본한컴
- line 14442: class 기본한컴
- line 14447: class 기본한컴
- line 14452: class 기본한컴
- line 17868: class 기본한컴
- line 18020: class 기본한컴
- line 18853: class 기본한컴
- line 18855: class 기본한컴
- line 18860: class 기본한컴
- line 18865: class 기본한컴
- line 18873: class 기본한컴
- line 19089: class 기본한컴
- line 19660: class 기본한컴
- line 20044: class 기본한컴
- line 20213: class 기본한컴
- line 20246: class 기본한컴
- line 20509: class 기본한컴
- line 20514: class 기본한컴
- line 21130: class 기본한컴
- line 21671: class 기본한컴
- line 22860: class 기본한컴
- line 22865: class 기본한컴
- line 24763: class 기본한컴
- line 24785: class 기본한컴
- line 25291: class 기본한컴
- line 25913: class 기본한컴
- line 25918: class 기본한컴
- line 25923: class 기본한컴
- line 26068: class 기본한컴
- line 26137: class 기본한컴
- line 26142: class 기본한컴
- line 26147: class 기본한컴
- line 26152: class 기본한컴
- line 26157: class 기본한컴
- line 27570: class 기본한컴

### recovered_source\interface.py

- line 15: class 버튼
- line 20: class 토글버튼
- line 25: class 입력창
- line 30: class 입력창넓이
- line 35: class 입력창넓이높이
- line 40: class 입력창넓이크기
- line 45: class 프레임
- line 50: class 상단바
- line 55: class 새탭
- line 60: class 우측새탭

### recovered_source\main.py

- line 32: def genpy폴더제거
- line 72: def 블록앞뒤붙임창
- line 77: def 블록바꾸기창
- line 82: def 셀앞뒤붙임창
- line 87: def 셀찾아바꾸기창
- line 92: def 금액비율창
- line 97: def 메일머지창
- line 102: def 시험서식창
- line 124: def 표대량계산창
- line 129: def 회신공문창
- line 134: def 공문틀생성기창
- line 139: def 공문언어순화창
- line 1180: def 남해창
- line 1310: def 산인공창
- line 1551: def 엑셀창
- line 2608: def 각종날짜입력창
- line 2613: def 날짜계산기창
- line 2650: def 목차만들기창
- line 2811: def 기본서식프레임
- line 2907: def 표프레임
- line 3141: def 이동프레임

## Interpretation

The recovered source is suitable for function discovery and implementation reference. It should not be treated as exact original source where pycdc emitted incomplete markers or suspicious expressions such as calls to `None(...)`. For those scopes, use the `.pyc` bytecode and disassembly as authoritative evidence.
