import tkinter as tk
import random
import re
from tkinter import font as tkFont
from tkinter import ttk
import sys, os
from pathlib import Path
from tkinter import messagebox

if sys.platform == "win32":
    import ctypes
    try:
        # Per-Monitor DPI Aware v2 (가장 선명)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            # Per-Monitor DPI Aware (대안)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                # System DPI Aware (최후 대안)
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

PUNCT_RE = re.compile(r'[,\-]')  # 쉼표/하이픈 무시용

def norm_token(s: str) -> str:
    """채점 및 정답 저장용: 쉼표/하이픈 제거."""
    return PUNCT_RE.sub('', s).strip()

def mask_len_keep_punct(tok: str) -> str:
    """모드1: 길이 힌트 O, 문장부호는 그대로."""
    return re.sub(r'[0-9A-Za-z가-힣]+', lambda m: '_' * len(m.group(0)), tok)

def mask_one_keep_punct(tok: str) -> str:
    """모드2/4: 길이 힌트 X, 문장부호는 그대로."""
    return re.sub(r'[0-9A-Za-z가-힣]+', '_', tok)

def parse_ref_parts(ref: str):
    """
    '(요 5:38-39)' -> ('요','5','38-39')
    항상 괄호로 들어온다고 가정.
    """
    s = ref.strip()[1:-1]  # 괄호 제거
    book, chap_verse = s.split()
    chap, verse = chap_verse.split(':', 1)
    return book, chap, verse

def split_verse_parts(verse: str):
    """
    '38-39' -> ('_-_', ['38','39'])
    '37,39' -> ('_,_', ['37','39'])
    '39'    -> ('_',   ['39'])
    """
    if '-' in verse:
        a, b = verse.split('-', 1)
        return '_-_', [a, b]
    if ',' in verse:
        parts = [p.strip() for p in verse.split(',') if p.strip()]
        # 파트 개수만큼 '_'와 ','를 섞어 마스크 문자열 생성 (예: '_,_,_' 등)
        mask = ','.join(['_'] * len(parts))
        return mask, parts
    return '_', [verse]

def ref_masked(ref: str, masked: bool) -> str:
    """
    masked=False: 원문 장절 그대로 (괄호 유지)
    masked=True : 책/장 가리고 절은 split 규칙에 맞춘 마스크, (괄호 유지)
                  예: (요 5:38-39) -> (_ _:_-_)
                      (요 5:37,39) -> (_ _:_,_)
                      (요 5:39)    -> (_ _:_)
    """
    book, chap, verse = parse_ref_parts(ref)
    if not masked:
        return f"({book} {chap}:{verse})"
    verse_mask, _ = split_verse_parts(verse)
    return f"(_ _:{verse_mask})"

