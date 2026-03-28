"""
=== 스팀 게이밍 패드 - PC 서버 ===
PC에서 실행하세요. 태블릿에서 보내는 터치 입력을 받아 실제 키보드 입력으로 변환합니다.

사용법:
  1. pip install pynput
  2. python server.py
  3. 표시되는 IP 주소를 태블릿 클라이언트에 입력
"""

import socket
import threading
import json
import sys

try:
    from pynput.keyboard import Controller, Key
except ImportError:
    print("=" * 50)
    print("  pynput 설치가 필요합니다!")
    print("  pip install pynput")
    print("=" * 50)
    sys.exit(1)

keyboard = Controller()

# 키 매핑: 클라이언트에서 보내는 이름 -> pynput Key
KEY_MAP = {
    # WASD (조이스틱)
    'w': 'w', 'a': 'a', 's': 's', 'd': 'd',
    # 액션 버튼 (ABXY)
    'j': 'j', 'k': 'k', 'l': 'l', 'i': 'i', 'u': 'u',
    # 트리거
    'q': 'q', 'e': 'e', 'r': 'r', 'f': 'f',
    # 특수키
    'space': Key.space,
    'enter': Key.enter,
    'escape': Key.esc,
    'shift': Key.shift_l,
    'tab': Key.tab,
    'ctrl': Key.ctrl_l,
    # 방향키
    'up': Key.up, 'down': Key.down,
    'left': Key.left, 'right': Key.right,
}

# 현재 눌린 키 추적
pressed_keys = set()

PORT = 9877


def get_local_ip():
    """로컬 IP 주소 가져오기"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def press_key(key_name):
    """키 누르기"""
    key = KEY_MAP.get(key_name)
    if key and key_name not in pressed_keys:
        pressed_keys.add(key_name)
        try:
            keyboard.press(key)
        except Exception as e:
            print(f"  키 입력 오류: {e}")


def release_key(key_name):
    """키 떼기"""
    key = KEY_MAP.get(key_name)
    if key and key_name in pressed_keys:
        pressed_keys.discard(key_name)
        try:
            keyboard.release(key)
        except Exception as e:
            print(f"  키 해제 오류: {e}")


def release_all():
    """모든 키 해제"""
    for key_name in list(pressed_keys):
        release_key(key_name)


def handle_client(conn, addr):
    """클라이언트 연결 처리"""
    print(f"\n  태블릿 연결됨: {addr[0]}")
    print("  게임패드 입력 수신 중...\n")

    buffer = ""
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break

            buffer += data.decode('utf-8')
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if not line:
                    continue

                try:
                    msg = json.loads(line)
                    action = msg.get('action')
                    key = msg.get('key', '')

                    if action == 'press':
                        press_key(key)
                        print(f"  [PRESS] {key}")
                    elif action == 'release':
                        release_key(key)
                        print(f"  [RELEASE] {key}")
                    elif action == 'ping':
                        conn.sendall(b'{"status":"ok"}\n')
                except json.JSONDecodeError:
                    pass
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        release_all()
        conn.close()
        print(f"  태블릿 연결 해제: {addr[0]}")


def main():
    ip = get_local_ip()

    print()
    print("=" * 50)
    print("   스팀 게이밍 패드 - PC 서버")
    print("=" * 50)
    print()
    print(f"   IP 주소: {ip}")
    print(f"   포트:    {PORT}")
    print()
    print("   태블릿 클라이언트에서 위 IP를 입력하세요")
    print("   종료: Ctrl+C")
    print()
    print("=" * 50)
    print()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', PORT))
    server.listen(2)

    print("  대기 중... 태블릿에서 연결해주세요\n")

    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n  서버 종료")
        release_all()
        server.close()


if __name__ == '__main__':
    main()
