import time
from pymodbus.client import ModbusSerialClient
import inspect
import pygame, time
from collections import deque

pygame.mixer.init()
pygame.mixer.music.load("WeWillRockYou.mp3")  # 잘라낸 음원 사용
pygame.mixer.music.play()

# 485통신 연결 설정
port = 'COM5'  # USB 시리얼 포트
baudrate = 9600  # 시리얼 속도
bytesize = 8
parity = 'N'
stopbits = 1
timeout = 3
UNIT_ID = 1

# Modbus 클라이언트 초기화
client = ModbusSerialClient(port=port, baudrate=baudrate, bytesize=bytesize, parity=parity, stopbits=stopbits, timeout=timeout)

# 접속 확인
if client.connect():
    print("접속 성공")
else:
    print("접속 실패")
    exit()

# --- 코일 주소 매핑 (16진 표기 가능) ---
L1 = 0x0004   # 0x0004 -> 4
L2 = 0x0005   # 0x0005 -> 5
L3 = 0x0006   # 0x0006 -> 6

def _write_coils_block(start_addr: int, bool_list: list, unit: int = None) -> bool:
    """
    Pymodbus 3.x 호환성 고려한 write_coils 래퍼:
    1) unit이 None이면 전역 UNIT_ID 사용
    2) client 인스턴스에 가능한 여러 속성 이름에 unit을 할당해 봄
    3) 키워드 없이 client.write_coils(start_addr, bool_list) 호출 시도
    4) 실패하면 inspect.signature 정보를 출력하여 다음 디버깅 토대 제공
    """
    if unit is None:
        try:
            unit = UNIT_ID
        except NameError:
            # 안전장치: UNIT_ID가 정의되지 않았으면 기본 1 사용
            unit = 1

    # 1) 클라이언트 인스턴스에 가능한 속성들 자동 설정 시도
    # (pymodbus 버전별로 속성명이 다를 수 있어서 여러 후보를 시도)
    attr_candidates = ("unit_id", "unit", "slave", "default_unit", "default_slave")
    for a in attr_candidates:
        try:
            setattr(client, a, unit)
        except Exception:
            # 일부 속성은 읽기전용이거나 존재하지 않을 수 있음 -> 무시
            pass

    # 2) 실제 호출 시도 (가장 간단한 형태: 키워드 없이)
    rr = None
    try:
        rr = client.write_coils(start_addr, bool_list)  # most compatible attempt
    except TypeError as e_type:
        # 실패하면 상세 디버깅 정보를 출력
        print("write_coils 호출 시 TypeError 발생:", repr(e_type))
        # 출력: client 클래스와 write_coils 시그니처 확인
        try:
            print("client class:", client.__class__)
            sig = inspect.signature(client.write_coils)
            print("write_coils signature:", sig)
        except Exception as e_sig:
            print("inspect.signature 실패:", repr(e_sig))

        # 추가 시도: write_coils에 positional로 unit 전달 (이미 시도하셨지만 재시도)
        try:
            rr = client.write_coils(start_addr, bool_list, unit)
        except Exception as e_pos:
            print("positional 시도 실패:", repr(e_pos))
            rr = None
    except Exception as e:
        # 다른 종류의 예외(연결문제 등)는 그대로 출력
        print("write_coils 호출 중 예외 발생:", repr(e))
        rr = None

    # 3) rr이 None이면 실패로 처리
    if rr is None:
        print("write_coils: 호출 실패(모든 시도).")
        return False

    # 4) pymodbus Response 검사
    if hasattr(rr, "isError") and rr.isError():
        print("write_coils: Response indicates error:", rr)
        return False

    return True

# --- 단일 램프 3개 ---
def L1_set() -> bool:
    _write_coils_block(L1, [True])
    time.sleep(0.05)
    _write_coils_block(L1, [False])
    return True

def L2_set() -> bool:
    _write_coils_block(L2, [True])
    time.sleep(0.05)
    _write_coils_block(L2, [False])
    return True

def L3_set() -> bool:
    _write_coils_block(L3, [True])
    time.sleep(0.05)
    _write_coils_block(L3, [False])
    return True


# --- 두 개 동시 점등 (L10: L1+L2, L11: L2+L3, L12: L1+L3) ---
def L10_set() -> bool:
    _write_coils_block(L1, [True, True])
    time.sleep(0.05)
    _write_coils_block(L1, [False, False])
    return True

def L11_set() -> bool:
    _write_coils_block(L2, [True, True])
    time.sleep(0.05)
    _write_coils_block(L2, [False, False])
    return True

def L12_set() -> bool:
    _write_coils_block(L1, [True, False, True])  # L1, L2, L3 중 L1/L3만 ON
    time.sleep(0.05)
    _write_coils_block(L1, [False, False, False])
    return True

# --- 세 개 동시 점등 (L20: L1+L2+L3) ---
def L20_set() -> bool:
    _write_coils_block(L1, [True, True, True])
    time.sleep(0.08)
    _write_coils_block(L1, [False, False, False])
    return True

timeline = []