# 문제를 생성하는 함수
def create_blank_problem(scripture, mode):
    global blank_num, whole_level_num
    reference, verse = scripture.split('^')
    words = verse.split()
    num_words = len(words)
    answers = []
    print(reference, verse, "\n")
    
    if mode == 1:
        num_words = len(words)
        num_blanks = int(num_words * max(blank_num, 0) * 0.1)
        num_blanks = max(0, min(num_blanks, num_words))
        blank_indices = sorted(random.sample(range(num_words), num_blanks)) if num_blanks else []

        # 정답은 문장부호 제거본으로 저장(중복 쉼표 방지)
        answers = [norm_token(words[i]) for i in blank_indices]

        # 화면은 길이 힌트 O + 문장부호 보존
        problem_words = [
            (mask_len_keep_punct(w) if i in blank_indices else w)
            for i, w in enumerate(words)
        ]

        # 장절 공개(괄호 유지)
        ref_view = ref_masked(reference, masked=False)
        problem_text = ref_view + " " + " ".join(problem_words)
        return problem_text, answers, reference

    elif mode == 2:
        # 정답은 문장부호 제거본으로 저장
        answers = [norm_token(w) for w in words]

        # 화면은 길이 힌트 X + 문장부호 보존
        problem_words = [mask_one_keep_punct(w) for w in words]

        ref_view = ref_masked(reference, masked=False)
        problem_text = ref_view + " " + " ".join(problem_words)
        return problem_text, answers, reference

    elif mode == 3:
        book, chap, verse = parse_ref_parts(reference)
        verse_mask, verse_parts = split_verse_parts(verse)

        # 장절은 마스크로, 본문은 공개
        ref_view = ref_masked(reference, masked=True)
        problem_text = ref_view + " " + " ".join(words)

        # 정답 순서: 책, 장, 절의 각 파트  (예: 38-39 -> ['38','39'])
        answers = [book, chap] + verse_parts
        return problem_text, answers, reference

    elif mode == 4:
        n = min(whole_level_num, len(words))
        rand_index = random.randint(0, len(words) - n)
        visible_words = words[rand_index:rand_index + n]

        first_occurrence = True
        problem_words = []
        i = 0
        while i < len(words):
            if first_occurrence and i <= len(words) - n and words[i:i+n] == visible_words:
                problem_words.extend(visible_words)    # 이 블록은 통째로 노출
                first_occurrence = False
                i += n
            else:
                problem_words.append(mask_one_keep_punct(words[i]))  # 힌트 X
                i += 1

        # 장절 마스킹
        book, chap, verse = parse_ref_parts(reference)
        verse_mask, verse_parts = split_verse_parts(verse)
        ref_view = ref_masked(reference, masked=True)

        problem_text = ref_view + " " + " ".join(problem_words)

        # 정답: 책, 장, 절 파트 + 가려진 단어들(문장부호 제거본)
        answers = [book, chap] + verse_parts

        i = 0
        while i < len(words):
            if i <= len(words) - n and words[i:i+n] == visible_words:
                i += n
            else:
                answers.append(norm_token(words[i]))   # 쉼표 없는 정답 저장
                i += 1

        return problem_text, answers, reference

def blank_level():
    blank_level_window = tk.Toplevel()
    blank_level_window.title("빈칸 난이도 선택")
    blank_level_window.focus_set()
    tk.Button(blank_level_window, text="0%", width=10, command=lambda : (level_num(-1), blank_level_window.destroy())).pack()
    for i in range(10):
        tk.Button(blank_level_window, text=str(i + 1)+"0%", width=10, command=lambda num=i: (level_num(num), blank_level_window.destroy())).pack()

def level_num(num):
    global blank_num
    blank_num = num + 1
    set_mode(1)
    
def whole_level():
    whole_level_window = tk.Toplevel()
    whole_level_window.title("어절 수 선택")
    whole_level_window.focus_set()
    tk.Button(whole_level_window, text="1어절", width=10, command=lambda : (whole_num(1), whole_level_window.destroy())).pack()
    for i in range(2, 5):
        tk.Button(whole_level_window, text=str(i) + "어절", width=10, command=lambda num=i: (whole_num(num), whole_level_window.destroy())).pack()    

def whole_num(num):
    global whole_level_num
    whole_level_num = num
    set_mode(4)

# 문제를 텍스트 박스에 표시
def display_problem(mode):
    global current_problem, current_answers, current_reference, attempts, problem_completed, scripture, problem_num
    if len(scripture)-1 == 0:
        problem_num = 0
    elif len(scripture)-1 < 0:
        return
    else:
        problem_num = random.randint(0, len(scripture)-1)
    current_problem, current_answers, current_reference = create_blank_problem(scripture[problem_num], mode)
    attempts = 0
    problem_completed = False
    problem_text_box.config(state=tk.NORMAL)
    problem_text_box.delete(1.0, tk.END)
    problem_text_box.insert(tk.END, current_problem)
    problem_text_box.config(state=tk.DISABLED)
    answer_text_box.delete(1.0, tk.END)

