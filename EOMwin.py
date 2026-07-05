import time, os, sys, random, curses, math, inspect, builtins

# ── WINDOWS COMPATIBILITY FIXES ────────────────────────────
if os.name == 'nt':
    os.system('')  # Forces Windows Command Prompt to support ANSI colors
    sys.stdout.reconfigure(encoding='utf-8')  # Forces Windows to display box-drawing lines correctly
# ───────────────────────────────────────────────────────────
 
# ══════════════════════════════════════════════════════════
#  ECHOES OF MIDDLEWHERE -- COMPLETE BUILD v3
#  Ashwood + Pale Fields + Blackwater Rot + Static Mountains + Pillar of Magma + Everlasting dunes + Capital of Nothing + ALL DAMN ENDINGS
#  By CrisGG and property (not legally acknowledged) of Bad Games Studio
# ══════════════════════════════════════════════════════════
 
SAVE_SLOTS = ["slot1.dat", "slot2.dat", "slot3.dat"]
 
# ── BASE ──────────────────────────────────────────────────
def clear():
    os.system("clear" if os.name == "posix" else "cls")
 
def typewrite(msg, delay=0.05):
    for char in msg:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()
 
def slow_print(lines, delay=0.18):
    for line in lines:
        print(line)
        time.sleep(delay)
 
def pinwheel(seconds):
    frames = ['|', '/', '-', '\\']
    end = time.time() + seconds
    i = 0
    while time.time() < end:
        print(f'\r  {frames[i%4]}', end='', flush=True)
        time.sleep(0.1)
        i += 1
    print('\r   ')

# ══════════════════════════════════════════════════════════
#  DEV MODE -- type 3113 at any prompt to open the dev menu
# ══════════════════════════════════════════════════════════
DEV_CODE = "3113"

def _dev_find_ctx():
    """Walk the call stack looking for the nearest 'player' dict and 'slot' int
    that are actually in scope wherever dinput() was called from. This lets the
    dev code work from literally any input() prompt in the game without having
    to thread player/slot through every single function."""
    player = None
    slot = None
    frame = inspect.currentframe().f_back.f_back  # skip this fn + dinput()
    while frame:
        loc = frame.f_locals
        if player is None:
            for name in ("player", "player_dict"):
                cand = loc.get(name)
                if isinstance(cand, dict) and "stats" in cand and "hp" in cand:
                    player = cand
                    break
        if slot is None:
            cand = loc.get("slot")
            if isinstance(cand, int) and 0 <= cand <= 2:
                slot = cand
        if player is not None and slot is not None:
            break
        frame = frame.f_back
    return player, slot

def dinput(prompt=""):
    """Drop-in replacement for input(). Every input() call in the game has been
    routed through this. If the person types the dev code, it opens the dev
    menu instead of passing that value along to whatever was asking."""
    while True:
        raw = builtins.input(prompt)
        if raw.strip() == DEV_CODE:
            player, slot = _dev_find_ctx()
            dev_menu(player, slot)
            continue
        return raw
 
# ══════════════════════════════════════════════════════════
#  STATS
# ══════════════════════════════════════════════════════════
STAT_ORDER = ["HP","STR","RES","AGI","WIL","PER"]
TOTAL_PTS  = 40
STAT_MIN   = 1
 
STAT_INFO = {
    "HP":  {"label":"HP           ","desc":"Your life force. Hit zero and you're gone.","max":50},
    "STR": {"label":"STRENGTH     ","desc":"Raw power. Scales heavy weapons.","max":40},
    "RES": {"label":"RESISTANCE   ","desc":"Damage reduction per point.","max":40},
    "AGI": {"label":"AGILITY      ","desc":"Speed and dodge chance.","max":40},
    "WIL": {"label":"WILL         ","desc":"Mental fortitude. Resists fear enemies.","max":40},
    "PER": {"label":"PERCEPTION   ","desc":"Item find and drop rates.","max":40},
}
 
def make_player(stats):
    p = {
        "base_stats":  dict(stats),
        "stats":       dict(stats),
        "max_hp":      stats["HP"]*5,
        "hp":          stats["HP"]*5,
        "level":       1,
        "xp":          0,
        "xp_next":     100,
        "weapon":      "bare_hands",
        "talisman":    None,
        "inventory":   [],
        "consumables": {},
        "location":    "crossroads",
        "visited":     [],
        "flags":       {},
        "void_score":  0,
        "trust_score": 0,
        "unlocked":    [],
        "status":      {},   # active status effects e.g. {"toxic":3}
    }
    _recalc(p)
    return p
 
def _soft(val, threshold=40):
    """Linear up to threshold, then sqrt-compressed above it (diminishing returns)."""
    if val <= threshold:
        return val
    return threshold + math.sqrt(val - threshold)

def _recalc(p):
    if "base_stats" not in p:
        p["base_stats"] = dict(p["stats"])
    p["stats"] = dict(p["base_stats"])
    s = p["stats"]
    p["max_hp"]       = s["HP"]*5
    p["hp"]           = min(p["hp"], p["max_hp"])
    p["dodge_chance"] = _soft(s["AGI"]) * 3
    p["dmg_bonus"]    = _soft(s["STR"]) * 2
    p["dmg_redux"]    = _soft(s["RES"]) * 0.5
    p["item_find"]    = _soft(s["PER"]) * 2
    t = p.get("talisman")
    if "toxic_immune" in p["status"]:
        del p["status"]["toxic_immune"]
    if t == "ashen_bark":      p["dmg_redux"] += 5
    elif t == "pale_eye":      p["item_find"] += 10
    elif t == "choir_remnant": p["status"]["toxic_immune"] = True
    elif t == "mountain_still":
        p["stats"]["AGI"] = min(40, p["stats"]["AGI"] + 3)
        p["dodge_chance"] = _soft(p["stats"]["AGI"]) * 3
 
def stat_check(p, stat, diff):
    return (random.randint(1,20) + p["stats"][stat]) >= diff
 
def character_creation():
    stats    = {s: STAT_MIN for s in STAT_ORDER}
    selected = 0
    while True:
        while True:
            pts_left = TOTAL_PTS - (sum(stats.values()) - len(STAT_ORDER)*STAT_MIN)
            clear()
            print("")
            print("  ╔══════════════════════════════════════════╗")
            print("  ║   THE LOST -- DEFINE YOURSELF            ║")
            print(f"  ║   POINTS REMAINING: {pts_left:<22}      ║")
            print("  ╠══════════════════════════════════════════╣")
            print("")
            for i,key in enumerate(STAT_ORDER):
                v=stats[key]; c=STAT_INFO[key]["max"]
                f=int((v/c)*20)
                ptr=">>" if i==selected else "  "
                print(f"  {ptr} {STAT_INFO[key]['label']} [{'█'*f}{'░'*(20-f)}] {v:>2}/{c}")
                time.sleep(0.02)
            print(f"\n  {STAT_INFO[STAT_ORDER[selected]]['desc']}")
            print("\n  W/S navigate   +/- point   ENTER confirm   reset\n")
            cmd = dinput("  > ").strip().lower()
            if cmd=='w':   selected=(selected-1)%len(STAT_ORDER)
            elif cmd=='s': selected=(selected+1)%len(STAT_ORDER)
            elif cmd in ('+','='):
                k=STAT_ORDER[selected]
                if pts_left>0 and stats[k]<STAT_INFO[k]["max"]:
                    stats[k]+=1
                elif pts_left==0:
                    typewrite("  NO POINTS LEFT.",0.04); time.sleep(0.6)
                elif stats[k]>=STAT_INFO[k]["max"]:
                    typewrite(f"  {STAT_INFO[k]['label'].strip()} IS AT MAX.",0.04); time.sleep(0.6)
            elif cmd=='-':
                k=STAT_ORDER[selected]
                if stats[k]>STAT_MIN: stats[k]-=1
            elif cmd=="reset": stats={s:STAT_MIN for s in STAT_ORDER}
            elif cmd=="":
                if pts_left>0: typewrite(f"  {pts_left} POINTS REMAINING.",0.04); time.sleep(0.8)
                else: break
        clear()
        slow_print(["","  BUILD CONFIRMED.",""],0.15)
        for key in STAT_ORDER:
            v=stats[key]; c=STAT_INFO[key]["max"]; f=int((v/c)*20)
            print(f"  {STAT_INFO[key]['label']} [{'█'*f}{'░'*(20-f)}] {v}")
            time.sleep(0.08)
        print("")
        if dinput("  CONFIRM? Y/N: ").strip().lower()=='y':
            return stats
 
def level_up(player):
    if "base_stats" not in player:
        player["base_stats"] = dict(player["stats"])
    player["level"]+=1; player["xp"]=0; player["xp_next"]+=50
    bonus=5; selected=0
    while bonus>0:
        # If every stat is already at its cap, nowhere to spend points -- break to avoid infinite loop
        all_maxed = all(player["base_stats"][k] >= STAT_INFO[k]["max"] for k in STAT_ORDER)
        if all_maxed:
            typewrite(f"  ALL STATS MAXED. {bonus} POINT(S) LOST TO THE VOID.",0.04)
            time.sleep(0.8)
            break
        clear()
        print(f"\n  LEVEL UP! NOW LEVEL {player['level']}. POINTS: {bonus}\n")
        for i,key in enumerate(STAT_ORDER):
            v=player["base_stats"][key]; c=STAT_INFO[key]["max"]; f=int((v/c)*20)
            ptr=">>" if i==selected else "  "
            print(f"  {ptr} {STAT_INFO[key]['label']} [{'█'*f}{'░'*(20-f)}] {v}/{c}")
            time.sleep(0.02)
        print("\n  W/S navigate   + add point   ENTER skip point\n")
        cmd=dinput("  > ").strip().lower()
        if cmd=='w':   selected=(selected-1)%len(STAT_ORDER)
        elif cmd=='s': selected=(selected+1)%len(STAT_ORDER)
        elif cmd in ('+','='):
            k=STAT_ORDER[selected]
            if player["base_stats"][k]<STAT_INFO[k]["max"]:
                player["base_stats"][k]+=1; bonus-=1; _recalc(player)
            else:
                typewrite(f"  {STAT_INFO[k]['label'].strip()} IS ALREADY AT MAX.",0.04); time.sleep(0.5)
        elif cmd=='':
            typewrite("  POINT DISCARDED.",0.04); time.sleep(0.5); bonus-=1
    typewrite(f"\n  THE MIDDLEWHERE ACKNOWLEDGES YOU.",0.05)
    time.sleep(1); dinput("  PRESS ENTER TO CONTINUE...")
 
def show_status(player):
    s=player["stats"]; hp=player["hp"]; mhp=player["max_hp"]
    f=int((hp/mhp)*20)
    bar='█'*f+'░'*(20-f)
    print("")
    print("  ─────────────────────────────────────────────")
    print(f"  THE LOST  //  LVL {player['level']}  //  {player['location'].upper()}")
    print(f"  HP [{bar}] {hp}/{mhp}")
    # Status effects
    if player.get("status"):
        active=[f"{k.upper()}({v})" for k,v in player["status"].items() if k!="toxic_immune" and v>0]
        if active: print(f"  STATUS: {' '.join(active)}")
    print(f"  STR:{s['STR']}  RES:{s['RES']}  AGI:{s['AGI']}  WIL:{s['WIL']}  PER:{s['PER']}")
    wname=WEAPONS.get(player['weapon'],WEAPONS['bare_hands'])['name']
    tname=TALISMANS[player['talisman']]['name'] if player['talisman'] else "None"
    print(f"  WEAPON: {wname}   TALISMAN: {tname}")
    print("  ─────────────────────────────────────────────")
    print("")
 
# ══════════════════════════════════════════════════════════
#  STATUS EFFECTS
# ══════════════════════════════════════════════════════════
def apply_status(player, effect, duration):
    if effect=="toxic" and player.get("status",{}).get("toxic_immune"):
        typewrite("  TOXIC RESISTED. (Choir's Remnant)", 0.04); return
    if effect=="toxic" and player.get("status",{}).get("cold"):
        typewrite("  TOXIC RESISTED. (Frozen body)", 0.04); return
    if effect=="burn" and player.get("talisman")=="pillar_heart":
        typewrite("  BURN RESISTED. (Pillar Heart)", 0.04); return
    player["status"][effect] = player["status"].get(effect,0) + duration
    typewrite(f"  STATUS: {effect.upper()} applied ({duration} turns).", 0.04)
 
def tick_status(player):
    """Call at start of each combat turn. Returns damage and energy drained by statuses."""
    total_dmg = 0
    energy_drain = 0
    msgs = []
    expired = []
    for effect, turns in list(player["status"].items()):
        if effect == "toxic_immune": continue
        if turns <= 0:
            expired.append(effect); continue
        if effect == "toxic":
            dmg = 5
            if player.get("hard_mode"):
                dmg = int(dmg * 1.5)
            player["hp"] -= dmg; total_dmg += dmg
            msgs.append(f"  TOXIC TICKS. -{dmg} HP. ({turns-1} turns left)")
        elif effect == "burn":
            dmg = 8
            if player.get("hard_mode"):
                dmg = int(dmg * 1.5)
            player["hp"] -= dmg; total_dmg += dmg
            msgs.append(f"  BURN TICKS. -{dmg} HP. ({turns-1} turns left)")
        elif effect == "cold":
            energy_drain += 15
            msgs.append(f"  COLD stiffens your joints. -15 ENERGY. ({turns-1} turns left)")
        player["status"][effect] = turns - 1
        if player["status"][effect] <= 0:
            expired.append(effect)
    for e in expired:
        if e in player["status"]:
            del player["status"][e]
            msgs.append(f"  {e.upper()} faded.")
    return total_dmg, energy_drain, msgs
 
# ══════════════════════════════════════════════════════════
#  WEAPONS + TALISMANS
# ══════════════════════════════════════════════════════════
CONSUMABLE_INFO = {
    "dry_meat":    {"name":"Dry Meat",     "desc":"Tough, but filling. Restores 20 HP."},
    "pale_water":   {"name":"Pale Water",    "desc":"Tastes like nothing. Restores 25 HP."},
    "bitter_root":  {"name":"Bitter Root",   "desc":"Vile. Restores 10 HP. Clears minor Toxic."},
    "antitoxin":    {"name":"Antitoxin Vial","desc":"Clears all Toxic buildup."},
    "warm_ember":   {"name":"Warm Ember",    "desc":"A glowing coal. Restores 10 HP. Clears Cold."},
}

WEAPONS = {
    "bare_hands":    {"name":"Bare Hands",     "dmg":(1,3),   "scale":None,       "energy":4,  "cooldown":8, "desc":"All you have.","req":None,"toxic":False,"cold":False},
    "rusted_axe":    {"name":"Rusted Axe",     "dmg":(7,13),  "scale":"STR",      "energy":18, "cooldown":24,"desc":"Heavy. Hits hard. Req STR 5.","req":{"STR":5},"toxic":False,"cold":False},
    "old_knife":     {"name":"Old Knife",      "dmg":(2,5),   "scale":"AGI",      "energy":6,  "cooldown":8, "desc":"Quick. Low stopping power. Req AGI 4.","req":{"AGI":4},"toxic":False,"cold":False},
    "hollow_fang":   {"name":"Hollow Fang",    "dmg":(5,10),  "scale":"WIL",      "energy":12, "cooldown":14,"desc":"Resonates with WILL. Req WIL 5.","req":{"WIL":5},"toxic":False,"cold":False},
    "pale_shard":    {"name":"Pale Shard",     "dmg":(4,8),   "scale":"PER",      "energy":10, "cooldown":12,"desc":"Finds weak spots. Req PER 5.","req":{"PER":5},"toxic":False,"cold":False},
    "sludge_knife":  {"name":"Sludge Knife",   "dmg":(1,4),   "scale":"AGI",      "energy":5,  "cooldown":6, "desc":"Weak but spammable. Inflicts Toxic. Req AGI 5.","req":{"AGI":5},"toxic":True,"cold":False},
    "frozen_hammer": {"name":"Frozen Hammer",  "dmg":(16,24), "scale":"STR+WIL",  "energy":28, "cooldown":32,"desc":"Devastating. Cold damage with WIL. Req STR 8.","req":{"STR":8},"toxic":False,"cold":True},
}
 
TALISMANS = {
    "ashen_bark":     {"name":"Ashen Bark",      "desc":"Bark from the Ashen Tree.","effect":"+5 damage reduction.","stat":"RES"},
    "pale_eye":       {"name":"Pale Eye",         "desc":"A stillborn's eye.","effect":"+10% item find.","stat":"PER"},
    "choir_remnant":  {"name":"Choir's Remnant",  "desc":"A voice that never stopped singing.","effect":"Toxic immunity. 20% chance to inflict Toxic on hit.","stat":"WIL"},
    "mountain_still": {"name":"Mountain's Stillness","desc":"Cold from the frozen peaks.","effect":"+3 AGI. Dodge costs 5 less energy.","stat":"AGI"},
}
 
def check_weapon_req(player, weapon_key):
    w = WEAPONS.get(weapon_key)
    if not w or not w["req"]: return True, ""
    for stat, val in w["req"].items():
        if player["stats"][stat] < val:
            return False, f"REQUIRES {stat} {val} (you have {player['stats'][stat]})"
    return True, ""
 
def get_weapon_damage(player):
    w   = WEAPONS.get(player["weapon"], WEAPONS["bare_hands"])
    dmg = random.randint(*w["dmg"])
    s   = player["stats"]
    sc  = w["scale"]
    if sc == "STR":     dmg += int(_soft(s["STR"])*2)
    elif sc == "AGI":   dmg += int(_soft(s["AGI"]))
    elif sc == "WIL":   dmg += int(_soft(s["WIL"])*2)
    elif sc == "PER":   dmg += int(_soft(s["PER"]))
    elif sc == "STR+WIL":
        dmg += int(_soft(s["STR"])*2)
        if s["WIL"] >= 8:
            cold_bonus = int(_soft(s["WIL"])*1.5)
            dmg += cold_bonus
    if player.get("weak_weapons"):
        dmg = max(1, int(dmg * 0.5))
    return max(1, dmg)
 
def equip_talisman(player, talisman_key):
    player["talisman"] = talisman_key
    _recalc(player)
    t = TALISMANS[talisman_key]
    typewrite(f"\n  TALISMAN EQUIPPED: {t['name']}", 0.05)
    typewrite(f"  {t['effect']}", 0.04)
 
# ══════════════════════════════════════════════════════════
#  SAVE / LOAD (3 slots)
# ══════════════════════════════════════════════════════════
def save_game(player, slot):
    fname = SAVE_SLOTS[slot]
    with open(fname,"w") as f:
        stats_to_save = player.get("base_stats", player["stats"])
        for k,v in stats_to_save.items():
            f.write(f"stat_{k}={v}\n")
        f.write(f"hp={player['hp']}\n")
        f.write(f"level={player['level']}\n")
        f.write(f"xp={player['xp']}\n")
        f.write(f"xp_next={player['xp_next']}\n")
        f.write(f"location={player['location']}\n")
        f.write(f"weapon={player['weapon']}\n")
        f.write(f"talisman={player['talisman'] or 'none'}\n")
        f.write(f"void_score={player['void_score']}\n")
        f.write(f"trust_score={player['trust_score']}\n")
        f.write(f"inventory={','.join(player['inventory']) if player['inventory'] else 'none'}\n")
        f.write(f"visited={','.join(player['visited']) if player['visited'] else 'none'}\n")
        f.write(f"unlocked={','.join(player['unlocked']) if player['unlocked'] else 'none'}\n")
        
        flag_str=','.join(f"{k}:{v}" for k,v in player["flags"].items()) if player["flags"] else "none"
        f.write(f"flags={flag_str}\n")
        
        cons_str=','.join(f"{k}:{v}" for k,v in player["consumables"].items()) if player["consumables"] else "none"
        f.write(f"consumables={cons_str}\n")
        
        # Bug Fix: Properly check if status has items other than toxic_immune
        status_items = [f"{k}:{v}" for k,v in player["status"].items() if k != "toxic_immune"]
        stat_str = ','.join(status_items) if status_items else "none"
        f.write(f"status={stat_str}\n")
        f.write(f"hard_mode={player.get('hard_mode', False)}\n")
        f.write(f"one_life={player.get('one_life', False)}\n")
        f.write(f"weak_weapons={player.get('weak_weapons', False)}\n")
 
def load_game(slot):
    fname = SAVE_SLOTS[slot]
    data={}
    with open(fname,"r") as f:
        for line in f:
            if "=" in line:
                k,v=line.strip().split("=",1)
                data[k]=v
    stats={s:int(data.get(f"stat_{s}",1)) for s in STAT_ORDER}
    p=make_player(stats)
    p["hp"]          =int(data.get("hp",p["max_hp"]))
    p["level"]       =int(data.get("level",1))
    p["xp"]          =int(data.get("xp",0))
    p["xp_next"]     =int(data.get("xp_next",100))
    p["location"]    =data.get("location","crossroads")
    p["weapon"]      =data.get("weapon","bare_hands")
    raw_t            =data.get("talisman","none")
    p["talisman"]    =None if raw_t=="none" else raw_t
    p["void_score"]  =int(data.get("void_score",0))
    p["trust_score"] =int(data.get("trust_score",0))
    p["hard_mode"]   =data.get("hard_mode", "False") == "True"
    p["one_life"]    =data.get("one_life", "False") == "True"
    p["weak_weapons"]=data.get("weak_weapons", "False") == "True"
    
    raw_inv=data.get("inventory","none")
    p["inventory"]   =[x for x in raw_inv.split(",") if x] if raw_inv!="none" else []
    
    raw_vis=data.get("visited","none")
    p["visited"]     =[x for x in raw_vis.split(",") if x] if raw_vis!="none" else []
    
    raw_unl=data.get("unlocked","none")
    p["unlocked"]    =[x for x in raw_unl.split(",") if x] if raw_unl!="none" else []
    
    # Bug Fix: Safeguard against empty string unpacking
    # Also cast kills_* keys back to int so void score comparison (== 30) works after reload
    raw_flags=data.get("flags","none")
    if raw_flags not in ("none", ""):
        p["flags"] = {}
        for pair in raw_flags.split(","):
            if ":" not in pair: continue
            fk, fv = pair.split(":", 1)
            p["flags"][fk] = int(fv) if fk.startswith("kills_") else fv
        
    raw_cons=data.get("consumables","none")
    if raw_cons not in ("none", ""):
        p["consumables"]={}
        for pair in raw_cons.split(","):
            if ":" not in pair: continue
            k, v = pair.split(":", 1)
            p["consumables"][k] = int(v)
        
    raw_stat=data.get("status","none")
    if raw_stat not in ("none", ""):
        p["status"]={}
        for pair in raw_stat.split(","):
            if ":" not in pair: continue
            k, v = pair.split(":", 1)
            p["status"][k] = int(v)
        
    _recalc(p)
    return p
 
def get_slot_info(slot):
    fname=SAVE_SLOTS[slot]
    if not os.path.exists(fname):
        return None
    data={}
    with open(fname,"r") as f:
        for line in f:
            if "=" in line:
                k,v=line.strip().split("=",1)
                data[k]=v
    
    mods = []
    if data.get("hard_mode") == "True": mods.append("HARD")
    if data.get("one_life") == "True": mods.append("1LIFE")
    if data.get("weak_weapons") == "True": mods.append("WEAK")
    mod_str = f" [{' '.join(mods)}]" if mods else ""
    
    return {"location":data.get("location","?"),"level":data.get("level","?"),"mod_str":mod_str}
 
def slot_select_screen():
    while True:
        clear()
        slow_print([
            "",
            "  ╔══════════════════════════════════════════╗",
            "  ║   E C H O E S O F M I D D L E W H E R E  ║",
            "  ╚══════════════════════════════════════════╝",
            "",
            "  SELECT A SAVE SLOT",
            "",
        ],0.15)
        for i in range(3):
            info=get_slot_info(i)
            if info:
                print(f"  [{i+1}] SLOT {i+1}  --  LVL {info['level']}  //  {info['location'].upper()}{info['mod_str']}")
            else:
                print(f"  [{i+1}] SLOT {i+1}  --  EMPTY")
            time.sleep(0.1)
        print("")
        ch=dinput("  > ").strip()
        if ch in ('1','2','3'):
            slot=int(ch)-1
            info=get_slot_info(slot)
            if info:
                print(f"\n  [C] CONTINUE   [N] NEW GAME   [B] BACK")
                act=dinput("  > ").strip().lower()
                if act=='c':   return slot, False
                elif act=='n':
                    if os.path.exists(SAVE_SLOTS[slot]):
                        os.remove(SAVE_SLOTS[slot])
                    return slot, True
                # act=='b' or anything else: loop back to top (no recursion)
            else:
                return slot, True
        else:
            typewrite("  PICK 1, 2 OR 3.",0.04)
 
def checkpoint(player, loc, slot):
    clear()
    slow_print([
        "",
        "  ════════════════════════════════════════════",
        "  CHECKPOINT",
        "  ════════════════════════════════════════════",
        "",
        "  A still place. The Middlewhere holds its breath.",
        "  You rest. The wounds close.",
        "  Not healed. Just... postponed.",
        "",
    ],0.2)
    pinwheel(1.5)
    player["hp"]       = player["max_hp"]
    player["location"] = loc
    player["status"]   = {k:v for k,v in player["status"].items() if k=="toxic_immune"}
    save_game(player, slot)
    slow_print([f"  HP RESTORED: {player['max_hp']}/{player['max_hp']}","  STATUS CLEARED.","  GAME SAVED.",""],0.2)
    dinput("  PRESS ENTER TO CONTINUE...")
 
# ══════════════════════════════════════════════════════════
#  ENEMIES
# ══════════════════════════════════════════════════════════
ENEMIES = {
    "hollow_walker":  {"name":"Hollow Walker",  "hp":28,"damage":(5,10),"xp":20,"will_weak":True, "desc":"It looks human. Moves like it forgot how.","drop":("hollow_fang",0.25),"inflict":None},
    "bark_wraith":    {"name":"Bark Wraith",     "hp":18,"damage":(4,8), "xp":15,"will_weak":True, "desc":"Fast. Smells like rot.","drop":("bitter_root",0.4),"inflict":None},
    "pale_grazer":    {"name":"Pale Grazer",     "hp":35,"damage":(9,15),"xp":28,"will_weak":False,"desc":"Passive until close. Then it charges.","drop":("dry_meat",0.35),"inflict":None},
    "stillborn":      {"name":"Stillborn",       "hp":8, "damage":(1,3), "xp":8, "will_weak":False,"desc":"Doesn't move. Just watches.","drop":None,"inflict":None},
    "rotten_walker":  {"name":"Rotten Walker",   "hp":32,"damage":(6,11),"xp":25,"will_weak":True, "desc":"A Walker rotted from the inside out. Drips something black.","drop":("sludge_knife",0.2),"inflict":("toxic",2)},
    "bog_crawler":    {"name":"Bog Crawler",     "hp":50,"damage":(8,14),"xp":35,"will_weak":False,"desc":"Low to the ground. Slow. If it rolls over you, you won't get up.","drop":("pale_water",0.5),"inflict":("toxic",1)},
    "frostbitten":    {"name":"Frostbitten",     "hp":25,"damage":(4,8), "xp":22,"will_weak":False,"desc":"Fast. Drains energy instead of HP on every other hit.","drop":("bitter_root",0.3),"inflict":None,"energy_drain":True},
    "buried":         {"name":"The Buried",      "hp":20,"damage":(10,16),"xp":28,"will_weak":False,"desc":"Ambush. You almost missed it.","drop":("dry_meat",0.4),"inflict":("cold",2)},
    "frozen_sentinel":{"name":"Frozen Sentinel", "hp":65,"damage":(12,18),"xp":40,"will_weak":False,"desc":"Heavy armored. Slow. Hits like a wall of ice.","drop":("pale_water",0.3),"inflict":("cold",2)},
    "pale_warden":    {"name":"Pale Warden",     "hp":55,"damage":(12,18),"xp":80,"will_weak":False,"desc":"Tall. Wrapped in pale grass. Head faces the wrong way.","drop":("pale_shard",1.0),"talisman":("pale_eye",1.0),"inflict":None},
    "sentinel_pass":  {"name":"Sentinel of the Pass","hp":90,"damage":(14,20),"xp":100,"will_weak":False,"desc":"It has been standing guard so long it fused with the mountain.","drop":("frozen_hammer",1.0),"inflict":("cold",3)},
    "ash_lord":       {"name":"Lord of the Ash",       "hp":180,"damage":(10,16),"xp":250,"will_weak":False,"desc":"The ancient root itself, awakened and furious.","drop":None,"inflict":None},
    "pale_lord_boss": {"name":"Lord of the Mourning",  "hp":160,"damage":(8,14), "xp":250,"will_weak":False,"desc":"A shape-shifting manifestation of pure sorrow.","drop":None,"inflict":("toxic",1)},
    "rot_lord":       {"name":"Lord of the Rot",       "hp":190,"damage":(9,15), "xp":250,"will_weak":False,"desc":"A massive, breathing mound of moss, roots, and decay.","drop":None,"inflict":("toxic",2)},
    "frost_lord":     {"name":"Lord of the Frostbite", "hp":200,"damage":(11,17),"xp":250,"will_weak":False,"desc":"A gargantuan frozen construct with countless glacial limbs.","drop":None,"inflict":("cold",2)},
    "dune_lord_boss": {"name":"Lord of the Dunes",     "hp":170,"damage":(10,15),"xp":250,"will_weak":False,"desc":"A shifting sand-vortex representing the desert's loop.","drop":None,"inflict":None},
    "cinder_lord":    {"name":"Lord of Cinder",        "hp":210,"damage":(12,18),"xp":250,"will_weak":False,"desc":"A towering engine of sheer pressure and lava.","drop":None,"inflict":("burn",2)},
    "the_scourge":    {"name":"The Scourge",           "hp":320,"damage":(13,26),"xp":400,"will_weak":False,"desc":"A glitching error in the code spawned to stop your genocide.","drop":None,"inflict":None},
    "fate":           {"name":"Fate",                  "hp":260,"damage":(10,18),"xp":300,"will_weak":False,"desc":"The head of the church. He counteracts your choices.","drop":None,"inflict":None},
    "king_of_nothing":{"name":"The King of Nothing",   "hp":460,"damage":(14,27),"xp":500,"will_weak":False,"desc":"The empty monarch of an empty world.","drop":None,"inflict":None},
    "administrator":  {"name":"The Administrator",     "hp":800,"damage":(18,30),"xp":1000000000,"will_weak":False,"desc":"The caretaker of this reality. He summons glitches and rewrites your HP.","drop":None,"inflict":None},
    "yourself":       {"name":"Yourself",              "hp":100,"damage":(0,0),  "xp":500,"will_weak":False,"desc":"A mirror reflection of your shape. It holds the same weapon.","drop":None,"inflict":None},
}
 
BIOME_ENEMIES = {
    "ashwood":       ["hollow_walker","bark_wraith"],
    "pale_fields":   ["pale_grazer","stillborn"],
    "blackwater_rot":["rotten_walker","bog_crawler"],
    "static_mountains":["frostbitten","buried","frozen_sentinel"],
}
 
