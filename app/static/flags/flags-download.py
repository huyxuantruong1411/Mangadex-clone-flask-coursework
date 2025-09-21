import os
import requests

# Danh sách iso hợp lệ
VALID_ISO_ALPHA2 = set([
    "af","ax","al","dz","as","ad","ao","ai","aq","ag","ar","am","aw","au","at","az",
    "bs","bh","bd","bb","by","be","bz","bj","bm","bt","bo","bq","ba","bw","bv","br",
    "io","bn","bg","bf","bi","kh","cm","ca","cv","ky","cf","td","cl","cn","cx","cc",
    "co","km","cg","cd","ck","cr","ci","hr","cu","cw","cy","cz","dk","dj","dm","do",
    "ec","eg","sv","gq","er","ee","et","fk","fo","fj","fi","fr","gf","pf","tf","ga",
    "gm","ge","de","gh","gi","gr","gl","gd","gp","gu","gt","gg","gn","gw","gy","ht",
    "hm","va","hn","hk","hu","is","in","id","ir","iq","ie","im","il","it","jm","jp",
    "je","jo","kz","ke","ki","kp","kr","kw","kg","la","lv","lb","ls","lr","ly","li",
    "lt","lu","mo","mk","mg","mw","my","mv","ml","mt","mh","mq","mr","mu","yt","mx",
    "fm","md","mc","mn","me","ms","ma","mz","mm","na","nr","np","nl","nc","nz","ni",
    "ne","ng","nu","nf","mp","no","om","pk","pw","ps","pa","pg","py","pe","ph","pn",
    "pl","pt","pr","qa","re","ro","ru","rw","bl","sh","kn","lc","mf","pm","vc","ws",
    "sm","st","sa","sn","rs","sc","sl","sg","sx","sk","si","sb","so","za","gs","ss",
    "es","lk","sd","sr","sj","se","ch","sy","tw","tj","tz","th","tl","tg","tk","to",
    "tt","tn","tr","tm","tc","tv","ug","ua","ae","gb","us","uy","uz","vu","ve","vn",
    "vg","vi","wf","eh","ye","zm","zw"
])

# mapping langcode -> country ISO alpha-2
lang_to_country = {
    "tr": "tr",
    "hu": "hu",
    "de": "de",
    "es-la": "es",
    "eu": "es",
    "jv": "id",
    "ja-ro": "jp",
    "cs": "cz",
    "da": "dk",
    "sq": "al",
    "be": "by",
    "he": "il",
    "af": "za",
    "tl": "ph",
    "ka": "ge",
    "ko": "kr",
    "te": "in",
    "it": "it",
    "nl": "nl",
    "vi": "vn",
    "ta": "in",
    "zh-ro": "cn",
    "ro": "ro",
    "la": "la",  # 'la' là Latin, không là quốc gia → có thể bỏ
    "ca": "es",
    "mn": "mn",
    "bg": "bg",
    "uk": "ua",
    "zh": "cn",
    "en": "gb",
    "ar": "sa",
    "hr": "hr",
    "th": "th",
    "zh-hk": "hk",
    "bn": "bd",
    "el": "gr",
    "ur": "pk",
    "pl": "pl",
    "lt": "lt",
    "cv": "ru",
    "fr": "fr",
    "eo": "es",  # Esperanto → dùng Spain như fallback?
    "id": "id",
    "et": "ee",
    "pt": "pt",
    "my": "mm",
    "ga": "ie",
    "??": None,
    "az": "az",
    "kk": "kz",
    "ms": "my",
    "sl": "si",
    "ru": "ru",
    "ne": "np",
    "uz": "uz",
    "fa": "ir",
    "ja": "jp",
    "hi": "in",
    "sk": "sk",
    "pt-br": "br",
    "es": "es",
    "sv": "se",
    "no": "no",
    "sr": "rs",
    "ko-ro": "kr",
    "fi": "fi"
}

# Kích thước thử, theo flagcdn API
SIZE_VARIANTS = [
    "16x12",
    "32x24",
    "64x48",
    "w20",
    "w40",
    "w80"
]

output_dir = os.path.dirname(os.path.abspath(__file__))

for lang, country in lang_to_country.items():
    if country is None:
        print(f"⚠️ No mapping for lang '{lang}' — skipping.")
        continue

    iso = country.lower()
    if iso not in VALID_ISO_ALPHA2:
        print(f"⚠️ ISO code '{iso}' invalid or not in list — lang '{lang}'.")
        continue

    success = False
    for size in SIZE_VARIANTS:
        if "x" in size:
            url = f"https://flagcdn.com/{size}/{iso}.png"
        else:  # w20, w40, etc
            url = f"https://flagcdn.com/{size}/{iso}.png"

        filename = os.path.join(output_dir, f"{lang}.png")
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(r.content)
                print(f"✅ Tải thành công lang '{lang}' (iso '{iso}') với size '{size}' → {filename}")
                success = True
                break
            else:
                print(f"   ❌ {lang}: size '{size}' → {url} trả về status {r.status_code}")
        except Exception as e:
            print(f"   ❌ {lang}: lỗi với url {url}: {e}")
    if not success:
        print(f"❌ Không tìm được ảnh cho lang '{lang}' — thử hết size.")

