from PIL import Image, ImageDraw

W, H = 160, 50
im = Image.new("RGB", (W, H), (0, 0, 0))
d = ImageDraw.Draw(im)

# Farbpalette
black = (0, 0, 0)
outline = (24, 20, 28)
skin = (232, 174, 125)
skin_light = (255, 213, 166)
skin_shadow = (166, 94, 70)
blond = (238, 190, 65)
blond_light = (255, 220, 100)
brown = (112, 65, 40)
dark = (42, 34, 34)
blue = (45, 95, 180)
blue_light = (85, 145, 220)
red = (180, 40, 50)
red_light = (225, 75, 75)
green = (55, 115, 75)
green_light = (95, 155, 100)
white = (230, 230, 230)

def person(y, hair, hair_light, shirt, shirt_light, style):
    # Schulter- und Oberkörper-Silhouette
    d.polygon([
        (7, y+15), (11, y+12), (17, y+11),
        (35, y+11), (42, y+13), (47, y+15)
    ], fill=outline)
    d.rectangle((13, y+13, 40, y+15), fill=shirt)
    d.rectangle((19, y+12, 34, y+14), fill=shirt_light)

    # Hals
    d.rectangle((24, y+10, 30, y+13), fill=skin_shadow)
    d.rectangle((25, y+10, 29, y+12), fill=skin)

    # Ohren
    d.rectangle((14, y+5, 18, y+9), fill=skin_shadow)
    d.rectangle((36, y+5, 40, y+9), fill=skin_shadow)
    d.rectangle((15, y+6, 17, y+8), fill=skin)
    d.rectangle((37, y+6, 39, y+8), fill=skin)

    # Gesicht mit dunkler Kontur
    d.rectangle((17, y+3, 37, y+11), fill=outline)
    d.rectangle((18, y+3, 36, y+10), fill=skin)
    d.rectangle((20, y+9, 34, y+11), fill=skin_shadow)
    d.rectangle((20, y+4, 34, y+8), fill=skin)

    # Frisuren
    if style == "justus":
        # Helle, leicht wuschelige Haare
        d.rectangle((17, y+2, 37, y+5), fill=hair)
        d.rectangle((19, y+1, 35, y+2), fill=hair_light)
        d.rectangle((15, y+3, 19, y+7), fill=hair)
        d.rectangle((35, y+3, 39, y+6), fill=hair)
        d.rectangle((21, y+5, 25, y+5), fill=hair_light)
    elif style == "peter":
        # Kurze, dunkle Haare
        d.rectangle((17, y+2, 37, y+4), fill=hair)
        d.rectangle((19, y+1, 35, y+2), fill=hair)
        d.rectangle((16, y+3, 19, y+6), fill=hair)
        d.rectangle((36, y+3, 38, y+5), fill=hair)
        d.rectangle((22, y+2, 29, y+2), fill=hair_light)
    else:
        # Braune, etwas längere Haare
        d.rectangle((17, y+2, 37, y+4), fill=hair)
        d.rectangle((19, y+1, 35, y+2), fill=hair_light)
        d.rectangle((15, y+3, 19, y+9), fill=hair)
        d.rectangle((36, y+3, 39, y+9), fill=hair)
        d.rectangle((18, y+8, 20, y+10), fill=hair)

    # Augenbrauen, Augen, Nase und Mund
    d.rectangle((21, y+5, 25, y+5), fill=hair)
    d.rectangle((29, y+5, 33, y+5), fill=hair)
    d.rectangle((22, y+6, 24, y+7), fill=outline)
    d.rectangle((30, y+6, 32, y+7), fill=outline)
    d.point((23, y+6), fill=white)
    d.point((31, y+6), fill=white)
    d.rectangle((26, y+7, 27, y+9), fill=skin_shadow)
    d.rectangle((24, y+10, 30, y+10), fill=(105, 40, 40))

    # Lichtkante am Gesicht
    d.rectangle((19, y+5, 19, y+8), fill=skin_light)

    # Kleidungskragen
    d.polygon([(22, y+12), (27, y+14), (32, y+12)], fill=white)

person(0, blond, blond_light, blue, blue_light, "justus")
person(17, dark, (90, 75, 65), red, red_light, "peter")
person(34, brown, (155, 105, 65), green, green_light, "bob")

# Blacky als Pixel-Rabe
d.ellipse((116, 36, 143, 48), fill=outline)
d.ellipse((126, 31, 143, 43), fill=(35, 35, 45))
d.polygon([(140, 36), (153, 39), (140, 42)], fill=(220, 150, 35))
d.rectangle((136, 33, 139, 35), fill=(255, 230, 80))
d.point((138, 34), fill=black)
d.polygon([(120, 44), (115, 49), (130, 46)], fill=outline)
d.polygon([(132, 44), (140, 49), (138, 43)], fill=outline)

# ANSI-Farbpalette
palette = [
    (0,0,0),(128,0,0),(0,128,0),(128,128,0),
    (0,0,128),(128,0,128),(0,128,128),(192,192,192),
    (128,128,128),(255,0,0),(0,255,0),(255,255,0),
    (0,0,255),(255,0,255),(0,255,255),(255,255,255)
]

def nearest(rgb):
    return min(range(16), key=lambda i: sum((rgb[j]-palette[i][j])**2 for j in range(3)))

def fg(i):
    return 30+i if i < 8 else 90+i-8

def bg(i):
    return 40+i if i < 8 else 100+i-8

out = ["\x1b[2J\x1b[H"]

# Pixel-Art-Bereich links: 27 Terminalspalten
for cy in range(25):
    for x in range(54):
        top = nearest(im.getpixel((x, cy*2)))
        bottom = nearest(im.getpixel((x, cy*2+1)))

        if top == 0 and bottom == 0:
            out.append("\x1b[30;40m ")
        elif top == 0:
            out.append(f"\x1b[{fg(bottom)};{bg(0)}m\u2584")
        elif bottom == 0:
            out.append(f"\x1b[{fg(top)};{bg(0)}m\u2580")
        else:
            out.append(f"\x1b[{fg(top)};{bg(bottom)}m\u2580")

    out.append("\x1b[0m\r\n")

def text(row, col, value, color=37):
    out.append(f"\x1b[{row};{col}H\x1b[{color}m{value}\x1b[0m")

text(2, 32, "DIE DREI", 37)
text(2, 41, "???", 31)
text(2, 45, "FRAGEZEICHEN", 37)
text(4, 32, "F A L L - A R C H I V", 34)
text(6, 31, "="*48, 37)

text(9, 34, "[1]  HOERSPIELFAELLE", 31)
text(12, 34, "[2]  PERSONEN", 37)
text(14, 34, "[3]  SPRECHER", 37)
text(16, 34, "[4]  ORTE UND OBJEKTE", 37)
text(18, 34, "[5]  ORGANISATIONEN", 37)
text(20, 34, "[6]  SUCHE", 31)

text(22, 31, "-"*48, 37)
text(23, 31, "EIN ARCHIV FUER FREUNDE DER ???", 37)
text(25, 69, "BLACKY", 31)

out.append("\x1b[0m")

target = r"C:\DreiFragezeichenArchiv\Mystic\themes\default\text\archiv_start.ans"
with open(target, "wb") as f:
    f.write("".join(out).encode("cp437", errors="replace"))

print("Neue Pixel-Art-Grafik erstellt:", target)