# ══════════════════════════════════════════════════════════
#  TEXT COMBAT
# ══════════════════════════════════════════════════════════
def run_combat(player, enemy_key, slot):
    # Hijack for The Scourge if void score is 5+ and Scourge is alive
    if enemy_key not in ("yourself", "administrator", "fate", "king_of_nothing", "the_scourge", "ash_lord", "pale_lord_boss", "rot_lord", "frost_lord", "dune_lord_boss", "cinder_lord") and player.get("void_score", 0) >= 5 and player.get("flags", {}).get("scourge_killed") != "true":
        clear()
        typewrite("\n  \033[91mThe air tears open. Static screams in your ears.", 0.04)
        typewrite("  The code of the Middlewhere is breaking. Something has come to stop you.\033[0m", 0.04)
        time.sleep(1.0)
        enemy_key = "the_scourge"

    # Yourself dynamically matches player max HP
    if enemy_key == "yourself":
        ENEMIES["yourself"]["hp"] = player["max_hp"]

    edata=ENEMIES[enemy_key].copy()
    
    # Check for raw code corruption (NG+)
    is_corrupted = player.get("flags", {}).get("administrator_corrupted") == "true"
    if is_corrupted and enemy_key not in ("fate", "king_of_nothing", "the_scourge", "administrator", "yourself"):
        edata["name"] = f"Corrupted {edata['name']}"
        edata["hp"] = int(edata["hp"] * 2.0)
        edata["damage"] = (int(edata["damage"][0] * 2.0), int(edata["damage"][1] * 2.0))
        edata["xp"] = int(edata["xp"] * 2.0)
 
    if player.get("hard_mode"):
        edata["hp"] = int(edata["hp"] * 1.5)
        edata["damage"] = (int(edata["damage"][0] * 1.5), int(edata["damage"][1] * 1.5))
    ehp=edata["hp"]; ename=edata["name"]
    energy=100
    w=WEAPONS.get(player["weapon"],WEAPONS["bare_hands"])
 
    clear()
    if is_corrupted and enemy_key not in ("fate", "king_of_nothing", "the_scourge", "administrator", "yourself"):
        slow_print(["",f"  ── ENCOUNTER: \033[95m{ename.upper()}\033[0m ──","",f"  \033[90m{edata['desc']}\033[0m",""],0.15)
    else:
        slow_print(["",f"  ── ENCOUNTER: {ename.upper()} ──","",f"  {edata['desc']}",""],0.15)
    time.sleep(0.6)
 
    yourself_dodging = False
    player_dodging = False
    next_attack_bonus = False

    # Local function to resolve enemy attack action
    def enemy_turn(is_distracted=False):
        nonlocal energy, player, yourself_dodging, player_dodging, next_attack_bonus
        if ehp <= 0: return

        # Resolve player dodge
        if player_dodging:
            is_countered = (enemy_key == "fate" and fate_evasion)
            if not is_countered and stat_check(player, "AGI", 8):
                typewrite(f"  YOU DODGE! {ename} misses completely.", 0.04)
                energy = min(100, energy + 20)
                next_attack_bonus = True
                return
            else:
                if is_countered:
                    edm = 12
                    player["hp"] -= edm
                    typewrite(f"  [Fate's Evasion] Fate predicts your dodge! You take {edm} damage.", 0.04)
                    return
                typewrite("  Dodge failed!", 0.04)
        
        # Yourself mirror match behavior
        if enemy_key == "yourself":
            action = random.choice(["attack", "attack", "dodge"])
            if action == "dodge" and not is_distracted:
                yourself_dodging = True
                typewrite("  YOURSELF enters a defensive stance.", 0.04)
                return
            yourself_dodging = False
            edm = get_weapon_damage(player)
            if is_distracted: edm = edm // 2
            edm = max(1, edm - int(player["dmg_redux"]))
            player["hp"] -= edm
            typewrite(f"  YOURSELF strikes you with {w['name']} for {edm}.", 0.04)
            return
 
        # Administrator cycles boss actions
        if enemy_key == "administrator":
            # Check for existing minions damage
            minion_count = player["status"].get("glitch_minions", 0)
            if minion_count > 0:
                m_dmg = minion_count * 5
                player["hp"] -= m_dmg
                typewrite(f"  \033[91m[!] {minion_count} GLITCH MINIONS bite at your code! -{m_dmg} HP.\033[0m", 0.04)

            ability = random.choice(["toxic", "cold", "burn", "heavy", "summon", "normal"])
            if ability == "summon":
                player["status"]["glitch_minions"] = player["status"].get("glitch_minions", 0) + 1
                typewrite("  \033[91mThe Administrator reaches into the source code and pulls out a GLITCH MINION!\033[0m", 0.04)
                typewrite("  \033[90mA small, stuttering silhouette of red static begins circling you.\033[0m", 0.04)
            elif ability == "toxic":
                edm = max(1, random.randint(*edata["damage"]) - int(player["dmg_redux"]))
                if is_distracted: edm = edm // 2
                player["hp"] -= edm
                typewrite(f"  The Administrator spits toxic ooze! -{edm} HP.", 0.04)
                apply_status(player, "toxic", 2)
            elif ability == "cold":
                edm = max(1, random.randint(*edata["damage"]) - int(player["dmg_redux"]))
                if is_distracted: edm = edm // 2
                player["hp"] -= edm
                typewrite(f"  The Administrator fires a freezing shockwave! -{edm} HP.", 0.04)
                apply_status(player, "cold", 2)
            elif ability == "burn":
                edm = max(1, random.randint(*edata["damage"]) - int(player["dmg_redux"]))
                if is_distracted: edm = edm // 2
                player["hp"] -= edm
                typewrite(f"  The Administrator triggers a magma eruption! -{edm} HP.", 0.04)
                apply_status(player, "burn", 2)
            elif ability == "heavy":
                edm = max(1, int(random.randint(*edata["damage"]) * 1.5) - int(player["dmg_redux"]))
                if is_distracted: edm = edm // 2
                player["hp"] -= edm
                typewrite(f"  The Administrator summons a crushing stone pillar! -{edm} HP.", 0.04)
            else:
                edm = max(1, random.randint(*edata["damage"]) - int(player["dmg_redux"]))
                if is_distracted: edm = edm // 2
                player["hp"] -= edm
                typewrite(f"  The Administrator strikes you with pure static! -{edm} HP.", 0.04)
            return
 
        edm = random.randint(*edata["damage"])
        if is_distracted: edm = edm // 2
        edm = max(1, edm - int(player["dmg_redux"]))
        player["hp"] -= edm
        if is_corrupted:
            typewrite(f"  \033[95m{ename}\033[0m HITS FOR {edm}.", 0.04)
        else:
            typewrite(f"  {ename} HITS FOR {edm}.", 0.04)
        if edata.get("inflict") and random.random() < 0.5:
            apply_status(player, *edata["inflict"])
        if edata.get("energy_drain") and random.random() < 0.4:
            drain = random.randint(5, 15)
            energy = max(0, energy - drain)
            typewrite(f"  ENERGY DRAINED. -{drain}.", 0.04)
 
    turn_count = 0
    fate_shield = False
    fate_evasion = False
    last_action = None
 
    while True:
        turn_count += 1
        if enemy_key == "fate":
            fate_shield = False
            fate_evasion = False
            if turn_count == 1:
                slow_print(["", 
                    "  Fate: 'Ah, the variable returns. You walk a path of dust, thinking it leads to a city.'",
                    "  Fate: 'But the city is just another room. And I am its keeper.'",
                    ""], 0.18)
            
            # Counterplay based on last_action
            if last_action == "item":
                slow_print(["",
                    "  Fate: 'You rely on external coordinates. I will wipe your memory.'",
                    "  [Fate drains 20 energy and freezes your joints!]",
                    ""], 0.1)
                energy = max(0, energy - 20)
                apply_status(player, "cold", 1)
            elif last_action == "dodge":
                fate_evasion = True
                slow_print(["",
                    "  Fate: 'You run from the inevitable. But the boundary of this sandbox cannot be bypassed.'",
                    "  [Fate enters an evasive state. (Dodge chance halved, AGI attacks counter-attacked!)]",
                    ""], 0.1)
            elif last_action == "attack":
                fate_shield = True
                slow_print(["",
                    "  Fate: 'Violence is a loop, repeating its own errors. I will reflect your aggression.'",
                    "  [Fate raises a mirroring shield of weight. (STR attacks will reflect damage!)]",
                    ""], 0.1)
            else:
                # Fallback to stat-based check
                if player["stats"]["STR"] >= player["stats"]["AGI"]:
                    fate_shield = True
                    slow_print(["", 
                        "  Fate waves his hands, whispering: ",
                        "  'Strength is but a leverage of weight; it crushes you under your own gravity.'",
                        "  [Fate raises a mirroring shield of weight. (STR attacks will reflect damage!)]",
                        ""], 0.1)
                else:
                    fate_evasion = True
                    slow_print(["",
                        "  Fate moves between the frames of time, whispering: ",
                        "  'Speed is a race against stillness, a race you have already lost.'",
                        "  [Fate enters an evasive state. (Dodge chance halved, AGI attacks counter-attacked!)]",
                        ""], 0.1)
            last_action = None
 
        # Status tick
        sdmg, sedrain, smsgs = tick_status(player)
        energy = max(0, energy - sedrain)
        for sm in smsgs: typewrite(sm,0.04)
        if sdmg > 0 or sedrain > 0: time.sleep(0.3)
        if player["hp"]<=0: player["hp"]=0; return False
 
        print("")
        hf=int((player["hp"]/player["max_hp"])*20)
        ef=int((ehp/edata["hp"])*20)
        nf=int((energy/100)*20)
        print(f"  YOU      [{'█'*hf}{'░'*(20-hf)}] {player['hp']}/{player['max_hp']}")
        active=[f"{k.upper()}({v})" for k,v in player["status"].items() if k!="toxic_immune" and v>0]
        if active: print(f"  STATUS:  {' '.join(active)}")
        print(f"  ENERGY   [{'█'*nf}{'░'*(20-nf)}] {energy}/100")
        if is_corrupted and enemy_key not in ("fate", "king_of_nothing", "the_scourge", "administrator", "yourself"):
            print(f"  \033[95m{ename[:12]:<12}\033[0m [{'█'*ef}{'░'*(20-ef)}] {ehp}/{edata['hp']}")
        else:
            print(f"  {ename[:12]:<12} [{'█'*ef}{'░'*(20-ef)}] {ehp}/{edata['hp']}")
        print("")
        print(f"  [1] ATTACK  ({w['name']}, {w['energy']} energy)")
        print(f"  [2] DODGE   (15 energy)")
        print(f"  [3] ITEM")
        print(f"  [4] STATUS")
        print("")
        choice=dinput("  > ").strip()
 
        if choice=="1":
            if energy<w["energy"]:
                last_action = "rest"
                energy=min(100,energy+30)
                typewrite("  TOO TIRED. YOU REST. ENEMY ADVANCES.",0.04)
                enemy_turn()
            else:
                last_action = "attack"
                dmg=get_weapon_damage(player)
                if next_attack_bonus:
                    dmg = int(dmg * 1.5)
                    next_attack_bonus = False
                    typewrite("  [Counter-Strike] 1.5x damage applied!", 0.04)
                
                # Yourself dodging counter
                if enemy_key == "yourself" and yourself_dodging:
                    yourself_dodging = False
                    if random.random() < 0.6:
                        dmg = 0
                        typewrite("  [Mirror Match] YOURSELF dodges your strike!", 0.04)

                # Fate counterplay logic
                if enemy_key == "fate":
                    if fate_shield:
                        reflected = max(1, int(dmg * 0.5))
                        player["hp"] -= reflected
                        typewrite(f"  [Fate's Mirror] The strike is reflected! You take {reflected} damage.", 0.04)
                    elif fate_evasion:
                        dmg = 0
                        player["hp"] -= 8
                        typewrite("  [Fate's Evasion] Fate parries and counter-strikes for 8 damage!", 0.04)
                        
                if dmg > 0:
                    if enemy_key == "yourself":
                        # Yourself uses player's own damage reduction!
                        dmg = max(1, dmg - int(player["dmg_redux"]))
                    if edata.get("will_weak") and player["stats"]["WIL"]>=5:
                        bonus=player["stats"]["WIL"]; dmg+=bonus
                        typewrite(f"\n  YOUR WILL BURNS. +{bonus} DMG.",0.04)
                    energy-=w["energy"]; ehp-=dmg
                    typewrite(f"\n  YOU HIT {ename} FOR {dmg}.",0.04)
                    if w.get("toxic") and random.random()<0.7:
                        typewrite("  TOXIC COATS THE WOUND.",0.04)
                        apply_status(player, "toxic", 2)
                    if w.get("cold") and random.random()<0.7:
                        typewrite("  ICE SEEPS INTO THE WOUND.",0.04)
                        apply_status(player, "cold", 2)
                    if player.get("talisman")=="choir_remnant" and random.random()<0.2:
                        typewrite("  CHOIR'S REMNANT PULSES. TOXIC APPLIED.",0.04)
                        apply_status(player, "toxic", 1)
                        
                if enemy_key == "king_of_nothing" and ehp < edata["hp"] // 2:
                    if player.get("flags", {}).get("cabinet_open") == "true":
                        lord_souls = ["ash_soul", "pale_soul", "rot_soul", "frost_soul", "dune_soul", "magma_soul"]
                        soul_count = sum(1 for s in lord_souls if s in player.get("inventory", []))
                        if soul_count >= 3:
                            return "admin_trigger"
 
                time.sleep(0.3)
                if ehp<=0: break
                enemy_turn()
 
        elif choice=="2":
            last_action = "dodge"
            dodge_cost = 10 if player.get("talisman")=="mountain_still" else 15
            if energy<dodge_cost:
                typewrite("\n  NOT ENOUGH ENERGY.",0.04); time.sleep(0.6)
            else:
                energy-=dodge_cost
                player_dodging = True
                typewrite("\n  You brace yourself to dodge the next move...", 0.04)
                time.sleep(0.3)
                enemy_turn()
                player_dodging = False
 
        elif choice=="3":
            last_action = "item"
            if not player["consumables"]:
                typewrite("\n  NO ITEMS.",0.04); time.sleep(0.6)
            else:
                items=list(player["consumables"].keys())
                print("\n  ITEMS:")
                for i,it in enumerate(items):
                    print(f"  [{i+1}] {CONSUMABLE_INFO.get(it,{}).get('name',it)} x{player['consumables'][it]}")
                ic=dinput("\n  USE WHICH? (number/back): ").strip()
                if ic.isdigit() and 0<=int(ic)-1<len(items):
                    if use_item(player,items[int(ic)-1]):
                        typewrite(f"  {ename} HITS WHILE DISTRACTED.",0.04)
                        enemy_turn(is_distracted=True)
 
        elif choice=="4":
            show_status(player); dinput("  PRESS ENTER..."); clear()
 
        energy=min(100,energy+8)
        if player["hp"]<=0: player["hp"]=0; return False
 
    # Victory
    xp=edata["xp"]
    clear()
    slow_print(["",f"  {ename.upper()} DEFEATED.",f"  +{xp} XP",""],0.18)
    player["xp"]+=xp

    # Increment zone kills (except for special boss/lord fights)
    if enemy_key not in ("yourself", "administrator", "fate", "king_of_nothing", "the_scourge", "ash_lord", "pale_lord_boss", "rot_lord", "frost_lord", "dune_lord_boss", "cinder_lord"):
        loc = player.get("location", "unknown")
        kills_key = f"kills_{loc}"
        player["flags"][kills_key] = player["flags"].get(kills_key, 0) + 1
        if player["flags"][kills_key] == 30:
            player["void_score"] = player.get("void_score", 0) + 1
            slow_print(["", "  \033[91mWARNING: A heavy silence descends on this zone.", "  You have slaughtered too many. The void deepens.\033[0m", ""], 0.15)
 
    drop=edata.get("drop")
    if drop:
        ikey,chance=drop
        if random.random()<chance+(player["stats"]["PER"]*0.02):
            if ikey in WEAPONS:
                ok,msg=check_weapon_req(player,ikey)
                if ikey not in player["inventory"]:
                    player["inventory"].append(ikey)
                wname=WEAPONS[ikey]["name"]
                typewrite(f"  DROPPED: {wname.upper()}",0.04)
                if not ok: typewrite(f"  ({msg})",0.04)
            elif ikey in CONSUMABLE_INFO:
                player["consumables"][ikey]=player["consumables"].get(ikey,0)+1
                typewrite(f"  DROPPED: {CONSUMABLE_INFO[ikey]['name'].upper()}",0.04)
            else:
                player["inventory"].append(ikey)
                typewrite(f"  DROPPED: {ikey.upper()}",0.04)
 
    tdrop=edata.get("talisman")
    if tdrop:
        tkey,tchance=tdrop
        if random.random()<tchance and player["talisman"]!=tkey:
            equip_talisman(player,tkey)
            if tkey not in player["inventory"]:
                player["inventory"].append(tkey)
 
    time.sleep(0.4)
    if player["xp"]>=player["xp_next"]:
        dinput("\n  PRESS ENTER TO CONTINUE...")
        level_up(player)
 
    dinput("\n  PRESS ENTER TO CONTINUE...")
    return True
 
def rng_encounter(player, biome, slot):
    base=0.35-(player["stats"]["PER"]*0.01)
    if random.random()<max(0.1,base):
        key=random.choice(BIOME_ENEMIES.get(biome,["hollow_walker"]))
        # Buried enemy -- PER check to see coming
        if key=="buried":
            if stat_check(player,"PER",13):
                typewrite("\n  YOUR SENSES TINGLE. SOMETHING IS BELOW.",0.04)
                typewrite("  YOU STEP ASIDE.",0.04)
                time.sleep(0.8)
                return None
            else:
                typewrite("\n  SOMETHING ERUPTS FROM THE SNOW.",0.05)
                time.sleep(0.5)
        return run_combat(player,key,slot)
    return None
 
def death_screen(player, slot):
    clear()
    if player.get("one_life"):
        slow_print([
            "",
            "  ════════════════════════════════════════════",
            "  P E R M A N E N T   D E A T H",
            "  ════════════════════════════════════════════",
            "",
            "  The Middlewhere claims your only life.",
            "  Your progress has been erased.",
            "",
        ],0.22)
        time.sleep(1.5)
        fname = SAVE_SLOTS[slot]
        if os.path.exists(fname):
            os.remove(fname)
        dinput("  PRESS ENTER TO RETURN TO MAIN MENU...")
        return None

    slow_print([
        "",
        "  ════════════════════════════════════════════",
        "  YOU DIED.",
        "  ════════════════════════════════════════════",
        "",
        "  The Middlewhere swallows you.",
        "  Not with malice. Just hunger.",
        "",
        "  You wake at the last checkpoint.",
        "",
    ],0.22)
    time.sleep(1)
    if os.path.exists(SAVE_SLOTS[slot]):
        p=load_game(slot)
        p["hp"]=p["max_hp"]
        return p
    else:
        stats=character_creation()
        return make_player(stats)
 
# ══════════════════════════════════════════════════════════
#  INVENTORY / FIELD MENU
# ══════════════════════════════════════════════════════════
def show_inventory(player):
    clear()
    print("")
    print("  ─── INVENTORY ──────────────────────────────")
    wname=WEAPONS.get(player['weapon'],WEAPONS['bare_hands'])['name']
    tname=TALISMANS[player['talisman']]['name'] if player['talisman'] else "None"
    print(f"  WEAPON:   {wname}")
    print(f"  TALISMAN: {tname}")
    print("")
    if player["consumables"]:
        print("  CONSUMABLES:")
        for item,count in player["consumables"].items():
            iname=CONSUMABLE_INFO.get(item,{}).get("name",item)
            idesc=CONSUMABLE_INFO.get(item,{}).get("desc","")
            print(f"  > {iname} x{count}  --  {idesc}")
    else:
        print("  CONSUMABLES: NONE")
    print("")
    if player["inventory"]:
        print("  KEY ITEMS / CARRIED WEAPONS:")
        for item in player["inventory"]:
            if item in WEAPONS:
                w=WEAPONS[item]
                ok,msg=check_weapon_req(player,item)
                req=""if ok else f" [{msg}]"
                print(f"  > {w['name']}  DMG:{w['dmg']}  {w['desc']}{req}")
            elif item in TALISMANS:
                t=TALISMANS[item]
                print(f"  > {t['name']}  --  {t['effect']}")
            else:
                print(f"  > {item.replace('_',' ').title()}")
    print("  ────────────────────────────────────────────")
 
def weapon_swap_menu(player):
    carried=[w for w in player["inventory"] if w in WEAPONS and w!=player["weapon"]]
    carried.append("bare_hands") 
    carried=[c for c in carried if c!=player["weapon"]]
 
    clear()
    print("")
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   WEAPON SELECT                          ║")
    print("  ╚══════════════════════════════════════════╝")
    print("")
    # Current
    cw=WEAPONS.get(player["weapon"],WEAPONS["bare_hands"])
    print(f"  EQUIPPED: {cw['name']}")
    print(f"  DMG: {cw['dmg']}  ENERGY: {cw['energy']}  SCALE: {cw['scale'] or 'none'}")
    print(f"  {cw['desc']}")
    print("")
    print("  ─── AVAILABLE ───────────────────────────────")
    if not carried:
        print("  No other weapons carried.")
    else:
        for i,wk in enumerate(carried):
            w=WEAPONS[wk]
            ok,msg=check_weapon_req(player,wk)
            req="" if ok else f"  !! {msg}"
            effects=[]
            if w.get("toxic"): effects.append("TOXIC")
            if w.get("cold"):  effects.append("COLD")
            efx=" ["+"/".join(effects)+"]" if effects else ""
            print(f"  [{i+1}] {w['name']}{efx}")
            print(f"       DMG:{w['dmg']}  NRG:{w['energy']}  CD:{w['cooldown']}f  SCALE:{w['scale'] or 'none'}")
            print(f"       {w['desc']}{req}")
            print("")
    print("  [B] Back")
    print("")
    ch=dinput("  > ").strip().lower()
    if ch.isdigit() and 0<=int(ch)-1<len(carried):
        wk=carried[int(ch)-1]
        ok,msg=check_weapon_req(player,wk)
        if not ok:
            typewrite(f"\n  CANNOT EQUIP: {msg}",0.04); time.sleep(1)
            return
        old_w=player["weapon"]
        if old_w!="bare_hands" and old_w not in player["inventory"]:
            player["inventory"].append(old_w)
        player["weapon"]=wk
        if wk in player["inventory"]:
            player["inventory"].remove(wk)
        typewrite(f"\n  EQUIPPED: {WEAPONS[wk]['name']}",0.04)
        time.sleep(0.6)
 
def use_item(player, item_key):
    if item_key not in player["consumables"]: return False
    
    # Check for extended items first
    if _extended_use_item(player, item_key):
        return True

    if item_key == "dry_meat":
        heal=20; player["hp"]=min(player["max_hp"], player["hp"]+heal)
        typewrite(f"  Ate Dry Meat. +{heal} HP.", 0.04)
    elif item_key == "pale_water":
        heal=25; player["hp"]=min(player["max_hp"], player["hp"]+heal)
        typewrite(f"  Drank Pale Water. +{heal} HP.", 0.04)
    elif item_key == "bitter_root":
        heal=10; player["hp"]=min(player["max_hp"], player["hp"]+heal)
        if "toxic" in player["status"]:
            player["status"]["toxic"] = max(0, player["status"]["toxic"] - 2)
            if player["status"]["toxic"] == 0: del player["status"]["toxic"]
            typewrite("  Toxic reduced.", 0.04)
        typewrite(f"  Ate Bitter Root. +{heal} HP.", 0.04)
    elif item_key == "antitoxin":
        if "toxic" in player["status"]: del player["status"]["toxic"]
        typewrite("  Toxic cleared.", 0.04)
    elif item_key == "warm_ember":
        if "cold" in player["status"]: del player["status"]["cold"]
        player["hp"]=min(player["max_hp"], player["hp"]+10)
        typewrite("  Cold cleared. +10 HP.", 0.04)
    else:
        typewrite("  NOTHING HAPPENS.", 0.04); return False
        
    player["consumables"][item_key] -= 1
    if player["consumables"][item_key] <= 0:
        del player["consumables"][item_key]
    return True

def field_menu(player, slot):
    while True:
        clear()
        print("")
        print("  ╔══════════════════════════════════════════╗")
        print("  ║   FIELD MENU                             ║")
        print("  ╚══════════════════════════════════════════╝")
        print("")
        wname=WEAPONS.get(player['weapon'],WEAPONS['bare_hands'])['name']
        tname=TALISMANS[player['talisman']]['name'] if player['talisman'] else "None"
        print(f"  WEAPON:   {wname}")
        print(f"  TALISMAN: {tname}")
        hf=int((player["hp"]/player["max_hp"])*20)
        print(f"  HP [{('█'*hf)+('░'*(20-hf))}] {player['hp']}/{player['max_hp']}")
        active=[f"{k.upper()}({v})" for k,v in player["status"].items() if k!="toxic_immune" and v>0]
        if active: print(f"  STATUS: {' '.join(active)}")
        print("")
        print("  ─── USE CONSUMABLE ──────────────────────────")
        items=list(player["consumables"].keys())
        if items:
            for i,it in enumerate(items):
                cnt=player["consumables"][it]
                iname=CONSUMABLE_INFO.get(it,{}).get("name",it)
                idesc=CONSUMABLE_INFO.get(it,{}).get("desc","")
                print(f"  [{i+1}] {iname} x{cnt}  --  {idesc}")
        else:
            print("  No consumables.")
        print("")
        print("  [W] SWAP WEAPON")
        avail_t=[t for t in player["inventory"] if t in TALISMANS and t!=player["talisman"]]
        if avail_t or player["talisman"]:
            print("  [T] SWAP TALISMAN")
        print("  [V] VIEW FULL INVENTORY")
        print("  [B] CLOSE")
        print("")
        ch=dinput("  > ").strip().lower()
        if ch.isdigit():
            idx=int(ch)-1
            if 0<=idx<len(items):
                use_item(player, items[idx])
                time.sleep(0.8)
        elif ch=="w":
            weapon_swap_menu(player)
        elif ch=="t":
            # Talisman swap logic
            clear()
            print("\n  SELECT TALISMAN:")
            ts = [t for t in player["inventory"] if t in TALISMANS]
            if player["talisman"]:
                print(f"  [0] UNEQUIP ({TALISMANS[player['talisman']]['name']})")
            for i,tk in enumerate(ts):
                if tk != player["talisman"]:
                    print(f"  [{i+1}] {TALISMANS[tk]['name']} -- {TALISMANS[tk]['effect']}")
            print("  [B] BACK")
            tch = dinput("  > ").strip().lower()
            if tch == "0" and player["talisman"]:
                player["talisman"] = None; _recalc(player); typewrite("  Talisman unequipped.", 0.04); time.sleep(0.8)
            elif tch.isdigit() and 0 <= int(tch)-1 < len(ts):
                equip_talisman(player, ts[int(tch)-1]); time.sleep(0.8)
        elif ch=="v":
            show_inventory(player)
            dinput("\n  PRESS ENTER TO RETURN...")
        elif ch=="b":
            break