# 답안 제출 함수
def submit_answer(event=None):
    global attempts, problem_completed, scripture, problem_num, left_verse, fail_num, wrong_verses
    user_answer = answer_text_box.get(1.0, tk.END).strip()

    if left_verse:
        if problem_completed or not current_answers:
            # 완료/소진 시 다음 문제로 (기존 semantics 유지)
            try:
                scripture.pop(problem_num)
                left_verse -= 1
            except Exception:
                pass
            reload_texts()
            display_problem(current_mode)
            answer_text_box.delete(1.0, tk.END)
            return "break" if event else None

        # if user_answer == current_answers[0]:
        if norm_token(user_answer) == norm_token(current_answers[0]):
            replace_blank_with_answer(current_answers[0], 1)
            current_answers.pop(0)
            answer_text_box.delete(1.0, tk.END)
            attempts = 0
            if not current_answers:
                problem_completed = True
        else:
            attempts += 1
            answer_text_box.delete(1.0, tk.END)
            # 틀렸을 때 처리 부분에서 (attempts >= 3일 때)
            if attempts >= 3:
                try:
                    # 틀린 구절 저장
                    wrong_verse = {
                        'reference': current_reference,
                        'verse': scripture[problem_num].split('^')[1],
                        'full_text': scripture[problem_num]  # 전체 텍스트 저장
                    }
                except:
                    pass
                # 중복 방지 체크
                if not any(w['full_text'] == wrong_verse['full_text'] for w in wrong_verses):
                    wrong_verses.append(wrong_verse)
                
                replace_blank_with_answer(current_answers[0], 0)
                current_answers.pop(0)
                fail_num += 1
                reload_texts()
                attempts = 0
                if not current_answers:
                    problem_completed = True
    else:
        answer_text_box.delete(1.0, tk.END)

    return "break" if event else None 

# 틀린 구절 팝업
def show_wrong_verses():
    if not wrong_verses:
        messagebox.showinfo("알림", "틀린 구절이 없습니다.")
        return
    
    popup = tk.Toplevel(root)
    popup.title("틀린 구절 모음")
    popup.geometry("600x400")
    popup.grid_rowconfigure(0, weight=1)
    popup.grid_columnconfigure(0, weight=1)
    
    # 스크롤 가능한 텍스트 박스
    frame = tk.Frame(popup)
    frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    
    current_font = (font_style_var.get(), 25, 'bold' if bold_var.get() else 'normal')
    
    text_box = tk.Text(frame, wrap=tk.WORD, font=current_font)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text_box.yview)
    text_box.config(yscrollcommand=scrollbar.set)
    
    text_box.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    
    # 틀린 구절들 표시
    for i, wrong in enumerate(wrong_verses, 1):
        text_box.insert(tk.END, f"{i}. {wrong['reference']} {wrong['verse']}\n\n")
    
    text_box.config(state=tk.DISABLED)
    
    # 암송 리스트에 추가 버튼
    def add_to_memorization():
        global scripture, left_verse, fail_num, wrong_verses
        scripture = [w['full_text'] for w in wrong_verses]
        left_verse = len(scripture)
        fail_num = 0  # 틀린 갯수 초기화
        wrong_verses = []  # 틀린 구절 목록 초기화
        reload_texts()
        
        # 현재 보여주고 있는 문제 지우기
        problem_text_box.config(state=tk.NORMAL)
        problem_text_box.delete(1.0, tk.END)
        problem_text_box.config(state=tk.DISABLED)
        answer_text_box.delete(1.0, tk.END)
        
        popup.destroy()
        messagebox.showinfo("완료", f"틀린 구절들이 암송 리스트에 추가되었습니다.\n틀린 구절 목록이 초기화되었습니다.")
    
    button = tk.Button(popup, text="틀린 구절 복습하기", command=add_to_memorization)
    button.grid(row=1, column=0, pady=10)

# 빈칸을 정답으로 대체하는 함수
def replace_blank_with_answer(answer, correct):
    global current_problem
    try:
        test_index = current_problem.index('_')
    except ValueError:
        return

    current_problem = re.sub(r'(_+)', answer, current_problem, count=1)

    problem_text_box.config(state=tk.NORMAL)
    problem_text_box.delete(1.0, tk.END)

    problem_text_box.tag_configure("highlight", foreground=("green" if correct else "red"))
    problem_text_box.insert(tk.END, current_problem)

    start_index = f"1.0 + {test_index} chars"
    end_index   = f"1.0 + {test_index + len(answer)} chars"
    problem_text_box.tag_add("highlight", start_index, end_index)
    problem_text_box.config(state=tk.DISABLED)

# 모드 선택에 따라 문제를 표시하는 함수
def set_mode(mode):
    global current_mode
    current_mode = mode
    display_problem(mode)