def at(ms, fn):
    """ ms(밀리초) 시점에 fn을 실행하도록 등록 """
    timeline.append((int(ms), fn))

def build_timeline():
    """기존 sleep 시퀀스를 절대시간으로 옮긴 예시(일부). 필요 구간을 계속 추가하세요."""
    timeline.clear()

    #전주부분
    at(1400,  L1_set)
    at(1700,  L2_set)
    at(2100,  L10_set)

    at(2900,  L3_set)
    at(3200,  L2_set)
    at(3600,  L11_set)

    at(4400,  L3_set)
    at(4700,  L2_set)
    at(5100,  L11_set)

    at(5900,  L1_set)
    at(6200,  L2_set)
    at(6600,  L10_set)

    at(7400,  L1_set)
    at(7700,  L2_set)
    at(8100,  L10_set)

    at(8900,  L3_set)
    at(9200,  L2_set)
    at(9600,  L11_set)

    at(10400,  L3_set)
    at(10700,  L2_set)
    at(11100,  L11_set)

    at(11900,  L1_set)
    at(12200,  L2_set)
    at(12600,  L10_set)

    #노래부분
    at(13400,  L1_set)
    at(13550,  L2_set)
    at(13700,  L3_set)
    at(13950,  L2_set)
    at(14000,  L1_set)
    at(14400,  L1_set)
    at(14550,  L2_set)
    at(14700,  L1_set)
    at(15000,  L1_set)

    at(15600,  L3_set)
    at(15750,  L2_set)
    at(15900,  L3_set)
    at(16050,  L2_set)
    at(16300,  L11_set)

    at(16700,  L3_set)
    at(16900,  L2_set)
    at(17100,  L1_set)
    at(17300,  L2_set)
    at(17500,  L3_set)
    at(17700,  L10_set)
    at(18100,  L10_set)
    at(18500,  L11_set)
    at(18900,  L11_set)

    at(19200,  L1_set)
    at(19350,  L2_set)
    at(19500,  L3_set)
    at(19600,  L2_set)
    at(19750,  L1_set)
    at(20500,  L3_set)
    at(20700,  L2_set)
    at(21000,  L3_set)
    at(21400,  L11_set)

    at(22200,  L3_set)
    at(22350,  L2_set)
    at(22500,  L1_set)
    at(22800,  L2_set)
    at(23100,  L12_set)
    at(23700,  L1_set)
    at(23850,  L3_set)
    at(24000,  L2_set)
    at(24150,  L1_set)

    #후렴부분
    at(24800,  L1_set)
    at(25000,  L1_set)

    at(25200,  L10_set)
    at(25350,  L10_set)
    at(25500,  L10_set)
    at(25650,  L10_set)
    at(25900,  L11_set)
    at(26050,  L11_set)
    at(26200,  L11_set)
    at(26350,  L11_set)
    at(26600,  L10_set)
    at(26750,  L10_set)
    at(26900,  L10_set)
    at(27050,  L10_set)
    at(27300,  L11_set)
    at(27450,  L11_set)
    at(27600,  L11_set)
    at(27750,  L11_set)
    at(28000,  L20_set)
    at(28300,  L20_set)

    at(29700,  L1_set)
    at(30000,  L2_set)
    at(30300,  L10_set)

    at(31100,  L10_set)
    at(31250,  L10_set)
    at(31400,  L10_set)
    at(31550,  L10_set)
    at(31800,  L11_set)
    at(31950,  L11_set)
    at(32100,  L11_set)
    at(32250,  L11_set)
    at(32500,  L10_set)
    at(32650,  L10_set)
    at(32800,  L10_set)
    at(32950,  L10_set)
    at(33200,  L11_set)
    at(33350,  L11_set)
    at(33500,  L11_set)
    at(33650,  L11_set)
    at(34050,  L20_set)
    at(34300,  L20_set)

    at(35600,  L3_set)
    at(35900,  L2_set)
    at(36200,  L11_set)

def run_synced(tolerance_ms=12, poll_sleep=0.003):
    """pygame 재생 위치와 타임라인을 동기화하여 트리거"""
    if not timeline:
        print("타임라인이 비었습니다. build_timeline()을 먼저 호출하세요.")
        return

    # 시간순 정렬 후 큐
    tl = sorted(timeline, key=lambda x: x[0])
    q = deque(tl)

    fired = set()  # (ms, fn_name) 중복 방지
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy() and q:
        pos = pygame.mixer.music.get_pos()  # ms
        if pos < 0:
            time.sleep(poll_sleep)
            continue

        # 큐 맨 앞 이벤트 검사
        ms, fn = q[0]
        # 아직 이르다
        if pos < ms - tolerance_ms:
            time.sleep(poll_sleep)
            continue

        # 허용오차 구간이거나 이미 지난 경우 → 즉시 실행
        key = (ms, fn.__name__)
        if key not in fired:
            try:
                fn()
            finally:
                fired.add(key)
        q.popleft()

        # 과도한 바쁨 방지
        time.sleep(poll_sleep)

build_timeline()
run_synced(tolerance_ms=12, poll_sleep=0.003)

client.close()