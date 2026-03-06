import pyxel
import random

# ─── Constants ────────────────────────────────────────────────────────────────
W, H = 256, 160
FPS = 30
GROUND_Y = 120          # ground line y
ALLY_BASE_X = 10        # left base x
ENEMY_BASE_X = W - 26   # right base x
BASE_W, BASE_H = 16, 32

# Unit specs: (hp, atk, speed, color, size, name)
UNIT_SPECS = {
    "nekosmall":   (30,  5, 1.2, 12, 8,  "Ko-Neko"),    # cyan  answer 1-20
    "nekobuilder": (60, 10, 0.9,  3, 10, "NekoBuild"),  # green answer 21-49
    "nekodra":     (130, 20, 0.7, 10, 13, "NekoKing"),  # yellow answer 50-81
}
ENEMY_SPECS = [
    (25,  4, 0.8, 8,  8,  "ZakoInu"),   # dark red
    (55,  9, 0.6, 2,  11, "DekaInu"),   # red
    (100, 18, 0.5, 14, 14, "BossInu"),  # orange-ish
]

# ─── Helper ───────────────────────────────────────────────────────────────────
def unit_spec_from_answer(ans: int):
    if ans <= 20:
        return UNIT_SPECS["nekosmall"]
    elif ans <= 49:
        return UNIT_SPECS["nekobuilder"]
    else:
        return UNIT_SPECS["nekodra"]


# ─── Unit ─────────────────────────────────────────────────────────────────────
class Unit:
    def __init__(self, x, hp, atk, speed, color, size, name, side):
        self.x = float(x)
        self.y = float(GROUND_Y)
        self.hp = hp
        self.max_hp = hp
        self.atk = atk
        self.speed = speed
        self.color = color
        self.size = size
        self.name = name
        self.side = side          # "ally" or "enemy"
        self.attacking = False    # paused to fight
        self.attack_timer = 0     # frames between attacks (every 15f)
        self.alive = True

    @property
    def cx(self):
        return self.x + self.size / 2

    @property
    def cy(self):
        return self.y - self.size / 2

    def rect(self):
        return self.x, self.y - self.size, self.size, self.size

    def overlaps(self, other):
        ax1, ax2 = self.x, self.x + self.size
        bx1, bx2 = other.x, other.x + other.size
        return ax1 < bx2 and ax2 > bx1

    def move(self):
        if self.side == "ally":
            self.x += self.speed
        else:
            self.x -= self.speed

    def draw(self):
        rx, ry, rw, rh = self.rect()
        pyxel.rect(int(rx), int(ry), rw, rh, self.color)
        # eyes
        eye_y = int(ry) + 2
        if self.side == "ally":
            pyxel.pset(int(rx) + rw - 2, eye_y, 7)
        else:
            pyxel.pset(int(rx) + 1, eye_y, 7)
        # HP bar
        bar_w = rw
        bar_x = int(rx)
        bar_y = int(ry) - 3
        pyxel.rect(bar_x, bar_y, bar_w, 2, 0)
        filled = max(0, int(bar_w * self.hp / self.max_hp))
        bar_color = 11 if self.side == "ally" else 8
        pyxel.rect(bar_x, bar_y, filled, 2, bar_color)