def select_day(num):
    global day_num, scripture, left_verse
    if num == 7:
        for i in range(6):
            scripture += selected_scriptures[i]
            left_verse += len(selected_scriptures[i])
    else:
        day_num = num
        scripture += selected_scriptures[day_num-1]
        left_verse += len(selected_scriptures[day_num-1])
    reload_texts()

def reload_texts():
    left_verse_label.config(text="남은 구절 : "+str(left_verse))
    fail_num_label.config(text="틀린 갯수 : "+str(fail_num))

def day_reset():
    global scripture, left_verse, problem_text_box, fail_num, wrong_verses
    scripture = []
    left_verse = 0
    fail_num = 0
    wrong_verses = []
    reload_texts()
    problem_text_box.config(state=tk.NORMAL)
    problem_text_box.delete(1.0, tk.END)
    problem_text_box.config(state=tk.DISABLED)

# GUI 설정
root = tk.Tk()
root.tk.call('tk', 'scaling', 1.0)
root.title("과정을 선택해 주세요.")
root.geometry("900x600")               # 기본 창 크기
root.minsize(450, 300)                  # 최소 크기
root.option_add("*Font", ("맑은 고딕", 15))
root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=1)

def resource_path(rel: str) -> str:
    # PyInstaller 실행파일(임시폴더 _MEIPASS)과 개발환경 둘 다 지원
    base = getattr(sys, "_MEIPASS", Path(__file__).parent)
    return str(Path(base, rel))

# 1) 우선 Windows에서는 .ico 시도
try:
    if sys.platform == "win32":
        ico = resource_path("samuel_icon.ico")
        if Path(ico).exists():
            root.iconbitmap(ico)   # 파일 경로 반드시 절대/정규화
        else:
            raise FileNotFoundError(ico)
    else:
        raise OSError("iconbitmap not reliable on this platform")
except Exception:
    # 2) 모든 OS에서 동작하는 대안: PNG로 창 아이콘 설정 (Tk 8.6+)
    try:
        png = resource_path("samuel_icon.png")  # 같은 폴더에 PNG도 준비
        if Path(png).exists():
            img = tk.PhotoImage(file=png)
            root.wm_iconphoto(True, img)
    except Exception:
        pass  # 아이콘 설정 실패해도 앱은 계속 뜨게

def load_original_scriptures_txt():
    days = []
    for d in range(1, 7):
        p = resource_path(os.path.join("data", f"day{d}.txt"))
        with open(p, "r", encoding="utf-8") as f:
            # 줄바꿈/공백 제거, 빈줄 제외
            items = [line.strip() for line in f.readlines() if line.strip()]
        days.append(items)
    return days

# 일차 번호
day_num = 1
# 일차가 선택된 구절들
scripture = []
# 과정이 선택된 구절들
selected_scriptures = [[], [], [], [], [], []]
# 원본 구절
original_scriptures = load_original_scriptures_txt()
# 틀린 구절들을 저장할 리스트 (existing globals 근처에 추가)
wrong_verses = []  # 각 항목: {'reference': str, 'verse': str, 'mode': int, 'blanks': list}

def init_ui_fonts(root, family="맑은 고딕", size=13):
    import tkinter.ttk as ttk
    from tkinter import font as tkFont

    # Tk 기본 폰트들(이미 생성된 위젯도 자동 반영)
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkTooltipFont"):
        try:
            f = tkFont.nametofont(name)
            f.configure(family=family, size=size)
        except Exception:
            pass

    # ttk 위젯(버튼/라벨 등)에도 적용
    try:
        style = ttk.Style(root)
        style.configure(".", font=(family, size))
        style.configure("TButton", font=(family, size))
    except Exception:
        pass

init_ui_fonts(root, family="맑은 고딕", size=13)

font_size = 30
font_form = "맑은 고딕"
font_style_var = tk.StringVar(value="맑은 고딕")

# 볼드체 상태 변수
bold_var = tk.BooleanVar(value=False)

def update_font():
    selected_font = font_style_var.get()
    selected_size = font_size_var.get()
    is_bold = bold_var.get()
    f = tkFont.Font(
        family=selected_font,
        size=selected_size,
        weight='bold' if is_bold else 'normal',
        slant='roman'
    )
    answer_text_box.config(font=f)
    problem_text_box.config(font=f)

