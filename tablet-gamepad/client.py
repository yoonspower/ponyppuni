"""
=== 스팀 게이밍 패드 - 태블릿 클라이언트 ===
태블릿에서 실행하세요. 터치 게임패드 UI를 표시하고 PC로 입력을 전송합니다.

사용법:
  1. pip install pygame
  2. python client.py
  3. PC 서버의 IP 주소를 입력하고 연결
"""

import pygame
import socket
import json
import sys
import math
import threading
import time

# ── 색상 ──
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY_BG = (20, 20, 30)
DARK_GRAY = (35, 35, 50)

# 버튼 색상 (R, G, B, alpha 느낌으로 사용)
GREEN = (76, 175, 80)
RED = (244, 67, 54)
BLUE = (33, 150, 243)
YELLOW = (255, 193, 7)
TRIGGER_COLOR = (80, 80, 120)
SPECIAL_COLOR = (60, 60, 90)
DPAD_COLOR = (70, 70, 100)

PORT = 9877


class NetworkClient:
    """PC 서버와 소켓 통신"""

    def __init__(self):
        self.sock = None
        self.connected = False
        self.lock = threading.Lock()

    def connect(self, ip):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(3)
            self.sock.connect((ip, PORT))
            self.sock.settimeout(None)
            self.connected = True
            return True
        except Exception as e:
            print(f"연결 실패: {e}")
            self.connected = False
            return False

    def send(self, action, key):
        if not self.connected:
            return
        msg = json.dumps({"action": action, "key": key}) + "\n"
        with self.lock:
            try:
                self.sock.sendall(msg.encode('utf-8'))
            except Exception:
                self.connected = False

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.connected = False