# ─── Base ─────────────────────────────────────────────────────────────────────
class Base:
    def __init__(self, x, side):
        self.x = x
        self.side = side
        self.hp = 200
        self.max_hp = 200
        self.color = 11 if side == "ally" else 8
        self.w = BASE_W
        self.h = BASE_H

    def draw(self):
        bx = int(self.x)
        by = GROUND_Y - self.h
        pyxel.rect(bx, by, self.w, self.h, self.color)
        # flag
        flag_col = 7
        pyxel.line(bx + self.w // 2, by, bx + self.w // 2, by - 6, flag_col)
        pyxel.tri(bx + self.w // 2, by - 6,
                  bx + self.w // 2 + 5, by - 4,
                  bx + self.w // 2, by - 2, self.color)
        # HP bar
        bar_x = bx
        bar_y = by - 5
        pyxel.rect(bar_x, bar_y, self.w, 2, 0)
        filled = max(0, int(self.w * self.hp / self.max_hp))
        pyxel.rect(bar_x, bar_y, filled, 2, self.color)


# ─── App ──────────────────────────────────────────────────────────────────────
class App:
    def __init__(self):
        pyxel.init(W, H, title="NyankoSenso", fps=FPS)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self):
        self.ally_base = Base(ALLY_BASE_X, "ally")
        self.enemy_base = Base(ENEMY_BASE_X, "enemy")
        self.units: list[Unit] = []
        self.frame = 0
        self.enemy_spawn_interval = 60   # frames between enemy spawns
        self.game_over = False
        self.win = False
        # Quiz
        self.input_buf = ""
        self.gen_quiz()
        self.penalty_timer = 0    # frames to show penalty message
        self.correct_fx_timer = 0

    # ── Quiz ──────────────────────────────────────────────────────────────────
    def gen_quiz(self):
        self.q_a = random.randint(1, 9)
        self.q_b = random.randint(1, 9)
        self.q_ans = self.q_a * self.q_b
        self.input_buf = ""

    def handle_quiz_input(self):
        for k in range(10):
            if pyxel.btnp(pyxel.KEY_0 + k):
                if len(self.input_buf) < 2:
                    self.input_buf += str(k)
        if pyxel.btnp(pyxel.KEY_BACKSPACE):
            self.input_buf = self.input_buf[:-1]
        if pyxel.btnp(pyxel.KEY_RETURN):
            if self.input_buf != "":
                entered = int(self.input_buf)
                if entered == self.q_ans:
                    self.spawn_ally(entered)
                    self.correct_fx_timer = 45
                else:
                    self.ally_base.hp = max(0, self.ally_base.hp - 10)
                    self.penalty_timer = 45
                self.gen_quiz()

    # ── Spawn ─────────────────────────────────────────────────────────────────
    def spawn_ally(self, ans: int):
        hp, atk, spd, col, sz, name = unit_spec_from_answer(ans)
        u = Unit(ALLY_BASE_X + BASE_W, hp, atk, spd, col, sz, name, "ally")
        self.units.append(u)

    def spawn_enemy(self):
        tier = min(2, self.frame // (FPS * 60))
        spec = ENEMY_SPECS[tier]
        hp, atk, spd, col, sz, name = spec
        hp = int(hp * random.uniform(0.9, 1.2))
        u = Unit(ENEMY_BASE_X - sz, hp, atk, spd, col, sz, name, "enemy")
        self.units.append(u)

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self):
        if self.game_over:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        self.frame += 1

        self.handle_quiz_input()

        if self.penalty_timer > 0:
            self.penalty_timer -= 1
        if self.correct_fx_timer > 0:
            self.correct_fx_timer -= 1

        # enemy auto-spawn, gradually faster
        interval = max(25, self.enemy_spawn_interval - (self.frame // (FPS * 30)) * 5)
        if self.frame % interval == 0:
            self.spawn_enemy()

        allies = [u for u in self.units if u.side == "ally" and u.alive]
        enemies = [u for u in self.units if u.side == "enemy" and u.alive]

        # reset attacking flag
        for u in self.units:
            u.attacking = False

        # detect collisions
        for a in allies:
            for e in enemies:
                if a.overlaps(e):
                    a.attacking = True
                    e.attacking = True

        # ally attacks
        for a in allies:
            if a.attacking:
                a.attack_timer += 1
                if a.attack_timer >= 15:
                    a.attack_timer = 0
                    for e in enemies:
                        if a.overlaps(e):
                            e.hp -= a.atk
                            if e.hp <= 0:
                                e.alive = False
                            break
            else:
                a.attack_timer = 0

        # enemy attacks
        for e in enemies:
            if e.attacking:
                e.attack_timer += 1
                if e.attack_timer >= 15:
                    e.attack_timer = 0
                    for a in allies:
                        if e.overlaps(a):
                            a.hp -= e.atk
                            if a.hp <= 0:
                                a.alive = False
                            break
            else:
                e.attack_timer = 0

        # movement
        for u in self.units:
            if u.alive and not u.attacking:
                u.move()

        # allies hitting enemy base
        for a in [u for u in self.units if u.side == "ally" and u.alive]:
            if a.x + a.size >= ENEMY_BASE_X:
                a.attacking = True
                a.attack_timer += 1
                if a.attack_timer >= 15:
                    a.attack_timer = 0
                    self.enemy_base.hp -= a.atk
                a.x = float(ENEMY_BASE_X - a.size)

        # enemies hitting ally base
        for e in [u for u in self.units if u.side == "enemy" and u.alive]:
            if e.x <= ALLY_BASE_X + BASE_W:
                e.attacking = True
                e.attack_timer += 1
                if e.attack_timer >= 15:
                    e.attack_timer = 0
                    self.ally_base.hp -= e.atk
                e.x = float(ALLY_BASE_X + BASE_W)

        # remove dead units
        self.units = [u for u in self.units if u.alive]

        # win / lose check
        if self.ally_base.hp <= 0:
            self.game_over = True
            self.win = False
        if self.enemy_base.hp <= 0:
            self.game_over = True
            self.win = True

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self):
        pyxel.cls(1)  # dark blue sky

        # ground
        pyxel.rect(0, GROUND_Y, W, H - GROUND_Y, 4)
        pyxel.line(0, GROUND_Y, W, GROUND_Y, 11)

        # bases
        self.ally_base.draw()
        self.enemy_base.draw()

        # units
        for u in self.units:
            if u.alive:
                u.draw()

        # ── HUD ───────────────────────────────────────────────────────────────
        # top quiz bar
        pyxel.rect(0, 0, W, 18, 0)
        pyxel.text(2, 2, "MATH QUIZ", 7)
        quiz_str = f"{self.q_a} x {self.q_b} = ?"
        pyxel.text(50, 2, quiz_str, 10)
        ans_disp = self.input_buf if self.input_buf else "_"
        pyxel.text(50, 10, f"Input: {ans_disp}", 15)

        # base HP labels below quiz bar
        pyxel.text(2, 20, f"BASE:{self.ally_base.hp}", 11)
        pyxel.text(W - 44, 20, f"ENEMY:{self.enemy_base.hp}", 8)

        # elapsed time
        sec = self.frame // FPS
        pyxel.text(W // 2 - 10, 2, f"T:{sec:03d}s", 6)

        # unit type legend (bottom)
        pyxel.text(2, H - 14, "1-20:Ko-Neko  21-49:NekoBuild  50-81:NekoKing", 5)

        # feedback messages
        if self.penalty_timer > 0:
            pyxel.text(W // 2 - 30, 30, "WRONG! -10HP!", 8)
        if self.correct_fx_timer > 0:
            pyxel.text(W // 2 - 24, 30, "CORRECT!", 10)

        # game over overlay
        if self.game_over:
            pyxel.rect(W // 2 - 45, H // 2 - 18, 90, 36, 0)
            if self.win:
                pyxel.text(W // 2 - 28, H // 2 - 10, "YOU WIN!", 10)
            else:
                pyxel.text(W // 2 - 36, H // 2 - 10, "GAME OVER...", 8)
            pyxel.text(W // 2 - 34, H // 2 + 4, "Press R to retry", 7)


if __name__ == "__main__":
    App()