# ADD: 글꼴/크기/진하게/초기화 통합 팝업
def open_font_popup():
    win = tk.Toplevel(root)
    win.title("글꼴 설정")
    win.resizable(False, False)
    
    include_vertical = tk.BooleanVar(value=False)
    qvar = tk.StringVar(value="")

    # 좌상단: 검색 입력 + @포함 체크
    tk.Label(win, text="검색:").grid(row=0, column=0, padx=8, pady=6, sticky="w")
    entry = ttk.Entry(win, textvariable=qvar, width=26)
    entry.grid(row=0, column=1, padx=4, pady=6, sticky="we")
    chk = ttk.Checkbutton(win, text="@ 세로쓰기 포함", variable=include_vertical)
    chk.grid(row=0, column=2, padx=8, pady=6, sticky="e")

    # 폰트 리스트
    lst = tk.Listbox(win, height=14, width=34, activestyle="dotbox", exportselection=False)
    lst.grid(row=1, column=0, columnspan=3, padx=8, pady=(0,8), sticky="nsew")
    sb = ttk.Scrollbar(win, orient="vertical", command=lst.yview)
    sb.grid(row=1, column=3, sticky="ns", pady=(0,8))
    lst.config(yscrollcommand=sb.set)

    # 미리보기
    sample = tk.Label(win, text="가나다 ABC 123 — Preview")
    sample.grid(row=2, column=0, columnspan=3, padx=8, pady=(0,4))

    # 크기 슬라이더 + 진하게 + 초기화/적용/닫기
    ctrl = tk.Frame(win)
    ctrl.grid(row=3, column=0, columnspan=3, pady=6, padx=8, sticky="we")

    tk.Label(ctrl, text="크기:").pack(side="left")
    size_scale = ttk.Scale(ctrl, from_=8, to=48, value=font_size_var.get(),
                           command=lambda _=None: apply_preview())
    size_scale.pack(side="left", padx=6)
    bold_chk = ttk.Checkbutton(ctrl, text="진하게", variable=bold_var,
                               command=lambda: apply_preview())
    bold_chk.pack(side="left", padx=10)

    ttk.Button(ctrl, text="초기화", command=lambda: do_reset()).pack(side="right", padx=4)
    ttk.Button(ctrl, text="적용", command=lambda: do_apply()).pack(side="right", padx=4)
    ttk.Button(ctrl, text="닫기", command=win.destroy).pack(side="right", padx=4)

    # 레이아웃 확장
    win.grid_columnconfigure(1, weight=1)
    win.grid_rowconfigure(1, weight=1)

    # 내부 상태
    all_fonts = get_all_fonts(root, include_vertical.get())
    filtered = all_fonts[:]

    def populate(items, keep_current=True):
        lst.delete(0, tk.END)
        for f in items:
            lst.insert(tk.END, f)
        if keep_current and font_style_var.get() in items:
            idx = items.index(font_style_var.get())
            lst.selection_set(idx); lst.see(idx)
        elif items:
            lst.selection_set(0)

    def current_family():
        sel = lst.curselection()
        if sel:
            return lst.get(sel[0])
        # 선택 없으면 현재 전역값
        return font_style_var.get()

    def apply_preview():
        fam = current_family()
        size = int(round(float(size_scale.get())))
        f = tkFont.Font(
            family=fam, size=size,
            weight='bold' if bold_var.get() else 'normal',
            slant='roman'
        )
        sample.config(font=f)

    def refresh():
        nonlocal all_fonts, filtered
        all_fonts = get_all_fonts(root, include_vertical.get())
        q = qvar.get().lower()
        filtered = [f for f in all_fonts if q in f.lower()]
        populate(filtered)
        apply_preview()

    def on_select(_=None):
        apply_preview()

    def on_search(_=None):
        refresh()

    def on_toggle_vertical():
        refresh()

    def do_reset():
        reset_font()
        refresh()

    def do_apply():
        fam = current_family()
        font_style_var.set(fam)
        font_size_var.set(int(round(float(size_scale.get()))))
        update_font()

    # 바인딩
    lst.bind("<<ListboxSelect>>", on_select)
    entry.bind("<KeyRelease>", on_search)
    chk.config(command=on_toggle_vertical)
    size_scale.bind("<ButtonRelease-1>", lambda e: apply_preview())

    # 초기 채움
    populate(filtered)
    apply_preview()