class Button:
    """터치 가능한 버튼"""

    def __init__(self, x, y, w, h, label, key, color=TRIGGER_COLOR, radius=0, font_size=20):
        self.rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
        self.label = label
        self.key = key
        self.color = color
        self.radius = radius if radius > 0 else min(w, h) // 4
        self.font_size = font_size
        self.pressed = False
        self.touch_id = None

    def draw(self, screen, font, pad_alpha):
        if self.pressed:
            alpha = min(pad_alpha + 80, 200)
        else:
            alpha = pad_alpha

        # 버튼 표면 (반투명)
        surf = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        color_a = (*self.color, alpha)
        pygame.draw.rect(surf, color_a, (0, 0, self.rect.w, self.rect.h),
                         border_radius=self.radius)

        # 테두리
        border_a = (*WHITE, alpha // 2)
        pygame.draw.rect(surf, border_a, (0, 0, self.rect.w, self.rect.h),
                         width=2, border_radius=self.radius)

        screen.blit(surf, self.rect.topleft)

        # 글자
        txt_alpha = min(alpha + 60, 255)
        txt_surf = font.render(self.label, True, (*WHITE, txt_alpha))
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        screen.blit(txt_surf, txt_rect)

    def contains(self, pos):
        return self.rect.collidepoint(pos)


class CircleButton(Button):
    """원형 버튼"""

    def __init__(self, x, y, r, label, key, color=TRIGGER_COLOR, font_size=22):
        super().__init__(x, y, r * 2, r * 2, label, key, color, r, font_size)
        self.cx = x
        self.cy = y
        self.r = r

    def draw(self, screen, font, pad_alpha):
        if self.pressed:
            alpha = min(pad_alpha + 80, 200)
        else:
            alpha = pad_alpha

        surf = pygame.Surface((self.r * 2, self.r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (self.r, self.r), self.r)
        pygame.draw.circle(surf, (*WHITE, alpha // 2), (self.r, self.r), self.r, 2)
        screen.blit(surf, (self.cx - self.r, self.cy - self.r))

        txt_alpha = min(alpha + 60, 255)
        txt_surf = font.render(self.label, True, (*WHITE, txt_alpha))
        txt_rect = txt_surf.get_rect(center=(self.cx, self.cy))
        screen.blit(txt_surf, txt_rect)

    def contains(self, pos):
        dx = pos[0] - self.cx
        dy = pos[1] - self.cy
        return dx * dx + dy * dy <= self.r * self.r


class Joystick:
    """아날로그 조이스틱"""

    def __init__(self, cx, cy, base_r, thumb_r):
        self.cx = cx
        self.cy = cy
        self.base_r = base_r
        self.thumb_r = thumb_r
        self.thumb_x = cx
        self.thumb_y = cy
        self.active = False
        self.touch_id = None
        self.keys = {'up': False, 'down': False, 'left': False, 'right': False}
        self.key_map = {'up': 'w', 'down': 's', 'left': 'a', 'right': 'd'}

    def draw(self, screen, pad_alpha):
        if self.active:
            alpha = min(pad_alpha + 60, 200)
        else:
            alpha = pad_alpha

        # 베이스
        surf = pygame.Surface((self.base_r * 2, self.base_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*WHITE, alpha // 4), (self.base_r, self.base_r), self.base_r)
        pygame.draw.circle(surf, (*WHITE, alpha // 2), (self.base_r, self.base_r), self.base_r, 2)
        screen.blit(surf, (self.cx - self.base_r, self.cy - self.base_r))

        # 방향 표시
        dirs = [
            (self.cx, self.cy - self.base_r + 18, '▲', self.keys['up']),
            (self.cx, self.cy + self.base_r - 18, '▼', self.keys['down']),
            (self.cx - self.base_r + 18, self.cy, '◀', self.keys['left']),
            (self.cx + self.base_r - 18, self.cy, '▶', self.keys['right']),
        ]
        dir_font = pygame.font.SysFont(None, 20)
        for dx, dy, ch, on in dirs:
            a = min(alpha + 80, 255) if on else alpha // 2
            ts = dir_font.render(ch, True, (*WHITE, a))
            screen.blit(ts, ts.get_rect(center=(dx, dy)))

        # 썸 (움직이는 원)
        t_surf = pygame.Surface((self.thumb_r * 2, self.thumb_r * 2), pygame.SRCALPHA)
        t_alpha = min(alpha + 40, 220)
        pygame.draw.circle(t_surf, (*WHITE, t_alpha // 2), (self.thumb_r, self.thumb_r), self.thumb_r)
        pygame.draw.circle(t_surf, (*WHITE, t_alpha), (self.thumb_r, self.thumb_r), self.thumb_r, 2)
        screen.blit(t_surf, (self.thumb_x - self.thumb_r, self.thumb_y - self.thumb_r))

    def contains(self, pos):
        dx = pos[0] - self.cx
        dy = pos[1] - self.cy
        return dx * dx + dy * dy <= self.base_r * self.base_r

    def update(self, pos, net):
        dx = pos[0] - self.cx
        dy = pos[1] - self.cy
        dist = math.sqrt(dx * dx + dy * dy)
        max_dist = self.base_r - self.thumb_r

        if dist > max_dist:
            dx = dx / dist * max_dist
            dy = dy / dist * max_dist

        self.thumb_x = self.cx + dx
        self.thumb_y = self.cy + dy

        deadzone = max_dist * 0.25
        new_keys = {
            'up': dy < -deadzone,
            'down': dy > deadzone,
            'left': dx < -deadzone,
            'right': dx > deadzone,
        }

        for d in new_keys:
            if new_keys[d] and not self.keys[d]:
                net.send('press', self.key_map[d])
            elif not new_keys[d] and self.keys[d]:
                net.send('release', self.key_map[d])

        self.keys = new_keys

    def reset(self, net):
        self.thumb_x = self.cx
        self.thumb_y = self.cy
        self.active = False
        self.touch_id = None
        for d in self.keys:
            if self.keys[d]:
                net.send('release', self.key_map[d])
        self.keys = {'up': False, 'down': False, 'left': False, 'right': False}


class GamePad:
    """메인 게임패드 앱"""

    def __init__(self):
        pygame.init()

        # 화면 설정 (전체화면)
        info = pygame.display.Info()
        self.W = info.current_w
        self.H = info.current_h
        self.screen = pygame.display.set_mode((self.W, self.H), pygame.FULLSCREEN)
        pygame.display.set_caption("게이밍 패드")

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        self.font_sm = pygame.font.SysFont(None, 18)
        self.font_lg = pygame.font.SysFont(None, 32)
        self.font_title = pygame.font.SysFont(None, 40)

        self.net = NetworkClient()
        self.pad_alpha = 50  # 기본 투명도 (0~255)
        self.running = True
        self.state = 'connect'  # 'connect' or 'pad'
        self.pad_visible = True  # 패드 표시/숨김 토글
        self.ip_text = ''
        self.connect_msg = ''
        self.touch_map = {}  # touch_id -> button/joystick

        self._init_controls()

    def _init_controls(self):
        """엑스박스 컨트롤러 레이아웃"""
        W, H = self.W, self.H

        # ── 왼쪽 스틱 (엑스박스: 왼쪽 위) ──
        self.joystick = Joystick(150, H // 2 - 20, 80, 30)

        # ── ABXY (엑스박스 배치: A아래 B오른 X왼 Y위) ──
        abxy_cx = W - 150
        abxy_cy = H // 2 + 30
        abxy_r = 34
        abxy_gap = 54

        # ── 엑스박스 컬러: A=초록 B=빨강 X=파랑 Y=노랑 ──
        XBOX_GREEN = (16, 124, 16)
        XBOX_RED = (176, 36, 24)
        XBOX_BLUE = (0, 80, 200)
        XBOX_YELLOW = (200, 160, 0)

        self.buttons = [
            # ABXY (엑스박스 배치)
            CircleButton(abxy_cx, abxy_cy + abxy_gap, abxy_r, "A", "j", XBOX_GREEN),
            CircleButton(abxy_cx + abxy_gap, abxy_cy, abxy_r, "B", "l", XBOX_RED),
            CircleButton(abxy_cx - abxy_gap, abxy_cy, abxy_r, "X", "u", XBOX_BLUE),
            CircleButton(abxy_cx, abxy_cy - abxy_gap, abxy_r, "Y", "i", XBOX_YELLOW),

            # LB RB (범퍼 - 상단)
            Button(100, 30, 90, 38, "LB", "q", TRIGGER_COLOR, 19),
            Button(W - 100, 30, 90, 38, "RB", "e", TRIGGER_COLOR, 19),

            # LT RT (트리거 - 범퍼 위)
            Button(220, 30, 90, 38, "LT", "shift", TRIGGER_COLOR, 19),
            Button(W - 220, 30, 90, 38, "RT", "space", TRIGGER_COLOR, 19),

            # View(Back) / Menu(Start) (가운데)
            CircleButton(W // 2 - 50, H // 2 - 40, 18, "⊞", "escape", SPECIAL_COLOR, 14),
            CircleButton(W // 2 + 50, H // 2 - 40, 18, "≡", "enter", SPECIAL_COLOR, 14),

            # Xbox 버튼 (가운데 위)
            CircleButton(W // 2, H // 2 - 90, 20, "X", "tab", (30, 120, 30), 16),

            # D-Pad (왼쪽 아래)
            Button(150, H - 130, 44, 44, "▲", "up", DPAD_COLOR, 8, 18),
            Button(150, H - 46, 44, 44, "▼", "down", DPAD_COLOR, 8, 18),
            Button(108, H - 88, 44, 44, "◀", "left", DPAD_COLOR, 8, 18),
            Button(192, H - 88, 44, 44, "▶", "right", DPAD_COLOR, 8, 18),

            # LS RS (스틱 클릭)
            CircleButton(W // 2 - 50, H - 50, 22, "LS", "f", SPECIAL_COLOR, 14),
            CircleButton(W // 2 + 50, H - 50, 22, "RS", "r", SPECIAL_COLOR, 14),
        ]

    def run(self):
        while self.running:
            if self.state == 'connect':
                self._connect_screen()
            else:
                self._pad_screen()
            self.clock.tick(60)

        self.net.close()
        pygame.quit()

    # ── 연결 화면 ──
    def _connect_screen(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return
                elif event.key == pygame.K_RETURN:
                    self._try_connect()
                elif event.key == pygame.K_BACKSPACE:
                    self.ip_text = self.ip_text[:-1]
                else:
                    ch = event.unicode
                    if ch and (ch.isdigit() or ch == '.'):
                        self.ip_text += ch
            elif event.type == pygame.FINGERDOWN:
                # 터치로 숫자 키패드 입력 (간단한 UI)
                self._handle_connect_touch(event)

        self.screen.fill(GRAY_BG)

        # 타이틀
        t = self.font_title.render("Steam Gaming Pad", True, WHITE)
        self.screen.blit(t, t.get_rect(center=(self.W // 2, self.H // 4)))

        sub = self.font.render("PC server IP address:", True, (*WHITE, 150))
        self.screen.blit(sub, sub.get_rect(center=(self.W // 2, self.H // 4 + 50)))

        # IP 입력 박스
        box_w, box_h = 320, 50
        box_rect = pygame.Rect(self.W // 2 - box_w // 2, self.H // 2 - box_h // 2, box_w, box_h)
        pygame.draw.rect(self.screen, DARK_GRAY, box_rect, border_radius=12)
        pygame.draw.rect(self.screen, (*WHITE, 80), box_rect, width=2, border_radius=12)

        ip_surf = self.font_lg.render(self.ip_text + "|", True, WHITE)
        self.screen.blit(ip_surf, ip_surf.get_rect(center=box_rect.center))

        # 숫자 키패드 (터치용)
        keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', '<']
        kw, kh = 70, 50
        start_x = self.W // 2 - (3 * kw + 20) // 2
        start_y = self.H // 2 + 50

        self._numpad_rects = []
        for i, k in enumerate(keys):
            row = i // 3
            col = i % 3
            x = start_x + col * (kw + 10)
            y = start_y + row * (kh + 8)
            r = pygame.Rect(x, y, kw, kh)
            self._numpad_rects.append((r, k))

            pygame.draw.rect(self.screen, DARK_GRAY, r, border_radius=10)
            pygame.draw.rect(self.screen, (*WHITE, 60), r, width=1, border_radius=10)
            ks = self.font.render(k, True, WHITE)
            self.screen.blit(ks, ks.get_rect(center=r.center))

        # 연결 버튼
        btn_rect = pygame.Rect(self.W // 2 - 80, start_y + 4 * (kh + 8) + 10, 160, 48)
        self._connect_btn_rect = btn_rect
        pygame.draw.rect(self.screen, (50, 80, 180), btn_rect, border_radius=12)
        bt = self.font.render("Connect", True, WHITE)
        self.screen.blit(bt, bt.get_rect(center=btn_rect.center))

        # 메시지
        if self.connect_msg:
            ms = self.font_sm.render(self.connect_msg, True, (255, 100, 100))
            self.screen.blit(ms, ms.get_rect(center=(self.W // 2, btn_rect.bottom + 30)))

        # ESC 안내
        esc = self.font_sm.render("ESC = exit", True, (*WHITE, 80))
        self.screen.blit(esc, (10, self.H - 25))

        pygame.display.flip()

    def _handle_connect_touch(self, event):
        tx = int(event.x * self.W)
        ty = int(event.y * self.H)
        pos = (tx, ty)

        if hasattr(self, '_numpad_rects'):
            for r, k in self._numpad_rects:
                if r.collidepoint(pos):
                    if k == '<':
                        self.ip_text = self.ip_text[:-1]
                    else:
                        self.ip_text += k
                    return

        if hasattr(self, '_connect_btn_rect') and self._connect_btn_rect.collidepoint(pos):
            self._try_connect()

    def _try_connect(self):
        ip = self.ip_text.strip()
        if not ip:
            self.connect_msg = "IP address required"
            return
        self.connect_msg = "Connecting..."
        pygame.display.flip()

        if self.net.connect(ip):
            self.state = 'pad'
            self.connect_msg = ''
        else:
            self.connect_msg = "Connection failed. Check IP and server."

    # ── 게임패드 화면 ──
    def _pad_screen(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.net.close()
                    self.state = 'connect'
                    self.connect_msg = ''
                    return
            elif event.type == pygame.FINGERDOWN:
                pos = self._get_touch_pos(event)
                # 토글 버튼 체크 (항상 우선)
                if self._toggle_rect.collidepoint(pos):
                    self._toggle_pad()
                elif self.pad_visible:
                    self._on_touch_down(event)
            elif event.type == pygame.FINGERMOTION:
                if self.pad_visible:
                    self._on_touch_move(event)
            elif event.type == pygame.FINGERUP:
                if self.pad_visible:
                    self._on_touch_up(event)

        # 연결 확인
        if not self.net.connected:
            self.state = 'connect'
            self.connect_msg = "Connection lost"
            return

        # 그리기
        self.screen.fill((0, 0, 0))

        if self.pad_visible:
            # 조이스틱
            self.joystick.draw(self.screen, self.pad_alpha)

            # 버튼
            for btn in self.buttons:
                btn.draw(self.screen, self.font, self.pad_alpha)

            # 상태 표시
            status = self.font_sm.render("Connected | ESC = back", True, (*WHITE, 60))
            self.screen.blit(status, (self.W // 2 - status.get_width() // 2, self.H - 20))

            # 투명도 표시
            op_text = self.font_sm.render(f"Opacity: {self.pad_alpha}", True, (*WHITE, 60))
            self.screen.blit(op_text, (self.W - 120, self.H - 20))

        # 토글 버튼 (패드 숨겨도 항상 표시)
        self._draw_toggle_btn()

        pygame.display.flip()

    def _draw_toggle_btn(self):
        """패드 ON/OFF 토글 버튼 (항상 표시)"""
        tw, th = 50, 50
        margin = 10
        self._toggle_rect = pygame.Rect(self.W - tw - margin, self.H // 2 - th // 2, tw, th)

        surf = pygame.Surface((tw, th), pygame.SRCALPHA)
        if self.pad_visible:
            pygame.draw.rect(surf, (30, 120, 30, 160), (0, 0, tw, th), border_radius=12)
            pygame.draw.rect(surf, (80, 200, 80, 120), (0, 0, tw, th), width=2, border_radius=12)
        else:
            pygame.draw.rect(surf, (120, 30, 30, 160), (0, 0, tw, th), border_radius=12)
            pygame.draw.rect(surf, (200, 80, 80, 120), (0, 0, tw, th), width=2, border_radius=12)
        self.screen.blit(surf, self._toggle_rect.topleft)

        label = "ON" if self.pad_visible else "OFF"
        txt = self.font_sm.render(label, True, WHITE)
        self.screen.blit(txt, txt.get_rect(center=self._toggle_rect.center))

    def _toggle_pad(self):
        """패드 표시/숨김 전환, 숨길 때 눌린 키 모두 해제"""
        self.pad_visible = not self.pad_visible
        if not self.pad_visible:
            # 조이스틱 리셋
            if self.joystick.active:
                self.joystick.reset(self.net)
            # 눌린 버튼 모두 해제
            for btn in self.buttons:
                if btn.pressed:
                    btn.pressed = False
                    btn.touch_id = None
                    self.net.send('release', btn.key)
            self.touch_map.clear()

    def _get_touch_pos(self, event):
        return (int(event.x * self.W), int(event.y * self.H))

    def _on_touch_down(self, event):
        pos = self._get_touch_pos(event)
        tid = event.finger_id

        # 조이스틱 체크
        if not self.joystick.active and self.joystick.contains(pos):
            self.joystick.active = True
            self.joystick.touch_id = tid
            self.joystick.update(pos, self.net)
            self.touch_map[tid] = self.joystick
            return

        # 버튼 체크
        for btn in self.buttons:
            if btn.contains(pos) and not btn.pressed:
                btn.pressed = True
                btn.touch_id = tid
                self.touch_map[tid] = btn
                self.net.send('press', btn.key)
                return

    def _on_touch_move(self, event):
        tid = event.finger_id
        pos = self._get_touch_pos(event)

        obj = self.touch_map.get(tid)
        if obj is self.joystick:
            self.joystick.update(pos, self.net)

    def _on_touch_up(self, event):
        tid = event.finger_id

        obj = self.touch_map.pop(tid, None)
        if obj is self.joystick:
            self.joystick.reset(self.net)
        elif isinstance(obj, (Button, CircleButton)):
            if obj.pressed:
                obj.pressed = False
                obj.touch_id = None
                self.net.send('release', obj.key)


def main():
    app = GamePad()
    app.run()


if __name__ == '__main__':
    main()