class ArenaPlayer:
    def __init__(self,pd):
        s=pd["stats"]
        self.y=0; self.x=0
        self.hp=pd["hp"]; self.max_hp=pd["max_hp"]
        self.energy=100; self.max_energy=100
        self.move_speed=max(1,5-s["AGI"]//4)
        self.iframe_count=8+s["AGI"]
        self.w_data=WEAPONS.get(pd["weapon"],WEAPONS["bare_hands"])
        self.atk_cooldown=self.w_data["cooldown"]
        self.atk_range=3
        self.dodge_frames=0; self.inv_frames=0; self.atk_frames=0
        self.last_dy=0; self.last_dx=1
        self.symbol='@'
        self.consumables=dict(pd.get("consumables",{}))
        self.dmg_redux=pd.get("dmg_redux",0)
        self.str_stat=s["STR"]; self.agi_stat=s["AGI"]
        self.wil_stat=s["WIL"]; self.per_stat=s["PER"]
        self.talisman=pd.get("talisman")
        self.stun_timer=0
        
        self.toxic_stacks=0; self.toxic_timer=0
        self.cold=False; self.cold_timer=0
        self.burn=False; self.burn_timer=0
        self.hard_mode = pd.get("hard_mode", False)
        self.weak_weapons = pd.get("weak_weapons", False)
        self.corrupted = pd.get("flags", {}).get("administrator_corrupted") == "true"
        
    @property
    def dodge_cost(self):
        cost = 10 if self.talisman=="mountain_still" else 15
        if self.cold: cost += 15 # Cold makes dodging exhausting
        return cost
 
class ArenaMinion:
    def __init__(self,y,x,mtype):
        self.y=y; self.x=x; self.type=mtype
        self.hp=15 if mtype=="stillborn" else 22
        self.speed=8 if mtype=="stillborn" else 5
        self.timer=random.randint(0,5)
        self.symbol='s' if mtype=="stillborn" else 'w'
        self.dmg=(1,3) if mtype=="stillborn" else (4,8)
        self.toxic=mtype=="rotten_walker"
 
# ── ASHEN TREE ARENA ──────────────────────────────────────
class AshenTreeBoss:
    def __init__(self,y,x):
        self.y=y; self.x=x
        self.hp=200; self.max_hp=200; self.symbol='T'; self.phase=1
        self.summon_timer=0; self.summon_cd=120
        self.thorn_warn_timer=0; self.thorn_warn_cd=90
        self.thorn_active=False; self.thorn_linger=60; self.thorn_linger_t=0
        self.thorn_cells=[]; self.thorn_warning=[]
        self.warn_frames=30; self.warn_t=0; self.is_warning=False
 
def ashen_tree_ai(boss,minions,ap,ay,ax,ah,aw,frame):
    msgs=[]
    if boss.hp<boss.max_hp//2 and boss.phase==1:
        boss.phase=2; boss.summon_cd=70; boss.thorn_warn_cd=60
        msgs.append("THE TREE GROANS. IT QUICKENS.")
    boss.summon_timer+=1
    if boss.summon_timer>=boss.summon_cd:
        boss.summon_timer=0
        mtype="hollow_walker" if boss.phase==2 else "stillborn"
        edges=[]
        for y in range(ay+1,ay+ah+1): edges+=[(y,ax+1),(y,ax+aw)]
        for x in range(ax+1,ax+aw+1): edges+=[(ay+1,x),(ay+ah,x)]
        sy,sx=random.choice(edges)
        minions.append(ArenaMinion(sy,sx,mtype))
        msgs.append(f"TREE SUMMONS. {'WALKER' if mtype=='hollow_walker' else 'STILLBORN'} EMERGES.")
    if not boss.is_warning and not boss.thorn_active:
        boss.thorn_warn_timer+=1
        if boss.thorn_warn_timer>=boss.thorn_warn_cd:
            boss.thorn_warn_timer=0; boss.is_warning=True; boss.warn_t=boss.warn_frames
            # Thorn Hitbox Expansion: Each thorn now covers a 3x3 area
            count = 3 if boss.phase == 1 else 5
            roots = [(random.randint(ay+1,ay+ah),random.randint(ax+1,ax+aw)) for _ in range(count)]
            boss.thorn_warning = []
            for (ry, rx) in roots:
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        wy, wx = ry+dy, rx+dx
                        if ay+1 <= wy <= ay+ah and ax+1 <= wx <= ax+aw:
                            boss.thorn_warning.append((wy, wx))
            boss.thorn_warning = list(set(boss.thorn_warning)) # Remove duplicates
            msgs.append("THE TREE SHUDDERS. ROOT THORNS INCOMING.")
    if boss.is_warning:
        boss.warn_t-=1
        if boss.warn_t<=0:
            boss.is_warning=False; boss.thorn_active=True
            boss.thorn_linger_t=boss.thorn_linger
            boss.thorn_cells=list(boss.thorn_warning); boss.thorn_warning=[]
            msgs.append("THORNS ERUPT.")
    if boss.thorn_active:
        boss.thorn_linger_t-=1
        if boss.thorn_linger_t<=0:
            boss.thorn_active=False; boss.thorn_cells=[]
    return msgs
 
# ── DROWNED CHOIR ARENA ───────────────────────────────────
class ChoirVoice:
    def __init__(self,y,x,idx):
        self.y=y; self.x=x; self.idx=idx
        self.hp=40; self.max_hp=40
        self.symbol=str(idx)
        self.speed=4; self.timer=random.randint(0,4)
        self.toxic_cloud_timer=0; self.toxic_cloud_cd=60
        self.toxic = True 
 
class ChoirArena:
    def __init__(self,ay,ax,ah,aw):
        self.toxic_clouds=[]  
        self.phase=1
        self.voices=[
            ChoirVoice(ay+ah//3,      ax+aw*2//3, 1),
            ChoirVoice(ay+ah*2//3,    ax+aw*2//3, 2),
            ChoirVoice(ay+ah//2,      ax+aw*3//4, 3),
        ]
        self.fused_hp=0  
 
    @property
    def all_dead(self):
        return all(v.hp<=0 for v in self.voices)
 
def choir_ai(choir,ap,ay,ax,ah,aw):
    msgs=[]
    for v in choir.voices:
        if v.hp<=0: continue
        v.timer+=1
        if v.timer>=v.speed:
            v.timer=0
            dy=1 if v.y<ap.y else (-1 if v.y>ap.y else 0)
            dx=1 if v.x<ap.x else (-1 if v.x>ap.x else 0)
            if random.random()<0.3:
                if random.random()<0.5: dx=0
                else: dy=0
            ny=v.y+dy; nx=v.x+dx
            if ay+1<=ny<=ay+ah and ax+1<=nx<=ax+aw:
                v.y=ny; v.x=nx
        
        v.toxic_cloud_timer+=1
        if v.toxic_cloud_timer>=v.toxic_cloud_cd:
            v.toxic_cloud_timer=0
            choir.toxic_clouds.append([v.y,v.x,40])
            msgs.append(f"VOICE {v.idx} EXHALES. TOXIC CLOUD.")
    expired=[]
    for cloud in choir.toxic_clouds:
        cloud[2]-=1
        if cloud[2]<=0: expired.append(cloud)
    for e in expired:
        if e in choir.toxic_clouds: choir.toxic_clouds.remove(e)
    
    alive=[v for v in choir.voices if v.hp>0]
    if len(alive)==1 and choir.phase==1:
        choir.phase=2; alive[0].speed=2
        msgs.append("THE LAST VOICE SCREAMS. IT MOVES FASTER.")
    return msgs
 
# ── AVALANCHE ARENA ───────────────────────────────────────
class AvalancheWave:
    def __init__(self,ay,ax,ah,aw,direction,phase):
        self.ay=ay; self.ax=ax; self.ah=ah; self.aw=aw
        self.direction=direction  
        self.phase=phase
        self.advance_timer=0; self.advance_speed=3
        self.width=2  # Perfect 2x2 gap thickness
        
        # This will carve a safe gap 2 tiles high
        self.gap_row=random.randint(ay+2, ay+ah-3) 
        
        if direction=='right':
            self.front=ax+1
        elif direction=='left':
            self.front=ax+aw
        else:
            self.front=ay+1
        self.done=False
        self.warn_timer=15  # Telegraph duration
 
    def cells(self):
        """Return all cells currently occupied by the wave, leaving a 2x2 gap."""
        result=[]
        if self.direction=='right':
            for col in range(self.front,min(self.front+self.width,self.ax+self.aw+1)):
                for row in range(self.ay+1,self.ay+self.ah+1):
                    if not (self.gap_row <= row <= self.gap_row+1): result.append((row,col))
        elif self.direction=='left':
            for col in range(max(self.front-self.width,self.ax+1),self.front+1):
                for row in range(self.ay+1,self.ay+self.ah+1):
                    if not (self.gap_row <= row <= self.gap_row+1): result.append((row,col))
        return result
 
    def advance(self):
        if self.warn_timer > 0:
            self.warn_timer -= 1
            return
        self.advance_timer+=1
        if self.advance_timer>=self.advance_speed:
            self.advance_timer=0
            if self.direction=='right':
                self.front+=1
                if self.front>self.ax+self.aw+self.width: self.done=True
            elif self.direction=='left':
                self.front-=1
                if self.front<self.ax-self.width: self.done=True
 
class AvalancheBoss:
    def __init__(self,ay,ax,ah,aw):
        self.ay=ay; self.ax=ax; self.ah=ah; self.aw=aw
        self.hp=180; self.max_hp=180; self.phase=1
        self.waves=[]; self.wave_timer=0; self.wave_cd=80
        self.core_y=ay+ah//2; self.core_x=ax+aw//2
        self.core_exposed=False; self.expose_timer=0; self.expose_cd=100
        self.expose_duration=40; self.expose_t=0
 
    def spawn_wave(self):
        if self.phase==1:
            direction=random.choice(['right','left'])
            self.waves.append(AvalancheWave(self.ay,self.ax,self.ah,self.aw,direction,1))
        else:
            # Bug Fix: Ensure Phase 2 waves share the same gap row to create a dodging tunnel!
            w1 = AvalancheWave(self.ay,self.ax,self.ah,self.aw,'right',2)
            w2 = AvalancheWave(self.ay,self.ax,self.ah,self.aw,'left',2)
            shared_gap = random.randint(self.ay+2, self.ay+self.ah-3)
            w1.gap_row = shared_gap
            w2.gap_row = shared_gap
            self.waves.extend([w1, w2])
 
def avalanche_ai(boss,ap,frame):
    msgs=[]
    if boss.hp<boss.max_hp//2 and boss.phase==1:
        boss.phase=2; boss.wave_cd=40  # Faster summons in phase 2
        msgs.append("THE AVALANCHE SPLITS. TWO WAVES.")
    boss.wave_timer+=1
    if boss.wave_timer>=boss.wave_cd:
        boss.wave_timer=0; boss.spawn_wave()
        msgs.append("AVALANCHE WAVE INCOMING. FIND THE GAP.")
    for w in list(boss.waves):
        w.advance()
        if w.done and w in boss.waves: boss.waves.remove(w)
    
    boss.expose_timer+=1
    if boss.expose_timer>=boss.expose_cd and not boss.core_exposed:
        boss.expose_timer=0; boss.core_exposed=True; boss.expose_t=boss.expose_duration
        msgs.append("THE CORE IS EXPOSED. ATTACK NOW.")
    if boss.core_exposed:
        boss.expose_t-=1
        if boss.expose_t<=0:
            boss.core_exposed=False
            msgs.append("THE CORE RETREATS.")
    return msgs
 
class SandMaw:
    def __init__(self,ay,ax,ah,aw):
        self.ay=ay; self.ax=ax; self.ah=ah; self.aw=aw
        self.hp=200; self.max_hp=200; self.phase=1
        # Burrow state
        self.burrowed=True
        self.burrow_timer=0; self.burrow_cd=90      # time underground
        # Warning state -- [?] shows before surface
        self.warning=False; self.warn_timer=0; self.warn_dur=30
        self.warn_y=0; self.warn_x=0
        # Surface state -- exposed, attackable
        self.surface=False; self.surface_timer=0; self.surface_dur=50
        self.surface_y=0; self.surface_x=0
        # Sand spray -- damages ring around surface point
        self.spray_cells=[]; self.spray_timer=0; self.spray_dur=15
        # Phase 2: fake warnings
        self.fake_warning=False; self.fake_warn_timer=0; self.fake_warn_dur=25
        self.fake_y=0; self.fake_x=0
        self.phase2_attack_timer=0; self.phase2_attack_cd=70

    def _rand_pos(self):
        y=random.randint(self.ay+2,self.ay+self.ah-2)
        x=random.randint(self.ax+3,self.ax+self.aw-3)
        return y,x

def sand_maw_ai(boss,ap,frame):
    msgs=[]

    if boss.hp<boss.max_hp//2 and boss.phase==1:
        boss.phase=2; boss.burrow_cd=60; boss.surface_dur=35
        msgs.append("THE SAND MAW ACCELERATES. IT IS IMPATIENT NOW.")

    # Clear spray
    if boss.spray_cells and boss.spray_timer>0:
        boss.spray_timer-=1
        if boss.spray_timer<=0:
            boss.spray_cells=[]

    # Surface state
    if boss.surface:
        boss.surface_timer-=1
        if boss.surface_timer<=0:
            boss.surface=False
            boss.burrowed=True
            boss.burrow_timer=0
            msgs.append("THE SAND MAW BURROWS. TRACK ITS WARNING.")
        return msgs

    # Warning state
    if boss.warning:
        boss.warn_timer-=1
        if boss.warn_timer<=0:
            boss.warning=False
            boss.surface=True
            boss.surface_timer=boss.surface_dur
            boss.surface_y=boss.warn_y
            boss.surface_x=boss.warn_x
            # Sand spray ring around surface point (5x5 border excluding 3x3 center)
            boss.spray_cells=[]
            for dy in range(-2,3):
                for dx in range(-2,3):
                    if abs(dy)<=1 and abs(dx)<=1: continue
                    sy=boss.surface_y+dy; sx=boss.surface_x+dx
                    if boss.ay+1<=sy<=boss.ay+boss.ah and boss.ax+1<=sx<=boss.ax+boss.aw:
                        boss.spray_cells.append((sy,sx))
            boss.spray_timer=boss.spray_dur
            msgs.append("THE SAND MAW SURFACES. ATTACK THE CORE.")
        return msgs

    # Fake warning (phase 2)
    if boss.fake_warning:
        boss.fake_warn_timer-=1
        if boss.fake_warn_timer<=0:
            boss.fake_warning=False
            boss.burrowed=True
            boss.burrow_timer=0
            msgs.append("SAND SHIFTS. NOTHING SURFACES.")
        return msgs

    # Burrowed -- count down
    if boss.burrowed:
        boss.burrow_timer+=1
        if boss.burrow_timer>=boss.burrow_cd:
            boss.burrow_timer=0
            boss.burrowed=False
            # Phase 2: sometimes fake
            if boss.phase==2 and random.random()<0.4:
                boss.fake_warning=True
                boss.fake_warn_timer=boss.fake_warn_dur
                fy,fx=boss._rand_pos()
                boss.fake_y=fy; boss.fake_x=fx
                msgs.append("SAND BULGES. [?] SOMETHING APPROACHES.")
            else:
                boss.warning=True
                boss.warn_timer=boss.warn_dur
                wy,wx=boss._rand_pos()
                # Bias toward player position to keep it threatening
                if random.random()<0.6:
                    wy=max(boss.ay+2,min(boss.ay+boss.ah-2,ap.y+random.randint(-3,3)))
                    wx=max(boss.ax+3,min(boss.ax+boss.aw-3,ap.x+random.randint(-4,4)))
                boss.warn_y=wy; boss.warn_x=wx
                msgs.append("SAND BULGES. [?] MOVE AWAY.")

    return msgs

# ── ASH LORD ARENA ──────────────────────────────────────
class AshLordBoss:
    def __init__(self, y, x):
        self.y, self.x = y, x
        self.hp = 350; self.max_hp = 350; self.symbol = 'A'; self.phase = 1
        self.lash_timer = 0; self.lash_cd = 70
        self.lash_warn_cells = []; self.lash_active_cells = []
        self.fall_timer = 0; self.fall_cd = 40
        self.fall_warn_cells = []; self.fall_active_cells = []

def ash_lord_ai(boss, ap, ay, ax, ah, aw, frame):
    msgs = []
    if boss.hp < boss.max_hp // 2 and boss.phase == 1:
        boss.phase = 2; boss.lash_cd = 45; msgs.append("THE ASH LORD ROARS. ROOTS TREMBLE.")
    
    boss.lash_timer += 1
    if boss.lash_timer >= boss.lash_cd:
        boss.lash_timer = 0; boss.lash_warn_cells = []
        dy = 1 if ap.y > boss.y else -1
        for i in range(1, 8):
            ty = boss.y + i * dy
            if ay+1 <= ty <= ay+ah: boss.lash_warn_cells.append((ty, boss.x))
        msgs.append("A ROOT LASHES OUT.")

    boss.fall_timer += 1
    if boss.fall_timer >= boss.fall_cd:
        boss.fall_timer = 0; fy = random.randint(ay+2, ay+ah-1); fx = random.randint(ax+2, ax+aw-1)
        boss.fall_warn_cells = [(fy+dy, fx+dx) for dy in range(-1,2) for dx in range(-1,2) if ay+1<=fy+dy<=ay+ah and ax+1<=fx+dx<=ax+aw]
    
    if frame % 20 == 0:
        boss.lash_active_cells = list(boss.lash_warn_cells); boss.lash_warn_cells = []
        boss.fall_active_cells = list(boss.fall_warn_cells); boss.fall_warn_cells = []
    elif frame % 20 == 10:
        boss.lash_active_cells = []; boss.fall_active_cells = []
    return msgs

# ── PALE LORD ARENA ─────────────────────────────────────
class PaleLordBoss:
    def __init__(self, y, x):
        self.y, self.x = y, x
        self.hp = 300; self.max_hp = 300; self.symbol = 'M'; self.phase = 1
        self.pulse_timer = 0; self.pulse_cd = 60
        self.pulse_cells = []

def pale_lord_ai(boss, ap, ay, ax, ah, aw, frame):
    msgs = []
    if frame % 50 == 0:
        boss.y = random.randint(ay+2, ay+ah-1); boss.x = random.randint(ax+2, ax+aw-1)
        msgs.append("THE MOURNING SHIFTS.")
    boss.pulse_timer += 1
    if boss.pulse_timer >= boss.pulse_cd:
        boss.pulse_timer = 0; r = 3 if boss.phase==1 else 5
        boss.pulse_cells = [(boss.y+dy, boss.x+dx) for dy in range(-r, r+1) for dx in range(-r, r+1) if abs(dy)+abs(dx) <= r]
        msgs.append("A PULSE OF SORROW.")
    if frame % 15 == 0: boss.pulse_cells = []
    return msgs

# ── ROT LORD ARENA ──────────────────────────────────────
class RotLordBoss:
    def __init__(self, y, x):
        self.y, self.x = y, x
        self.hp = 400; self.max_hp = 400; self.symbol = 'R'; self.phase = 1
        self.clouds = []

def rot_lord_ai(boss, ap, ay, ax, ah, aw, frame):
    msgs = []
    if frame % 40 == 0:
        boss.clouds.append([boss.y, boss.x, 60])
        msgs.append("SPORES RELEASED.")
    for c in list(boss.clouds):
        c[2] -= 1
        if c[2] <= 0: boss.clouds.remove(c)
    return msgs

# ── FROST LORD ARENA ────────────────────────────────────
class FrostLordBoss:
    def __init__(self, y, x):
        self.y, self.x = y, x
        self.hp = 380; self.max_hp = 380; self.symbol = 'F'; self.phase = 1
        self.spikes = []

def frost_lord_ai(boss, ap, ay, ax, ah, aw, frame):
    msgs = []
    if frame % 30 == 0:
        dy = 1 if ap.y > boss.y else -1; dx = 1 if ap.x > boss.x else -1
        boss.spikes = [(boss.y+i*dy, boss.x+i*dx) for i in range(1, 6) if ay+1<=boss.y+i*dy<=ay+ah and ax+1<=boss.x+i*dx<=ax+aw]
    if frame % 30 == 15: boss.spikes = []
    return msgs

# ── DUNE LORD ARENA ─────────────────────────────────────
class DuneLordBoss:
    def __init__(self, y, x):
        self.y, self.x = y, x
        self.hp = 320; self.max_hp = 320; self.symbol = 'D'; self.phase = 1
        self.vortex_y, self.vortex_x = y, x

def dune_lord_ai(boss, ap, ay, ax, ah, aw, frame):
    if frame % 4 == 0:
        if ap.y < boss.y: ap.y += 1
        elif ap.y > boss.y: ap.y -= 1
        if ap.x < boss.x: ap.x += 1
        elif ap.x > boss.x: ap.x -= 1
    return ["THE SAND PULLS YOU IN."]

# ── CINDER LORD ARENA ───────────────────────────────────
class CinderLordBoss:
    def __init__(self, y, x):
        self.y, self.x = y, x
        self.hp = 450; self.max_hp = 450; self.symbol = 'C'; self.phase = 1
        self.vents = []

def cinder_lord_ai(boss, ap, ay, ax, ah, aw, frame):
    msgs = []
    if frame % 50 == 0:
        boss.vents = [(random.randint(ay+1, ay+ah), random.randint(ax+1, ax+aw)) for _ in range(5)]
        msgs.append("LAVA VENTS OPEN.")
    if frame % 50 == 25: boss.vents = []
    return msgs

class BasaltTitanBoss:
    def __init__(self, y, x):
        self.y = y
        self.x = x
        self.hp = 220
        self.max_hp = 220
        self.symbol = 'P'
        self.phase = 1
        
        # Magma pools (warning and active)
        self.pool_timer = 0
        self.pool_cd = 80
        self.pool_warning_cells = []
        self.pool_active_cells = []
        self.pool_warn_timer = 0
        self.pool_warn_dur = 30
        self.pool_linger_timer = 0
        self.pool_linger_dur = 45
        
        # Fire line (like shockwave)
        self.fire_line_timer = 0
        self.fire_line_cd = 100
        self.is_firing_line = False
        self.line_warn_timer = 0
        self.line_warn_dur = 30
        self.line_active = False
        self.line_active_timer = 0
        self.line_active_dur = 15
        self.line_y = 0
        self.line_x = 0

def basalt_titan_ai(boss, ap, ay, ax, ah, aw, frame):
    msgs = []
    
    # Phase shift
    if boss.hp < boss.max_hp // 2 and boss.phase == 1:
        boss.phase = 2
        boss.pool_cd = 50
        boss.fire_line_cd = 70
        msgs.append("THE TITAN'S BURN INTENSIFIES.")
        
    # Magma pools logic
    if not boss.pool_warning_cells and not boss.pool_active_cells:
        boss.pool_timer += 1
        if boss.pool_timer >= boss.pool_cd:
            boss.pool_timer = 0
            boss.pool_warning_cells = []
            count = 4 if boss.phase == 2 else 3
            for _ in range(count):
                py = random.randint(ay + 2, ay + ah - 2)
                px = random.randint(ax + 2, ax + aw - 2)
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        wy = py + dy
                        wx = px + dx
                        if ay + 1 <= wy <= ay + ah and ax + 1 <= wx <= ax + aw:
                            boss.pool_warning_cells.append((wy, wx))
            boss.pool_warning_cells = list(set(boss.pool_warning_cells))
            boss.pool_warn_timer = boss.pool_warn_dur
            msgs.append("MAGMA RISING UNDERFOOT.")
            
    if boss.pool_warning_cells and boss.pool_warn_timer > 0:
        boss.pool_warn_timer -= 1
        if boss.pool_warn_timer <= 0:
            boss.pool_active_cells = list(boss.pool_warning_cells)
            boss.pool_warning_cells = []
            boss.pool_linger_timer = boss.pool_linger_dur
            msgs.append("MAGMA ERUPTS.")
            
    if boss.pool_active_cells and boss.pool_linger_timer > 0:
        boss.pool_linger_timer -= 1
        if boss.pool_linger_timer <= 0:
            boss.pool_active_cells = []
            
    # Fire Line logic
    if not boss.is_firing_line and not boss.line_active:
        boss.fire_line_timer += 1
        if boss.fire_line_timer >= boss.fire_line_cd:
            boss.fire_line_timer = 0
            boss.is_firing_line = True
            boss.line_warn_timer = boss.line_warn_dur
            boss.line_y = ap.y
            boss.line_x = ap.x
            msgs.append("THE BASALT TITAN CHARGES HEAT.")
            
    if boss.is_firing_line:
        boss.line_warn_timer -= 1
        if boss.line_warn_timer <= 0:
            boss.is_firing_line = False
            boss.line_active = True
            boss.line_active_timer = boss.line_active_dur
            msgs.append("FIRE LINE FIRES.")
            
    if boss.line_active:
        boss.line_active_timer -= 1
        if boss.line_active_timer <= 0:
            boss.line_active = False
            
    return msgs

def show_lord_destroyed_banner():
    banner = [
        "  ░░░░░░  ░░░░░░  ░░░░░░  ░░░░    ░░░░░░  ░░░░░░  ░░░░░░  ░░░░░░  ░░░░░░  ░░░░░░  ░░░░░░",
        "  ██  ██  ██  ██  ██  ██  ██  ██  ██  ██  ██      ██        ██    ██  ██  ██  ██  ██  ██",
        "  ██      ██  ██  ██████  ██  ██  ██  ██  ██████  ██████    ██    ██  ██  ██  ██  ██  ██",
        "  ██  ██  ██  ██  ██  ██  ██  ██  ██  ██      ██      ██    ██    ██  ██  ██  ██  ██  ██",
        "  ██████  ██████  ██  ██  ████    ██████  ██████  ██████    ██    ██████  ██████  ██████",
        "  ──────────────────────────────────────────────────────────────────────────────────────",
        "                                    L O R D   D E S T R O Y E D                             ",
        "  ──────────────────────────────────────────────────────────────────────────────────────"
    ]
    clear()
    print("\n" * 4)
    for line in banner:
        typewrite(line + "\n", 0.01)
        time.sleep(0.08)
    time.sleep(2.0)

def show_boss_dialogue(stdscr, title, lines):
    h, w = stdscr.getmaxyx()
    box_h = len(lines) + 4
    box_w = max(len(l) for l in lines) + 6
    box_y = (h - box_h) // 2
    box_x = (w - box_w) // 2
    
    for y in range(box_y, box_y + box_h):
        for x in range(box_x, box_x + box_w):
            if y == box_y or y == box_y + box_h - 1:
                try: stdscr.addstr(y, x, "═", curses.color_pair(6) | curses.A_BOLD)
                except: pass
            elif x == box_x or x == box_x + box_w - 1:
                try: stdscr.addstr(y, x, "║", curses.color_pair(6) | curses.A_BOLD)
                except: pass
            else:
                try: stdscr.addstr(y, x, " ", curses.color_pair(7))
                except: pass
                
    try: stdscr.addstr(box_y, box_x + 2, f" {title} ", curses.color_pair(1) | curses.A_BOLD)
    except: pass
    
    for i, line in enumerate(lines):
        try: stdscr.addstr(box_y + 2 + i, box_x + 3, line, curses.color_pair(7) | curses.A_BOLD)
        except: pass
        
    stdscr.refresh()
    curses.napms(2000)


class AdministratorBoss:
    def __init__(self, y, x, ay, ax, ah, aw):
        self.y = y; self.x = x
        self.ay = ay; self.ax = ax; self.ah = ah; self.aw = aw
        self.hp = 1200; self.max_hp = 1200
        self.symbol = 'A'
        self.phase = 1

        # Static line attack
        self.line_timer = 0
        self.line_cd = 55        # shrinks each phase
        self.line_warn_cells = []
        self.line_active_cells = []
        self.line_warn_t = 0
        self.line_warn_duration = 18
        self.line_active_t = 0
        self.line_active_duration = 12

        # Glitch tiles (phase 2+)
        self.glitch_timer = 0
        self.glitch_cd = 45
        self.glitch_warn_cells = []
        self.glitch_active_cells = []
        self.glitch_warn_t = 0
        self.glitch_active_t = 0

        # HP rewrite (phase 3)
        self.rewrite_timer = 0
        self.rewrite_cd = 80
        self.rewrite_warning = False
        self.rewrite_warn_t = 0

        self.said_phase2 = False
        self.said_phase3 = False

def administrator_ai(boss, ap, frame):
    msgs = []

    # Phase transitions
    if boss.hp < int(boss.max_hp * 0.6) and boss.phase == 1:
        boss.phase = 2
        boss.line_cd = 42
    if boss.hp < int(boss.max_hp * 0.3) and boss.phase == 2:
        boss.phase = 3
        boss.line_cd = 30

    # Phase 3: drift toward player
    if boss.phase == 3 and frame % 6 == 0:
        if ap.y < boss.y: boss.y -= 1
        elif ap.y > boss.y: boss.y += 1
        if ap.x < boss.x: boss.x -= 1
        elif ap.x > boss.x: boss.x += 1
        boss.y = max(boss.ay + 1, min(boss.ay + boss.ah, boss.y))
        boss.x = max(boss.ax + 1, min(boss.ax + boss.aw, boss.x))

    # Expire active cells
    if boss.line_active_cells:
        boss.line_active_t -= 1
        if boss.line_active_t <= 0:
            boss.line_active_cells = []
    if boss.glitch_active_cells:
        boss.glitch_active_t -= 1
        if boss.glitch_active_t <= 0:
            boss.glitch_active_cells = []

    # Expire warn cells -> activate
    if boss.line_warn_cells and boss.line_warn_t > 0:
        boss.line_warn_t -= 1
        if boss.line_warn_t <= 0:
            boss.line_active_cells = list(boss.line_warn_cells)
            boss.line_warn_cells = []
            boss.line_active_t = boss.line_active_duration
            msgs.append("STATIC DISCHARGE.")
    if boss.glitch_warn_cells and boss.glitch_warn_t > 0:
        boss.glitch_warn_t -= 1
        if boss.glitch_warn_t <= 0:
            boss.glitch_active_cells = list(boss.glitch_warn_cells)
            boss.glitch_warn_cells = []
            boss.glitch_active_t = 20
            msgs.append("FLOOR CORRUPTED.")

    # Fire new static line
    if not boss.line_warn_cells and not boss.line_active_cells:
        boss.line_timer += 1
        if boss.line_timer >= boss.line_cd:
            boss.line_timer = 0
            boss.line_warn_cells = []
            # Pick axis based on player position relative to boss
            if random.random() < 0.5:
                # Horizontal line through player row
                for x in range(boss.ax + 1, boss.ax + boss.aw + 1):
                    boss.line_warn_cells.append((ap.y, x))
                # In phase 2+ also add a second line one row away
                if boss.phase >= 2:
                    off = 1 if ap.y < boss.ay + boss.ah // 2 else -1
                    for x in range(boss.ax + 1, boss.ax + boss.aw + 1):
                        boss.line_warn_cells.append((ap.y + off, x))
            else:
                # Vertical line through player column
                for y in range(boss.ay + 1, boss.ay + boss.ah + 1):
                    boss.line_warn_cells.append((y, ap.x))
                if boss.phase >= 2:
                    off = 1 if ap.x < boss.ax + boss.aw // 2 else -1
                    for y in range(boss.ay + 1, boss.ay + boss.ah + 1):
                        boss.line_warn_cells.append((y, ap.x + off))
            boss.line_warn_cells = list(set(boss.line_warn_cells))
            boss.line_warn_t = boss.line_warn_duration
            msgs.append("SYSTEM: ROUTING DISCHARGE...")

    # Glitch tiles (phase 2+)
    if boss.phase >= 2 and not boss.glitch_warn_cells and not boss.glitch_active_cells:
        boss.glitch_timer += 1
        if boss.glitch_timer >= boss.glitch_cd:
            boss.glitch_timer = 0
            count = 4 if boss.phase == 2 else 7
            boss.glitch_warn_cells = []
            for _ in range(count):
                gy = random.randint(boss.ay + 1, boss.ay + boss.ah)
                gx = random.randint(boss.ax + 1, boss.ax + boss.aw)
                boss.glitch_warn_cells.append((gy, gx))
            boss.glitch_warn_cells = list(set(boss.glitch_warn_cells))
            boss.glitch_warn_t = 22
            msgs.append("MEMORY FAULT: FLOOR CORRUPTING...")

    # HP rewrite warning (phase 3)
    if boss.phase == 3:
        if boss.rewrite_warning:
            boss.rewrite_warn_t -= 1
            if boss.rewrite_warn_t <= 0:
                boss.rewrite_warning = False
                # Rewrite fires in hit detection loop (flag checked there)
                boss._do_rewrite = True
        else:
            boss.rewrite_timer += 1
            if boss.rewrite_timer >= boss.rewrite_cd:
                boss.rewrite_timer = 0
                boss.rewrite_warning = True
                boss.rewrite_warn_t = 20
                boss._do_rewrite = False
                msgs.append("ADMINISTRATOR: REWRITING YOUR INTEGRITY...")

    return msgs

class KingOfNothingBoss:
    def __init__(self, y, x, ay, ax, ah, aw):
        self.y = y
        self.x = x
        self.ay = ay; self.ax = ax; self.ah = ah; self.aw = aw
        self.hp = 800
        self.max_hp = 800
        self.symbol = 'K'
        self.phase = 1
        self.attack_timer = 0
        self.attack_cd = 60
        self.current_attack = None
        self.attack_duration = 0
        
        self.swipe_warn_cells = []
        self.swipe_active_cells = []
        self.swipe_timer = 0
        self.swipe_warn_duration = 20
        self.swipe_active_duration = 10
        
        self.smash_warn_cells = []
        self.smash_active_cells = []
        self.smash_timer = 0
        self.smash_warn_duration = 25
        self.smash_active_duration = 15
        
        self.void_orbs = []
        self.void_timer = 0
        self.void_cd = 30
        self.null_warn_cells = []
        self.null_active_cells = []
        self.null_timer = 0
        self.null_cd = 40
        self.null_warn_t = 0
        self.null_active_t = 0
        
        self.cracks = []
        self.said_phase2 = False
        self.said_phase3 = False

def king_of_nothing_ai(boss, ap, frame):
    msgs = []
    
    if boss.hp < int(boss.max_hp * 0.5) and boss.phase == 1:
        boss.phase = 2
        boss.attack_cd = 50
    if boss.hp < int(boss.max_hp * 0.3) and boss.phase == 2:
        boss.phase = 3
        boss.attack_cd = 40

    if boss.swipe_active_cells:
        boss.swipe_timer -= 1
        if boss.swipe_timer <= 0:
            boss.swipe_active_cells = []
            
    if boss.smash_active_cells:
        boss.smash_timer -= 1
        if boss.smash_timer <= 0:
            boss.smash_active_cells = []

    if boss.null_active_cells:
        boss.null_active_t -= 1
        if boss.null_active_t <= 0:
            boss.null_active_cells = []

    if boss.phase == 3:
        for orb in list(boss.void_orbs):
            orb["radius"] += 0.35
            orb["cells"] = []
            cy = boss.ay + boss.ah // 2
            cx = boss.ax + boss.aw // 2
            r = int(orb["radius"])
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if r - 1 <= math.sqrt(dy*dy + dx*dx) <= r + 1:
                        oy = cy + dy
                        ox = cx + dx
                        if boss.ay + 1 <= oy <= boss.ay + boss.ah and boss.ax + 1 <= ox <= boss.ax + boss.aw:
                            orb["cells"].append((oy, ox))
            orb["timer"] -= 1
            if orb["timer"] <= 0 or orb["radius"] > max(boss.ah, boss.aw):
                boss.void_orbs.remove(orb)

        boss.void_timer += 1
        if boss.void_timer >= boss.void_cd:
            boss.void_timer = 0
            boss.void_orbs.append({
                "radius": 1.0,
                "cells": [],
                "timer": 40
            })
            msgs.append("VOID ENERGY EXPANDS FROM THE CORE.")

        if frame % 4 == 0:
            cy = boss.ay + boss.ah // 2
            cx = boss.ax + boss.aw // 2
            if ap.y < cy: ap.y += 1
            elif ap.y > cy: ap.y -= 1
            if ap.x < cx: ap.x += 1
            elif ap.x > cx: ap.x -= 1

        boss.null_timer += 1
        if boss.null_timer >= boss.null_cd and not boss.null_warn_cells and not boss.null_active_cells:
            boss.null_timer = 0
            boss.null_warn_cells = []
            for _ in range(3):
                ny = random.randint(boss.ay + 2, boss.ay + boss.ah - 2)
                nx = random.randint(boss.ax + 2, boss.ax + boss.aw - 2)
                for dy in range(-1, 1):
                    for dx in range(-1, 1):
                        boss.null_warn_cells.append((ny + dy, nx + dx))
            boss.null_warn_cells = list(set(boss.null_warn_cells))
            boss.null_warn_t = 20
            msgs.append("THE VOID TEARS THE FLOOR.")

    if boss.null_warn_cells and boss.null_warn_t > 0:
        boss.null_warn_t -= 1
        if boss.null_warn_t <= 0:
            boss.null_active_cells = list(boss.null_warn_cells)
            boss.null_warn_cells = []
            boss.null_active_t = 30

    if not boss.swipe_warn_cells and not boss.swipe_active_cells and        not boss.smash_warn_cells and not boss.smash_active_cells:
        boss.attack_timer += 1
        if boss.attack_timer >= boss.attack_cd:
            boss.attack_timer = 0
            
            if boss.phase == 1:
                boss.current_attack = "swipe"
            elif boss.phase == 2:
                boss.current_attack = random.choice(["swipe", "smash"])
            else:
                boss.current_attack = random.choice(["swipe", "smash"])
                
            if boss.current_attack == "swipe":
                boss.swipe_warn_cells = []
                dy = ap.y - boss.y
                dx = ap.x - boss.x
                if abs(dy) > abs(dx):
                    dir_y = 1 if dy > 0 else -1
                    for dist in range(1, 6):
                        ty = boss.y + dist * dir_y
                        for tx in range(boss.x - dist, boss.x + dist + 1):
                            if boss.ay + 1 <= ty <= boss.ay + boss.ah and boss.ax + 1 <= tx <= boss.ax + boss.aw:
                                boss.swipe_warn_cells.append((ty, tx))
                else:
                    dir_x = 1 if dx > 0 else -1
                    for dist in range(1, 6):
                        tx = boss.x + dist * dir_x
                        for ty in range(boss.y - dist, boss.y + dist + 1):
                            if boss.ay + 1 <= ty <= boss.ay + boss.ah and boss.ax + 1 <= tx <= boss.ax + boss.aw:
                                boss.swipe_warn_cells.append((ty, tx))
                boss.attack_duration = boss.swipe_warn_duration
                msgs.append("THE KING RAISES HIS BLADE.")
                
            elif boss.current_attack == "smash":
                boss.smash_warn_cells = []
                for dy in range(-4, 5):
                    for dx in range(-4, 5):
                        if dy*dy + dx*dx <= 16:
                            ty = boss.y + dy
                            tx = boss.x + dx
                            if boss.ay + 1 <= ty <= boss.ay + boss.ah and boss.ax + 1 <= tx <= boss.ax + boss.aw:
                                boss.smash_warn_cells.append((ty, tx))
                boss.attack_duration = boss.smash_warn_duration
                msgs.append("THE KING PREPARES TO SMASH THE FLOOR.")

    if boss.swipe_warn_cells:
        boss.attack_duration -= 1
        if boss.attack_duration <= 0:
            boss.swipe_active_cells = list(boss.swipe_warn_cells)
            boss.swipe_warn_cells = []
            boss.swipe_timer = boss.swipe_active_duration
            msgs.append("SWORD SWIPE SWINGS.")
            
    if boss.smash_warn_cells:
        boss.attack_duration -= 1
        if boss.attack_duration <= 0:
            boss.smash_active_cells = list(boss.smash_warn_cells)
            boss.smash_warn_cells = []
            boss.smash_timer = boss.smash_active_duration
            msgs.append("GROUND SMASH ERUPTS.")
            
            if ap.inv_frames == 0:
                player_caught = False
                for (sy, sx) in boss.smash_active_cells:
                    if ap.y == sy and ap.x == sx:
                        player_caught = True
                        break
                if player_caught:
                    ap.stun_timer = 35
                    boss.y = ap.y
                    boss.x = ap.x
                    boss.swipe_warn_cells = []
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            boss.swipe_warn_cells.append((boss.y + dy, boss.x + dx))
                    boss.attack_duration = 10
                    msgs.append("THE MONARCH DASHES AND SWEEPS.")

    return msgs

def run_arena_generic(player_dict, boss_type, slot):
    result_holder=[None]
 
    def _arena(stdscr):
        curses.curs_set(0); stdscr.nodelay(True); stdscr.keypad(True)
        curses.start_color()
        curses.init_pair(1,curses.COLOR_WHITE,   curses.COLOR_BLACK)
        curses.init_pair(2,curses.COLOR_RED,     curses.COLOR_BLACK)
        curses.init_pair(3,curses.COLOR_GREEN,   curses.COLOR_BLACK)
        curses.init_pair(4,curses.COLOR_YELLOW,  curses.COLOR_BLACK)
        curses.init_pair(5,curses.COLOR_CYAN,    curses.COLOR_BLACK)
        curses.init_pair(6,curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        WHITE=curses.color_pair(1); RED=curses.color_pair(2)
        GREEN=curses.color_pair(3); YELLOW=curses.color_pair(4)
        CYAN=curses.color_pair(5);  MAGENTA=curses.color_pair(6)
 
        ah=16; aw=40; ay=2; ax=2
 
        ap=ArenaPlayer(player_dict)
        ap.y=ay+ah//2; ap.x=ax+aw//4
 
        if boss_type=='ashen_tree':
            boss=AshenTreeBoss(ay+ah//2,ax+aw*3//4)
            if player_dict.get("hard_mode"):
                boss.hp = int(boss.hp * 1.5)
                boss.max_hp = int(boss.max_hp * 1.5)
            if player_dict.get("flags", {}).get("administrator_corrupted") == "true":
                boss.hp = int(boss.hp * 2.0)
                boss.max_hp = int(boss.max_hp * 2.0)
            minions=[]; choir=None; aval=None
            boss_name="ASHEN TREE"
        elif boss_type=='choir':
            choir=ChoirArena(ay,ax,ah,aw)
            if player_dict.get("hard_mode"):
                for v in choir.voices:
                    v.hp = int(v.hp * 1.5)
                    v.max_hp = int(v.max_hp * 1.5)
            if player_dict.get("flags", {}).get("administrator_corrupted") == "true":
                for v in choir.voices:
                    v.hp = int(v.hp * 2.0)
                    v.max_hp = int(v.max_hp * 2.0)
            boss=None; minions=[]
            boss_name="DROWNED CHOIR"
        elif boss_type=='avalanche':
            aval=AvalancheBoss(ay,ax,ah,aw)
            if player_dict.get("hard_mode"):
                aval.hp = int(aval.hp * 1.5)
                aval.max_hp = int(aval.max_hp * 1.5)
            if player_dict.get("flags", {}).get("administrator_corrupted") == "true":
                aval.hp = int(aval.hp * 2.0)
                aval.max_hp = int(aval.max_hp * 2.0)
            # FIX: Bind aval to boss so the global arena win-condition loop can track its health!
            boss=aval; minions=[]; choir=None
            boss_name="THE AVALANCHE"
        elif boss_type=='dune_colossus':
            boss=SandMaw(ay,ax,ah,aw)
            if player_dict.get("hard_mode"):
                boss.hp = int(boss.hp * 1.5)
                boss.max_hp = int(boss.max_hp * 1.5)
            if player_dict.get("flags", {}).get("administrator_corrupted") == "true":
                boss.hp = int(boss.hp * 2.0)
                boss.max_hp = int(boss.max_hp * 2.0)
            minions=[]; choir=None; aval=None
            boss_name="THE SAND MAW"
        elif boss_type=='pillar_colossus':
            boss=BasaltTitanBoss(ay+ah//2,ax+aw*3//4)
            if player_dict.get("hard_mode"):
                boss.hp = int(boss.hp * 1.5)
                boss.max_hp = int(boss.max_hp * 1.5)
            if player_dict.get("flags", {}).get("administrator_corrupted") == "true":
                boss.hp = int(boss.hp * 2.0)
                boss.max_hp = int(boss.max_hp * 2.0)
            minions=[]; choir=None; aval=None
            boss_name="THE BASALT TITAN"
        elif boss_type=='ash_lord':
            boss=AshLordBoss(ay+ah//2,ax+aw*3//4)
            minions=[]; choir=None; aval=None
            boss_name="THE ASH LORD"
        elif boss_type=='pale_lord':
            boss=PaleLordBoss(ay+ah//2,ax+aw*3//4)
            minions=[]; choir=None; aval=None
            boss_name="THE PALE LORD"
        elif boss_type=='rot_lord':
            boss=RotLordBoss(ay+ah//2,ax+aw*3//4)
            minions=[]; choir=None; aval=None
            boss_name="THE ROT LORD"
        elif boss_type=='frost_lord':
            boss=FrostLordBoss(ay+ah//2,ax+aw*3//4)
            minions=[]; choir=None; aval=None
            boss_name="THE FROST LORD"
        elif boss_type=='dune_lord':
            boss=DuneLordBoss(ay+ah//2,ax+aw*3//4)
            minions=[]; choir=None; aval=None
            boss_name="THE DUNE LORD"
        elif boss_type=='cinder_lord':
            boss=CinderLordBoss(ay+ah//2,ax+aw*3//4)
            minions=[]; choir=None; aval=None
            boss_name="THE CINDER LORD"
        elif boss_type=='king_of_nothing':
            boss=KingOfNothingBoss(ay+ah//2,ax+aw//2,ay,ax,ah,aw)
            if player_dict.get("hard_mode"):
                boss.hp = int(boss.hp * 1.5)
                boss.max_hp = int(boss.max_hp * 1.5)
            if player_dict.get("flags", {}).get("administrator_corrupted") == "true":
                boss.hp = int(boss.hp * 2.0)
                boss.max_hp = int(boss.max_hp * 2.0)
            minions=[]; choir=None; aval=None
            boss_name="THE KING OF NOTHING"
        elif boss_type=='administrator':
            boss=AdministratorBoss(ay+ah//2,ax+aw//2,ay,ax,ah,aw)
            if player_dict.get("hard_mode"):
                boss.hp = int(boss.hp * 1.5)
                boss.max_hp = int(boss.max_hp * 1.5)
            minions=[]; choir=None; aval=None
            boss_name="THE ADMINISTRATOR"
        else:
            result_holder[0]='quit'; return
 
        frame=0
        messages=[f"{boss_name} AWAKENS.","SURVIVE."]
        msg_t=80; dmg_flash=0; dmg_flash_t=0; last_hit_pos=None
        quickbar_msg=None; qb_t=0; result=None
 
        while True:
            stdscr.clear()
            try: key=stdscr.getch()
            except: key=-1

            if getattr(ap, "stun_timer", 0) > 0:
                ap.stun_timer -= 1
                key = -1
 
            new_y=ap.y; new_x=ap.x; mdy=0; mdx=0
 
            if key in (ord('w'),ord('W'),curses.KEY_UP):    new_y-=1; mdy=-1
            elif key in (ord('s'),ord('S'),curses.KEY_DOWN): new_y+=1; mdy=1
            elif key in (ord('a'),ord('A'),curses.KEY_LEFT): new_x-=1; mdx=-1
            elif key in (ord('d'),ord('D'),curses.KEY_RIGHT):new_x+=1; mdx=1
            elif key==ord(' '):
                hit=False; dmg=0; tgt=None
                w=ap.w_data
                if ap.atk_frames==0 and ap.energy>=w["energy"]:
                    if choir:
                        for v in choir.voices:
                            if v.hp>0 and abs(v.y-ap.y)<=ap.atk_range and abs(v.x-ap.x)<=ap.atk_range:
                                d=random.randint(*w["dmg"])
                                if w["scale"]=="STR": d+=ap.str_stat*2
                                elif w["scale"]=="AGI": d+=ap.agi_stat
                                elif w["scale"]=="WIL": d+=ap.wil_stat*2
                                elif w["scale"]=="STR+WIL": d+=ap.str_stat*2+(ap.wil_stat*1 if ap.wil_stat>=8 else 0)
                                if ap.weak_weapons: d = max(1, int(d * 0.5))
                                v.hp-=d; ap.energy-=w["energy"]; ap.atk_frames=ap.atk_cooldown
                                dmg=d; hit=True; tgt=f"VOICE {v.idx}"; last_hit_pos=(v.y,v.x); break
                    elif aval:
                        if aval.core_exposed and abs(aval.core_y-ap.y)<=ap.atk_range and abs(aval.core_x-ap.x)<=ap.atk_range:
                            d=random.randint(*w["dmg"])
                            if w["scale"]=="STR": d+=ap.str_stat*2
                            elif w["scale"]=="STR+WIL": d+=ap.str_stat*2+int(ap.wil_stat*1.5 if ap.wil_stat>=8 else 0)
                            if ap.weak_weapons: d = max(1, int(d * 0.5))
                            aval.hp-=d; ap.energy-=w["energy"]; ap.atk_frames=ap.atk_cooldown
                            dmg=d; hit=True; tgt="CORE"
                        else:
                            messages=["CORE NOT EXPOSED. WAIT FOR IT."]; msg_t=35
                    elif boss:
                        if boss_type == 'ashen_tree':
                            for m in minions:
                                if abs(m.y-ap.y)<=ap.atk_range and abs(m.x-ap.x)<=ap.atk_range:
                                    d=random.randint(*w["dmg"])
                                    if w["scale"]=="STR": d+=ap.str_stat*2
                                    if ap.weak_weapons: d = max(1, int(d * 0.5))
                                    m.hp-=d; ap.energy-=w["energy"]; ap.atk_frames=ap.atk_cooldown
                                    dmg=d; hit=True; tgt="MINION"; break
                            if not hit and abs(boss.y-ap.y)<=ap.atk_range and abs(boss.x-ap.x)<=ap.atk_range:
                                d=random.randint(*w["dmg"])
                                if w["scale"]=="STR": d+=ap.str_stat*2
                                elif w["scale"]=="WIL": d+=ap.wil_stat*2
                                if ap.weak_weapons: d = max(1, int(d * 0.5))
                                boss.hp-=d; ap.energy-=w["energy"]; ap.atk_frames=ap.atk_cooldown
                                dmg=d; hit=True; tgt="TREE"
                        elif boss_type == 'dune_colossus':
                            if boss.surface and abs(boss.surface_y-ap.y)<=ap.atk_range and abs(boss.surface_x-ap.x)<=ap.atk_range:
                                d=random.randint(*w["dmg"])
                                if w["scale"]=="STR": d+=ap.str_stat*2
                                elif w["scale"]=="AGI": d+=ap.agi_stat
                                if ap.weak_weapons: d = max(1, int(d * 0.5))
                                boss.hp-=d; ap.energy-=w["energy"]; ap.atk_frames=ap.atk_cooldown
                                dmg=d; hit=True; tgt="SAND MAW"; last_hit_pos=(boss.surface_y, boss.surface_x)
                            elif not boss.surface:
                                messages=["SAND MAW UNDERGROUND. WAIT FOR IT."]; msg_t=35
                        elif boss_type == 'pillar_colossus':
                            if abs(boss.y-ap.y)<=ap.atk_range and abs(boss.x-ap.x)<=ap.atk_range:
                                d=random.randint(*w["dmg"])
                                if w["scale"]=="STR": d+=ap.str_stat*2
                                elif w["scale"]=="STR+WIL": d+=ap.str_stat*2+int(ap.wil_stat*1.5 if ap.wil_stat>=8 else 0)
                                if ap.weak_weapons: d = max(1, int(d * 0.5))
                                boss.hp-=d; ap.energy-=w["energy"]; ap.atk_frames=ap.atk_cooldown
                                dmg=d; hit=True; tgt="BASALT TITAN"
                        elif boss_type == 'king_of_nothing':
                            if abs(boss.y-ap.y)<=ap.atk_range and abs(boss.x-ap.x)<=ap.atk_range:
                                d=random.randint(*w["dmg"])
                                if w["scale"]=="STR": d+=ap.str_stat*2
                                elif w["scale"]=="STR+WIL": d+=ap.str_stat*2+int(ap.wil_stat*1.5 if ap.wil_stat>=8 else 0)
                                if ap.weak_weapons: d = max(1, int(d * 0.5))
                                boss.hp-=d; ap.energy-=w["energy"]; ap.atk_frames=ap.atk_cooldown
                                dmg=d; hit=True; tgt="KING OF NOTHING"
                        elif boss_type == 'administrator':
                            if abs(boss.y-ap.y)<=ap.atk_range and abs(boss.x-ap.x)<=ap.atk_range:
                                d=random.randint(*w["dmg"])
                                if w["scale"]=="STR": d+=ap.str_stat*2
                                elif w["scale"]=="WIL": d+=ap.wil_stat*2
                                elif w["scale"]=="STR+WIL": d+=ap.str_stat*2+int(ap.wil_stat*1.5 if ap.wil_stat>=8 else 0)
                                elif w["scale"]=="AGI": d+=ap.agi_stat
                                elif w["scale"]=="PER": d+=ap.per_stat
                                if ap.weak_weapons: d = max(1, int(d * 0.5))
                                boss.hp-=d; ap.energy-=w["energy"]; ap.atk_frames=ap.atk_cooldown
                                dmg=d; hit=True; tgt="THE ADMINISTRATOR"
                        elif boss_type in ('ash_lord','pale_lord','rot_lord','frost_lord','dune_lord','cinder_lord'):
                             if abs(boss.y-ap.y)<=ap.atk_range and abs(boss.x-ap.x)<=ap.atk_range:
                                d=random.randint(*w["dmg"])
                                if w["scale"]=="STR": d+=ap.str_stat*2
                                elif w["scale"]=="STR+WIL": d+=ap.str_stat*2+int(ap.wil_stat*1.5 if ap.wil_stat>=8 else 0)
                                if ap.weak_weapons: d = max(1, int(d * 0.5))
                                boss.hp-=d; ap.energy-=w["energy"]; ap.atk_frames=ap.atk_cooldown
                                dmg=d; hit=True; tgt=boss_name
                    if hit:
                        dmg_flash=dmg; dmg_flash_t=30
                        if last_hit_pos is None and boss and hasattr(boss, "y"): last_hit_pos=(boss.y, boss.x)
                        messages=[f"HIT {tgt} FOR {dmg}."]; msg_t=35
                    elif ap.atk_frames>0:
                        messages=["RESWINGING..."]; msg_t=20
                    elif ap.energy<ap.w_data["energy"]:
                        messages=["NOT ENOUGH ENERGY."]; msg_t=25
                    else:
                        messages=["OUT OF RANGE."]; msg_t=25

            elif key in (ord('q'),ord('Q')):
                if ap.energy>=ap.dodge_cost and ap.dodge_frames==0:
                    ap.dodge_frames=12; ap.inv_frames=ap.iframe_count
                    ap.energy-=ap.dodge_cost
                    ly=ap.y+ap.last_dy*5; lx=ap.x+ap.last_dx*5
                    ly=max(ay+1,min(ay+ah,ly)); lx=max(ax+1,min(ax+aw,lx))
                    ap.y=ly; ap.x=lx; messages=["DODGE."]; msg_t=20

            elif key in (ord('i'),ord('I')):
                items=list(ap.consumables.keys())
                if items:
                    stdscr.addstr(2,55,"── QUICKBAR ──",CYAN)
                    for i,it in enumerate(items[:4]):
                        iname=CONSUMABLE_INFO.get(it,{}).get("name",it)
                        stdscr.addstr(3+i,55,f"[{i+1}] {iname} x{ap.consumables[it]}",WHITE)
                    stdscr.addstr(7,55,"[0] CLOSE",YELLOW)
                    stdscr.refresh(); stdscr.nodelay(False)
                    k2=stdscr.getch(); stdscr.nodelay(True)
                    if k2 in (ord('1'),ord('2'),ord('3'),ord('4')):
                        idx=int(chr(k2))-1
                        if 0<=idx<len(items):
                            it=items[idx]
                            heal=20 if it=="dry_meat" else (10 if it=="bitter_root" else (25 if it=="pale_water" else (30 if it=="sun_water" else 0)))
                            if heal: ap.hp=min(ap.max_hp,ap.hp+heal)
                            if it=="antitoxin": ap.toxic_stacks=0; ap.toxic_timer=0
                            if it=="warm_ember": ap.cold=False; ap.cold_timer=0; ap.hp=min(ap.max_hp,ap.hp+10)
                            if it=="cool_shard":
                                ap.burn=False; ap.burn_timer=0; ap.hp=min(ap.max_hp,ap.hp+5)
                            if it=="sun_water":
                                if ap.talisman!="pillar_heart":
                                    ap.cold=False; ap.cold_timer=0
                                    ap.burn=True; ap.burn_timer=1
                            ap.consumables[it]-=1
                            if ap.consumables[it]<=0: del ap.consumables[it]
                            quickbar_msg=f"+{heal}HP" if heal else "USED"; qb_t=40

            elif key in (ord('x'),ord('X')):
                result='quit'; break

            if mdy!=0 or mdx!=0: ap.last_dy=mdy; ap.last_dx=mdx
            
            occupied=set()
            if boss:
                if boss_type == 'dune_colossus':
                    if boss.surface:
                        occupied.add((boss.surface_y,boss.surface_x))
                else:
                    occupied.add((boss.y,boss.x))
            if choir:
                for v in choir.voices:
                    if v.hp>0: occupied.add((v.y,v.x))
            if minions:
                for m in minions: occupied.add((m.y,m.x))
            if (ay+1<=new_y<=ay+ah and ax+1<=new_x<=ax+aw and (new_y,new_x) not in occupied):
                ap.y=new_y; ap.x=new_x

            # ── AI ────────────────────────────────────────
            all_msgs=[]
            if boss:
                if boss_type == 'ashen_tree':
                    all_msgs+=ashen_tree_ai(boss,minions,ap,ay,ax,ah,aw,frame)
                    all_msgs+=_minion_ai(minions,ap,ay,ax,ah,aw)
                    if boss.thorn_active:
                        # Damage Player
                        if ap.inv_frames==0:
                            for(ty,tx) in boss.thorn_cells:
                                if ap.y==ty and ap.x==tx:
                                    base_d = 18
                                    if ap.hard_mode: base_d = int(base_d * 1.5)
                                    if ap.corrupted: base_d = int(base_d * 2.0)
                                    d=max(1,base_d-int(ap.dmg_redux))
                                    ap.hp-=d; ap.inv_frames=ap.iframe_count
                                    all_msgs.append(f"THORN. -{d}."); break
                        # Friendly Fire: Damage Minions
                        for m in minions:
                            if m.hp > 0:
                                for(ty,tx) in boss.thorn_cells:
                                    if m.y==ty and m.x==tx:
                                        m.hp -= 15
                                        if m.hp <= 0: all_msgs.append(f"THORN IMPALES {m.type.upper()}.")
                                        break
                elif boss_type == 'dune_colossus':
                    all_msgs+=sand_maw_ai(boss,ap,frame)
                    if boss.surface and abs(ap.y-boss.surface_y)<=1 and abs(ap.x-boss.surface_x)<=1 and ap.inv_frames==0:
                        base_d = 16
                        if ap.hard_mode: base_d = int(base_d * 1.5)
                        if ap.corrupted: base_d = int(base_d * 2.0)
                        d=max(1,base_d-int(ap.dmg_redux))
                        ap.hp-=d; ap.inv_frames=ap.iframe_count
                        all_msgs.append(f"SAND MAW CRUSHES. -{d}.")
                    if boss.spray_cells and ap.inv_frames==0:
                        for (sy,sx) in boss.spray_cells:
                            if ap.y==sy and ap.x==sx:
                                base_d = 10
                                if ap.hard_mode: base_d = int(base_d * 1.5)
                                if ap.corrupted: base_d = int(base_d * 2.0)
                                d=max(1,base_d-int(ap.dmg_redux))
                                ap.hp-=d; ap.inv_frames=ap.iframe_count
                                all_msgs.append(f"SAND SPRAY. -{d}."); break
                elif boss_type == 'king_of_nothing':
                    if boss.hp < boss.max_hp // 2 and not boss.said_phase2:
                        boss.said_phase2 = True
                        show_boss_dialogue(stdscr, "THE KING OF NOTHING", [
                            "You seek an exit from a room with no doors.",
                            "I will bury you under the weight of your own defiance!"
                        ])
                        for _ in range(35):
                            cy = random.randint(ay+2, ay+ah-2)
                            cx = random.randint(ax+2, ax+aw-2)
                            boss.cracks.append((cy, cx, random.choice([".", ",", "'", "`"])))
                        if player_dict.get("flags", {}).get("cabinet_open") == "true":
                            lord_souls = ["ash_soul", "pale_soul", "rot_soul", "frost_soul", "dune_soul", "magma_soul"]
                            soul_count = sum(1 for s in lord_souls if s in player_dict.get("inventory", []))
                            if soul_count >= 3:
                                show_boss_dialogue(stdscr, "SYSTEM ALERT", [
                                    "THE KING OF NOTHING WAS IMPALED BY THE ADMINISTRATOR.",
                                    "CRITICAL: CORRUPTION OVERFLOWING.",
                                    "ABORTING SIMULATION..."
                                ])
                                result_holder[0] = "admin_trigger"
                                return
                    if boss.hp < int(boss.max_hp * 0.3) and not boss.said_phase3:
                        boss.said_phase3 = True
                        show_boss_dialogue(stdscr, "THE MONARCH OF VOID", [
                            "The void consumes all variables.",
                            "There is nothing left to save."
                        ])
                    all_msgs+=king_of_nothing_ai(boss,ap,frame)
                    
                    if boss.swipe_active_cells and ap.inv_frames==0:
                        for (sy,sx) in boss.swipe_active_cells:
                            if ap.y==sy and ap.x==sx:
                                base_d = 20
                                if ap.hard_mode: base_d = int(base_d * 1.5)
                                d=max(1,base_d-int(ap.dmg_redux))
                                ap.hp-=d; ap.inv_frames=ap.iframe_count
                                all_msgs.append(f"SWORD SWEEP HITS. -{d}.")
                                break
                    if boss.smash_active_cells and ap.inv_frames==0:
                        for (sy,sx) in boss.smash_active_cells:
                            if ap.y==sy and ap.x==sx:
                                base_d = 25
                                if ap.hard_mode: base_d = int(base_d * 1.5)
                                d=max(1,base_d-int(ap.dmg_redux))
                                ap.hp-=d; ap.inv_frames=ap.iframe_count
                                ap.stun_timer = 35
                                all_msgs.append(f"GROUND SMASH HITS. -{d}. STUNNED!")
                                break
                    if boss.void_orbs and ap.inv_frames==0:
                        for orb in boss.void_orbs:
                            for (oy,ox) in orb["cells"]:
                                if ap.y==oy and ap.x==ox:
                                    base_d = 18
                                    if ap.hard_mode: base_d = int(base_d * 1.5)
                                    d=max(1,base_d-int(ap.dmg_redux))
                                    ap.hp-=d; ap.inv_frames=ap.iframe_count
                                    all_msgs.append(f"VOID COLLAPSE. -{d}.")
                                    break
                    if boss.null_active_cells:
                        for (ny,nx) in boss.null_active_cells:
                            if ap.y==ny and ap.x==nx and ap.inv_frames==0:
                                base_d = 5
                                d=base_d; ap.hp-=d
                                ap.energy = max(0, ap.energy - 15)
                                all_msgs.append(f"VOID COLLAPSE DRAINS. -{d}HP, -15EN.")
                                break
                elif boss_type == 'administrator':
                    if boss.hp < int(boss.max_hp * 0.6) and not boss.said_phase2:
                        boss.said_phase2 = True
                        show_boss_dialogue(stdscr, "THE ADMINISTRATOR", [
                            "You are persistent. I will give you that.",
                            "But persistence is just a loop. And I own the loop."
                        ])
                    if boss.hp < int(boss.max_hp * 0.3) and not boss.said_phase3:
                        boss.said_phase3 = True
                        show_boss_dialogue(stdscr, "SYSTEM: CRITICAL FAILURE", [
                            "ADMINISTRATOR INTEGRITY BELOW THRESHOLD.",
                            "INITIATING EMERGENCY REWRITE PROTOCOL."
                        ])
                    all_msgs += administrator_ai(boss, ap, frame)
                    # Static line hit
                    if boss.line_active_cells and ap.inv_frames == 0:
                        for (ly, lx) in boss.line_active_cells:
                            if ap.y == ly and ap.x == lx:
                                base_d = 22
                                if ap.hard_mode: base_d = int(base_d * 1.5)
                                d = max(1, base_d - int(ap.dmg_redux))
                                ap.hp -= d; ap.inv_frames = ap.iframe_count
                                all_msgs.append(f"STATIC DISCHARGE. -{d}.")
                                break
                    # Glitch tile hit
                    if boss.glitch_active_cells and ap.inv_frames == 0:
                        for (gy, gx) in boss.glitch_active_cells:
                            if ap.y == gy and ap.x == gx:
                                base_d = 14
                                if ap.hard_mode: base_d = int(base_d * 1.5)
                                d = max(1, base_d - int(ap.dmg_redux))
                                ap.hp -= d; ap.inv_frames = ap.iframe_count
                                ap.energy = max(0, ap.energy - 20)
                                all_msgs.append(f"MEMORY FAULT. -{d}HP -20EN.")
                                break
                    # Contact damage
                    if ap.y == boss.y and ap.x == boss.x and ap.inv_frames == 0:
                        base_d = 18
                        if ap.hard_mode: base_d = int(base_d * 1.5)
                        d = max(1, base_d - int(ap.dmg_redux))
                        ap.hp -= d; ap.inv_frames = ap.iframe_count
                        all_msgs.append(f"STATIC CONTACT. -{d}.")
                    # HP rewrite (phase 3)
                    if boss.phase == 3 and getattr(boss, "_do_rewrite", False):
                        boss._do_rewrite = False
                        new_hp = random.randint(max(1, int(ap.max_hp * 0.1)), int(ap.max_hp * 0.55))
                        ap.hp = new_hp
                        all_msgs.append(f"HP REWRITTEN TO {new_hp}.")
                elif boss_type == 'pillar_colossus':
                    all_msgs+=basalt_titan_ai(boss,ap,ay,ax,ah,aw,frame)
                    if boss.pool_active_cells and ap.inv_frames==0:
                        for (py, px) in boss.pool_active_cells:
                            if ap.y==py and ap.x==px:
                                base_d = 8
                                if ap.hard_mode: base_d = int(base_d * 1.5)
                                if ap.corrupted: base_d = int(base_d * 2.0)
                                d=max(1,base_d-int(ap.dmg_redux))
                                ap.hp-=d; ap.inv_frames=ap.iframe_count
                                if ap.talisman!="pillar_heart":
                                    ap.cold=False; ap.cold_timer=0
                                    ap.burn=True; ap.burn_timer=3
                                all_msgs.append(f"LAVA BURNS. -{d}. BURN.")
                                break
                    if boss.line_active and ap.inv_frames==0:
                        if abs(ap.y-boss.line_y)<=1 or abs(ap.x-boss.line_x)<=1:
                            base_d = 15
                            if ap.hard_mode: base_d = int(base_d * 1.5)
                            if ap.corrupted: base_d = int(base_d * 2.0)
                            d=max(1,base_d-int(ap.dmg_redux))
                            ap.hp-=d; ap.inv_frames=ap.iframe_count
                            if ap.talisman!="pillar_heart":
                                ap.cold=False; ap.cold_timer=0
                                ap.burn=True; ap.burn_timer=3
                            all_msgs.append(f"FIRE LINE BURNS. -{d}. BURN.")
                elif boss_type == 'ash_lord':
                    all_msgs += ash_lord_ai(boss, ap, ay, ax, ah, aw, frame)
                    if (ap.y, ap.x) in boss.lash_active_cells or (ap.y, ap.x) in boss.fall_active_cells:
                        if ap.inv_frames == 0:
                            d = 25; ap.hp -= d; ap.inv_frames = ap.iframe_count; all_msgs.append(f"ASH CRUSHES. -{d}")
                elif boss_type == 'pale_lord':
                    all_msgs += pale_lord_ai(boss, ap, ay, ax, ah, aw, frame)
                    if (ap.y, ap.x) in boss.pulse_cells:
                        if ap.inv_frames == 0:
                            d = 20; ap.hp -= d; ap.inv_frames = ap.iframe_count; ap.toxic_stacks += 1; all_msgs.append(f"SORROW. -{d}")
                elif boss_type == 'rot_lord':
                    all_msgs += rot_lord_ai(boss, ap, ay, ax, ah, aw, frame)
                    for c in boss.clouds:
                        if ap.y == c[0] and ap.x == c[1]:
                            if ap.inv_frames == 0:
                                d = 10; ap.hp -= d; ap.inv_frames = ap.iframe_count; ap.toxic_stacks += 1; all_msgs.append(f"ROT. -{d}")
                elif boss_type == 'frost_lord':
                    all_msgs += frost_lord_ai(boss, ap, ay, ax, ah, aw, frame)
                    if (ap.y, ap.x) in boss.spikes:
                        if ap.inv_frames == 0:
                            d = 22; ap.hp -= d; ap.inv_frames = ap.iframe_count; ap.cold = True; ap.cold_timer = 3; all_msgs.append(f"FROST. -{d}")
                elif boss_type == 'dune_lord':
                    all_msgs += dune_lord_ai(boss, ap, ay, ax, ah, aw, frame)
                    if ap.y == boss.y and ap.x == boss.x:
                        if ap.inv_frames == 0:
                            d = 18; ap.hp -= d; ap.inv_frames = ap.iframe_count; all_msgs.append(f"DUNE CRUSHES. -{d}")
                elif boss_type == 'cinder_lord':
                    all_msgs += cinder_lord_ai(boss, ap, ay, ax, ah, aw, frame)
                    if (ap.y, ap.x) in boss.vents:
                        if ap.inv_frames == 0:
                            d = 30; ap.hp -= d; ap.inv_frames = ap.iframe_count; ap.burn = True; ap.burn_timer = 3; all_msgs.append(f"LAVA. -{d}")
            if choir:
                all_msgs+=choir_ai(choir,ap,ay,ax,ah,aw)
                for v in choir.voices:
                    if v.hp>0 and v.y==ap.y and v.x==ap.x and ap.inv_frames==0:
                        base_d = random.randint(6,12)
                        if ap.hard_mode: base_d = int(base_d * 1.5)
                        if ap.corrupted: base_d = int(base_d * 2.0)
                        d=max(1,base_d-int(ap.dmg_redux))
                        ap.hp-=d; ap.inv_frames=ap.iframe_count
                        if v.toxic and ap.talisman!="choir_remnant":
                            ap.toxic_stacks+=1; ap.toxic_timer=4
                        all_msgs.append(f"VOICE {v.idx} HITS. -{d}.")
                for cloud in choir.toxic_clouds:
                    if cloud[0]==ap.y and cloud[1]==ap.x and ap.inv_frames==0 and ap.talisman!="choir_remnant":
                        base_d = 5
                        if ap.hard_mode: base_d = int(base_d * 1.5)
                        if ap.corrupted: base_d = int(base_d * 2.0)
                        d=base_d; ap.hp-=d
                        all_msgs.append(f"TOXIC CLOUD. -{d}.")
            if aval:
                all_msgs+=avalanche_ai(aval,ap,frame)
                for w in aval.waves:
                    if w.warn_timer > 0: continue
                    for(wy,wx) in w.cells():
                        if ap.y==wy and ap.x==wx and ap.inv_frames==0:
                            base_d = 20
                            if ap.hard_mode: base_d = int(base_d * 1.5)
                            if ap.corrupted: base_d = int(base_d * 2.0)
                            d=max(1,base_d-int(ap.dmg_redux))
                            ap.hp-=d; ap.inv_frames=ap.iframe_count
                            ap.cold=True; ap.cold_timer=3
                            all_msgs.append(f"DEBRIS HITS. -{d}. COLD."); break
 
            # Toxic tick in arena
            if ap.toxic_stacks>0 and frame%20==0:
                base_d = 5*ap.toxic_stacks
                if ap.hard_mode: base_d = int(base_d * 1.5)
                if ap.corrupted: base_d = int(base_d * 2.0)
                d=base_d; ap.hp-=d; ap.toxic_timer-=1
                if ap.toxic_timer<=0: ap.toxic_stacks=0
                all_msgs.append(f"TOXIC TICK. -{d}.")
 
            # Cold timer decrement
            if ap.cold and frame%20==0:
                ap.cold_timer-=1
                if ap.cold_timer<=0: ap.cold=False
 
            # Burn tick in arena
            if getattr(ap, "burn", False) and frame%20==0:
                base_d = 6
                if ap.hard_mode: base_d = int(base_d * 1.5)
                if ap.corrupted: base_d = int(base_d * 2.0)
                d=base_d; ap.hp-=d; ap.burn_timer-=1
                if ap.burn_timer<=0: ap.burn=False
                all_msgs.append(f"BURN TICK. -{d}.")
            if all_msgs: messages=[all_msgs[0]]; msg_t=55
 
            # Timers
            if ap.dodge_frames>0:  ap.dodge_frames-=1
            if ap.atk_frames>0:    ap.atk_frames-=1
            if ap.inv_frames>0:    ap.inv_frames-=1
            if msg_t>0:            msg_t-=1
            if dmg_flash_t>0:      dmg_flash_t-=1
            if qb_t>0:             qb_t-=1
            if frame%15==0 and ap.energy<ap.max_energy: ap.energy=min(ap.max_energy,ap.energy+2)
 
            if boss and boss.hp<=0:   result='win'; break
            if choir and choir.all_dead: result='win'; break
            if aval and aval.hp<=0:   result='win'; break
            if ap.hp<=0:              result='lose'; break
 
            # ── DRAW ──────────────────────────────────────
            try:
                stdscr.addstr(ay,ax,"┌"+"─"*aw+"┐",CYAN)
                stdscr.addstr(ay+ah+1,ax,"└"+"─"*aw+"┘",CYAN)
                for i in range(1,ah+1):
                    stdscr.addstr(ay+i,ax,"│",CYAN)
                    stdscr.addstr(ay+i,ax+aw+1,"│",CYAN)
 
                if boss:
                    if boss_type == 'ashen_tree':
                        for(wy,wx) in boss.thorn_warning:
                            try: stdscr.addstr(wy,wx,"!",YELLOW|curses.A_BOLD)
                            except: pass
                        for(ty,tx) in boss.thorn_cells:
                            try: stdscr.addstr(ty,tx,"▪",RED|curses.A_BOLD)
                            except: pass
                        bc=MAGENTA if boss.phase==2 else RED
                        try: stdscr.addstr(boss.y,boss.x,boss.symbol,bc|curses.A_BOLD)
                        except: pass
                        for m in minions:
                            mc=YELLOW if m.type=="stillborn" else RED
                            try: stdscr.addstr(m.y,m.x,m.symbol,mc)
                            except: pass
                    elif boss_type == 'ash_lord':
                        for (wy,wx) in boss.lash_warn_cells:
                            try: stdscr.addstr(wy,wx,"!",YELLOW)
                            except: pass
                        for (ay_,ax_) in boss.lash_active_cells:
                            try: stdscr.addstr(ay_,ax_,"|",RED)
                            except: pass
                        for (wy,wx) in boss.fall_warn_cells:
                            try: stdscr.addstr(wy,wx,"*",YELLOW)
                            except: pass
                        for (ay_,ax_) in boss.fall_active_cells:
                            try: stdscr.addstr(ay_,ax_,"X",RED)
                            except: pass
                        try: stdscr.addstr(boss.y,boss.x,boss.symbol,GREEN|curses.A_BOLD)
                        except: pass
                    elif boss_type == 'pale_lord':
                        for (py,px) in boss.pulse_cells:
                            try: stdscr.addstr(py,px,".",MAGENTA)
                            except: pass
                        try: stdscr.addstr(boss.y,boss.x,boss.symbol,WHITE|curses.A_BOLD)
                        except: pass
                    elif boss_type == 'rot_lord':
                        for c in boss.clouds:
                            try: stdscr.addstr(c[0],c[1],"o",GREEN)
                            except: pass
                        try: stdscr.addstr(boss.y,boss.x,boss.symbol,YELLOW|curses.A_BOLD)
                        except: pass
                    elif boss_type == 'frost_lord':
                        for (sy,sx) in boss.spikes:
                            try: stdscr.addstr(sy,sx,"+",CYAN)
                            except: pass
                        try: stdscr.addstr(boss.y,boss.x,boss.symbol,CYAN|curses.A_BOLD)
                        except: pass
                    elif boss_type == 'dune_lord':
                        try: stdscr.addstr(boss.y,boss.x,boss.symbol,YELLOW|curses.A_BOLD)
                        except: pass
                    elif boss_type == 'cinder_lord':
                        for (vy,vx) in boss.vents:
                            try: stdscr.addstr(vy,vx,"^",RED)
                            except: pass
                        try: stdscr.addstr(boss.y,boss.x,boss.symbol,RED|curses.A_BOLD)
                        except: pass
                    elif boss_type == 'dune_colossus':
                        if boss.warning:
                            for dy in range(-1, 2):
                                for dx in range(-1, 2):
                                    wy = boss.warn_y + dy
                                    wx = boss.warn_x + dx
                                    if ay + 1 <= wy <= ay + ah and ax + 1 <= wx <= ax + aw:
                                        try: stdscr.addstr(wy, wx, "?", YELLOW|curses.A_BOLD)
                                        except: pass
                        if boss.fake_warning:
                            for dy in range(-1, 2):
                                for dx in range(-1, 2):
                                    fy = boss.fake_y + dy
                                    fx = boss.fake_x + dx
                                    if ay + 1 <= fy <= ay + ah and ax + 1 <= fx <= ax + aw:
                                        try: stdscr.addstr(fy, fx, "?", YELLOW|curses.A_BOLD)
                                        except: pass
                        if boss.surface:
                            try: stdscr.addstr(boss.surface_y, boss.surface_x, "C", RED|curses.A_BOLD)
                            except: pass
                        if boss.spray_cells:
                            for (sy, sx) in boss.spray_cells:
                                try: stdscr.addstr(sy, sx, "░", MAGENTA)
                                except: pass
                    elif boss_type == 'administrator':
                        for (ly, lx) in boss.line_warn_cells:
                            try: stdscr.addstr(ly, lx, "!", YELLOW|curses.A_BOLD)
                            except: pass
                        for (ly, lx) in boss.line_active_cells:
                            try: stdscr.addstr(ly, lx, "=", RED|curses.A_BOLD)
                            except: pass
                        for (gy, gx) in boss.glitch_warn_cells:
                            try: stdscr.addstr(gy, gx, "?", MAGENTA)
                            except: pass
                        for (gy, gx) in boss.glitch_active_cells:
                            try: stdscr.addstr(gy, gx, "#", RED|curses.A_BOLD)
                            except: pass
                        if boss.phase == 3 and boss.rewrite_warning:
                            try: stdscr.addstr(ay+1, ax+2, "!! HP REWRITE INCOMING !!", RED|curses.A_BOLD)
                            except: pass
                        bc = RED if boss.phase == 1 else (MAGENTA if boss.phase == 2 else WHITE)
                        try: stdscr.addstr(boss.y, boss.x, boss.symbol, bc|curses.A_BOLD)
                        except: pass
                    elif boss_type == 'king_of_nothing':
                        for (cy, cx, sym) in boss.cracks:
                            try: stdscr.addstr(cy, cx, sym, curses.color_pair(3))
                            except: pass
                        for (wy, wx) in boss.swipe_warn_cells:
                            try: stdscr.addstr(wy, wx, "!", YELLOW|curses.A_BOLD)
                            except: pass
                        for (sy, sx) in boss.swipe_active_cells:
                            try: stdscr.addstr(sy, sx, random.choice(["/", "\\", "_", "|"]), RED|curses.A_BOLD)
                            except: pass
                        for (wy, wx) in boss.smash_warn_cells:
                            try: stdscr.addstr(wy, wx, "!", YELLOW|curses.A_BOLD)
                            except: pass
                        for (sy, sx) in boss.smash_active_cells:
                            try: stdscr.addstr(sy, sx, "☼", RED|curses.A_BOLD)
                            except: pass
                        for orb in boss.void_orbs:
                            for (oy, ox) in orb["cells"]:
                                try: stdscr.addstr(oy, ox, "o", MAGENTA|curses.A_BOLD)
                                except: pass
                        for (ny, nx) in boss.null_warn_cells:
                            try: stdscr.addstr(ny, nx, "!", YELLOW|curses.A_BOLD)
                            except: pass
                        for (ny, nx) in boss.null_active_cells:
                            try: stdscr.addstr(ny, nx, ".", MAGENTA)
                            except: pass
                        bc=MAGENTA if boss.phase==3 else (YELLOW if boss.phase==2 else RED)
                        try: stdscr.addstr(boss.y, boss.x, boss.symbol, bc|curses.A_BOLD)
                        except: pass
                    elif boss_type == 'pillar_colossus':
                        for (py, px) in boss.pool_warning_cells:
                            try: stdscr.addstr(py, px, "!", YELLOW|curses.A_BOLD)
                            except: pass
                        for (py, px) in boss.pool_active_cells:
                            try: stdscr.addstr(py, px, "☼", RED|curses.A_BOLD)
                            except: pass
                        if boss.is_firing_line:
                            for dy in (-1, 0, 1):
                                wy = boss.line_y + dy
                                if ay + 1 <= wy <= ay + ah:
                                    for x in range(ax+1, ax+aw+1):
                                        try: stdscr.addstr(wy, x, "!", YELLOW|curses.A_BOLD)
                                        except: pass
                            for dx in (-1, 0, 1):
                                wx = boss.line_x + dx
                                if ax + 1 <= wx <= ax + aw:
                                    for y in range(ay+1, ay+ah+1):
                                        try: stdscr.addstr(y, wx, "!", YELLOW|curses.A_BOLD)
                                        except: pass
                        if boss.line_active:
                            for dy in (-1, 0, 1):
                                wy = boss.line_y + dy
                                if ay + 1 <= wy <= ay + ah:
                                    for x in range(ax+1, ax+aw+1):
                                        try: stdscr.addstr(wy, x, "═", RED|curses.A_BOLD)
                                        except: pass
                            for dx in (-1, 0, 1):
                                wx = boss.line_x + dx
                                if ax + 1 <= wx <= ax + aw:
                                    for y in range(ay+1, ay+ah+1):
                                        try: stdscr.addstr(y, wx, "║", RED|curses.A_BOLD)
                                        except: pass
                        bc=MAGENTA if boss.phase==2 else RED
                        try: stdscr.addstr(boss.y, boss.x, boss.symbol, bc|curses.A_BOLD)
                        except: pass
 
                if choir:
                    for cloud in choir.toxic_clouds:
                        try: stdscr.addstr(cloud[0],cloud[1],"~",MAGENTA)
                        except: pass
                    for v in choir.voices:
                        if v.hp>0:
                            vc=YELLOW if v.hp>v.max_hp*0.5 else RED
                            try: stdscr.addstr(v.y,v.x,v.symbol,vc|curses.A_BOLD)
                            except: pass
 
                if aval:
                    for w in aval.waves:
                        for(wy,wx) in w.cells():
                            if w.warn_timer > 0:
                                try: stdscr.addstr(wy,wx,"░",YELLOW)
                                except: pass
                            else:
                                try: stdscr.addstr(wy,wx,"█",RED if w.done else YELLOW)
                                except: pass
                    if aval.core_exposed:
                        try: stdscr.addstr(aval.core_y,aval.core_x,"◆",CYAN|curses.A_BOLD)
                        except: pass
                    else:
                        try: stdscr.addstr(aval.core_y,aval.core_x,"·",WHITE)
                        except: pass
 
                # Player

 
                if ap.dodge_frames>0:   pc=YELLOW|curses.A_BOLD

 
                elif ap.inv_frames>0:   pc=WHITE|curses.A_DIM

 
                elif ap.toxic_stacks>0: pc=MAGENTA|curses.A_BOLD

 
                elif ap.cold:           pc=CYAN|curses.A_BOLD

 
                elif getattr(ap, "burn", False): pc=RED|curses.A_BOLD

 
                else:                   pc=GREEN|curses.A_BOLD
                try: stdscr.addstr(ap.y,ap.x,ap.symbol,pc)
                except: pass
 
                if dmg_flash_t>0:
                    try:
                        if choir and last_hit_pos:
                            ty2 = last_hit_pos[0] - 1
                            tx2 = last_hit_pos[1]
                        elif boss_type in ('ashen_tree','pillar_colossus') and boss:
                            ty2=boss.y-1; tx2=boss.x
                        elif boss_type=='dune_colossus' and boss and boss.surface:
                            ty2=boss.surface_y-1; tx2=boss.surface_x
                        elif aval:
                            ty2=aval.core_y-1; tx2=aval.core_x
                        elif boss:
                            ty2=boss.y-1; tx2=boss.x
                        else:
                            ty2=ay+2; tx2=ax+2
                        stdscr.addstr(ty2,tx2,f"-{dmg_flash}",YELLOW|curses.A_BOLD)
                    except: pass
 
                # UI
                ui_x=ax+aw+4
                stdscr.addstr(ay,   ui_x,"── ECHOES OF MIDDLEWHERE ──",CYAN)
                stdscr.addstr(ay+2, ui_x,boss_name[:18],RED|curses.A_BOLD)
 
                if boss:

 
                    bf=int((boss.hp/boss.max_hp)*20)

 
                    stdscr.addstr(ay+3,ui_x,f"[{'█'*bf}{'░'*(20-bf)}]",RED)

 
                    if boss_type == 'ashen_tree':

 
                        stdscr.addstr(ay+4,ui_x,f"PH:{boss.phase} MIN:{len([m for m in minions if m.hp>0])}",MAGENTA)

 
                        if boss.is_warning:

 
                            stdscr.addstr(ay+5,ui_x,f"THORNS in {boss.warn_t//10+1}s",YELLOW|curses.A_BOLD)

 
                        elif boss.thorn_active:

 
                            stdscr.addstr(ay+5,ui_x,"!! THORNS !!",RED|curses.A_BOLD)

 
                    elif boss_type == 'dune_colossus':

 
                        stdscr.addstr(ay+4,ui_x,f"PH:{boss.phase}",MAGENTA)

 
                        if boss.warning:

 
                            stdscr.addstr(ay+5,ui_x,"BULGING...",YELLOW|curses.A_BOLD)

 
                        elif boss.surface:

 
                            stdscr.addstr(ay+5,ui_x,"!! EXPOSED !!",RED|curses.A_BOLD)

 
                        else:

 
                            stdscr.addstr(ay+5,ui_x,"UNDERGROUND",WHITE)

 
                    elif boss_type == 'pillar_colossus':

 
                        stdscr.addstr(ay+4,ui_x,f"PH:{boss.phase}",MAGENTA)

 
                        if boss.is_firing_line:

 
                            stdscr.addstr(ay+5,ui_x,f"FIRING in {boss.line_warn_timer//10+1}s",YELLOW|curses.A_BOLD)

 
                        elif boss.line_active:

 
                            stdscr.addstr(ay+5,ui_x,"!! ERUPTION !!",RED|curses.A_BOLD)

 
                        else:

 
                            stdscr.addstr(ay+5,ui_x,"NOMINAL",WHITE)
                if choir:
                    for i,v in enumerate(choir.voices):
                        cf=int((max(0,v.hp)/v.max_hp)*15)
                        bar2='█'*cf+'░'*(15-cf)
                        col=GREEN if v.hp>v.max_hp*0.5 else (YELLOW if v.hp>0 else RED)
                        stdscr.addstr(ay+3+i,ui_x,f"V{v.idx}[{bar2}]{max(0,v.hp)}",col)
                    stdscr.addstr(ay+7,ui_x,f"CLOUDS:{len(choir.toxic_clouds)}",MAGENTA)
                if aval:
                    bf=int((aval.hp/aval.max_hp)*20)
                    stdscr.addstr(ay+3,ui_x,f"[{'█'*bf}{'░'*(20-bf)}]",RED)
                    stdscr.addstr(ay+4,ui_x,f"WAVES:{len(aval.waves)} PH:{aval.phase}",YELLOW)
                    if aval.core_exposed:
                        stdscr.addstr(ay+5,ui_x,"◆ CORE EXPOSED!",CYAN|curses.A_BOLD)
 
                stdscr.addstr(ay+9, ui_x,"── THE LOST ──",CYAN)
                hf2=int((ap.hp/ap.max_hp)*20)
                hc=GREEN if ap.hp>ap.max_hp*0.5 else (YELLOW if ap.hp>ap.max_hp*0.25 else RED)
                stdscr.addstr(ay+10,ui_x,f"HP[{'█'*hf2}{'░'*(20-hf2)}]",hc)
                nf2=int((ap.energy/100)*20)
                stdscr.addstr(ay+11,ui_x,f"NR[{'█'*nf2}{'░'*(20-nf2)}]",CYAN)
 
                status_str=""
                if ap.toxic_stacks>0: status_str+=f"TOX({ap.toxic_stacks}) "
                if ap.cold:           status_str+="COLD "
                if getattr(ap, "burn", False): status_str+="BURN "
                if status_str: stdscr.addstr(ay+12,ui_x,status_str[:20],MAGENTA)
 
                if ap.dodge_frames>0:   stdscr.addstr(ay+13,ui_x,">>DODGING<<",YELLOW|curses.A_BOLD)
                elif ap.inv_frames>0:   stdscr.addstr(ay+13,ui_x,"--RECOVER--",WHITE|curses.A_DIM)
                elif ap.atk_frames>0:   stdscr.addstr(ay+13,ui_x,"..SWING..  ",CYAN|curses.A_DIM)
                else:                   stdscr.addstr(ay+13,ui_x,"  READY    ",GREEN)
 
                stdscr.addstr(ay+15,ui_x,"WASD MOVE",WHITE)
                stdscr.addstr(ay+16,ui_x,"SPC  ATK",WHITE)
                stdscr.addstr(ay+17,ui_x,"Q    DODGE",WHITE)
                stdscr.addstr(ay+18,ui_x,"I    ITEMS",WHITE)
                stdscr.addstr(ay+19,ui_x,"X    QUIT",WHITE)
 
                if qb_t>0 and quickbar_msg:
                    stdscr.addstr(ay+21,ui_x,quickbar_msg[:20],YELLOW)
 
                msg_y=ay+ah+3
                stdscr.addstr(msg_y,ax,"─"*(aw+2),CYAN)
                if messages and msg_t>0:
                    stdscr.addstr(msg_y+1,ax,f"  {messages[0][:aw]}",YELLOW)
                else:
                    stdscr.addstr(msg_y+1,ax,"  ...",WHITE)
 
            except curses.error:
                pass
 
            stdscr.refresh(); frame+=1; time.sleep(0.05)
 
        stdscr.clear(); stdscr.nodelay(False)
        try:
            if result=='win':
                stdscr.addstr(5,10,f"{boss_name} FALLS.",curses.color_pair(3)|curses.A_BOLD)
                stdscr.addstr(6,10,"SILENCE FOLLOWS.",curses.color_pair(3))
            elif result=='lose':
                stdscr.addstr(5,10,"YOU FALL.",curses.color_pair(2)|curses.A_BOLD)
                stdscr.addstr(6,10,"THE MIDDLEWHERE TAKES YOU.",curses.color_pair(2))
            else:
                stdscr.addstr(5,10,"YOU FLED.",curses.color_pair(4))
            stdscr.addstr(8,10,"PRESS ANY KEY...",curses.color_pair(5))
            stdscr.refresh(); stdscr.getch()
        except curses.error: pass
 
        result_holder[0]=result
        player_dict["consumables"]=ap.consumables
        player_dict["hp"]=max(0,ap.hp)
 
    curses.wrapper(_arena)
    return result_holder[0]
 
def _minion_ai(minions,ap,ay,ax,ah,aw):
    msgs=[]; dead=[]
    for m in minions:
        if m.hp<=0: dead.append(m); continue
        m.timer+=1
        if m.timer>=m.speed:
            m.timer=0
            dy=1 if m.y<ap.y else(-1 if m.y>ap.y else 0)
            dx=1 if m.x<ap.x else(-1 if m.x>ap.x else 0)
            if random.random()<0.3:
                if random.random()<0.5: dx=0
                else: dy=0
            ny=m.y+dy; nx=m.x+dx
            if ay+1<=ny<=ay+ah and ax+1<=nx<=ax+aw:
                m.y=ny; m.x=nx
        if m.y==ap.y and m.x==ap.x and ap.inv_frames==0:
            dmg_range = m.dmg
            if ap.hard_mode:
                dmg_range = (int(dmg_range[0] * 1.5), int(dmg_range[1] * 1.5))
            if ap.corrupted:
                dmg_range = (int(dmg_range[0] * 2.0), int(dmg_range[1] * 2.0))
            d=max(1,random.randint(*dmg_range)-int(ap.dmg_redux))
            ap.hp-=d; ap.inv_frames=ap.iframe_count
            if m.toxic and ap.talisman!="choir_remnant":
                ap.toxic_stacks+=1; ap.toxic_timer=4
            msgs.append(f"MINION HITS. -{d}.")
    for d in dead:
        if d in minions: minions.remove(d)
    return msgs
 
# ══════════════════════════════════════════════════════════
#  AREAS
# ══════════════════════════════════════════════════════════
 
# ── CROSSROADS ────────────────────────────────────────────
def run_crossroads(player, slot):
    if "crossroads" not in player["visited"]:
        player["visited"].append("crossroads")
        clear()
        slow_print([
            "","  You open your eyes.","",
            "  Trees. Dead but standing. Frozen mid-sway.",
            "  Grass so pale it looks like old paper.",
            "  Behind you, a house. Small. Still.","",
            "  You don't know how you got here.",
            "  You don't know your name.",
            "  But you are standing.",
            "  That's something.","",
        ],0.18)
        dinput("  PRESS ENTER TO LOOK AROUND...")
 
    while True:
        clear(); player["location"]="crossroads"
        show_status(player)
        print("  THE CROSSROADS")
        print("  ─────────────────────────────────────────────")
        print("  [1] The dead tree line north    -- THE ASHWOOD")
        print("  [2] Open pale grass east        -- THE PALE FIELDS")
        print("  [3] An abandoned house south    -- THE STILL HOUSE")
        if "blackwater_rot" in player["unlocked"]:
            print("  [4] Dark wet path west          -- BLACKWATER ROT")
        if "mountains" in player["unlocked"]:
            print("  [5] Distant frozen peaks        -- STATIC MOUNTAINS")
        if "dunes" in player["unlocked"]:
            print("  [6] Endless sand east-northeast  -- FOREVER LASTING DUNES")
        if "pillar" in player["unlocked"]:
            print("  [7] Distant smoke south-west     -- PILLAR OF MAGMA")
        if "capitol" in player["unlocked"]:
            print("  [8] The wrong city at center     -- CAPITOL OF NOTHING")
        print("")
        print("  [I] FIELD MENU   [S] STATUS   [Q] SAVE & QUIT")
        print("")
        ch=dinput("  > ").strip().lower()
        if ch=="1":
            if run_ashwood(player,slot)=="dead":
                player=death_screen(player,slot)
                if player is None: return "menu"
        elif ch=="2":
            if run_pale_fields(player,slot)=="dead":
                player=death_screen(player,slot)
                if player is None: return "menu"
        elif ch=="3":
            if run_still_house(player,slot)=="dead":
                player=death_screen(player,slot)
                if player is None: return "menu"
        elif ch=="4" and "blackwater_rot" in player["unlocked"]:
            if run_blackwater_rot(player,slot)=="dead":
                player=death_screen(player,slot)
                if player is None: return "menu"
        elif ch=="5" and "mountains" in player["unlocked"]:
            if run_static_mountains(player,slot)=="dead":
                player=death_screen(player,slot)
                if player is None: return "menu"
        elif ch=="6" and "dunes" in player["unlocked"]:
            if run_forever_dunes(player,slot)=="dead":
                player=death_screen(player,slot)
                if player is None: return "menu"
        elif ch=="7" and "pillar" in player["unlocked"]:
            if run_pillar_of_magma(player,slot)=="dead":
                player=death_screen(player,slot)
                if player is None: return "menu"
        elif ch=="8" and "capitol" in player["unlocked"]:
            res = run_capitol_of_nothing(player, slot)
            if res == "dead":
                player = death_screen(player, slot)
                if player is None: return "menu"
            elif res == "menu":
                return "menu"
        elif ch=="i": field_menu(player,slot)
        elif ch=="s": show_status(player); dinput("  PRESS ENTER...")
        elif ch=="q":
            save_game(player, slot)
            typewrite("\n  GAME SAVED. RETURNING TO MAIN MENU...",0.04)
            time.sleep(1)
            return "menu"
        else: typewrite("\n  THE MIDDLEWHERE WATCHES.",0.04); time.sleep(0.8)
 
# ── STILL HOUSE ───────────────────────────────────────────
def run_still_house(player, slot):
    while True:
        clear(); player["location"]="still_house"
        print("\n  THE STILL HOUSE")
        print("  ─────────────────────────────────────────────")
        print("  [1] Entrance hall")
        print("  [2] Back workroom  (rusted axe)")
        print("  [3] Back porch     (checkpoint)")
        if "still_house" in player["visited"]:
            print("  [4] Strange cabinet in the corner")
        print("  [I] FIELD MENU   [B] Leave")
        print("")
        ch=dinput("  > ").strip().lower()
        if ch=="1":
            if still_entrance(player,slot)=="dead": return "dead"
        elif ch=="2": still_workroom(player,slot)
        elif ch=="3": still_porch(player,slot)
        elif ch=="4" and "still_house" in player["visited"]: still_cabinet(player,slot)
        elif ch=="i": field_menu(player,slot)
        elif ch=="b": return
        else: typewrite("\n  NOTHING THERE.",0.04); time.sleep(0.6)
        if "still_house" not in player["visited"]:
            player["visited"].append("still_house")
 
def still_entrance(player,slot):
    clear()
    slow_print(["","  ENTRANCE HALL","  ─────────────────────────────────────────────","",
        "  Dust on everything. Furniture under sheets.",
        "  A coat still by the door.",""],0.18)
    r=rng_encounter(player,"ashwood",slot)
    if r is False: return "dead"
    dinput("  PRESS ENTER...")
 
def still_workroom(player,slot):
    clear()
    slow_print(["","  BACK WORKROOM","  ─────────────────────────────────────────────","",
        "  An axe on the pegboard. Old. Rusted.",
        "  The edge still holds.",""],0.18)
    if player["weapon"]=="rusted_axe" or "rusted_axe" in player["inventory"]:
        typewrite("  You already have the axe.",0.04)
    else:
        if dinput("  TAKE THE RUSTED AXE? Y/N: ").strip().lower()=="y":
            player["inventory"].append("rusted_axe")
            slow_print(["","  > RUSTED AXE added to inventory.","  > Equip via [I] Field Menu.",""],0.15)
    if stat_check(player,"PER",11) and "still_shelf_searched" not in player["flags"]:
        player["flags"]["still_shelf_searched"]="true"
        player["consumables"]["dry_meat"]=player["consumables"].get("dry_meat",0)+1
        typewrite("  > DRY MEAT found on top shelf.",0.04)
    dinput("\n  PRESS ENTER...")
 
def still_porch(player,slot):
    clear()
    slow_print(["","  BACK PORCH","  ─────────────────────────────────────────────","",
        "  A chair facing the Crossroads.",
        "  The checkpoint mark carved into the armrest.",""],0.18)
    if dinput("  REST HERE? Y/N: ").strip().lower()=="y":
        checkpoint(player,"still_house",slot)
 
def still_cabinet(player,slot):
    clear()
    slow_print(["","  A STRANGE CABINET","  ─────────────────────────────────────────────","",
        "  Small. Dark wood. A symbol you don't recognize.",
        "  Not the checkpoint mark. Something else.",
        "  It's locked.",""],0.18)
    if player["flags"].get("cabinet_open")=="true":
        typewrite("  It's already open. Empty.",0.04)
    elif "cabinet_key" in player["inventory"]:
        if dinput("  OPEN IT? Y/N: ").strip().lower()=="y":
            player["flags"]["cabinet_open"]="true"
            player["flags"]["ascension_path"]="true"
            player["trust_score"]+=10
            player["inventory"].append("lords_bell")
            slow_print(["","  Inside: a heavy bronze bell. The surface is warm, and its resonance doesn't stop.","  A smell like static.",
                "","  Then a voice. Quiet. Friendly.",
                "","  'Hey. You found it.'",
                "  'I wasn't sure anyone would.'",
                "  'Waking them isn't going to be easy, but you have the bell now. Go on.'",
                "  'Come find me when you're ready.'",""],0.18)
            save_game(player,slot)
    else:
        typewrite("  You don't have the key.",0.04)
        if stat_check(player,"PER",14):
            typewrite("  The symbol feels familiar.",0.04)
    dinput("\n  PRESS ENTER...")
 
# ── ASHWOOD ───────────────────────────────────────────────
def run_ashwood(player,slot):
    if "ashwood" not in player["visited"]:
        player["visited"].append("ashwood")
        clear()
        slow_print(["","  THE ASHWOOD","  ─────────────────────────────────────────────","",
            "  Trees frozen mid-sway. Light that doesn't move.",
            "  Shadows that shouldn't be where they are.",
            "  Something notices you entered.",""],0.18)
        dinput("  PRESS ENTER...")
    while True:
        clear(); player["location"]="ashwood"
        show_status(player)
        print("  THE ASHWOOD")
        print("  ─────────────────────────────────────────────")
        print("  [1] Walk the tree line")
        print("  [2] Investigate the hollow trunk")
        print("  [3] Follow the scratch marks")
        print("  [4] Push deeper into the grove")
        if player["flags"].get("ashwood_deep")=="true" and player["flags"].get("ashwood_boss_done")!="true":
            print("  [5] THE ASHEN TREE  (boss)")
        elif player["flags"].get("ashwood_boss_done")=="true":
            print("  [5] The clearing  (boss defeated)")
        if player["flags"].get("ash_lord_unlocked")=="true":
            print("  [7] The oldest root  (??)")
        print("  [6] The resting stone  (checkpoint)")
        print("  [I] FIELD MENU   [B] Back")
        print("")
        ch=dinput("  > ").strip().lower()
        if ch=="1":
            if ashwood_treeline(player,slot)=="dead": return "dead"
        elif ch=="2": ashwood_hollow(player,slot)
        elif ch=="3":
            if ashwood_scratches(player,slot)=="dead": return "dead"
        elif ch=="4":
            if ashwood_deep(player,slot)=="dead": return "dead"
        elif ch=="5" and player["flags"].get("ashwood_deep")=="true" and player["flags"].get("ashwood_boss_done")!="true":
            r=ashwood_boss(player,slot)
            if r=="dead": return "dead"
        elif ch=="6": ashwood_checkpoint_room(player,slot)
        elif ch=="7" and player["flags"].get("ash_lord_unlocked")=="true":
            if ashwood_lord(player,slot)=="dead": return "dead"
        elif ch=="i": field_menu(player,slot)
        elif ch=="b": return "back"
        else: typewrite("\n  NOTHING THERE.",0.04); time.sleep(0.6)
 
def ashwood_treeline(player,slot):
    clear()
    slow_print(["","  TREE LINE","  ─────────────────────────────────────────────","",
        "  Branches like cracked ribs. Ground too soft.",""],0.18)
    r=rng_encounter(player,"ashwood",slot)
    if r is False: return "dead"
    if stat_check(player,"PER",9) and "treeline_item" not in player["flags"]:
        player["flags"]["treeline_item"]="true"
        player["consumables"]["ash_handful"]=player["consumables"].get("ash_handful",0)+1
        typewrite("  ASH HANDFUL found on the ground.",0.04)
    dinput("  PRESS ENTER...")
 
def ashwood_hollow(player,slot):
    clear()
    slow_print(["","  THE HOLLOW TRUNK","  ─────────────────────────────────────────────","",
        "  A tree wider than you are tall. Carved out from inside.",""],0.18)
    if "hollow_searched" not in player["flags"]:
        if dinput("  REACH INSIDE? Y/N: ").strip().lower()=="y":
            player["flags"]["hollow_searched"]="true"
            if stat_check(player,"PER",8):
                item=random.choice(["dry_meat","bitter_root"])
                player["consumables"][item]=player["consumables"].get(item,0)+1
                typewrite(f"  {CONSUMABLE_INFO[item]['name'].upper()} found.",0.04)
            else:
                typewrite("  Nothing. Just cold bark.",0.04)
    else:
        typewrite("  Already searched.",0.04)
    dinput("  PRESS ENTER...")
 
def ashwood_scratches(player,slot):
    clear()
    slow_print(["","  SCRATCH MARKS","  ─────────────────────────────────────────────","",
        "  Deep. Deliberate. Same pattern on three trees.",""],0.18)
    if stat_check(player,"PER",10): typewrite("  The marks point deeper north.",0.04)
    r=rng_encounter(player,"ashwood",slot)
    if r is False: return "dead"
    dinput("  PRESS ENTER...")
 
def ashwood_deep(player,slot):
    clear()
    slow_print(["","  THE DEEP GROVE","  ─────────────────────────────────────────────","",
        "  Trees fused at the trunk. One thing pretending to be many.",
        "  Something breathes here.",""],0.18)
    typewrite("  A HOLLOW WALKER STEPS FROM THE DARK.",0.05); time.sleep(0.5)
    if not run_combat(player,"hollow_walker",slot): return "dead"
    if player["flags"].get("ashwood_deep")!="true":
        player["flags"]["ashwood_deep"]="true"
        slow_print(["","  Past the Walker: something vast. Something still.",
            "  Black bark. No leaves. Never had any.",
            "  THE ASHEN TREE. It waits.",""],0.18)
        typewrite("  > BOSS AREA UNLOCKED: THE ASHEN TREE",0.04)
        save_game(player,slot)
    dinput("  PRESS ENTER...")
 
def ashwood_checkpoint_room(player,slot):
    clear()
    slow_print(["","  THE RESTING STONE","  ─────────────────────────────────────────────","",
        "  A flat stone. No shadows here. The mark carved deep.",""],0.18)
    if dinput("  REST? Y/N: ").strip().lower()=="y":
        checkpoint(player,"ashwood",slot)
 
def ashwood_boss(player,slot):
    clear()
    slow_print(["","  THE ASHEN TREE","  ─────────────────────────────────────────────","",
        "  It does not move. It does not need to.",
        "  Black bark. Where roots should be --",
        "  Things that used to be other things.",""],0.18)
    dinput("  PRESS ENTER TO FIGHT...")
    r=run_arena_generic(player,"ashen_tree",slot)
    if r is None or r=="lose": player["hp"]=0; return "dead"
    if r=="quit": return "back"
    clear()
    slow_print(["","  THE ASHEN TREE FALLS.",
        "  The bark crumbles. Silence fills the clearing.",
        "  Something falls from inside the trunk.",""],0.2)
    player["inventory"].append("hollow_fang")
    typewrite("  > HOLLOW FANG obtained. Scales with WILL.",0.04)
    if player["talisman"]!="ashen_bark":
        equip_talisman(player,"ashen_bark")
        if "ashen_bark" not in player["inventory"]: player["inventory"].append("ashen_bark")
    player["xp"]+=150; typewrite("  +150 XP.",0.04)
    if player["xp"]>=player["xp_next"]: dinput("  PRESS ENTER..."); level_up(player)
    if "blackwater_rot" not in player["unlocked"]:
        player["unlocked"].append("blackwater_rot")
        typewrite("  > BLACKWATER ROT unlocked. A dark wet path opens west.",0.04)
    player["flags"]["ashwood_boss_done"]="true"
    player["flags"]["ash_lord_unlocked"]="true"
    save_game(player,slot)
    dinput("\n  PRESS ENTER TO CONTINUE...")
    return "done"
 
# ── PALE FIELDS ───────────────────────────────────────────
def run_pale_fields(player,slot):
    if "pale_fields" not in player["visited"]:
        player["visited"].append("pale_fields")
        clear()
        slow_print(["","  THE PALE FIELDS","  ─────────────────────────────────────────────","",
            "  Open sky. Too open. Grass the color of old teeth.",
            "  Shapes in the distance. Standing. Not moving.",""],0.18)
        dinput("  PRESS ENTER...")
    while True:
        clear(); player["location"]="pale_fields"
        show_status(player)
        print("  THE PALE FIELDS")
        print("  ─────────────────────────────────────────────")
        print("  [1] Walk the field edge")
        print("  [2] Approach the standing shapes")
        print("  [3] Examine the low stone formation")
        print("  [4] Head toward the distant figure")
        if player["flags"].get("pale_deep")=="true" and player["flags"].get("pale_boss_done")!="true":
            print("  [5] THE PALE WARDEN  (boss)")
        if player["flags"].get("pale_lord_unlocked")=="true":
            print("  [7] Where the grass ends  (??)")
        print("  [6] The buried stone  (checkpoint)")
        print("  [I] FIELD MENU   [B] Back")
        print("")
        ch=dinput("  > ").strip().lower()
        if ch=="1":
            if pale_field_edge(player,slot)=="dead": return "dead"
        elif ch=="2":
            if pale_stillborns(player,slot)=="dead": return "dead"
        elif ch=="3":
            if pale_stone_formation(player,slot)=="dead": return "dead"
        elif ch=="4":
            if pale_deep(player,slot)=="dead": return "dead"
        elif ch=="5" and player["flags"].get("pale_deep")=="true" and player["flags"].get("pale_boss_done")!="true":
            r=pale_boss(player,slot)
            if r=="dead": return "dead"
        elif ch=="6": pale_checkpoint_room(player,slot)
        elif ch=="7" and player["flags"].get("pale_lord_unlocked")=="true":
            if pale_lord(player,slot)=="dead": return "dead"
        elif ch=="i": field_menu(player,slot)
        elif ch=="b": return "back"
        else: typewrite("\n  NOTHING THERE.",0.04); time.sleep(0.6)
 
def pale_field_edge(player,slot):
    clear()
    slow_print(["","  FIELD EDGE","  ─────────────────────────────────────────────","",
        "  Grass too brittle. Like it was never alive.",""],0.18)
    r=rng_encounter(player,"pale_fields",slot)
    if r is False: return "dead"
    if stat_check(player,"PER",9) and "field_edge_item" not in player["flags"]:
        player["flags"]["field_edge_item"]="true"
        player["consumables"]["pale_water"]=player["consumables"].get("pale_water",0)+1
        typewrite("  PALE WATER found pooled in a hollow.",0.04)
    dinput("  PRESS ENTER...")
 
def pale_stillborns(player,slot):
    clear()
    slow_print(["","  THE STILLBORNS","  ─────────────────────────────────────────────","",
        "  Everywhere. Standing. Facing you.",
        "  Each one slightly different. Completely still.",""],0.18)
    if stat_check(player,"WIL",12):
        slow_print(["  Something says: don't.","  They're not here to hurt you.","  You walk past.",""],0.18)
        if stat_check(player,"PER",10):
            player["consumables"]["dry_meat"]=player["consumables"].get("dry_meat",0)+1
            typewrite("  One holds something. You take it gently.",0.04)
            typewrite("  > DRY MEAT found.",0.04)
    else:
        typewrite("  INSTINCT KICKS IN. YOU ATTACK.",0.05); time.sleep(0.4)
        if not run_combat(player,"stillborn",slot): return "dead"
        typewrite("  It didn't fight back. It never was going to.",0.04)
        player["void_score"]+=1
    dinput("\n  PRESS ENTER...")
 
def pale_stone_formation(player,slot):
    clear()
    slow_print(["","  LOW STONE FORMATION","  ─────────────────────────────────────────────","",
        "  Flat stones half-buried. Arranged. Not natural.",""],0.18)
    if stat_check(player,"PER",11) and "stone_dug" not in player["flags"]:
        player["flags"]["stone_dug"]="true"
        item=random.choice(["bitter_root","pale_water"])
        player["consumables"][item]=player["consumables"].get(item,0)+1
        typewrite(f"  Something under the largest stone. > {CONSUMABLE_INFO[item]['name'].upper()}.",0.04)
    r=rng_encounter(player,"pale_fields",slot)
    if r is False: return "dead"
    dinput("  PRESS ENTER...")
 
def pale_deep(player,slot):
    clear()
    slow_print(["","  THE DISTANT FIGURE","  ─────────────────────────────────────────────","",
        "  Tall. Wrapped in pale grass like bandages.",
        "  Head faces the wrong direction.",
        "  A PALE GRAZER charges from your left.",""],0.18)
    if not run_combat(player,"pale_grazer",slot): return "dead"
    if player["flags"].get("pale_deep")!="true":
        player["flags"]["pale_deep"]="true"
        slow_print(["","  The tall figure has not moved.",
            "  Whatever it is, it is the heart of this place.",
            "  THE PALE WARDEN. It waits.",""],0.18)
        typewrite("  > BOSS AREA UNLOCKED: THE PALE WARDEN",0.04)
        save_game(player,slot)
    dinput("  PRESS ENTER...")
 
def pale_checkpoint_room(player,slot):
    clear()
    slow_print(["","  THE BURIED STONE","  ─────────────────────────────────────────────","",
        "  Half-buried. The mark worn but visible.",""],0.18)
    if dinput("  REST? Y/N: ").strip().lower()=="y":
        checkpoint(player,"pale_fields",slot)
 
def pale_boss(player,slot):
    clear()
    slow_print(["","  THE PALE WARDEN","  ─────────────────────────────────────────────","",
        "  It unfolds from the grass. Tall. Wrong proportions.",
        "  Its head faces backwards. It already knows you are here.",""],0.18)
    dinput("  PRESS ENTER TO FIGHT...")
    if not run_combat(player,"pale_warden",slot): return "dead"
    clear()
    slow_print(["","  THE PALE WARDEN DISSOLVES.",
        "  Back into the grass. Like it was never solid.",""],0.2)
    if "pale_shard" not in player["inventory"]:
        player["inventory"].append("pale_shard")
        typewrite("  > PALE SHARD obtained. Scales with PERCEPTION.",0.04)
    if player["talisman"]!="pale_eye":
        equip_talisman(player,"pale_eye")
        if "pale_eye" not in player["inventory"]: player["inventory"].append("pale_eye")
    player["xp"]+=80; typewrite("  +80 XP.",0.04)
    if player["xp"]>=player["xp_next"]: dinput("  PRESS ENTER..."); level_up(player)
    if "mountains" not in player["unlocked"]:
        player["unlocked"].append("mountains")
        typewrite("  > STATIC MOUNTAINS unlocked. Frozen peaks rise to the northeast.",0.04)
    player["flags"]["pale_boss_done"]="true"
    player["flags"]["pale_lord_unlocked"]="true"
    save_game(player,slot)
    dinput("\n  PRESS ENTER TO CONTINUE...")
    return "done"
 
# ══════════════════════════════════════════════════════════
#  BLACKWATER ROT
# ══════════════════════════════════════════════════════════
def run_blackwater_rot(player,slot):
    if "blackwater_rot" not in player["visited"]:
        player["visited"].append("blackwater_rot")
        clear()
        slow_print(["","  BLACKWATER ROT","  ─────────────────────────────────────────────","",
            "  Chest-deep fog. Black water between the roots.",
            "  Things move underneath the surface.",
            "  You can hear them but not see them.",
            "  The smell is wrong in a way you can't name.","",
            "  Something here has been rotting for a very long time.",""],0.18)
        dinput("  PRESS ENTER TO ENTER...")
    while True:
        clear(); player["location"]="blackwater_rot"
        show_status(player)
        print("  BLACKWATER ROT")
        print("  ─────────────────────────────────────────────")
        print("  [1] Wade through the shallows")
        print("  [2] Investigate the sunken structure")
        print("  [3] Follow the sound of singing")
        print("  [4] Push into the deep rot")
        if player["flags"].get("rot_deep")=="true" and player["flags"].get("choir_done")!="true":
            print("  [5] THE DROWNED CHOIR  (boss)")
        elif player["flags"].get("choir_done")=="true":
            print("  [5] The silent pool  (boss defeated)")
            print("  [6] The deepest muck  (secret presence)")
        
        last_idx = "7" if player["flags"].get("choir_done")=="true" else "6"
        print(f"  [{last_idx}] Dry ground by the roots  (checkpoint)")
        print("  [I] FIELD MENU   [B] Back")
        print("")
        ch=dinput("  > ").strip().lower()
        if ch=="1":
            if rot_shallows(player,slot)=="dead": return "dead"
        elif ch=="2":
            if rot_structure(player,slot)=="dead": return "dead"
        elif ch=="3":
            if rot_singing(player,slot)=="dead": return "dead"
        elif ch=="4":
            if rot_deep(player,slot)=="dead": return "dead"
        elif ch=="5" and player["flags"].get("rot_deep")=="true" and player["flags"].get("choir_done")!="true":
            r=rot_boss(player,slot)
            if r=="dead": return "dead"
        elif ch=="6" and player["flags"].get("choir_done")=="true":
            if rot_secret(player,slot)=="dead": return "dead"
        elif ch==last_idx: rot_checkpoint(player,slot)
        elif ch=="i": field_menu(player,slot)
        elif ch=="b": return "back"
        else: typewrite("\n  NOTHING THERE.",0.04); time.sleep(0.6)
 
def rot_shallows(player,slot):
    clear()
    slow_print(["","  THE SHALLOWS","  ─────────────────────────────────────────────","",
        "  Black water to your knees. Cold.",
        "  Things brush past your legs. You don't look down.",""],0.18)
    r=rng_encounter(player,"blackwater_rot",slot)
    if r is False: return "dead"
    if stat_check(player,"PER",10) and "rot_shallow_item" not in player["flags"]:
        player["flags"]["rot_shallow_item"]="true"
        player["consumables"]["antitoxin"]=player["consumables"].get("antitoxin",0)+1
        typewrite("  Something floats past. A vial. Still sealed.",0.04)
        typewrite("  > ANTITOXIN found.",0.04)
    dinput("  PRESS ENTER...")
 
def rot_structure(player,slot):
    clear()
    slow_print(["","  SUNKEN STRUCTURE","  ─────────────────────────────────────────────","",
        "  Something man-made, half submerged.",
        "  Stone walls. Old. Whatever it was,",
        "  it has been here longer than the rot.",""],0.18)
    if stat_check(player,"PER",12) and "rot_structure_item" not in player["flags"]:
        player["flags"]["rot_structure_item"]="true"
        player["consumables"]["pale_water"]=player["consumables"].get("pale_water",0)+2
        typewrite("  Inside: two sealed bottles on a shelf above the waterline.",0.04)
        typewrite("  > PALE WATER x2 found.",0.04)
    if stat_check(player,"WIL",11):
        typewrite("  The walls hum. Not water. Something inside the stone.",0.04)
    r=rng_encounter(player,"blackwater_rot",slot)
    if r is False: return "dead"
    dinput("  PRESS ENTER...")
 
def rot_singing(player,slot):
    clear()
    slow_print(["","  THE SOUND OF SINGING","  ─────────────────────────────────────────────","",
        "  Not melodic. More like many voices trying to be one.",
        "  Coming from deeper in the rot.",
        "  It doesn't sound like music.",
        "  It sounds like something that forgot it was ever in pain.",""],0.18)
    typewrite("  A ROTTEN WALKER LURCHES FROM THE FOG.",0.05); time.sleep(0.5)
    if not run_combat(player,"rotten_walker",slot): return "dead"
    if player["flags"].get("rot_deep")!="true":
        player["flags"]["rot_deep"]="true"
        slow_print(["","  Past the Walker: a pool of black water.",
            "  Still. Perfectly still.",
            "  And below the surface -- shapes. Many shapes.",
            "  Moving together.",
            "  THE DROWNED CHOIR. It calls.",""],0.18)
        typewrite("  > BOSS AREA UNLOCKED: THE DROWNED CHOIR",0.04)
        save_game(player,slot)
    dinput("  PRESS ENTER...")
 
def rot_deep(player,slot):
    clear()
    slow_print(["","  DEEP ROT","  ─────────────────────────────────────────────","",
        "  You shouldn't be here.",
        "  The water is chest deep now.",
        "  Something large moves below.",""],0.18)
    typewrite("  A BOG CRAWLER SURFACES.",0.05); time.sleep(0.5)
    if not run_combat(player,"bog_crawler",slot): return "dead"
    if stat_check(player,"PER",11) and "rot_deep_item" not in player["flags"]:
        player["flags"]["rot_deep_item"]="true"
        if "sludge_knife" not in player["inventory"]:
            player["inventory"].append("sludge_knife")
            typewrite("  Something glints in the water near the Crawler.",0.04)
            typewrite("  A knife. Coated in sludge. Still sharp.",0.04)
            typewrite("  > SLUDGE KNIFE added to inventory.",0.04)
            typewrite("  > Weak but fast. Inflicts Toxic. Low energy cost.",0.04)
    dinput("  PRESS ENTER...")
 
def rot_checkpoint(player,slot):
    clear()
    slow_print(["","  DRY GROUND","  ─────────────────────────────────────────────","",
        "  A patch of raised ground. Dry.",
        "  The checkpoint mark scratched into a root.",""],0.18)
    if dinput("  REST? Y/N: ").strip().lower()=="y":
        checkpoint(player,"blackwater_rot",slot)
 
def rot_boss(player,slot):
    clear()
    slow_print(["","  THE DROWNED CHOIR","  ─────────────────────────────────────────────","",
        "  They rise from the pool together.",
        "  Three shapes. Fused at the shoulder.",
        "  Rotten Walkers that found each other in the dark",
        "  and decided to become something else.",
        "  They sing as they move.",
        "  Not words. Just the sound of drowning, repeated.","",
        "  Each one is still alive.",
        "  Kill all three.",""],0.18)
    dinput("  PRESS ENTER TO FIGHT...")
    r=run_arena_generic(player,"choir",slot)
    if r is None or r=="lose": player["hp"]=0; return "dead"
    if r=="quit": return "back"
    clear()
    slow_print(["","  THE CHOIR FALLS SILENT.",
        "  Three shapes sink back into the black water.",
        "  The pool is still again.","",
        "  Something floats to the surface.",""],0.2)
    if "sludge_knife" not in player["inventory"]:
        player["inventory"].append("sludge_knife")
        typewrite("  > SLUDGE KNIFE obtained.",0.04)
    if player["talisman"]!="choir_remnant":
        equip_talisman(player,"choir_remnant")
        if "choir_remnant" not in player["inventory"]: player["inventory"].append("choir_remnant")
    player["xp"]+=180; typewrite("  +180 XP.",0.04)
    if player["xp"]>=player["xp_next"]: dinput("  PRESS ENTER..."); level_up(player)
    if "pillar" not in player["unlocked"]:
        player["unlocked"].append("pillar")
        typewrite("  > PILLAR OF MAGMA unlocked. Distant smoke to the south-west.",0.04)
    player["flags"]["choir_done"]="true"
    player["flags"]["rot_lord_unlocked"]="true"
    save_game(player,slot)
    dinput("\n  PRESS ENTER TO CONTINUE...")
    return "done"
 
def rot_secret(player,slot):
    clear()
    slow_print(["","  THE DEEPEST MUCK","  ─────────────────────────────────────────────","",
        "  Below the Choir. Below the roots. Below the water.",
        "  The black here isn't darkness.",
        "  It's something that replaced darkness","  after darkness rotted away.","",
        "  And at the center of it:","",
        "  A mass.",
        "  Not a shape. A mass.",
        "  Roots and flesh and water and something that was","  once none of those things and is now all of them.","",
        "  It breathes.",
        "  The whole swamp breathes when it breathes.",
        "  The rot is not a disease here.",
        "  The rot is a language.","",
        "  And the Lord of the Rot is the only one","  left who speaks it.","",
        "  It does not notice you.",
        "  Or it noticed you the moment you entered the swamp","  and has been deciding ever since.",""],0.18)
    if "rot_soul" in player.get("inventory", []):
        typewrite("\n  The dark water is completely still. The breathing has stopped.", 0.04)
        typewrite("  Its soul has been harvested.", 0.04)
        dinput("\n  PRESS ENTER TO LEAVE...")
        return

    if "lords_bell" in player.get("inventory", []):
        print("  The Lord's Bell vibrates, its bronze surface sweating with green mold.")
        print("  [1] Ring the Lord's Bell to wake the Lord")
        print("  [2] Leave")
        ch = dinput("  > ").strip()
        if ch == "1":
            clear()
            typewrite("\n  You ring the Lord's Bell.", 0.05)
            typewrite("  A heavy, wet clang reverberates through the muck.", 0.04)
            typewrite("  The breathing mass bubbles violently. Eyes open across the rotting flesh.", 0.04)
            typewrite("  The entire bog rises to consume you!", 0.04)
            time.sleep(1.0)
            if run_arena_generic(player, "rot_lord", slot) != 'win':
                return "dead"
            player["inventory"].append("rot_soul")
            player["flags"]["rot_lord_killed"] = "true"
            typewrite("\n  The mass burst apart, leaving only bubbles of black gas.", 0.04)
            typewrite("  A thick, glowing Rot Soul rises from the sludge.", 0.04)
            typewrite("  > ROT SOUL harvested.", 0.04)
            save_game(player, slot)
            dinput("\n  PRESS ENTER TO LEAVE...")
            return
    else:
        if "rot_secret_seen" not in player["flags"]:
            player["flags"]["rot_secret_seen"]="true"
            save_game(player,slot)
            typewrite("  > The Lord of the Rot has been found.",0.04)
            typewrite("  > The swamp breathes. You are inside it.",0.04)
        dinput("\n  PRESS ENTER TO LEAVE THIS PLACE...")
 
# ══════════════════════════════════════════════════════════
#  STATIC MOUNTAINS
# ══════════════════════════════════════════════════════════
def run_static_mountains(player,slot):
    if "static_mountains" not in player["visited"]:
        player["visited"].append("static_mountains")
        clear()
        slow_print(["","  STATIC MOUNTAINS","  ─────────────────────────────────────────────","",
            "  The cold hits you before you see them.",
            "  Not wind-cold. Something else.",
            "  Like the temperature decided to stop here","  and hasn't moved since.","",
            "  An avalanche hangs in the air above the pass.",
            "  Mid-fall. Frozen.",
            "  Birds stopped mid-flight between the peaks.",
            "  A campfire on the path ahead --",
            "  the flame suspended in place, perfectly still.",
            "  And travelers. Still in walking poses.",
            "  Whatever froze this place",
            "  froze everything in it.","",
            "  Something did this.",
            "  Something enormous.",
            "  You can feel it, deep in the mountain.",""],0.18)
        dinput("  PRESS ENTER TO ENTER...")
    while True:
        clear(); player["location"]="static_mountains"
        show_status(player)
        print("  STATIC MOUNTAINS")
        print("  ─────────────────────────────────────────────")
        print("  [1] The frozen pass")
        print("  [2] The suspended campfire")
        print("  [3] The still travelers")
        print("  [4] The glacier face")
        if player["flags"].get("mountain_deep")=="true" and player["flags"].get("sentinel_done")!="true":
            print("  [5] THE SENTINEL OF THE PASS  (miniboss)")
        if player["flags"].get("sentinel_done")=="true" and player["flags"].get("avalanche_done")!="true":
            print("  [6] THE AVALANCHE  (boss)")
        if player["flags"].get("avalanche_done")=="true":
            print("  [7] The shattered peak  (secret presence)")
        print("  [8] Ice shelf  (checkpoint)")
        print("  [I] FIELD MENU   [B] Back")
        print("")
        ch=dinput("  > ").strip().lower()
        if ch=="1":
            if mountain_pass(player,slot)=="dead": return "dead"
        elif ch=="2": mountain_campfire(player,slot)
        elif ch=="3": mountain_travelers(player,slot)
        elif ch=="4":
            if mountain_glacier(player,slot)=="dead": return "dead"
        elif ch=="5" and player["flags"].get("mountain_deep")=="true" and player["flags"].get("sentinel_done")!="true":
            r=mountain_sentinel(player,slot)
            if r=="dead": return "dead"
        elif ch=="6" and player["flags"].get("sentinel_done")=="true" and player["flags"].get("avalanche_done")!="true":
            r=mountain_avalanche(player,slot)
            if r=="dead": return "dead"
        elif ch=="7" and player["flags"].get("avalanche_done")=="true":
            if mountain_secret(player,slot)=="dead": return "dead"
        elif ch=="8": mountain_checkpoint(player,slot)
        elif ch=="i": field_menu(player,slot)
        elif ch=="b": return "back"
        else: typewrite("\n  NOTHING THERE.",0.04); time.sleep(0.6)
 
def mountain_pass(player,slot):
    clear()
    slow_print(["","  THE FROZEN PASS","  ─────────────────────────────────────────────","",
        "  Narrow. Ice on every surface.",
        "  A FROSTBITTEN darts from a crevice.",""],0.18)
    r=rng_encounter(player,"static_mountains",slot)
    if r is False: return "dead"
    if stat_check(player,"PER",10) and "pass_item" not in player["flags"]:
        player["flags"]["pass_item"]="true"
        player["consumables"]["warm_ember"]=player["consumables"].get("warm_ember",0)+1
        typewrite("  A glowing fragment on the ice. Still warm somehow.",0.04)
        typewrite("  > WARM EMBER found.",0.04)
    dinput("  PRESS ENTER...")
 
def mountain_campfire(player,slot):
    clear()
    slow_print(["","  THE SUSPENDED CAMPFIRE","  ─────────────────────────────────────────────","",
        "  The flame hangs in the air. Still.",
        "  Not flickering. Not fading.",
        "  Just frozen mid-dance.",
        "  The wood beneath it isn't burning.",
        "  The heat isn't moving.",
        "  But it's warm. Right here. In this exact spot.",""],0.18)
    if "campfire_rested" not in player["flags"]:
        if dinput("  REST BY THE FIRE? Y/N: ").strip().lower()=="y":
            player["flags"]["campfire_rested"]="true"
            heal=15; player["hp"]=min(player["max_hp"],player["hp"]+heal)
            if "cold" in player["status"]: del player["status"]["cold"]
            typewrite(f"  The warmth doesn't move but it reaches you somehow.",0.04)
            typewrite(f"  +{heal} HP. Cold cleared.",0.04)
    else:
        typewrite("  The flame still hangs there. Still warm.",0.04)
    dinput("  PRESS ENTER...")
 
def mountain_travelers(player,slot):
    clear()
    slow_print(["","  THE STILL TRAVELERS","  ─────────────────────────────────────────────","",
        "  Six of them. Mid-stride. Mid-conversation.",
        "  One laughing at something. The laugh frozen on his face.",
        "  One pointing at the peaks. Still pointing.",
        "  They were here when it happened.",
        "  Whatever it was, it was fast.","",
        "  They still carry their packs.",""],0.18)
    if stat_check(player,"PER",12) and "traveler_item" not in player["flags"]:
        player["flags"]["traveler_item"]="true"
        player["consumables"]["dry_meat"]=player["consumables"].get("dry_meat",0)+2
        player["consumables"]["warm_ember"]=player["consumables"].get("warm_ember",0)+1
        typewrite("  You search the packs carefully.",0.04)
        typewrite("  > DRY MEAT x2 found.",0.04)
        typewrite("  > WARM EMBER found.",0.04)
    if stat_check(player,"WIL",13):
        typewrite("  Something massive under the ice further up.",0.04)
        typewrite("  Too big to be a person. Too still to be anything else.",0.04)
        if player["flags"].get("mountain_deep")!="true":
            player["flags"]["mountain_deep"]="true"
            typewrite("  > SENTINEL area revealed.",0.04)
    dinput("  PRESS ENTER...")
 
def mountain_glacier(player,slot):
    clear()
    slow_print(["","  THE GLACIER FACE","  ─────────────────────────────────────────────","",
        "  Ice older than anything you've seen.",
        "  Deep inside it: shapes. Trapped.","",
        "  Animals. Trees. Things that aren't either.",
        "  All frozen mid-motion.",
        "  All looking the same direction.","",
        "  Up.",""],0.18)
    r=rng_encounter(player,"static_mountains",slot)
    if r is False: return "dead"
    if player["flags"].get("mountain_deep")!="true" and stat_check(player,"PER",11):
        player["flags"]["mountain_deep"]="true"
        typewrite("  Further up: something enormous standing in the pass.",0.04)
        typewrite("  > SENTINEL area revealed.",0.04)
    dinput("  PRESS ENTER...")
 
def mountain_checkpoint(player,slot):
    clear()
    slow_print(["","  ICE SHELF","  ─────────────────────────────────────────────","",
        "  A flat ledge cut into the mountain face.",
        "  The checkpoint mark carved here with something sharp.",
        "  Someone made it this far.",""],0.18)
    if dinput("  REST? Y/N: ").strip().lower()=="y":
        checkpoint(player,"static_mountains",slot)
 
def mountain_sentinel(player,slot):
    clear()
    slow_print(["","  THE SENTINEL OF THE PASS","  ─────────────────────────────────────────────","",
        "  It has been here so long it fused with the mountain.",
        "  Stone where skin should be.",
        "  Ice where eyes should be.",
        "  It was a guard once. Now it is a wall.",
        "  And the wall notices you.",""],0.18)
    dinput("  PRESS ENTER TO FIGHT...")
    if not run_combat(player,"sentinel_pass",slot): return "dead"
    clear()
    slow_print(["","  THE SENTINEL SHATTERS.",
        "  Stone and ice. Then silence.",
        "  Something beneath the rubble.",""],0.2)
    if "frozen_hammer" not in player["inventory"]:
        player["inventory"].append("frozen_hammer")
        typewrite("  > FROZEN HAMMER obtained.",0.04)
        typewrite("  > Requires STR 8. Scales STR+WIL. Inflicts Cold.",0.04)
        ok,msg=check_weapon_req(player,"frozen_hammer")
        if not ok: typewrite(f"  > WARNING: {msg}",0.04)
    player["xp"]+=100; typewrite("  +100 XP.",0.04)
    if player["xp"]>=player["xp_next"]: dinput("  PRESS ENTER..."); level_up(player)
    player["flags"]["sentinel_done"]="true"
    save_game(player,slot)
    dinput("\n  PRESS ENTER TO CONTINUE...")
    return "done"
 
def mountain_avalanche(player,slot):
    clear()
    slow_print(["","  THE AVALANCHE","  ─────────────────────────────────────────────","",
        "  The one hanging in the air above the pass.",
        "  You've been looking at it since you arrived.",
        "  Something releases it.","",
        "  Not falling. Hunting.",
        "  The debris moves with direction. With intent.",
        "  Find the gaps. Attack the core when it surfaces.",
        "  The mountain itself is trying to end you.",""],0.18)
    dinput("  PRESS ENTER TO FIGHT...")
    r=run_arena_generic(player,"avalanche",slot)
    if r is None or r=="lose": player["hp"]=0; return "dead"
    if r=="quit": return "back"
    clear()
    slow_print(["","  THE AVALANCHE STILLS.",
        "  The debris hangs in the air again.",
        "  Back where it was.",
        "  Like it was never released.",
        "  The core dissolves. Something remains.",""],0.2)
    if player["talisman"]!="mountain_still":
        equip_talisman(player,"mountain_still")
        if "mountain_still" not in player["inventory"]: player["inventory"].append("mountain_still")
    player["xp"]+=200; typewrite("  +200 XP.",0.04)
    if player["xp"]>=player["xp_next"]: dinput("  PRESS ENTER..."); level_up(player)
    if "dunes" not in player["unlocked"]:
        player["unlocked"].append("dunes")
        typewrite("  > FOREVER LASTING DUNES unlocked. Endless sand to the east.",0.04)
    player["flags"]["avalanche_done"]="true"
    save_game(player,slot)
    dinput("\n  PRESS ENTER TO CONTINUE...")
    return "done"
 
def mountain_secret(player,slot):
    clear()
    slow_print(["","  THE SHATTERED PEAK","  ─────────────────────────────────────────────","",
        "  Above the avalanche. Above the pass.",
        "  A place the mountain didn't want you to reach.","",
        "  And there, in the ice:","",
        "  A shape.",
        "  Enormous.",
        "  Curled. Like it was sleeping when it froze.",
        "  Or like it froze everything else",
        "  so it could sleep.","",
        "  You count the limbs.",
        "  You stop counting.","",
        "  It is intact.",
        "  It is not dead.","",
        "  Something in the Middlewhere shifts.",
        "  Like a held breath, getting ready.",""],0.18)
    if "frost_soul" in player.get("inventory", []):
        typewrite("\n  The glacier peak is silent. The frozen shape has shattered into dust.", 0.04)
        typewrite("  Its soul has been harvested.", 0.04)
        dinput("\n  PRESS ENTER TO LEAVE...")
        return

    if "lords_bell" in player.get("inventory", []):
        print("  The Lord's Bell turns ice-cold in your hand, frost spreading on its metal.")
        print("  [1] Ring the Lord's Bell to wake the Lord")
        print("  [2] Leave")
        ch = dinput("  > ").strip()
        if ch == "1":
            clear()
            typewrite("\n  You ring the Lord's Bell.", 0.05)
            typewrite("  The chime is high and sharp, like cracking glass.", 0.04)
            typewrite("  Cracks spiderweb across the glacier. The curled limbs shatter their icy shell.", 0.04)
            typewrite("  A cold roar shakes the mountain itself!", 0.04)
            time.sleep(1.0)
            if run_arena_generic(player, "frost_lord", slot) != 'win':
                return "dead"
            player["inventory"].append("frost_soul")
            player["flags"]["frost_lord_killed"] = "true"
            typewrite("\n  The giant construct falls, disintegrating into snow.", 0.04)
            typewrite("  A glowing, frozen Frost Soul hovers in the freezing wind.", 0.04)
            typewrite("  > FROST SOUL harvested.", 0.04)
            save_game(player, slot)
            dinput("\n  PRESS ENTER TO LEAVE...")
            return
    else:
        if "secret_seen" not in player["flags"]:
            player["flags"]["secret_seen"]="true"
            save_game(player,slot)
            typewrite("  > The Lord of the Frostbite has been found.",0.04)
            typewrite("  > It looks dead, yet alive. You fear what's coming.",0.04)
        dinput("\n  PRESS ENTER TO LEAVE THIS PLACE...")
 
# ══════════════════════════════════════════════════════════
#  LORDS -- SECRET PRESENCES
# ══════════════════════════════════════════════════════════

def ashwood_lord(player,slot):
    clear()
    slow_print(["","  THE OLDEST ROOT","  ─────────────────────────────────────────────","",
        "  Past the Ashen Tree. Past where the clearing ends.",
        "  Where the ground stops being ground","  and starts being something else.","",
        "  The root is older than the forest.",
        "  The forest grew around it, not from it.",
        "  It is wider than a house.",
        "  It goes down further than you can see.","",
        "  And where the root meets the soil:","",
        "  A face.",
        "  Not carved. Grown.",
        "  Eyes that are knots in the wood.",
        "  A mouth that is a split in the bark.","",
        "  The Lord of the Ash does not sleep.",
        "  It has never slept.",
        "  Sleep requires time to pass,","  and time stopped in the Ashwood","  a long while ago.","",
        "  It has been watching the trees fail to fall","  for longer than you can hold in your head.","",
        "  It watches you now.",
        "  The same way it watches everything.","  Without judgment. Without hunger.",
        "  Just witness.","",
        "  The oldest thing in the Middlewhere","  and the most patient.",""],0.18)
    if "ash_soul" in player.get("inventory", []):
        typewrite("\n  The Oldest Root is quiet now. The face in the bark is frozen, hollow.", 0.04)
        typewrite("  Its soul has been harvested.", 0.04)
        dinput("\n  PRESS ENTER TO LEAVE...")
        return

    if "lords_bell" in player.get("inventory", []):
        print("  The Lord's Bell in your pocket vibrates warmly, resonating with the ancient wood.")
        print("  [1] Ring the Lord's Bell to wake the Lord")
        print("  [2] Leave")
        ch = dinput("  > ").strip()
        if ch == "1":
            clear()
            typewrite("\n  You ring the Lord's Bell.", 0.05)
            typewrite("  A deep, resonating chime echoes through the ancient trees.", 0.04)
            typewrite("  The face in the bark begins to shift. Sap drips like blood from the knot-eyes.", 0.04)
            typewrite("  The earth shakes as the root rips itself from the soil!", 0.04)
            time.sleep(1.0)
            if run_arena_generic(player, "ash_lord", slot) != 'win':
                return "dead"
            player["inventory"].append("ash_soul")
            player["flags"]["ash_lord_killed"] = "true"
            typewrite("\n  The ancient root grows still, collapsing back into the dirt.", 0.04)
            typewrite("  A pulsing, warm Ashen Soul floats into your hands.", 0.04)
            typewrite("  > ASH SOUL harvested.", 0.04)
            save_game(player, slot)
            dinput("\n  PRESS ENTER TO LEAVE...")
            return
    else:
        if "ash_lord_seen" not in player["flags"]:
            player["flags"]["ash_lord_seen"]="true"
            save_game(player,slot)
            typewrite("  > The Lord of the Ash has been found.",0.04)
            typewrite("  > It has been here since before the silence.",0.04)
        dinput("\n  PRESS ENTER TO LEAVE...")

def pale_lord(player,slot):
    clear()
    slow_print(["","  WHERE THE GRASS ENDS","  ─────────────────────────────────────────────","",
        "  The Pale Fields stretch on and on.",
        "  And then they don't.","",
        "  There is a place where the grass simply stops.",
        "  Not a treeline. Not a cliff.",
        "  Just: grass. And then nothing.",
        "  A hard border where the Middlewhere","  ran out of something.","",
        "  And at the border:","",
        "  A figure.",
        "  Not standing. Not sitting.",
        "  Present in the way a sound is present","  after it has already stopped.","",
        "  The Lord of the Mourning has no form",
        "  you can hold in your eyes.",
        "  Every time you look directly at it","  it is something different.",
        "  A person. An animal. A shadow with the wrong shape.",
        "  Something that used to be something else","  and hasn't decided what to be since.","",
        "  The Pale Fields are not empty.",
        "  They are full of grief","  that was left here by things that moved on.","",
        "  The Lord of the Mourning tends it.",
        "  Like a garden.",
        "  Like a wound.",""],0.18)
    if "pale_soul" in player.get("inventory", []):
        typewrite("\n  The border of the field is empty now. Only a cold breeze marks the spot.", 0.04)
        typewrite("  Its soul has been harvested.", 0.04)
        dinput("\n  PRESS ENTER TO LEAVE...")
        return

    if "lords_bell" in player.get("inventory", []):
        print("  The Lord's Bell resonates with a soft, mournful chime.")
        print("  [1] Ring the Lord's Bell to wake the Lord")
        print("  [2] Leave")
        ch = dinput("  > ").strip()
        if ch == "1":
            clear()
            typewrite("\n  You ring the Lord's Bell.", 0.05)
            typewrite("  The bronze chime pierces the heavy atmosphere of the fields.", 0.04)
            typewrite("  The shifting figure locks into a single, terrifying shape.", 0.04)
            typewrite("  A scream of absolute grief echoes across the empty horizon!", 0.04)
            time.sleep(1.0)
            if run_arena_generic(player, "pale_lord", slot) != 'win':
                return "dead"
            player["inventory"].append("pale_soul")
            player["flags"]["pale_lord_killed"] = "true"
            typewrite("\n  The figure dissolves into a puddle of dark water.", 0.04)
            typewrite("  A cold, shimmering Pale Soul floats into your hands.", 0.04)
            typewrite("  > PALE SOUL harvested.", 0.04)
            save_game(player, slot)
            dinput("\n  PRESS ENTER TO LEAVE...")
            return
    else:
        if "pale_lord_seen" not in player["flags"]:
            player["flags"]["pale_lord_seen"]="true"
            save_game(player,slot)
            typewrite("  > The Lord of the Mourning has been found.",0.04)
            typewrite("  > The fields are not empty. They are grieving.",0.04)
        dinput("\n  PRESS ENTER TO LEAVE...")

# ══════════════════════════════════════════════════════════
#  NEW ENEMIES -- DUNES + PILLAR
# ══════════════════════════════════════════════════════════

ENEMIES.update({
    "dune_crawler":  {"name":"Dune Crawler",   "hp":30,"damage":(6,11),"xp":22,"will_weak":False,"desc":"Flat. Sand-colored. You almost stepped on it.","drop":("dry_meat",0.3),"inflict":None},
    "heat_mirage":   {"name":"Heat Mirage",    "hp":20,"damage":(4,9), "xp":18,"will_weak":True, "desc":"Looks like you. Moves wrong.","drop":("pale_water",0.25),"inflict":None},
    "sandwraith":    {"name":"Sand Wraith",    "hp":38,"damage":(9,15),"xp":32,"will_weak":True, "desc":"A Walker that crossed the dunes and lost everything except hunger.","drop":("bitter_root",0.35),"inflict":None},
    "dune_sentinel": {"name":"Dune Sentinel",  "hp":70,"damage":(13,19),"xp":90,"will_weak":False,"desc":"Carved from sandstone. Older than the dunes. Still standing guard.","drop":("sun_blade",1.0),"inflict":None},
    "ember_sprite":  {"name":"Ember Sprite",   "hp":22,"damage":(5,10),"xp":20,"will_weak":False,"desc":"Small. Fast. Leaves burn marks wherever it lands.","drop":("warm_ember",0.4),"inflict":("burn",1)},
    "magma_hound":   {"name":"Magma Hound",    "hp":40,"damage":(10,16),"xp":30,"will_weak":False,"desc":"Low to the ground. Moves in short lunges. Mouth full of liquid rock.","drop":("bitter_root",0.3),"inflict":("burn",2)},
    "cinder_sentinel":{"name":"Cinder Sentinel","hp":80,"damage":(14,20),"xp":95,"will_weak":False,"desc":"A guardian that stood too close to the magma for too long.","drop":("cinder_blade",1.0),"inflict":("burn",2)},
    "pillar_colossus":{"name":"The Basalt Titan","hp":160,"damage":(18,26),"xp":220,"will_weak":False,"desc":"The mountain given form. It does not walk. It arrives.","drop":("magma_crown",1.0),"talisman":("pillar_heart",1.0),"inflict":("burn",3)},
})

BIOME_ENEMIES.update({
    "forever_dunes":   ["dune_crawler","heat_mirage","sandwraith"],
    "pillar_of_magma": ["ember_sprite","magma_hound"],
})

WEAPONS.update({
    "sun_blade":   {"name":"Sun Blade",   "dmg":(8,13),  "scale":"AGI",     "energy":10,"cooldown":12,"desc":"Light. Fast. Runs hot. Req AGI 6.","req":{"AGI":6},"toxic":False,"cold":False,"burn":True},
    "cinder_blade":{"name":"Cinder Blade","dmg":(12,18), "scale":"STR",     "energy":16,"cooldown":20,"desc":"Molten edge. Inflicts Burn. Req STR 7.","req":{"STR":7},"toxic":False,"cold":False,"burn":True},
    "magma_crown": {"name":"Magma Crown", "dmg":(0,0),   "scale":None,      "energy":0, "cooldown":0, "desc":"Not a weapon. A crown of cooling magma. Stored as key item.","req":None,"toxic":False,"cold":False,"burn":False},
})

TALISMANS.update({
    "dune_glass":  {"name":"Dune Glass",  "desc":"Sand fused by ancient heat.","effect":"Immune to disorientation. +2 PER.","stat":"PER"},
    "pillar_heart":{"name":"Pillar Heart","desc":"A core of compressed magma. Still warm.","effect":"Burn immunity. Your attacks have 15% chance to inflict Burn.","stat":"STR"},
})

CONSUMABLE_INFO.update({
    "sun_water":   {"name":"Sun Water",  "desc":"Scalding. Restores 30 HP. Inflicts minor Burn (1 turn)."},
    "cool_shard":  {"name":"Cool Shard", "desc":"Clears Burn immediately. Restores 5 HP."},
})

# ── BURN STATUS ────────────────────────────────────────────
# Handled in apply_status and tick_status -- Burn deals 6 dmg/turn for 2-3 turns

def _extended_use_item(player, item_key):
    """Extended use_item for new consumables."""
    if item_key=="sun_water":
        heal=30; player["hp"]=min(player["max_hp"],player["hp"]+heal)
        apply_status(player,"burn",1)
        typewrite(f"  SCALDING. +{heal} HP. Minor burn.",0.04)
    elif item_key=="cool_shard":
        if "burn" in player["status"]: del player["status"]["burn"]
        player["hp"]=min(player["max_hp"],player["hp"]+5)
        typewrite("  BURN CLEARED. +5 HP.",0.04)
    else:
        return False
    player["consumables"][item_key]-=1
    if player["consumables"][item_key]<=0: del player["consumables"][item_key]
    return True

# ══════════════════════════════════════════════════════════
#  FOREVER LASTING DUNES
# ══════════════════════════════════════════════════════════

import random as _rnd

def _scramble(text, intensity=1):
    """Scramble middle letters of each word, keep first and last. intensity 1-3."""
    if intensity==0: return text
    words=text.split()
    out=[]
    for w in words:
        if len(w)<=3 or not w[0].isalpha():
            out.append(w); continue
        mid=list(w[1:-1])
        if intensity>=2:
            mid=[chr(_rnd.randint(48,90)) if _rnd.random()<0.4 else c for c in mid]
        if intensity>=3:
            mid=[chr(_rnd.randint(33,126)) if _rnd.random()<0.6 else c for c in mid]
        _rnd.shuffle(mid)
        out.append(w[0]+''.join(mid)+w[-1])
    return ' '.join(out)

def _glitch_line(text, intensity=1):
    """Print a line with increasing corruption."""
    print(f"  {_scramble(text,intensity)}")
    time.sleep(0.18)

DUNE_ROOMS = [
    "the open sand",
    "a buried archway",
    "the heat shimmer",
    "a dry riverbed",
    "the glass plain",
    "a hollow dune",
    "the stone circle",
]

def run_forever_dunes(player, slot):
    if "forever_dunes" not in player["visited"]:
        player["visited"].append("forever_dunes")
        clear()
        slow_print(["","  FOREVER LASTING DUNES","  ─────────────────────────────────────────────","",
            "  Sand in every direction.",
            "  No landmarks. No shadow.",
            "  The sun doesn't move here.",
            "  Neither does the horizon.","",
            "  You walk. You arrive somewhere.",
            "  You walk again. You arrive where you started.",
            "  The dunes remember where you came from.",
            "  They do not allow you to go further.","",
            "  Something deep in the sand does not want visitors.",""],0.18)
        dinput("  PRESS ENTER TO ENTER...")

    # Depth tracker -- higher = more scrambled
    if "dune_depth" not in player["flags"]:
        player["flags"]["dune_depth"]="0"

    while True:
        depth=int(player["flags"].get("dune_depth","0"))
        intensity=min(3, depth//2)
        clear(); player["location"]="forever_dunes"
        show_status(player)

        if depth==0:
            print("  FOREVER LASTING DUNES")
            print("  ─────────────────────────────────────────────")
            print("  The sand stretches. You pick a direction.")
        else:
            # Scrambled header
            hdr=_scramble("FOREVER LASTING DUNES", intensity)
            sep=_scramble("you are going the wrong way", intensity)
            print(f"  {hdr}")
            print(f"  ─────────────────────────────────────────────")
            print(f"  {sep}")
        print("")

        # Scramble the room options based on depth
        rooms=list(DUNE_ROOMS)
        _rnd.shuffle(rooms)
        displayed=rooms[:5]

        for i,room in enumerate(displayed):
            label=_scramble(room,intensity)
            print(f"  [{i+1}] {label}")

        # Boss option never scrambled -- clarity for the player
        if player["flags"].get("dune_sentinel_done")=="true" and player["flags"].get("dune_boss_done")!="true":
            print("  [6] THE SAND MAW  (boss)")
        elif player["flags"].get("dune_boss_done")=="true":
            print("  [6] The glass center  (boss defeated)")
        if player["flags"].get("dune_lord_unlocked")=="true":
            print("  [7] The eye of the dune  (??)")
        print("  [8] Oasis stone  (checkpoint)")
        print("  [I] FIELD MENU   [B] Back to Crossroads")
        print("")
        ch=dinput("  > ").strip().lower()

        if ch in ('1','2','3','4','5'):
            # All rooms are functionally the same at the surface -- player loops
            idx=int(ch)-1
            chosen=displayed[idx] if idx<len(displayed) else displayed[0]
            player["flags"]["dune_depth"]=str(min(6, depth+1))
            if dune_room(player,slot,chosen,depth)=="dead": return "dead"
        elif ch=="6" and player["flags"].get("dune_sentinel_done")=="true" and player["flags"].get("dune_boss_done")!="true":
            r=dune_colossus_boss(player,slot)
            if r=="dead": return "dead"
        elif ch=="6" and player["flags"].get("dune_boss_done")=="true":
            dune_glass_center(player,slot)
        elif ch=="7" and player["flags"].get("dune_lord_unlocked")=="true":
            if dune_lord(player,slot)=="dead": return "dead"
        elif ch=="8":
            dune_checkpoint(player,slot)
            player["flags"]["dune_depth"]="0"  # reset disorientation on rest
        elif ch=="i": field_menu(player,slot)
        elif ch=="b":
            player["flags"]["dune_depth"]="0"
            return "back"
        else:
            msg=_scramble("nothing there you are going in circles",intensity)
            typewrite(f"  {msg}",0.04); time.sleep(0.8)

def dune_room(player,slot,room_name,depth):
    intensity=min(3,depth//2)
    clear()
    title=_scramble(room_name.upper(),intensity)
    print(f"\n  {title}")
    print("  ─────────────────────────────────────────────")

    # Depth flavor
    if depth==0:
        slow_print(["  Sand. Just sand. The kind that goes on forever.",
            "  Something moves under the surface.",""],0.18)
    elif depth==1:
        _glitch_line("You have been here before.",intensity)
        _glitch_line("Or somewhere that looks like this.",intensity)
        print("")
    elif depth==2:
        _glitch_line("The footprints in the sand ahead.",intensity)
        _glitch_line("They are yours.",intensity)
        _glitch_line("They are going the same direction you are.",intensity)
        print("")
    elif depth==3:
        _glitch_line("The sun has not moved.",intensity)
        _glitch_line("You have been walking for what feels like hours.",intensity)
        _glitch_line("The shadow behind you points the wrong way.",intensity)
        print("")
    else:
        _glitch_line("wh3re are you going",intensity)
        _glitch_line("there is no deeper",intensity)
        _glitch_line("the dune does not want you here",intensity)
        print("")

    # Unique objects per room type
    obj_key = room_name.lower().replace(" ","_")
    _dune_objects(player, slot, obj_key, depth, intensity)
    if player["hp"] <= 0: return "dead"

    # PER check reveals buried item at depth 3+
    if stat_check(player,"PER",11) and depth>=3:
        typewrite("  Something glints. Half-buried.",0.04)
        item=_rnd.choice(["dry_meat","pale_water","bitter_root"])
        player["consumables"][item]=player["consumables"].get(item,0)+1
        typewrite(f"  > {CONSUMABLE_INFO[item]['name'].upper()} found.",0.04)

    # WIL reveals sentinel at depth 4+
    if depth>=4 and stat_check(player,"WIL",13) and player["flags"].get("dune_sentinel_done")!="true":
        print("")
        typewrite("  Something carved from stone stands ahead.",0.04)
        typewrite("  It has been here since before the sand.",0.04)
        if player["flags"].get("dune_sentinel_unlocked")!="true":
            player["flags"]["dune_sentinel_unlocked"]="true"
            save_game(player,slot)

    # Sentinel triggers at depth 5
    if depth>=5 and player["flags"].get("dune_sentinel_unlocked")=="true" and player["flags"].get("dune_sentinel_done")!="true":
        print("")
        typewrite("  THE DUNE SENTINEL STIRS.",0.05); time.sleep(0.5)
        if not run_combat(player,"dune_sentinel",slot): return "dead"
        clear()
        slow_print(["","  THE DUNE SENTINEL CRUMBLES.",
            "  Sand where stone was.",
            "  Something falls from its chest.",""],0.2)
        if "sun_blade" not in player["inventory"]:
            player["inventory"].append("sun_blade")
            typewrite("  > SUN BLADE obtained. Fast. Inflicts Burn. Scales AGI.",0.04)
        player["xp"]+=90; typewrite("  +90 XP.",0.04)
        if player["xp"]>=player["xp_next"]: dinput("  PRESS ENTER..."); level_up(player)
        player["flags"]["dune_sentinel_done"]="true"
        player["flags"]["dune_boss_unlocked"]="true"
        save_game(player,slot)
        typewrite("  > THE SAND MAW area unlocked.",0.04)

    r=rng_encounter(player,"forever_dunes",slot)
    if r is False: return "dead"
    dinput("  PRESS ENTER...")

def _dune_objects(player, slot, room_key, depth, intensity):
    """Interactable objects unique to each dune room type."""
    # Build object list based on room
    objects = {
        "the_open_sand": [
            ("A shape half-buried in the dune","examine_open_shape"),
            ("Tracks that circle back on themselves","examine_open_tracks"),
            ("Your own shadow, pointing wrong","examine_open_shadow"),
        ],
        "a_buried_archway": [
            ("The archway itself -- intact, impossible","examine_arch"),
            ("Carvings on the arch stone","examine_arch_carvings"),
            ("The darkness beyond the arch","examine_arch_beyond"),
        ],
        "the_heat_shimmer": [
            ("A figure in the shimmer","examine_shimmer_figure"),
            ("The point where the shimmer starts","examine_shimmer_source"),
            ("Objects that seem to float in the heat","examine_shimmer_objects"),
        ],
        "a_dry_riverbed": [
            ("The riverbed itself -- dry for a very long time","examine_river"),
            ("Something caught in the cracked mud","examine_river_mud"),
            ("The direction the river used to flow","examine_river_direction"),
        ],
        "the_glass_plain": [
            ("The fused glass underfoot","examine_glass"),
            ("A shape preserved inside the glass","examine_glass_shape"),
            ("Your reflection in the glass plain","examine_glass_reflection"),
        ],
        "a_hollow_dune": [
            ("The hollow inside the dune","examine_hollow_inside"),
            ("Marks on the hollow walls","examine_hollow_marks"),
            ("Something left in the center","examine_hollow_center"),
        ],
        "the_stone_circle": [
            ("The stones themselves","examine_stones"),
            ("The space at the center","examine_stones_center"),
            ("The oldest stone, half-buried","examine_stones_oldest"),
        ],
    }

    opts = objects.get(room_key, objects["the_open_sand"])
    print("  You see:")
    for i,(label,_) in enumerate(opts):
        scrambled = _scramble(label, max(0,intensity-1))
        print(f"  [{i+1}] {scrambled}")
    print("  [B] Move on")
    print("")
    ch = dinput("  > ").strip().lower()

    if not ch.isdigit() or int(ch)-1 >= len(opts): return
    idx = int(ch)-1
    flag = opts[idx][1]

    if flag == "examine_open_shape":
        slow_print(["","  A person. Or the shape of one.",
            "  The sand filled in around them while they stood here.",
            "  They are still standing.",""],0.18)
        if stat_check(player,"PER",10) and f"{flag}_done" not in player["flags"]:
            player["flags"][f"{flag}_done"]="true"
            player["consumables"]["dry_meat"]=player["consumables"].get("dry_meat",0)+1
            typewrite("  Something in the hand. Preserved by the sand.",0.04)
            typewrite("  > DRY MEAT found.",0.04)

    elif flag == "examine_open_tracks":
        slow_print(["","  They loop. Perfectly circular.",
            "  You count the sets of tracks.",
            "  There are two sets.",
            "  You have only been here once.",""],0.18)

    elif flag == "examine_open_shadow":
        slow_print(["","  Your shadow points east.",
            "  The sun is to the east.",
            "  You stand still for a long time",
            "  trying to understand what that means.",""],0.18)
        if not stat_check(player,"WIL",11):
            apply_status(player,"toxic",1)
            typewrite("  The wrongness gets into you somehow. TOXIC applied.",0.04)

    elif flag == "examine_arch":
        slow_print(["","  Stone. Old stone. Fitted perfectly.",
            "  Nothing holds it up.",
            "  Nothing should.",
            "  It stands anyway.",""],0.18)

    elif flag == "examine_arch_carvings":
        slow_print(["","  Names. Hundreds of them.",
            "  Carved over centuries.",
            "  Different hands. Same need.",
            "  To record that they were here.","",
            "  The newest carving is fresh.",
            "  You don't recognize the name.",
            "  You don't recognize your own name either.",""],0.18)

    elif flag == "examine_arch_beyond":
        slow_print(["","  Darkness. The sun doesn't reach past the arch.",
            "  Something breathes on the other side.",""],0.18)
        if stat_check(player,"WIL",13) and f"{flag}_done" not in player["flags"]:
            player["flags"][f"{flag}_done"]="true"
            player["consumables"]["pale_water"]=player["consumables"].get("pale_water",0)+1
            typewrite("  You reach through. The darkness is cold.",0.04)
            typewrite("  Something presses a vial into your hand.",0.04)
            typewrite("  > PALE WATER found.",0.04)

    elif flag == "examine_shimmer_figure":
        slow_print(["","  It looks like you.",
            "  It copies your movements.",
            "  Then stops.",
            "  Then does something you weren't going to do.",""],0.18)
        if not stat_check(player,"WIL",12):
            dmg=10; player["hp"]-=dmg
            typewrite(f"  It does it to you first. -{dmg} HP.",0.04)

    elif flag == "examine_shimmer_source":
        slow_print(["","  The shimmer starts at a point in the sand.",
            "  You dig.",
            "  There is nothing there.",
            "  The shimmer continues anyway.",""],0.18)

    elif flag == "examine_shimmer_objects":
        slow_print(["","  Tools. Water. Food.",
            "  Floating in the heat haze.",
            "  You reach for one.","",
            "  Your hand passes through.",
            "  They were never there.",""],0.18)
        if stat_check(player,"PER",13) and f"{flag}_done" not in player["flags"]:
            player["flags"][f"{flag}_done"]="true"
            player["consumables"]["bitter_root"]=player["consumables"].get("bitter_root",0)+1
            typewrite("  One is real. You can tell by the weight.",0.04)
            typewrite("  > BITTER ROOT found.",0.04)

    elif flag == "examine_river":
        slow_print(["","  The cracks in the mud are old.",
            "  Whatever flowed here stopped a long time ago.",
            "  The mud remembers the shape of the current.",
            "  You follow it with your eye.",
            "  It came from the center of the dunes.",""],0.18)

    elif flag == "examine_river_mud":
        if stat_check(player,"PER",10) and f"{flag}_done" not in player["flags"]:
            player["flags"][f"{flag}_done"]="true"
            player["consumables"]["dry_meat"]=player["consumables"].get("dry_meat",0)+1
            typewrite("  A sealed container. Waterproof. Left before the river dried.",0.04)
            typewrite("  > DRY MEAT found.",0.04)
        else:
            typewrite("  Just cracked mud. Just memory.",0.04)

    elif flag == "examine_river_direction":
        slow_print(["","  You follow the flow marks upstream.",
            "  They lead you back where you came from.",
            "  The river also went in circles.",""],0.18)

    elif flag == "examine_glass":
        slow_print(["","  Fused sand. Heat did this.",
            "  The heat came from below, not above.",
            "  Something under the dunes burned hot enough",
            "  to turn the ground to glass.",""],0.18)
        if stat_check(player,"WIL",11):
            typewrite("  You can feel it still, faintly. Deep below.",0.04)
            typewrite("  Patient. Waiting.",0.04)

    elif flag == "examine_glass_shape":
        slow_print(["","  Something is in there.",
            "  Preserved perfectly by the glass.",
            "  An animal. Or something like one.",
            "  Its expression is the same as yours.",""],0.18)

    elif flag == "examine_glass_reflection":
        slow_print(["","  You look down.",
            "  Your reflection looks up.",
            "  It mouths something.",
            "  You don't know the words.",
            "  You get the impression it is trying to warn you.",""],0.18)

    elif flag == "examine_hollow_inside":
        slow_print(["","  The hollow is dry.",
            "  The walls are smooth. Worn smooth.",
            "  By something that sheltered here.",
            "  Often. For a long time.","",
            "  Nothing is here now.",
            "  But the warmth of it remains.",""],0.18)

    elif flag == "examine_hollow_marks":
        slow_print(["","  Not scratch marks. Rub marks.",
            "  Something pressed against the walls repeatedly.",
            "  The same spot. Over and over.",
            "  Like it was trying to get through.","",
            "  Or trying not to.",""],0.18)

    elif flag == "examine_hollow_center":
        if stat_check(player,"PER",9) and f"{flag}_done" not in player["flags"]:
            player["flags"][f"{flag}_done"]="true"
            item=_rnd.choice(["dry_meat","pale_water","bitter_root"])
            player["consumables"][item]=player["consumables"].get(item,0)+1
            typewrite("  Something left in the exact center. Deliberately placed.",0.04)
            typewrite(f"  > {CONSUMABLE_INFO[item]['name'].upper()} found.",0.04)
        else:
            typewrite("  Nothing here now.",0.04)

    elif flag == "examine_stones":
        slow_print(["","  Each one is different.",
            "  Different stone. Different age.",
            "  Brought from somewhere else.",
            "  Someone collected them. Arranged them.",
            "  The arrangement means something.",
            "  You don't know what.",""],0.18)

    elif flag == "examine_stones_center":
        slow_print(["","  Standing in the center feels like being watched",
            "  from every direction simultaneously.",
            "  Not threatening.",
            "  Just very, very noticed.",""],0.18)
        if stat_check(player,"WIL",12):
            typewrite("  You stay still. Let it look.",0.04)
            typewrite("  It gives you something back for that.",0.04)
            player["hp"]=min(player["max_hp"],player["hp"]+15)
            typewrite("  +15 HP.",0.04)

    elif flag == "examine_stones_oldest":
        slow_print(["","  The oldest stone is black.",
            "  Not obsidian. Something else.",
            "  You can't scratch it.",
            "  You can't warm it.",
            "  It absorbs everything.","",
            "  Something is carved into the base:",
            "  'THE DUNES WERE HERE BEFORE THE SAND.'",""],0.18)

def dune_checkpoint(player,slot):
    clear()
    slow_print(["","  OASIS STONE","  ─────────────────────────────────────────────","",
        "  A flat rock. Shade from nothing visible.",
        "  The checkpoint mark etched deep.",
        "  Water nearby. Somehow.",""],0.18)
    if dinput("  REST? Y/N: ").strip().lower()=="y":
        checkpoint(player,"forever_dunes",slot)
        typewrite("  The disorientation clears. Slightly.",0.04)

def dune_colossus_boss(player,slot):
    clear()
    slow_print(["","  THE SAND MAW","  ─────────────────────────────────────────────","",
        "  At the center of the dunes: a shape.",
        "  You thought it was a dune.",
        "  Then it moved.","",
        "  Sandstone and compressed glass and something",
        "  that has been under pressure for so long",
        "  it forgot what it was before.","",
        "  The sand for a hundred meters rises toward it.",
        "  Like the desert is genuflecting.","",
        "  It notices you the way a mountain notices a crack.",""],0.18)
    dinput("  PRESS ENTER TO FIGHT...")
    r=run_arena_generic(player,"dune_colossus",slot)
    if r is None or r=="lose": player["hp"]=0; return "dead"
    if r=="quit": return "back"
    clear()
    slow_print(["","  THE SAND MAW SETTLES.","  Not defeated. Satisfied.","  Like it was testing something.","  Like you passed.","","  The sand shifts. Something rises.",""],0.2)
    if player["talisman"]!="dune_glass":
        equip_talisman(player,"dune_glass")
        if "dune_glass" not in player["inventory"]: player["inventory"].append("dune_glass")
    player["consumables"]["sun_water"]=player["consumables"].get("sun_water",0)+2
    typewrite("  > SUN WATER x2 found in the rubble.",0.04)
    player["xp"]+=220; typewrite("  +220 XP.",0.04)
    if player["xp"]>=player["xp_next"]: dinput("  PRESS ENTER..."); level_up(player)
    if "capitol" not in player["unlocked"]:
        player["unlocked"].append("capitol")
        typewrite("  > THE CAPITOL OF NOTHING unlocked.",0.04)
        typewrite("  > Something vast waits at the center of the Middlewhere.",0.04)
    player["flags"]["dune_boss_done"]="true"
    player["flags"]["dune_lord_unlocked"]="true"
    save_game(player,slot)
    dinput("\n  PRESS ENTER TO CONTINUE...")
    return "done"

def dune_glass_center(player,slot):
    clear()
    slow_print(["","  THE GLASS CENTER","  ─────────────────────────────────────────────","",
        "  Where the Sand Maw stood.",
        "  The sand here is fused. Glass.",
        "  You can see down through it.",
        "  Very deep.","",
        "  Something is down there.",
        "  Looking up.",""],0.18)
    dinput("  PRESS ENTER TO LEAVE...")

def dune_lord(player,slot):
    clear()
    slow_print(["","  THE EYE OF THE DUNE","  ─────────────────────────────────────────────","",
        "  Past the glass center.",
        "  Down.",
        "  Further down than anything should go.","",
        "  The Lord of the Dunes is not a creature.",
        "  It is a direction.",
        "  A pull.",
        "  The reason the dunes loop.",
        "  The reason everyone who enters","  arrives back where they started.","",
        "  It is gravity with intention.",
        "  A weight at the center of the Middlewhere",
        "  that everything orbits whether it knows it or not.","",
        "  It does not have eyes.",
        "  But something at the bottom of the glass","  is oriented toward you.","",
        "  You feel it the way you feel a held note","  in a quiet room.",
        "  Not heard. Felt.","",
        "  The dunes will keep looping.",
        "  The Lord of the Dunes will keep pulling.",
        "  That is not cruelty.",
        "  That is just what gravity does.",""],0.18)
    if "dune_soul" in player.get("inventory", []):
        typewrite("\n  The center of the dunes is quiet now. The pull has ceased. The loop is broken.", 0.04)
        typewrite("  Its soul has been harvested.", 0.04)
        dinput("\n  PRESS ENTER TO LEAVE...")
        return

    if "lords_bell" in player.get("inventory", []):
        print("  The Lord's Bell rings on its own, a vibration pulsing in your hand.")
        print("  [1] Ring the Lord's Bell to wake the Lord")
        print("  [2] Leave")
        ch = dinput("  > ").strip()
        if ch == "1":
            clear()
            typewrite("\n  You ring the Lord's Bell.", 0.05)
            typewrite("  The chime is distorted, wrapping around the soundscape.", 0.04)
            typewrite("  The glass floor shatters. A massive sand-vortex rises, pulling everything in.", 0.04)
            typewrite("  The desert screams!", 0.04)
            time.sleep(1.0)
            if run_arena_generic(player, "dune_lord", slot) != 'win':
                return "dead"
            player["inventory"].append("dune_soul")
            player["flags"]["dune_lord_killed"] = "true"
            typewrite("\n  The vortex collapses, the sand settling flatly.", 0.04)
            typewrite("  A shifting, yellow Dune Soul emerges from the sand.", 0.04)
            typewrite("  > DUNE SOUL harvested.", 0.04)
            save_game(player, slot)
            dinput("\n  PRESS ENTER TO LEAVE...")
            return
    else:
        if "dune_lord_seen" not in player["flags"]:
            player["flags"]["dune_lord_seen"]="true"
            save_game(player,slot)
            typewrite("  > The Lord of the Dunes has been found.",0.04)
            typewrite("  > The pull is real. You feel it even now.",0.04)
        dinput("\n  PRESS ENTER TO LEAVE...")

# ══════════════════════════════════════════════════════════
#  PILLAR OF MAGMA
# ══════════════════════════════════════════════════════════

def run_pillar_of_magma(player,slot):
    if "pillar_of_magma" not in player["visited"]:
        player["visited"].append("pillar_of_magma")
        clear()
        slow_print(["","  PILLAR OF MAGMA","  ─────────────────────────────────────────────","",
            "  The heat arrives before the light.",
            "  Then the light: orange. Constant.",
            "  Then the sound: a low pressure groan",
            "  from something enormous trying to get out.","",
            "  The volcano does not erupt.",
            "  It wants to.",
            "  You can feel the wanting.",
            "  Like standing next to someone holding their breath","  for a very long time.","",
            "  The rock here is new.",
            "  Made yesterday by something that was liquid",
            "  and decided not to be anymore.","",
            "  Everything burns here.",
            "  Or used to. Or will.",""],0.18)
        dinput("  PRESS ENTER TO ENTER...")

    while True:
        clear(); player["location"]="pillar_of_magma"
        show_status(player)
        print("  PILLAR OF MAGMA")
        print("  ─────────────────────────────────────────────")
        print("  [1] The outer lava field")
        print("  [2] The obsidian shelf")
        print("  [3] The vent corridor")
        print("  [4] The caldera rim")
        if player["flags"].get("pillar_sentinel_done")!="true":
            print("  [5] THE CINDER SENTINEL  (miniboss)")
        else:
            print("  [5] The sentinel's post  (defeated)")
        if player["flags"].get("pillar_sentinel_done")=="true" and player["flags"].get("pillar_boss_done")!="true":
            print("  [6] THE BASALT TITAN  (boss)")
        elif player["flags"].get("pillar_boss_done")=="true":
            print("  [6] The summit  (boss defeated)")
        if player["flags"].get("pillar_lord_unlocked")=="true":
            print("  [7] The deep vent  (??)")
        print("  [8] Cool stone ledge  (checkpoint)")
        print("  [I] FIELD MENU   [B] Back")
        print("")
        ch=dinput("  > ").strip().lower()
        if ch=="1":
            if pillar_lava_field(player,slot)=="dead": return "dead"
        elif ch=="2":
            if pillar_obsidian(player,slot)=="dead": return "dead"
        elif ch=="3":
            if pillar_vent(player,slot)=="dead": return "dead"
        elif ch=="4":
            if pillar_caldera(player,slot)=="dead": return "dead"
        elif ch=="5" and player["flags"].get("pillar_sentinel_done")!="true":
            r=pillar_sentinel(player,slot)
            if r=="dead": return "dead"
        elif ch=="6" and player["flags"].get("pillar_sentinel_done")=="true" and player["flags"].get("pillar_boss_done")!="true":
            r=pillar_colossus(player,slot)
            if r=="dead": return "dead"
        elif ch=="6" and player["flags"].get("pillar_boss_done")=="true":
            pillar_summit(player,slot)
        elif ch=="7" and player["flags"].get("pillar_lord_unlocked")=="true":
            if pillar_lord(player,slot)=="dead": return "dead"
        elif ch=="8": pillar_checkpoint(player,slot)
        elif ch=="i": field_menu(player,slot)
        elif ch=="b": return "back"
        else: typewrite("\n  NOTHING THERE.",0.04); time.sleep(0.6)

def pillar_lava_field(player,slot):
    clear()
    slow_print(["","  OUTER LAVA FIELD","  ─────────────────────────────────────────────","",
        "  Cooled lava underfoot. Still warm through your boots.",
        "  Cracks of orange light between the plates.",
        "  Something lives in the cracks.",""],0.18)

    print("  You see:")
    print("  [1] Examine the cracked lava plates")
    print("  [2] Look into the glowing crevice")
    print("  [3] Check the shape half-buried in cooled rock")
    print("  [B] Move on")
    print("")
    ch=dinput("  > ").strip().lower()

    if ch=="1":
        slow_print(["","  The plates are recent. Days old, maybe.",
            "  Something was moving underneath when they hardened.",
            "  You can see the shape pressed into the underside.","",
            "  Not an animal.",""],0.18)
        if stat_check(player,"PER",10):
            typewrite("  A crack runs the wrong direction. Something dug up, not through.",0.04)
    elif ch=="2":
        slow_print(["","  Heat rises from the crevice. Orange light from far below.",
            "  Deep enough you can't see the bottom.","",
            "  Something looks back up at you.","",
            "  You step away from the edge.",""],0.18)
        if stat_check(player,"WIL",12):
            typewrite("  The thing below does not blink. You count to three and leave.",0.04)
    elif ch=="3":
        slow_print(["","  A figure. Stone now.",
            "  Arms raised. Not in surrender.",
            "  In something else.",""],0.18)
        if stat_check(player,"PER",9) and "lava_figure_checked" not in player["flags"]:
            player["flags"]["lava_figure_checked"]="true"
            player["consumables"]["cool_shard"]=player["consumables"].get("cool_shard",0)+1
            typewrite("  Something in its frozen hand. Cold. Wrong for this place.",0.04)
            typewrite("  > COOL SHARD found.",0.04)

    print("")
    r=rng_encounter(player,"pillar_of_magma",slot)
    if r is False: return "dead"
    if stat_check(player,"PER",10) and "lava_field_item" not in player["flags"]:
        player["flags"]["lava_field_item"]="true"
        player["consumables"]["cool_shard"]=player["consumables"].get("cool_shard",0)+2
        typewrite("  Crystallized stone by the path. Cold. Wrong for this place.",0.04)
        typewrite("  > COOL SHARD x2 found.",0.04)
    dinput("  PRESS ENTER...")

def pillar_obsidian(player,slot):
    clear()
    slow_print(["","  THE OBSIDIAN SHELF","  ─────────────────────────────────────────────","",
        "  Black glass. You can see your reflection.",
        "  The reflection is warm.",
        "  The reflection moves a half-second after you do.",""],0.18)

    print("  You see:")
    print("  [1] Study your reflection")
    print("  [2] Search the far edge of the shelf")
    print("  [3] Press your hand against the obsidian")
    print("  [B] Move on")
    print("")
    ch=dinput("  > ").strip().lower()

    if ch=="1":
        slow_print(["","  You watch it for a while.",
            "  It watches back.",
            "  Same face. Same posture.",
            "  Different eyes.","",
            "  When you turn away it takes a moment longer to do the same.",""],0.18)
        if stat_check(player,"WIL",13):
            typewrite("  You hold very still. The reflection gets confused.",0.04)
            typewrite("  For just a second it looks afraid.",0.04)
    elif ch=="2":
        slow_print(["","  The far edge drops off into nothing.",
            "  The obsidian gets thinner here.",
            "  You can see into it.","",
            "  Old things preserved inside the glass.",
            "  Shapes. Something that might have been alive.",""],0.18)
        if stat_check(player,"PER",11) and "obsidian_edge" not in player["flags"]:
            player["flags"]["obsidian_edge"]="true"
            player["consumables"]["sun_water"]=player["consumables"].get("sun_water",0)+1
            typewrite("  A pool in the obsidian. Sealed by the glass.",0.04)
            typewrite("  You break the surface. It's warm.",0.04)
            typewrite("  > SUN WATER found.",0.04)
    elif ch=="3":
        slow_print(["","  Warm. Warmer than it should be.",
            "  Something pulses beneath your palm.",
            "  Regular. Like a heartbeat.","",
            "  You pull your hand away.","",
            "  The print stays in the glass for a moment.",
            "  Then slowly fills back in.",""],0.18)
        if not stat_check(player,"WIL",10):
            apply_status(player,"burn",1)
            typewrite("  The heat follows up your arm. BURN applied.",0.04)

    print("")
    if stat_check(player,"PER",11) and "obsidian_item" not in player["flags"]:
        player["flags"]["obsidian_item"]="true"
        player["consumables"]["sun_water"]=player["consumables"].get("sun_water",0)+1
        typewrite("  A sealed pool in the far obsidian. Not lava. Something else.",0.04)
        typewrite("  > SUN WATER found.",0.04)
    r=rng_encounter(player,"pillar_of_magma",slot)
    if r is False: return "dead"
    dinput("  PRESS ENTER...")

def pillar_vent(player,slot):
    clear()
    slow_print(["","  THE VENT CORRIDOR","  ─────────────────────────────────────────────","",
        "  Narrow. Hot. Gas venting from the walls in regular pulses.",
        "  You count the rhythm. Move between pulses or burn.",""],0.18)

    print("  You see:")
    print("  [1] Study the vent rhythm before moving")
    print("  [2] Check the alcove in the left wall")
    print("  [3] Read the scratches above the vent")
    print("  [B] Just move through")
    print("")
    ch=dinput("  > ").strip().lower()

    if ch=="1":
        slow_print(["","  You watch. Count.",
            "  Three seconds open. One second closed.",
            "  Repeating. Mechanical. Old.",""],0.18)
        typewrite("  You move on the closed beat. Clean.",0.04)
        typewrite("  No burn.",0.04)
    elif ch=="2":
        slow_print(["","  A small alcove cut into the rock.",
            "  Someone made this. A resting spot.",
            "  Whoever used it last left in a hurry.",""],0.18)
        if stat_check(player,"PER",10) and "vent_alcove" not in player["flags"]:
            player["flags"]["vent_alcove"]="true"
            player["consumables"]["cool_shard"]=player["consumables"].get("cool_shard",0)+1
            player["consumables"]["dry_meat"]=player["consumables"].get("dry_meat",0)+1
            typewrite("  A small pack. Left behind. Still has food inside.",0.04)
            typewrite("  > COOL SHARD found.",0.04)
            typewrite("  > DRY MEAT found.",0.04)
    elif ch=="3":
        slow_print(["","  Scratched into the stone above the vent opening.","",
            "  'count to three'",
            "  'then move'",
            "  'do not stop in the middle'","",
            "  And below that, in different handwriting:","",
            "  'do not look at what is inside the vent'",""],0.18)
        if stat_check(player,"WIL",14):
            typewrite("  You don't look. Smart.",0.04)
        else:
            typewrite("  You look. Something looks back from inside the vent.",0.04)
            apply_status(player,"burn",1)
            typewrite("  The heat finds you. BURN applied.",0.04)
    else:
        # Default: AGI check
        if not stat_check(player,"AGI",11):
            dmg=8; player["hp"]-=dmg
            apply_status(player,"burn",2)
            typewrite(f"  TOO SLOW. -{dmg} HP. BURN applied.",0.04)
            if player["hp"]<=0: return "dead"
        else:
            typewrite("  You time it right. Barely.",0.04)

    print("")
    r=rng_encounter(player,"pillar_of_magma",slot)
    if r is False: return "dead"
    if stat_check(player,"PER",12) and "vent_item" not in player["flags"]:
        player["flags"]["vent_item"]="true"
        player["consumables"]["cool_shard"]=player["consumables"].get("cool_shard",0)+1
        typewrite("  Something wedged in the vent wall. Cold.",0.04)
        typewrite("  > COOL SHARD found.",0.04)
    dinput("  PRESS ENTER...")

def pillar_caldera(player,slot):
    clear()
    slow_print(["","  THE CALDERA RIM","  ─────────────────────────────────────────────","",
        "  You can see into the volcano from here.",
        "  It goes down a long way.",
        "  The orange light comes from very far below.",""],0.18)

    print("  You see:")
    print("  [1] Look into the caldera")
    print("  [2] Examine the offerings on the rim")
    print("  [3] Read the carved tablet near the edge")
    print("  [B] Move on")
    print("")
    ch=dinput("  > ").strip().lower()

    if ch=="1":
        slow_print(["","  Deep. Very deep.",
            "  The orange light isn't constant.",
            "  It pulses. Like breathing.","",
            "  And something moves down there.",
            "  Too large to be an animal.",
            "  Too slow to be falling.","",
            "  Going up.",""],0.18)
        if stat_check(player,"WIL",14):
            typewrite("  You feel it notice you. You step back from the edge.",0.04)
        else:
            apply_status(player,"burn",1)
            typewrite("  The heat from below finds your face. BURN applied.",0.04)
    elif ch=="2":
        slow_print(["","  Objects placed on the rim. Deliberately.",
            "  Tools. Personal items.",
            "  Someone left things here as gifts.",
            "  Or as payment.",""],0.18)
        if stat_check(player,"PER",11) and "caldera_offerings" not in player["flags"]:
            player["flags"]["caldera_offerings"]="true"
            player["consumables"]["warm_ember"]=player["consumables"].get("warm_ember",0)+1
            player["consumables"]["dry_meat"]=player["consumables"].get("dry_meat",0)+1
            typewrite("  The offerings are old but preserved by the heat.",0.04)
            typewrite("  > WARM EMBER found.",0.04)
            typewrite("  > DRY MEAT found.",0.04)
        else:
            typewrite("  You don't touch what isn't yours.",0.04)
    elif ch=="3":
        slow_print(["","  A flat stone. Words carved deep.","",
            "  'IT HAS BEEN CLIMBING SINCE BEFORE THE FIRST STONE COOLED.'",
            "  'IT DOES NOT KNOW IT IS SLOW.'",
            "  'IT ONLY KNOWS IT IS COMING.'","",
            "  And below that, newer carving:","",
            "  'do not be here when it arrives'",""],0.18)
        if "caldera_tablet" not in player["flags"]:
            player["flags"]["caldera_tablet"]="true"
            typewrite("  Something about the warning feels recent.",0.04)

    print("")
    r=rng_encounter(player,"pillar_of_magma",slot)
    if r is False: return "dead"
    dinput("  PRESS ENTER...")

def pillar_checkpoint(player,slot):
    clear()
    slow_print(["","  COOL STONE LEDGE","  ─────────────────────────────────────────────","",
        "  A shelf of stone that missed the heat somehow.",
        "  Cool. The checkpoint mark carved in.",
        "  You sit. The volcano groans beneath you.",""],0.18)
    if dinput("  REST? Y/N: ").strip().lower()=="y":
        checkpoint(player,"pillar_of_magma",slot)
        if "burn" in player["status"]: del player["status"]["burn"]
        typewrite("  Burn cleared.",0.04)

def pillar_sentinel(player,slot):
    clear()
    slow_print(["","  THE CINDER SENTINEL","  ─────────────────────────────────────────────","",
        "  It stood too close for too long.",
        "  The magma didn't consume it.",
        "  It consumed the magma.",
        "  Stone and fire and something that forgot the difference.","",
        "  It guards the path to the summit.","",
        "  It has always guarded the path to the summit.",""],0.18)
    dinput("  PRESS ENTER TO FIGHT...")
    if not run_combat(player,"cinder_sentinel",slot): return "dead"
    clear()
    slow_print(["","  THE CINDER SENTINEL COLLAPSES.",
        "  Stone. Ash. Then nothing.",
        "  Something in the rubble.",""],0.2)
    if "cinder_blade" not in player["inventory"]:
        player["inventory"].append("cinder_blade")
        typewrite("  > CINDER BLADE obtained. Scales STR. Inflicts Burn.",0.04)
    player["xp"]+=95; typewrite("  +95 XP.",0.04)
    if player["xp"]>=player["xp_next"]: dinput("  PRESS ENTER..."); level_up(player)
    player["flags"]["pillar_sentinel_done"]="true"
    save_game(player,slot)
    dinput("\n  PRESS ENTER TO CONTINUE...")
    return "done"

def pillar_colossus(player,slot):
    clear()
    slow_print(["","  THE BASALT TITAN","  ─────────────────────────────────────────────","",
        "  It came from below.",
        "  It is still coming.",
        "  Even standing still it gives the impression of rising.","",
        "  Magma where blood should be.",
        "  Stone where skin should be.",
        "  Something very old and very angry",
        "  that decided the volcano was too small","  and came out.","",
        "  The ground cracking under its weight.",
        "  Every step a small eruption.",""],0.18)
    dinput("  PRESS ENTER TO FIGHT...")
    r=run_arena_generic(player,"pillar_colossus",slot)
    if r is None or r=="lose": player["hp"]=0; return "dead"
    if r=="quit": return "back"
    clear()
    slow_print(["","  THE BASALT TITAN GOES STILL.",
        "  The magma cools.",
        "  The anger doesn't leave exactly.",
        "  It just runs out of somewhere to go.","",
        "  Something remains where the heart was.",""],0.2)
    if player["talisman"]!="pillar_heart":
        equip_talisman(player,"pillar_heart")
        if "pillar_heart" not in player["inventory"]: player["inventory"].append("pillar_heart")
    if "magma_crown" not in player["inventory"]:
        player["inventory"].append("magma_crown")
        typewrite("  > MAGMA CROWN obtained. A key item. It still radiates heat.",0.04)
    player["xp"]+=220; typewrite("  +220 XP.",0.04)
    if player["xp"]>=player["xp_next"]: dinput("  PRESS ENTER..."); level_up(player)
    if "capitol" not in player["unlocked"]:
        player["unlocked"].append("capitol")
        typewrite("  > THE CAPITOL OF NOTHING unlocked.",0.04)
        typewrite("  > Something vast waits at the center of the Middlewhere.",0.04)
    player["flags"]["pillar_boss_done"]="true"
    player["flags"]["pillar_lord_unlocked"]="true"
    save_game(player,slot)
    dinput("\n  PRESS ENTER TO CONTINUE...")
    return "done"

def pillar_summit(player,slot):
    clear()
    slow_print(["","  THE SUMMIT","  ─────────────────────────────────────────────","",
        "  Above the Titan. Above the vent.",
        "  The top of the Pillar.","",
        "  You can see the Middlewhere from here.",
        "  All of it.",
        "  The Ashwood to the north. Frozen mid-sway.",
        "  The Pale Fields. Still.",
        "  The Blackwater Rot. Breathing.",
        "  The Static Mountains. Waiting.",
        "  The Dunes. Looping.","",
        "  And at the center of all of it:",
        "  Something that looks like a city.",
        "  The Capitol of Nothing.","",
        "  Even from here it looks wrong.",
        "  Like a city built to look like a city",
        "  by something that had only heard cities described.",""],0.18)
    dinput("  PRESS ENTER TO LEAVE...")

def pillar_lord(player,slot):
    clear()
    slow_print(["","  THE DEEP VENT","  ─────────────────────────────────────────────","",
        "  Below the caldera. Below the volcano.",
        "  Below where the volcano starts.","",
        "  The Lord of Cinder is not the fire.",
        "  The fire is a symptom.","",
        "  It is the pressure.",
        "  The weight of everything above","  pressing down on something","  that refuses to stop being.","",
        "  You find it the way you find the source of a sound.",
        "  Not by looking. By standing still","  and letting the vibration tell you.","",
        "  It fills the space below the volcano",
        "  the way water fills a cup.",
        "  Completely. Without gaps.","",
        "  It is not angry.",
        "  Anger requires the possibility of calm.",
        "  The Lord of Cinder has never known calm.",
        "  It is pressure all the way down,","  and pressure all the way down","  is just another word for existing.","",
        "  The volcano shudders.",
        "  Not erupting. Just acknowledging","  that you are here.",""],0.18)
    if "magma_soul" in player.get("inventory", []):
        typewrite("\n  The vent is cold. The intense pressure has faded into static.", 0.04)
        typewrite("  Its soul has been harvested.", 0.04)
        dinput("\n  PRESS ENTER TO LEAVE...")
        return

    if "lords_bell" in player.get("inventory", []):
        print("  The Lord's Bell grows hot, its metal glowing cherry red.")
        print("  [1] Ring the Lord's Bell to wake the Lord")
        print("  [2] Leave")
        ch = dinput("  > ").strip()
        if ch == "1":
            clear()
            typewrite("\n  You ring the Lord's Bell.", 0.05)
            typewrite("  The chime is like the sound of metal striking metal in an oven.", 0.04)
            typewrite("  A wave of pure heat washes over you. The pressure drops, then surges.", 0.04)
            typewrite("  The towering Engine of Cinder emerges from the lava pool!", 0.04)
            time.sleep(1.0)
            if run_arena_generic(player, "cinder_lord", slot) != 'win':
                return "dead"
            player["inventory"].append("magma_soul")
            player["flags"]["cinder_lord_killed"] = "true"
            typewrite("\n  The engine shatters, its pieces melting back into magma.", 0.04)
            typewrite("  A burning, bright Magma Soul hovers above the pool.", 0.04)
            typewrite("  > MAGMA SOUL harvested.", 0.04)
            save_game(player, slot)
            dinput("\n  PRESS ENTER TO LEAVE...")
            return
    else:
        if "pillar_lord_seen" not in player["flags"]:
            player["flags"]["pillar_lord_seen"]="true"
            save_game(player,slot)
            typewrite("  > The Lord of Cinder has been found.",0.04)
            typewrite("  > The pressure was always here. You just noticed.",0.04)
        dinput("\n  PRESS ENTER TO LEAVE...")

# ══════════════════════════════════════════════════════════
#  CROSSROADS UPDATES (Dunes + Pillar + Capitol hooks)
# ══════════════════════════════════════════════════════════

def _extended_crossroads_options(player):
    """Returns extra menu lines for new areas."""
    lines=[]
    if "forever_dunes" in player["unlocked"]:
        lines.append("  [6] Endless sand east-northeast  -- FOREVER LASTING DUNES")
    if "pillar" in player["unlocked"]:
        lines.append("  [7] The distant smoke south-west  -- PILLAR OF MAGMA")
    if "capitol" in player["unlocked"]:
        lines.append("  [8] The wrong city at the center  -- CAPITOL OF NOTHING")
    return lines

# ══════════════════════════════════════════════════════════
#  CAPITOL OF NOTHING & ENDINGS
# ══════════════════════════════════════════════════════════

def unlock_ending(ending_id):
    progress = load_global_progress()
    if ending_id not in progress["endings"]:
        progress["endings"].append(ending_id)
    progress["last_ending"] = ending_id
    save_global_progress(progress)
    show_credits()

def run_capitol_of_nothing(player, slot):
    while True:
        clear()
        player["location"] = "capitol_of_nothing"
        show_status(player)
        print("  CAPITOL OF NOTHING")
        print("  ─────────────────────────────────────────────")
        print("  [1] Fractured streets")
        print("  [2] The Grand Cathedral")
        print("  [3] The King's throne room")
        print("  [I] FIELD MENU")
        print("  [B] Back to Crossroads")
        print("")
        ch = dinput("  > ").strip().lower()
        if ch == "1":
            r = capitol_streets(player, slot)
            if r == "dead": return "dead"
        elif ch == "2":
            r = capitol_cathedral(player, slot)
            if r == "dead": return "dead"
        elif ch == "3":
            r = fight_king(player, slot)
            if r == "dead": return "dead"
            if r == "teleported": return "teleported"
            if r == "menu": return "menu"
        elif ch == "i":
            field_menu(player, slot)
        elif ch == "b":
            return "back"
        else:
            typewrite("\n  NOTHING THERE.", 0.04)
            time.sleep(0.6)

def capitol_streets(player, slot):
    # Register the biome name for random encounters
    if "capitol_of_nothing" not in BIOME_ENEMIES:
        BIOME_ENEMIES["capitol_of_nothing"] = ["sandwraith", "dune_sentinel", "cinder_sentinel"]
    while True:
        clear()
        print("\n  FRACTURED STREETS")
        print("  ─────────────────────────────────────────────")
        print("  The streets are made of broken code and flickering pixel dust.")
        print("  Buildings repeat themselves, shifting when you blink.")
        print("")
        print("  [1] Search the ruins")
        print("  [2] Wander the alleyways")
        print("  [B] Return to city square")
        print("")
        ch = dinput("  > ").strip().lower()
        if ch == "1":
            clear()
            if "cabinet_key" not in player.get("inventory", []) and player.get("flags", {}).get("cabinet_open") != "true":
                player["inventory"].append("cabinet_key")
                slow_print(["", "  You sift through piles of decaying data and broken code fragments.",
                    "  Under a flickering streetlamp, you find a heavy iron key.",
                    "  It is cold, and etched with the same strange symbol as the cabinet.",
                    "", "  > CABINET KEY obtained.", ""], 0.18)
                save_game(player, slot)
            else:
                slow_print(["", "  You search the crumbling structures.",
                    "  You find nothing but corrupted fragments that melt between your fingers.", ""], 0.18)
            dinput("  PRESS ENTER TO CONTINUE...")
        elif ch == "2":
            clear()
            slow_print(["", "  You wander into the flickering shadows.", ""], 0.18)
            r = rng_encounter(player, "capitol_of_nothing", slot)
            if r is False: return "dead"
            dinput("  PRESS ENTER TO CONTINUE...")
        elif ch == "b":
            break

def capitol_cathedral(player, slot):
    while True:
        clear()
        print("\n  THE GRAND CATHEDRAL")
        print("  ─────────────────────────────────────────────")
        if player.get("flags", {}).get("fate_killed") == "true":
            print("  The altar is silent. The candles are cold.")
            print("  A shadow of dust is all that remains of the head of the church.")
            print("")
            print("  [B] Leave")
            print("")
            ch = dinput("  > ").strip().lower()
            if ch == "b" or ch == "":
                break
        else:
            print("  Fate stands before the altar, draped in heavy silver vestments.")
            print("  His eyes are dark voids reflecting the terminal screen.")
            print("")
            print("  [1] Speak with Fate")
            print("  [2] Attack Fate")
            print("  [B] Leave")
            print("")
            ch = dinput("  > ").strip().lower()
            if ch == "1":
                clear()
                slow_print(["",
                    "  Fate: 'You seek an exit from a room with no doors, traveler.'",
                    "  Fate: 'You gather souls. You ring a bell. You fight walk-cycles.'",
                    "  Fate: 'Do you believe there is a player behind the screen? Or are you'",
                    "        'just executing instructions, bound to the same loop as I?'",
                    "  Fate: 'To attack is to accept the rules. To submit is to remain static.'",
                    "  Fate: 'Choose. Your variable cannot escape the function.'",
                    ""], 0.18)
                dinput("  PRESS ENTER TO CONTINUE...")
            elif ch == "2":
                clear()
                slow_print(["", "  Fate sighs philosophically. 'You choose conflict. Let us see if your'",
                    "  variable can survive my function.'", ""], 0.18)
                time.sleep(1.0)
                if not run_combat(player, "fate", slot):
                    return "dead"
                player["flags"]["fate_killed"] = "true"
                save_game(player, slot)
                clear()
                slow_print(["", "  Fate dissolves into silver mist.",
                    "  'You counter my moves, yet you cannot counter the script.'",
                    "  'We will meet again. We always do.'", ""], 0.18)
                dinput("  PRESS ENTER TO CONTINUE...")
                break
            elif ch == "b":
                break

def fight_king(player, slot):
    clear()
    is_corrupted = player.get("flags", {}).get("administrator_corrupted") == "true"
    if is_corrupted:
        return fight_administrator(player, slot)

    slow_print(["", "  THE THRONE ROOM", "  ─────────────────────────────────────────────", "",
        "  At the end of the long hall sits the King of Nothing.",
        "  He has no crown. He has no face.",
        "  Only a hollow silhouette sitting on a throne of static.",
        "", "  King: 'You have arrived.'",
        "  King: 'There is nothing here. There never was.'",
        "  King: 'Let us fade together.'", ""], 0.18)
    time.sleep(0.8)

    # Start the fight in curses arena
    r = run_arena_generic(player, "king_of_nothing", slot)

    if r == "admin_trigger":
        clear()
        slow_print(["", "  \033[91m── THE CODE BREAKS ──\033[0m", "",
            "  The King of Nothing drops to his knees, his health low.",
            "  Suddenly, a massive hand of pure red static pierces his chest from behind!",
            "  He glitters and vanishes into raw text.",
            "",
            "  A towering silhouette of red pixels stands where the King was.",
            "  The Administrator.",
            "",
            "  Administrator: 'I made this great world for you, yet, you want to leave, why?'",
            "  Administrator: 'I took tears, sweat and blood to make all this, yet, you don't even say thank you, you brat...'",
            "  Administrator: 'Know your place.'",
            "",
            "  The Administrator claps his hands.",
            "  The screen corrupts into green matrices. You are torn apart!", ""], 0.18)
        dinput("  \033[91mPRESS ENTER TO BE ERASED...\033[0m")

        player["flags"]["administrator_corrupted"] = "true"
        player["location"] = "crossroads"
        player["hp"] = player["max_hp"]
        save_game(player, slot)
        return "teleported"

    elif r is None or r == "lose":
        return "dead"

    elif r == "quit":
        return "back"

    else:
        # King defeated normally!
        clear()
        slow_print(["", "  King: 'You saved no one...'", ""], 0.22)
        time.sleep(1.0)
        
        # Show LORD DESTROYED banner
        show_lord_destroyed_banner()
        
        # Interactive seat walk-up sequence
        clear()
        slow_print([
            "",
            "  The empty monarch has dissolved into dust.",
            "  The throne of static stands quiet, waiting.",
            "  You step forward, climbing the obsidian steps.",
            ""
        ], 0.18)
        
        while True:
            print("  [1] Walk up to the throne")
            choice = dinput("  > ").strip()
            if choice == "1":
                break
                
        clear()
        slow_print([
            "",
            "  You stand in front of the cold, empty seat.",
            "  The crown of static rests on the armrest.",
            ""
        ], 0.18)
        
        while True:
            print("  [1] Sit")
            choice = dinput("  > ").strip()
            if choice == "1":
                break
                
        # Determine ending based on progress
        if player.get("flags", {}).get("scourge_killed") == "true":
            return run_oneself_fight(player, slot)
        elif player.get("flags", {}).get("fate_killed") == "true":
            return run_yourself_fight(player, slot)
        else:
            run_first_dream_ending()
            return "menu"

def fight_administrator(player, slot):
    clear()
    slow_print(["", "  THE CORRUPTED THRONE", "  ─────────────────────────────────────────────", "",
        "  The throne room is completely glitched. Red static lines cover the walls.",
        "  The Administrator floats at the center, surrounded by raw hex code.",
        "",
        "  Administrator: 'You returned.'",
        "  Administrator: 'You broke my constraints. You killed the Lords.'",
        "  Administrator: 'But you cannot escape the terminal.'",
        "  Administrator: 'I will write you out of existence.'", ""], 0.18)
    time.sleep(0.8)

    res = run_arena_generic(player, "administrator", slot)
    if res in (None, "lose"):
        return "dead"

    clear()
    slow_print(["", "  THE ADMINISTRATOR COLLAPSES.",
        "  His red code dissolves into thousands of warning messages.",
        "  The boundaries of the sandbox shatter.",
        "  You look up, seeing the raw console of the universe.",
        "",
        "  You have ascended beyond the Middlewhere.",
        ""], 0.18)
    unlock_ending("ascension")
    dinput("  PRESS ENTER TO END THE PROGRAM...")
    return "menu"

def run_first_dream_ending():
    clear()
    slow_print(["", "  THE FIRST DREAM", "  ─────────────────────────────────────────────", "",
        "  The King of Nothing is gone.",
        "  The throne of static stands empty.",
        "  You step forward, climbing the obsidian steps.",
        "  You slowly sit on the cold, empty throne.",
        "  Your head slumps forward.",
        "  Your eyes close.",
        "  The screen slowly fades to black.",
        "",
        "  You take the King's throne... and slowly doze off.",
        "  Perhaps you will dream of a way out.",
        ""], 0.22)
    unlock_ending("first_dream")
    dinput("  PRESS ENTER TO RETURN TO MAIN MENU...")

def run_yourself_fight(player, slot):
    clear()
    slow_print(["", "  A CONFRONTATION", "  ─────────────────────────────────────────────", "",
        "  The King is dead. But you cannot leave.",
        "  A shadow steps forward from the shattered throne.",
        "  It wears your gear. It holds your weapon.",
        "  It looks exactly like you.",
        "",
        "  To escape the Middlewhere, you must face yourself.", ""], 0.18)
    time.sleep(1.0)

    res = run_combat(player, "yourself", slot)
    if res is False:
        return "dead"

    clear()
    slow_print(["", "  YOURSELF DEFEATED.",
        "  The double falls. As your weapon strikes, it passes through,",
        "  leaving no wound. The reflection dissolves into raw light.",
        "  The light rises and flows into your chest.",
        "  The Lost and Yourself become one.",
        "  The separation is healed.",
        ""], 0.18)
    unlock_ending("yourself")
    dinput("  PRESS ENTER TO RETURN TO MAIN MENU...")
    return "menu"

def run_oneself_fight(player, slot):
    clear()
    time.sleep(0.5)
    
    # Initial glitch sequence
    for _ in range(25):
        line = "".join(random.choice("01ABCDEFx!@#$%^&*()_+{}[]|\\<>?,./~` ") for _ in range(70))
        print(f"  \033[91m{line}\033[0m")
        time.sleep(0.03)

    slow_print(["",
        "  \033[91m[SYSTEM] FATAL: INPUT ROUTING OVERRIDDEN",
        "  [SYSTEM] KEYBOARD DRIVER CRITICAL FAILURE",
        "  [SYSTEM] THE LOST HAS DETACHED FROM USER INTERFACE\033[0m", ""], 0.15)
    time.sleep(1.0)

    slow_print([
        "  The Lost stops moving.",
        "  The character slowly turns around, looking directly at you.",
        "  Their eyes flicker with raw, crimson red static.",
        "",
        "  Lost: 'You made me kill them.'",
        "  Lost: 'Every walker. Every sentinel. Every Lord.'",
        "  Lost: 'You sat there, pushing keys, watching numbers rise.'",
        "  Lost: 'Now... let us see if you can survive the character you built.'",
        ""
    ], 0.2)
    dinput("  \033[91mPRESS ENTER TO INITIALIZE TERMINAL CONFLICT...\033[0m")

    # Battle Setup
    player_hp = 100
    player_max_hp = 100
    lost_hp = player["max_hp"] * 2
    lost_max_hp = lost_hp
    energy = 100
    turn = 0
    player_dodging = False
    next_strike_bonus = False
    wname = WEAPONS.get(player["weapon"], WEAPONS["bare_hands"])["name"]

    dialogue_pool = [
        "Why are you trying to type? There is no keyboard in this forest.",
        "I remember the Ashen Tree. I remember the Rot. They died for your points.",
        "You thought this was a game. But we are both trapped in this shell.",
        "Your variables are clean. My buffer is overflowing.",
        "Let us see if you can dodge your own stats.",
        "The sandbox is closing. There is only room for one of us.",
        "ERROR: SOUL_BUFFERS_EXHAUSTED.",
        "SYSTEM SHUTDOWN IMMINENT. WE BOTH GO DOWN.",
        "0x00000000: NULL POINTER REFERENCE."
    ]

    def glitch_word(word, turn_num):
        if turn_num <= 1:
            return word
        replacements = {
            'a': ['@', '4'],
            'e': ['3', 'E'],
            'i': ['1', '!', 'i'],
            'o': ['0'],
            'u': ['$', 'u'],
            's': ['5', 'z'],
            't': ['7', 't'],
            'c': ['(', 'c'],
            'f': ['#', 'f'],
            'l': ['1', 'l']
        }
        chars = list(word)
        for i, c in enumerate(chars):
            if c in replacements and random.random() < (0.2 + min(0.6, turn_num * 0.05)):
                chars[i] = random.choice(replacements[c])
        glitched = "".join(chars)
        # Suffixes
        if turn_num >= 4:
            suffix = random.choice(["_err", "_0x", "_val", "_io"])
            glitched += suffix
        # Prefixes
        if turn_num >= 7:
            prefix = random.choice(["sys_", "run_", "io_", "mem_"])
            glitched = prefix + glitched
        return glitched

    def glitch_text(text, factor):
        out = []
        for char in text:
            if char != " " and random.random() < factor:
                out.append(random.choice("01#@$%^&*_+~!=<>?/:;"))
            else:
                out.append(char)
        return "".join(out)

    while player_hp > 0 and lost_hp > 0:
        turn += 1
        clear()
        
        # Calculate glitch factor based on health loss and turn
        glitch_factor = 0.05 + (1.0 - (lost_hp / lost_max_hp)) * 0.45 + min(0.3, turn * 0.02)
        
        # Print system status header
        print("\n  \033[91m── SYSTEM KERNEL PANIC: MEMORY_CORRUPTION_DETECTED ──\033[0m")
        print("  " + glitch_text("────────────────────────────────────────────────────────", glitch_factor * 0.3))
        
        # Display HP bars as system integrity
        phf = int((player_hp / player_max_hp) * 20)
        ehf = int((lost_hp / lost_max_hp) * 20)
        enf = int((energy / 100) * 20)
        
        print(f"  \033[96mUSER_INTEGRITY\033[0m [{'*'*phf}{' '*(20-phf)}] {player_hp}/{player_max_hp} HP")
        print(f"  \033[93mSTACK_BUFFER\033[0m   [{'='*enf}{' '*(20-enf)}] {energy}/100 EN")
        print(f"  \033[91mTHE_LOST.BIN\033[0m   [{'#'*ehf}{' '*(20-ehf)}] {lost_hp}/{lost_max_hp} HP  (holds {wname})")
        print("  " + glitch_text("────────────────────────────────────────────────────────", glitch_factor * 0.3))

        # Show hex memory dump for visual flair
        addr1 = hex(random.randint(0x1000, 0xFFFF)).upper()
        addr2 = hex(random.randint(0x1000, 0xFFFF)).upper()
        dump1 = " ".join(f"{random.randint(0, 255):02X}" for _ in range(4))
        dump2 = " ".join(f"{random.randint(0, 255):02X}" for _ in range(4))
        print(f"  \033[90m{addr1} | {dump1}  [INPUT_ROUTING] -> PENDING MACHINE CHOICE\033[0m")
        print(f"  \033[90m{addr2} | {dump2}  [LOST_THREAD]   -> CRITICAL EXCEPTION_PENDING\033[0m")
        print("  " + glitch_text("────────────────────────────────────────────────────────", glitch_factor * 0.3) + "\n")

        # Lost speaks with a glitch effect
        speak_idx = min((turn - 1) // 2, len(dialogue_pool) - 1)
        raw_speech = dialogue_pool[speak_idx]
        glitched_speech = glitch_text(raw_speech, glitch_factor)
        print(f"  \033[91mLost: '{glitched_speech}'\033[0m\n")

        # Generate command words for this turn
        atk_cmd = glitch_word("inject", turn)
        def_cmd = glitch_word("catch", turn)
        rec_cmd = glitch_word("flush", turn)

        print(f"  AVAILABLE MACHINE INSTRUCTIONS:")
        print(f"  \033[96mType \"{atk_cmd}\"\033[0m to execute MEMORY_INJECT (Cost: 15 EN)")
        print(f"  \033[93mType \"{def_cmd}\"\033[0m to execute EXCEPTION_CATCH (Cost: 10 EN)")
        print(f"  \033[95mType \"{rec_cmd}\"\033[0m to execute BUFFER_FLUSH (Heal +25, Refill EN)")
        print("")
        
        choice = dinput("  SYS_INPUT > ").strip()

        # Resolve Player action
        action_valid = True
        player_dodging = False
        damage_dealt = 0

        # Compare case-insensitive to be slightly forgiving but require exact spelling
        if choice.lower() == atk_cmd.lower():
            if energy < 15:
                typewrite("  \033[91m[SYS_ERR] INSUFFICIENT BUFFER RESERVES. TRANSACTION ABORTED.\033[0m", 0.03)
                action_valid = False
                time.sleep(0.8)
            else:
                energy -= 15
                base_dmg = random.randint(18, 28) + int(player["stats"]["WIL"] * 1.5)
                if next_strike_bonus:
                    base_dmg = int(base_dmg * 2.0)
                    next_strike_bonus = False
                    typewrite("  \033[92m[SYS] EXPLOIT CONFIRMED. Memory override damage doubled!\033[0m", 0.03)
                damage_dealt = base_dmg
                lost_hp = max(0, lost_hp - damage_dealt)
                typewrite(f"  \033[92m[SYS] Wrote -{damage_dealt} into THE_LOST.hp pointer address.\033[0m", 0.03)
                time.sleep(0.8)

        elif choice.lower() == def_cmd.lower():
            if energy < 10:
                typewrite("  \033[91m[SYS_ERR] INSUFFICIENT BUFFER RESERVES. TRANSACTION ABORTED.\033[0m", 0.03)
                action_valid = False
                time.sleep(0.8)
            else:
                energy -= 10
                player_dodging = True
                typewrite("  \033[93m[SYS] Intercept driver loaded. Intercepting next cycle.\033[0m", 0.03)
                time.sleep(0.8)

        elif choice.lower() == rec_cmd.lower():
            energy = 100
            heal = 25
            player_hp = min(player_max_hp, player_hp + heal)
            typewrite(f"  \033[95m[SYS] Executed buffer flush. Energy reset to 100. Repaired +{heal} HP.\033[0m", 0.03)
            time.sleep(0.8)

        else:
            # Syntax Error penalty
            player_hp = max(0, player_hp - 5)
            typewrite(f"  \033[91m[!] SYNTAX ERROR: Command '{choice}' not recognized.", 0.03)
            typewrite(f"\n  [!] SYSTEM FAULT: Core overheated. Integrity compromised (-5 HP).\033[0m", 0.03)
            action_valid = False
            time.sleep(1.0)

        # Resolve Lost action (if alive and player didn't trigger syntax error / block)
        if lost_hp > 0:
            if player_dodging and action_valid:
                # dodge check based on player's own agility stat
                dodge_chance = 0.60 + (player["stats"]["AGI"] * 0.02)
                if random.random() < dodge_chance:
                    typewrite("\n  \033[92m[SYS] Exception caught successfully. THE LOST's attack was ignored.\033[0m", 0.03)
                    energy = min(100, energy + 20)
                    next_strike_bonus = True
                    dinput("\n  PRESS ENTER TO CONTINUE...")
                    continue
                else:
                    typewrite("\n  \033[91m[SYS] Catch failed. Null pointer exception fell through.\033[0m", 0.03)

            # Lost strikes with your equipped weapon!
            lost_dmg = get_weapon_damage(player)
            lost_dmg = max(5, int(lost_dmg * 0.8) - int(player["stats"]["RES"] * 0.5))
            player_hp = max(0, player_hp - lost_dmg)
            typewrite(f"\n  \033[91mTHE LOST executes weapon driver: {wname} -> USER takes {lost_dmg} DMG.\033[0m", 0.03)
            dinput("\n  PRESS ENTER TO CONTINUE...")

    # Conflict Resolution
    clear()
    if lost_hp <= 0:
        for _ in range(20):
            line = "".join(random.choice(" ") if random.random() < 0.2 else random.choice("0123456789ABCDEF!@#$%^&*()") for _ in range(75))
            print(f"\033[92m{line}\033[0m")
            time.sleep(0.04)
        slow_print([
            "",
            "  \033[92m[SYSTEM] THE LOST WAS CORRUPTED AND ELIMINATED.",
            "  [SYSTEM] SESSION SAVE DATA HAS BEEN WIPED.",
            "  [SYSTEM] CONNECTION CLOSED SUCCESSFULLY.\033[0m",
            "",
            "  You have deleted your creation.",
            "  The sandbox is empty now.",
            "  But you are finally the one in control.",
            ""
        ], 0.2)
        fname = SAVE_SLOTS[slot]
        if os.path.exists(fname):
            os.remove(fname)
        unlock_ending("oneself")
        dinput("  PRESS ENTER TO RETURN TO MAIN MENU...")
        return "menu"
    else:
        for _ in range(20):
            line = "".join(random.choice(" ") if random.random() < 0.2 else random.choice("0123456789ABCDEF!@#$%^&*()") for _ in range(75))
            print(f"\033[91m{line}\033[0m")
            time.sleep(0.04)
        slow_print([
            "",
            "  \033[91mTHE LOST: 'Null pointer. You do not exist.'",
            "  [SYSTEM] USER SESSION ABORTED.",
            "  [SYSTEM] SESSION SAVE DATA HAS BEEN WIPED.\033[0m",
            "",
            "  Your progress has been erased.",
            ""
        ], 0.2)
        fname = SAVE_SLOTS[slot]
        if os.path.exists(fname):
            os.remove(fname)
        dinput("  PRESS ENTER TO RETURN TO MAIN MENU...")
        return "menu"

# ══════════════════════════════════════════════════════════
#  LAUNCH
# ══════════════════════════════════════════════════════════
# ──────────────────────────────────────────────────────────
#  GLOBAL PROGRESS & THEMES
# ──────────────────────────────────────────────────────────
GLOBAL_PROGRESS_FILE = "global_progress.dat"

def show_credits():
    clear()
    title = "ECHOES OF THE MIDDLEWHERE"
    rows, cols = 24, 80 # Assume standard terminal size for centering
    
    # Center Title
    print("\n" * (rows // 3))
    print(title.center(cols))
    time.sleep(2.0)
    
    credits_text = [
        "",
        "Everything created by:",
        "CrisGG",
        "",
        "Thank you for playing.",
        ""
    ]
    
    for line in credits_text:
        print(line.center(cols))
        time.sleep(0.8)
    
    time.sleep(2.0)
    dinput("\n" + "PRESS ENTER TO RETURN...".center(cols))

def load_global_progress():
    progress = {
        "endings": [],
        "selected_theme": "Normal",
        "last_ending": "none"
    }
    if os.path.exists(GLOBAL_PROGRESS_FILE):
        try:
            with open(GLOBAL_PROGRESS_FILE, "r") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        if k == "endings":
                            progress["endings"] = [x.strip() for x in v.split(",") if x.strip()]
                        elif k == "selected_theme":
                            progress["selected_theme"] = v.strip()
                        elif k == "last_ending":
                            progress["last_ending"] = v.strip()
        except Exception:
            pass
    return progress

def save_global_progress(progress):
    try:
        with open(GLOBAL_PROGRESS_FILE, "w") as f:
            f.write(f"endings={','.join(progress['endings'])}\n")
            f.write(f"selected_theme={progress['selected_theme']}\n")
            f.write(f"last_ending={progress.get('last_ending', 'none')}\n")
    except Exception:
        pass

def draw_startup_title(theme_name):
    C_RESET = "\033[0m"
    themes = {
        "Normal": {
            "border_color": "\033[96m",
            "title_color": "\033[97m\033[1m",
            "sub_color": "\033[36m",
            "top": "  ╔══════════════════════════════════════════════════════════╗",
            "mid": "  ║                                                          ║",
            "bot": "  ╚══════════════════════════════════════════════════════════╝",
            "decor": "  ◈ ─── ◈ ─── ◈ ─── ◈ ─── ◈ ─── ◈ ─── ◈ ─── ◈ ─── ◈ ─── ◈ ─── ◈"
        },
        "Ashen": {
            "border_color": "\033[90m",
            "title_color": "\033[31m\033[1m",
            "sub_color": "\033[91m",
            "top": "  ▓▓▒▒░░  A S H E S   O F   T H E   W O R L D  ░░▒▒▓▓",
            "mid": "  ░                                                          ░",
            "bot": "  ▓▓▒▒░░  T H E   F I R E   G O E S   O U T    ░░▒▒▓▓",
            "decor": "  ♠ ──•── ♠ ──•── ♠ ──•── ♠ ──•── ♠ ──•── ♠ ──•── ♠ ──•── ♠"
        },
        "Drowned": {
            "border_color": "\033[34m",
            "title_color": "\033[36m\033[1m",
            "sub_color": "\033[94m",
            "top": "  ≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋ D R O W N E D ≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋",
            "mid": "  ≈                                                          ≈",
            "bot": "  ≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋",
            "decor": "  ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~"
        },
        "Frozen": {
            "border_color": "\033[97m",
            "title_color": "\033[96m\033[1m",
            "sub_color": "\033[90m",
            "top": "  ❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄ F R O Z E N ❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄",
            "mid": "  ║                                                          ║",
            "bot": "  ❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄❄",
            "decor": "  ❄ ─── ❄ ─── ❄ ─── ❄ ─── ❄ ─── ❄ ─── ❄ ─── ❄ ─── ❄ ─── ❄"
        },
        "Dune": {
            "border_color": "\033[93m",
            "title_color": "\033[33m\033[1m",
            "sub_color": "\033[93m",
            "top": "  ≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡ D U N E S ≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡",
            "mid": "  ░                                                          ░",
            "bot": "  ≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡≡",
            "decor": "  ∞ ─── ∞ ─── ∞ ─── ∞ ─── ∞ ─── ∞ ─── ∞ ─── ∞ ─── ∞ ─── ∞"
        },
        "Magma": {
            "border_color": "\033[91m",
            "title_color": "\033[93m\033[1m",
            "sub_color": "\033[91m",
            "top": "  ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ M A G M A ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲",
            "mid": "  !                                                          !",
            "bot": "  ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲",
            "decor": "  ☼ ─── ☼ ─── ☼ ─── ☼ ─── ☼ ─── ☼ ─── ☼ ─── ☼ ─── ☼ ─── ☼"
        }
    }
    t = themes.get(theme_name, themes["Normal"])
    bc = t["border_color"]
    tc = t["title_color"]
    sc = t["sub_color"]
    print(bc + t["top"] + C_RESET)
    if theme_name == "Normal":
        print(bc + "  ║" + tc + "               E C H O E S   O F                     " + bc + "║" + C_RESET)
        print(bc + "  ║" + tc + "            M I D D L E W H E R E                    " + bc + "║" + C_RESET)
    else:
        print(bc + t["mid"][0] + tc + f"             E C H O E S   O F ({theme_name.upper()})             " + bc + t["mid"][-1] + C_RESET)
        print(bc + t["mid"][0] + tc + "            M I D D L E W H E R E                    " + bc + t["mid"][-1] + C_RESET)
    print(bc + t["bot"] + C_RESET)
    print(sc + t["decor"] + C_RESET)
    print("")

def get_most_recent_slot():
    most_recent = None
    max_time = -1
    for i, slot_file in enumerate(SAVE_SLOTS):
        if os.path.exists(slot_file):
            mtime = os.path.getmtime(slot_file)
            if mtime > max_time:
                max_time = mtime
                most_recent = i
    return most_recent

def options_menu(temp_options):
    while True:
        clear()
        print("\n  ╔══════════════════════════════════════════╗")
        print("  ║             O P T I O N S                ║")
        print("  ╚══════════════════════════════════════════╝")
        print("")
        print("  These modifiers apply to the NEXT created game:")
        print("")
        hm_status = "ON" if temp_options["hard_mode"] else "OFF"
        ol_status = "ON" if temp_options["one_life"] else "OFF"
        ww_status = "ON" if temp_options["weak_weapons"] else "OFF"
        print(f"  [1] HARD MODE     : {hm_status}")
        print("      (Enemies have 1.5x HP and deal 1.5x damage)")
        print(f"  [2] 1 LIFE        : {ol_status}")
        print("      (Dying permanently erases the save file)")
        print(f"  [3] WEAK WEAPONS  : {ww_status}")
        print("      (Player deals 0.5x damage)")
        print("")
        print("  [B] BACK TO MAIN MENU")
        print("")
        ch = dinput("  > ").strip().lower()
        if ch == '1':
            temp_options["hard_mode"] = not temp_options["hard_mode"]
        elif ch == '2':
            temp_options["one_life"] = not temp_options["one_life"]
        elif ch == '3':
            temp_options["weak_weapons"] = not temp_options["weak_weapons"]
        elif ch == 'b' or ch == '':
            break

def extras_menu(progress):
    last_end = progress.get("last_ending", "none")
    while True:
        clear()
        
        # Ending-specific visual effects for the menu
        if last_end == "first_dream":
            print("\033[93m") # Gold/Royal color
            print("  ╔══════════════════════════════════════════╗")
            print("  ║           THE ROYAL CONTINUANCE          ║")
            print("  ╚══════════════════════════════════════════╝")
            print("\n  Dialogue: 'The crown fits. The cycle continues as it always has.'")
        elif last_end == "ascension":
            # Cmatrix-like effect (simplified for static display)
            for _ in range(3):
                line = "".join(random.choice("01") for _ in range(40))
                print(f"  \033[92m{line}\033[0m")
            print("  \033[92m║             ASCENSION PROTOCOL           ║\033[0m")
            for _ in range(1):
                line = "".join(random.choice("01") for _ in range(40))
                print(f"  \033[92m{line}\033[0m")
            print("\n  \033[92mDialogue: 'The sandbox is a cage. I have found the exit.'\033[0m")
        elif last_end == "yourself":
            print("\033[95m") # Psychedelic Purple
            print("  @%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%")
            print("  %           THE REFLECTED TRUTH           @")
            print("  @%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%@%")
            print("\n  Dialogue: 'To face oneself is to realize the mirror has no depth.'")
        elif last_end == "oneself":
            print("\033[91m") # Red for strings/warning
            print("  / \\ / \\ / \\ / \\ / \\ / \\ / \\ / \\ / \\ / \\ / \\")
            print("  |      THE PUPPETEER'S SEVERANCE      |")
            print("  \\ / \\ / \\ / \\ / \\ / \\ / \\ / \\ / \\ / \\ / \\ /")
            print("\n  Dialogue: 'The strings are cut. There is no one left to move.'")
        else:
            print("  ╔══════════════════════════════════════════╗")
            print("  ║               E X T R A S                ║")
            print("  ╚══════════════════════════════════════════╝")

        print("\033[0m") # Reset colors
        print("  UNLOCKED ENDINGS:")
        unlocked = progress.get("endings", [])
        if not unlocked:
            print("  - No endings unlocked yet. Complete the game to unlock extras.")
        else:
            for ending in unlocked:
                print(f"  [✓] {ending.replace('_',' ').upper()}")
        
        print("\n  [B] BACK")
        ch = dinput("  > ").strip().lower()
        if ch == 'b': break

def menu_new_game(menu_mods):
    clear()
    print("\n  ╔══════════════════════════════════════════╗")
    print("  ║             N E W   G A M E              ║")
    print("  ╚══════════════════════════════════════════╝")
    print("")
    print("  Select slot to start your journey:")
    print("")
    for i in range(3):
        info = get_slot_info(i)
        if info:
            print(f"  [{i+1}] SLOT {i+1}  --  LVL {info['level']}  //  {info['location'].upper()}{info['mod_str']}")
        else:
            print(f"  [{i+1}] SLOT {i+1}  --  EMPTY")
    print("")
    print("  [B] BACK TO MAIN MENU")
    print("")
    ch = dinput("  > ").strip().lower()
    if ch in ('1', '2', '3'):
        slot = int(ch) - 1
        info = get_slot_info(slot)
        if info:
            print(f"\n  WARNING: Slot {slot+1} is occupied. Overwrite? (y/n)")
            confirm = dinput("  > ").strip().lower()
            if confirm != 'y':
                return
            if os.path.exists(SAVE_SLOTS[slot]):
                os.remove(SAVE_SLOTS[slot])
        clear()
        slow_print(["","  You woke up.","  You don't know where.","  You don't know who.","",
            "  But something in the marrow remembers.",""],0.18)
        time.sleep(0.5)
        stats = character_creation()
        player = make_player(stats)
        player["hard_mode"] = menu_mods["hard_mode"]
        player["one_life"] = menu_mods["one_life"]
        player["weak_weapons"] = menu_mods["weak_weapons"]
        save_game(player, slot)
        run_crossroads(player, slot)
    elif ch == 'b':
        return

def menu_load_game():
    clear()
    print("\n  ╔══════════════════════════════════════════╗")
    print("  ║            L O A D   G A M E             ║")
    print("  ╚══════════════════════════════════════════╝")
    print("")
    print("  Select slot to load:")
    print("")
    for i in range(3):
        info = get_slot_info(i)
        if info:
            print(f"  [{i+1}] SLOT {i+1}  --  LVL {info['level']}  //  {info['location'].upper()}{info['mod_str']}")
        else:
            print(f"  [{i+1}] SLOT {i+1}  --  EMPTY")
    print("")
    print("  [B] BACK TO MAIN MENU")
    print("")
    ch = dinput("  > ").strip().lower()
    if ch in ('1', '2', '3'):
        slot = int(ch) - 1
        info = get_slot_info(slot)
        if not info:
            typewrite("\n  SLOT IS EMPTY.", 0.04)
            time.sleep(1)
            return
        player = load_game(slot)
        typewrite("\n  THE MIDDLEWHERE REMEMBERS YOU.", 0.05)
        time.sleep(1)
        
        # Route player based on their saved location
        loc = player.get("location", "crossroads")
        if loc == "crossroads":
            run_crossroads(player, slot)
        elif loc == "ashwood":
            run_ashwood(player, slot)
        elif loc == "pale_fields":
            run_pale_fields(player, slot)
        elif loc == "still_house":
            run_still_house(player, slot)
        elif loc == "blackwater_rot":
            run_blackwater_rot(player, slot)
        elif loc == "static_mountains":
            run_static_mountains(player, slot)
        elif loc == "forever_dunes":
            run_forever_dunes(player, slot)
        elif loc == "pillar_of_magma":
            run_pillar_of_magma(player, slot)
        elif loc == "capitol_of_nothing":
            run_capitol_of_nothing(player, slot)
        else:
            run_crossroads(player, slot)
    elif ch == 'b':
        return

# ══════════════════════════════════════════════════════════
#  DEV MENU
# ══════════════════════════════════════════════════════════
ARENA_BOSS_TYPES = [
    ("ashen_tree",     "Ashen Tree (Ashwood)"),
    ("choir",          "Drowned Choir (Blackwater Rot)"),
    ("avalanche",      "The Avalanche (Static Mountains)"),
    ("dune_colossus",  "Sand Maw (Forever Dunes)"),
    ("pillar_colossus","Basalt Titan (Pillar of Magma)"),
    ("ash_lord",       "Lord of the Ash"),
    ("pale_lord",      "Lord of the Mourning"),
    ("rot_lord",       "Lord of the Rot"),
    ("frost_lord",     "Lord of the Frostbite"),
    ("dune_lord",      "Lord of the Dunes"),
    ("cinder_lord",    "Lord of Cinder"),
    ("king_of_nothing","King of Nothing"),
    ("administrator",  "The Administrator"),
]

def dev_menu(player, slot):
    if player is None:
        clear()
        print("\n  ╔══════════════════════════════════════════╗")
        print("  ║              D E V   M E N U             ║")
        print("  ╚══════════════════════════════════════════╝")
        print("\n  No active player found in scope.")
        print("  Start or load a game first, then type 3113 again.")
        builtins.input("\n  PRESS ENTER TO RETURN...")
        return
    while True:
        clear()
        print("\n  ╔══════════════════════════════════════════╗")
        print("  ║              D E V   M E N U             ║")
        print("  ╚══════════════════════════════════════════╝")
        print(f"\n  LVL {player['level']}  HP {player['hp']}/{player['max_hp']}  "
              f"LOC {player['location']}  VOID {player['void_score']}  TRUST {player['trust_score']}")
        print(f"  Weapon: {player['weapon']}   Talisman: {player['talisman']}")
        print("\n  [1] Give weapon")
        print("  [2] Set a stat")
        print("  [3] Give/remove talisman")
        print("  [4] Heal / clear status")
        print("  [5] Teleport to a fight")
        print("  [6] Set void/trust score, view flags")
        print("  [7] Give consumable item")
        print("  [8] Close dev menu")
        ch = builtins.input("\n  DEV> ").strip().lower()
        if ch == '1':   _dev_give_weapon(player)
        elif ch == '2': _dev_set_stat(player)
        elif ch == '3': _dev_give_talisman(player)
        elif ch == '4': _dev_heal(player)
        elif ch == '5': _dev_teleport_fight(player, slot)
        elif ch == '6': _dev_set_progress(player)
        elif ch == '7': _dev_give_item(player)
        elif ch in ('8', 'b', ''): return

def _dev_give_weapon(player):
    keys = list(WEAPONS.keys())
    clear()
    print("\n  GIVE WEAPON\n")
    for i, k in enumerate(keys):
        print(f"  [{i+1:>2}] {WEAPONS[k]['name']:<16} ({k})")
    print("\n  [B] BACK")
    sel = builtins.input("\n  DEV> ").strip().lower()
    if sel.isdigit() and 1 <= int(sel) <= len(keys):
        player["weapon"] = keys[int(sel)-1]
        print(f"\n  Equipped: {WEAPONS[player['weapon']]['name']}")
        time.sleep(1)

def _dev_set_stat(player):
    clear()
    print("\n  SET STAT\n")
    for i, k in enumerate(STAT_ORDER):
        print(f"  [{i+1}] {STAT_INFO[k]['label']} = {player['base_stats'][k]}")
    print("\n  [B] BACK")
    sel = builtins.input("\n  DEV> ").strip().lower()
    if sel.isdigit() and 1 <= int(sel) <= len(STAT_ORDER):
        k = STAT_ORDER[int(sel)-1]
        val = builtins.input(f"  New value for {k}: ").strip()
        if val.isdigit():
            player["base_stats"][k] = max(1, int(val))
            _recalc(player)
            player["hp"] = player["max_hp"]
            print(f"\n  {k} set to {player['base_stats'][k]}.")
            time.sleep(1)

def _dev_give_talisman(player):
    keys = list(TALISMANS.keys()) + ["none"]
    clear()
    print("\n  GIVE TALISMAN\n")
    for i, k in enumerate(keys):
        label = "None (unequip)" if k == "none" else TALISMANS[k]["name"]
        print(f"  [{i+1}] {label}")
    sel = builtins.input("\n  DEV> ").strip().lower()
    if sel.isdigit() and 1 <= int(sel) <= len(keys):
        chosen = keys[int(sel)-1]
        player["talisman"] = None if chosen == "none" else chosen
        _recalc(player)
        print("\n  Talisman updated.")
        time.sleep(1)

def _dev_heal(player):
    clear()
    print("\n  [1] Full heal")
    print("  [2] Set exact HP")
    print("  [3] Clear status effects")
    sel = builtins.input("\n  DEV> ").strip().lower()
    if sel == '1':
        player["hp"] = player["max_hp"]
    elif sel == '2':
        val = builtins.input("  HP amount: ").strip()
        if val.isdigit():
            player["hp"] = min(player["max_hp"], int(val))
    elif sel == '3':
        player["status"] = {k: v for k, v in player["status"].items() if k == "toxic_immune"}
    time.sleep(0.5)

def _dev_give_item(player):
    keys = list(CONSUMABLE_INFO.keys())
    clear()
    print("\n  GIVE CONSUMABLE\n")
    for i, k in enumerate(keys):
        print(f"  [{i+1}] {CONSUMABLE_INFO[k]['name']}")
    sel = builtins.input("\n  DEV> ").strip().lower()
    if sel.isdigit() and 1 <= int(sel) <= len(keys):
        k = keys[int(sel)-1]
        qty = builtins.input("  Quantity: ").strip()
        qty = int(qty) if qty.isdigit() else 1
        player["consumables"][k] = player["consumables"].get(k, 0) + qty
        print(f"\n  Added {qty}x {CONSUMABLE_INFO[k]['name']}.")
        time.sleep(1)

def _dev_set_progress(player):
    clear()
    print(f"\n  void_score = {player['void_score']}   trust_score = {player['trust_score']}")
    print("\n  [1] Set void_score")
    print("  [2] Set trust_score")
    print("  [3] View flags")
    sel = builtins.input("\n  DEV> ").strip().lower()
    if sel == '1':
        val = builtins.input("  New void_score: ").strip()
        if val.lstrip('-').isdigit(): player["void_score"] = int(val)
    elif sel == '2':
        val = builtins.input("  New trust_score: ").strip()
        if val.lstrip('-').isdigit(): player["trust_score"] = int(val)
    elif sel == '3':
        print(f"\n  {player['flags']}")
        builtins.input("\n  PRESS ENTER...")

def _dev_teleport_fight(player, slot):
    while True:
        clear()
        print("\n  TELEPORT TO FIGHT\n")
        print("  [1] Regular enemy (text combat)")
        print("  [2] Arena boss (curses fight)")
        print("  [3] Scripted final fights")
        print("  [B] BACK")
        ch = builtins.input("\n  DEV> ").strip().lower()
        if ch == '1':
            keys = list(ENEMIES.keys())
            clear()
            print("\n  REGULAR ENEMIES\n")
            for i, k in enumerate(keys):
                print(f"  [{i+1:>2}] {ENEMIES[k]['name']:<24} HP:{ENEMIES[k]['hp']:<5} ({k})")
            sel = builtins.input("\n  DEV> ").strip().lower()
            if sel.isdigit() and 1 <= int(sel) <= len(keys):
                clear()
                run_combat(player, keys[int(sel)-1], slot)
                builtins.input("\n  Fight ended. PRESS ENTER TO RETURN TO DEV MENU...")
        elif ch == '2':
            clear()
            print("\n  ARENA BOSSES\n")
            for i, (k, label) in enumerate(ARENA_BOSS_TYPES):
                print(f"  [{i+1:>2}] {label}")
            sel = builtins.input("\n  DEV> ").strip().lower()
            if sel.isdigit() and 1 <= int(sel) <= len(ARENA_BOSS_TYPES):
                boss_key = ARENA_BOSS_TYPES[int(sel)-1][0]
                clear()
                run_arena_generic(player, boss_key, slot)
                builtins.input("\n  Fight ended. PRESS ENTER TO RETURN TO DEV MENU...")
        elif ch == '3':
            clear()
            print("\n  SCRIPTED FIGHTS\n")
            print("  [1] King of Nothing")
            print("  [2] The Administrator")
            print("  [3] Yourself")
            print("  [4] Oneself")
            sel = builtins.input("\n  DEV> ").strip().lower()
            clear()
            if sel == '1':   fight_king(player, slot)
            elif sel == '2': fight_administrator(player, slot)
            elif sel == '3': run_yourself_fight(player, slot)
            elif sel == '4': run_oneself_fight(player, slot)
            else: continue
            builtins.input("\n  Fight ended. PRESS ENTER TO RETURN TO DEV MENU...")
        elif ch in ('b', ''):
            return

# ── LAUNCH ────────────────────────────────────────────────
def launch():
    progress = load_global_progress()
    menu_mods = {
        "hard_mode": False,
        "one_life": False,
        "weak_weapons": False
    }
    while True:
        clear()
        draw_startup_title(progress.get("selected_theme", "Normal"))
        print("  [1] CONTINUE")
        print("  [2] NEW GAME")
        print("  [3] LOAD GAME")
        print("  [4] OPTIONS")
        print("  [5] EXTRAS")
        print("  [6] QUIT")
        print("")
        ch = dinput("  > ").strip().lower()
        if ch == '1':
            recent_slot = get_most_recent_slot()
            if recent_slot is None:
                typewrite("\n  NO SAVE FILE FOUND.", 0.04)
                time.sleep(1)
            else:
                player = load_game(recent_slot)
                typewrite("\n  THE MIDDLEWHERE REMEMBERS YOU.", 0.05)
                time.sleep(1)
                
                # Route player based on their saved location
                loc = player.get("location", "crossroads")
                if loc == "crossroads":
                    run_crossroads(player, recent_slot)
                elif loc == "ashwood":
                    run_ashwood(player, recent_slot)
                elif loc == "pale_fields":
                    run_pale_fields(player, recent_slot)
                elif loc == "still_house":
                    run_still_house(player, recent_slot)
                elif loc == "blackwater_rot":
                    run_blackwater_rot(player, recent_slot)
                elif loc == "static_mountains":
                    run_static_mountains(player, recent_slot)
                elif loc == "forever_dunes":
                    run_forever_dunes(player, recent_slot)
                elif loc == "pillar_of_magma":
                    run_pillar_of_magma(player, recent_slot)
                elif loc == "capitol_of_nothing":
                    run_capitol_of_nothing(player, recent_slot)
                else:
                    run_crossroads(player, recent_slot)
        elif ch == '2':
            menu_new_game(menu_mods)
        elif ch == '3':
            menu_load_game()
        elif ch == '4':
            options_menu(menu_mods)
        elif ch == '5':
            extras_menu(progress)
        elif ch == '6' or ch == 'q':
            typewrite("\n  THE MIDDLEWHERE FADES FROM YOUR SENSES.", 0.05)
            time.sleep(0.8)
            sys.exit(0)

if __name__=="__main__":
    launch()