def get_all_fonts(root, include_vertical=False):
    fams = sorted(tkFont.families(root))
    return fams if include_vertical else [f for f in fams if not f.startswith('@')]

def reset_font():
    """폰트를 기본값으로 초기화합니다."""
    font_style_var.set("맑은 고딕")
    font_size_var.set(30)
    bold_var.set(False)  # 볼드체 초기화
    update_font()
    
def create_size_slider():
    """폰트 크기를 조정할 수 있는 슬라이더를 생성합니다."""
    slider_window = tk.Toplevel(root)
    slider_window.title("크기 설정")

    # 글자 크기를 표시하는 라벨
    size_label = tk.Label(slider_window, text="글자 크기 : ")
    size_label.pack(side=tk.LEFT)

    # 글자 크기 값을 표시할 라벨
    size_value_label = tk.Label(slider_window, text=str(font_size_var.get()))
    size_value_label.pack(side=tk.LEFT)

    # 폰트 크기를 조절하는 슬라이더
    size_slider = ttk.Scale(slider_window, from_=8, to=48, variable=font_size_var, 
                            command=lambda x: update_font_and_label(size_value_label))
    size_slider.pack(pady=20)

    # 슬라이더 초기값 설정
    size_slider.set(font_size_var.get())

def update_font_and_label(size_value_label):
    """슬라이더 값이 변경될 때 폰트 크기를 업데이트하고, 라벨에 값을 표시합니다."""
    size_value_label.config(text=str(font_size_var.get()))
    update_font()

APP_NAME = "Samuel Memorization"
APP_VERSION = "버전 : 제42기 사무엘학교\n최신 버전 링크 :\nhttps://github.com/devRenio/Bible-verse-memorization"
APP_DESC = (
    "제출 : [ Space ] 혹은 [ Enter ]\n"
    "문자 그대로 일치해야 정답이 인정됩니다.\n"
    "세 번 틀린 후에 정답이 공개됩니다.\n\n"
    "문의 / 건의 :\n서울양천교회 공은호 형제 (깨사모 쪽지)\n\n"
    "개선점 / 오류 제보 언제나 감사합니다."
)

# 앱 정보 표시 함수
def show_about():
    info = (
        f"{APP_NAME}\n{APP_VERSION}\n\n"
        f"{APP_DESC}"
    )

    win = tk.Toplevel()
    win.title("정보")
    win.grab_set()
    win.resizable(False, False)

    text = tk.Text(win, wrap="word", height=15, width=40)
    text.insert("1.0", info)
    text.config(state="disabled")
    text.pack(padx=12, pady=8)

    # 확인 버튼
    ok_btn = ttk.Button(win, text="확인", command=win.destroy)
    ok_btn.pack(pady=(0, 8))

def on_space_key(event):
    if event.keycode == 229:  # Windows IME 조합 처리키
        return
    if event.char == " ":
        root.after_idle(submit_answer)
        return "break"  # space 입력 자체는 막고, 제출로만 처리


# 문제 텍스트박스 + 스크롤
problem_frame = tk.Frame(root)
problem_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(8, 6))
problem_frame.grid_rowconfigure(0, weight=1)
problem_frame.grid_columnconfigure(0, weight=1)

problem_text_box = tk.Text(
    problem_frame,
    font=(font_form, font_size),
    wrap=tk.WORD,
    state=tk.DISABLED
)
problem_text_box.grid(row=0, column=0, sticky="nsew")

problem_scroll = ttk.Scrollbar(problem_frame, orient="vertical", command=problem_text_box.yview)
problem_scroll.grid(row=0, column=1, sticky="ns")
problem_text_box.config(yscrollcommand=problem_scroll.set)

# 답안 텍스트박스
answer_text_box = tk.Text(root, height=1, width=30, font=(font_form, font_size), wrap=tk.WORD)
answer_text_box.grid(row=2, column=0, sticky="we", padx=12, pady=(0, 10))
answer_text_box.unbind("<space>")
answer_text_box.bind("<space>", on_space_key)
answer_text_box.bind("<Return>", lambda e: (root.after_idle(submit_answer), "break")[1])
answer_text_box.bind("<KP_Enter>", lambda e: (root.after_idle(submit_answer), "break")[1])

def select_course(course_number):
    global selected_scriptures
    selected_scriptures = [[], [], [], [], [], []]

    # 과정을 인자로 받았을 경우 (팝업 없이 처리)
    if course_number :
        for i, scripture_list in enumerate(original_scriptures):
            for scripture in scripture_list:
                split_data = scripture.split("\\", 1)
                if len(split_data) == 2:
                    number, content = split_data
                    if int(number) <= course_number:
                        selected_scriptures[i].append(content)
        course = str(course_number) + "과정"
        course_label.config(text = course, padx = 18)

def create_slider_window(title, min_value, max_value, update_func):
    """슬라이더를 표시하는 새 창을 생성."""
    slider_window = tk.Toplevel(root)
    slider_window.title(title + " 슬라이더")
    
    slider = tk.Scale(
        slider_window,
        from_=min_value,
        to=max_value,
        orient="horizontal",
        label=title,
        command=update_func
    )
    slider.pack(padx=10, pady=10)

def skip_problem():
    display_problem(current_mode)

root.title("samuel_memorization")

# 메뉴바 생성
menu_bar = tk.Menu(root)

# '과정' 메뉴 생성
course_menu = tk.Menu(menu_bar, tearoff=0)

for i in range(4) :
    course_menu.add_command(label=str(i + 1)+"과정", command=lambda i=i: select_course(i+1))

menu_bar.add_cascade(label="과정", menu=course_menu)

# '일차' 메뉴 생성
day_menu = tk.Menu(menu_bar, tearoff=0)

for i in range(6) :
    day_menu.add_command(label=str(i + 1)+"일차", command=lambda i=i: select_day(i+1))
day_menu.add_command(label="전체", command=lambda : select_day(7))

day_menu.add_separator()
day_menu.add_command(label="초기화", command=lambda : day_reset())

menu_bar.add_cascade(label="일차", menu=day_menu)

menu_bar.add_command(label="글꼴", command=open_font_popup)

menu_bar.add_command(label="정보", command=show_about)
root.bind("<F1>", lambda e: show_about())

font_size_var = tk.IntVar(value=30)  # 기본 크기 설정

# 메뉴바 설정
root.config(menu=menu_bar)

# 모드 선택 버튼
mode_buttons_frame = tk.Frame(root)
mode_buttons_frame.grid(row=0, column=0, sticky="we", padx=12, pady=(8, 4))

blank_num = 5
blank_mode_button = tk.Button(mode_buttons_frame, text="빈칸 모드", command=lambda: blank_level())
blank_mode_button.pack(side=tk.LEFT, padx=5)

verse_mode_button = tk.Button(mode_buttons_frame, text="구절 모드", command=lambda: set_mode(2))
verse_mode_button.pack(side=tk.LEFT, padx=5)

reference_mode_button = tk.Button(mode_buttons_frame, text="장절 모드", command=lambda: set_mode(3))
reference_mode_button.pack(side=tk.LEFT, padx=5)

full_mode_button = tk.Button(mode_buttons_frame, text="전체 모드", command=lambda: whole_level())
full_mode_button.pack(side=tk.LEFT, padx=5)

text_frame = tk.Frame(root)
text_frame.grid(row=3, column=0, sticky="we", padx=12, pady=(0, 8))

course = "과정 미선택"
course_label = tk.Label(text_frame, text=course)
course_label.pack(side=tk.LEFT, padx=5)

left_verse = 0
left_verse_label = tk.Label(text_frame, text="남은 구절 : "+str(left_verse))
left_verse_label.pack(side=tk.LEFT, padx=5)

fail_num = 0
fail_num_label = tk.Label(text_frame, text="틀린 갯수 : "+str(fail_num))
fail_num_label.pack(side=tk.LEFT)

skip_button = tk.Button(text_frame, text="스킵", command=skip_problem)
skip_button.pack(side=tk.LEFT, padx=5)

wrong_verses_button = tk.Button(text_frame, text="틀린 구절", command=show_wrong_verses)
wrong_verses_button.pack(side=tk.RIGHT, padx=5)

current_mode = 1
problem_num = 0
problem_completed = False
display_problem(current_mode)

root.mainloop()
