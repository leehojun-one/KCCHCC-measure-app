import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageOps, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates
import json
import datetime
import base64
from io import BytesIO
import requests

# 사이드바 닫기 및 넓은 화면
st.set_page_config(page_title="KCC Homecc 실측지 시스템", layout="wide", initial_sidebar_state="collapsed")

# ✨ 로그인 시스템 (Session State 활용) ✨
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

# 로그인이 안 되어 있으면 로그인 화면만 보여주고 멈춤(그만)
if not st.session_state.logged_in:
    st.markdown("<br><br><h1 style='text-align: center; color: #004b9b;'>KCC Homecc 스마트 실측 시스템</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>직원 확인을 위해 이름(또는 사번)을 입력해 주세요.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            emp_name = st.text_input("작업자 성함", placeholder="예: 홍길동 팀장")
            submit_btn = st.form_submit_button("시스템 접속하기", use_container_width=True)
            
            if submit_btn:
                if emp_name.strip() == "":
                    st.error("⚠️ 성함을 입력해 주세요!")
                else:
                    st.session_state.logged_in = True
                    st.session_state.user_name = emp_name
                    st.rerun()
    st.stop() # 로그인 전에는 아래 코드(도면 설계)가 실행되지 않도록 차단

# ✨ 프린트 & 페이지 분할 제어 CSS ✨
st.markdown("""
<style>
@media print {
    body * { visibility: hidden; }
    #print-section, #print-section * { visibility: visible; }
    #print-section {
        position: absolute;
        left: 0;
        top: 0;
        width: 100vw;
        margin: 0;
        padding: 10mm;
        background-color: white !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
    @page { size: A3 landscape; margin: 5mm; }
}
/* 우측 폼 침범을 막기 위한 내부 렌더링 컨테이너 설정 */
div[data-testid="stMarkdownContainer"] { max-width: 100%; overflow-x: visible; }
</style>
""", unsafe_allow_html=True)

# KCC Homecc 공식 로고 (로그인한 사용자 이름 표시 추가)
st.markdown(f"""
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px; padding-bottom: 10px; border-bottom: 2px solid #eee;">
    <div style="display: flex; align-items: center; gap: 15px;">
        <svg height="40" viewBox="0 0 250 40" xmlns="http://www.w3.org/2000/svg" style="display:block;">
            <g transform="skewX(-15) translate(15, 0)">
                <rect x="0" y="5" width="85" height="30" fill="#004b9b" rx="2" ry="2" />
            </g>
            <polygon points="32,4 45,4 40,11 27,11" fill="#e60012" />
            <text x="22" y="32" font-family="'Arial Black', 'Impact', sans-serif" font-size="26" font-weight="900" font-style="italic" fill="#ffffff" letter-spacing="-1.5">KCC</text>
            <text x="105" y="32" font-family="'Arial Black', 'Impact', sans-serif" font-size="26" font-weight="900" letter-spacing="-1">
                <tspan fill="#333">Home</tspan><tspan fill="#f37321">cc</tspan>
            </text>
        </svg>
        <div style="font-size: 14px; color: #888; border-left: 2px solid #ddd; padding-left: 15px; font-weight: bold; align-self: flex-end; padding-bottom: 6px;">
            Smart Measurement System v6.1 (Team Edition)
        </div>
    </div>
    <div style="font-size: 15px; font-weight: bold; color: #004b9b; background: #e8f0fe; padding: 8px 15px; border-radius: 20px;">
        👤 현재 접속자: {st.session_state.user_name}
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander("⚙️ 시스템 데이터 관리 (초기화 / 저장 / 불러오기)", expanded=False):
    sys1, sys2, sys3 = st.columns(3)
    with sys1:
        if st.button("📄 전체 도면 초기화", use_container_width=True):
            for key in ['windows_data', 'current_window_num', 'group_counter', 'edit_target', 'floor_plan_original', 'floor_plan_marked', 'markers', 'uploaded_filename', 'rendered_svg', 'site_info']:
                if key in st.session_state: del st.session_state[key]
            st.rerun()
            
    with sys2:
        if 'windows_data' in st.session_state and st.session_state.windows_data:
            save_data = {"windows": st.session_state.windows_data, "site_info": st.session_state.get('site_info', {})}
            json_data = json.dumps(save_data, ensure_ascii=False, indent=2)
            st.download_button("💾 현재 데이터 저장 (JSON)", data=json_data, file_name="KCC_실측데이터.json", mime="application/json", use_container_width=True)
        else:
            st.info("저장할 데이터가 없습니다.")

    with sys3:
        uploaded_json = st.file_uploader("JSON 데이터 불러오기", type="json", label_visibility="collapsed")
        if uploaded_json is not None:
            if st.button("데이터 적용하기", use_container_width=True):
                try:
                    loaded_data = json.load(uploaded_json)
                    if "windows" in loaded_data:
                        st.session_state.windows_data = loaded_data["windows"]
                        st.session_state.site_info = loaded_data.get("site_info", {})
                    else:
                        st.session_state.windows_data = loaded_data
                    max_num = max([w['num'] for w in st.session_state.windows_data]) if st.session_state.windows_data else 0
                    st.session_state.current_window_num = max_num + 1
                    st.rerun()
                except Exception as e:
                    st.error("데이터 형식이 맞지 않습니다.")

PIXEL_SCALE = 150.0 / 2300.0

if 'windows_data' not in st.session_state: st.session_state.windows_data = []
if 'current_window_num' not in st.session_state: st.session_state.current_window_num = 1
if 'group_counter' not in st.session_state: st.session_state.group_counter = 1
if 'edit_target' not in st.session_state: st.session_state.edit_target = None 
if 'floor_plan_original' not in st.session_state: st.session_state.floor_plan_original = None
if 'floor_plan_marked' not in st.session_state: st.session_state.floor_plan_marked = None
if 'markers' not in st.session_state: st.session_state.markers = [] 
if 'uploaded_filename' not in st.session_state: st.session_state.uploaded_filename = None

if 'site_info' not in st.session_state: 
    st.session_state.site_info = {
        "address": "", "date": datetime.date.today().strftime("%Y-%m-%d"), 
        "partner": "", "salesperson": "", "manager_name": "", "manager_phone": "", 
        "house_pw": "", "common_pw": "", "team": "", "team_phone": "", "notes": ""
    }

def get_circled_num(n):
    circles = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    return circles[n-1] if 1 <= n <= 20 else f"[{n}]"

def renumber_and_redraw():
    st.session_state.windows_data.sort(key=lambda x: x['num'])
    mapping, new_num = {}, 1
    for w in st.session_state.windows_data:
        mapping[w['num']] = new_num; w['num'] = new_num; new_num += 1
    st.session_state.current_window_num = new_num
    
    valid_markers = []
    for m in st.session_state.markers:
        if m['num'] in mapping:
            m['num'] = mapping[m['num']]; valid_markers.append(m)
    floating = [m for m in st.session_state.markers if m['num'] not in mapping and m['num'] >= new_num]
    if floating: valid_markers.append({'x': floating[-1]['x'], 'y': floating[-1]['y'], 'num': new_num})
    st.session_state.markers = valid_markers
    
    if st.session_state.floor_plan_original:
        img_draw = st.session_state.floor_plan_original.copy()
        draw = ImageDraw.Draw(img_draw)
        for marker in st.session_state.markers:
            mx, my = marker['x'], marker['y']
            draw.ellipse((mx-15, my-15, mx+15, my+15), fill='#e60012', outline='darkred')
            txt = str(marker['num'])
            for ox, oy in [(-4,-6), (-3,-6), (-4,-5), (-3,-5)]: draw.text((mx+ox, my+oy), txt, fill='white')
        st.session_state.floor_plan_marked = img_draw

def delete_window(target_num):
    st.session_state.windows_data = [w for w in st.session_state.windows_data if w['num'] != target_num]
    if st.session_state.edit_target == target_num: st.session_state.edit_target = None
    renumber_and_redraw()

def get_image_base64(pil_image):
    if pil_image is None: return ""
    buffered = BytesIO()
    pil_image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

tab1, tab2 = st.tabs(["🛠️ 실측지 도면 설계", "🖨️ 최종 실측지 PDF / 캡처 출력"])

# ==========================================
# TAB 1: 실측지 설계
# ==========================================
with tab1:
    with st.expander("📝 1단계: 현장 실측지 정보 입력 (클릭해서 열기/닫기)", expanded=True):
        info = st.session_state.site_info
        try: def_date = datetime.datetime.strptime(info.get('date', '2026-06-18'), "%Y-%m-%d").date()
        except: def_date = datetime.date.today()

        c1, c2, c3, c4 = st.columns(4)
        info['address'] = c1.text_input("현장주소", info.get('address', ''))
        selected_date = c2.date_input("시공일", value=def_date)
        info['date'] = selected_date.strftime("%Y-%m-%d")
        info['partner'] = c3.text_input("파트너명", info.get('partner', ''))
        info['salesperson'] = c4.text_input("영업자명", info.get('salesperson', ''))
        
        c5, c6, c7, c8 = st.columns(4)
        info['manager_name'] = c5.text_input("담당자명 (실장)", info.get('manager_name', ''))
        info['manager_phone'] = c6.text_input("담당자 연락처", info.get('manager_phone', ''))
        info['house_pw'] = c7.text_input("세대비번", info.get('house_pw', ''))
        info['common_pw'] = c8.text_input("공용현관비번", info.get('common_pw', ''))
        
        c9, c10, c11, c12 = st.columns(4)
        info['team'] = c9.text_input("시공팀", info.get('team', ''))
        info['team_phone'] = c10.text_input("시공팀 연락처", info.get('team_phone', ''))
        
        info['notes'] = st.text_area("특이사항 및 비고 (도면 하단에 인쇄됩니다)", info.get('notes', ''), height=68)

    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.6, 3.1, 1.3])

    with col1:
        st.subheader("2. 도면 마킹")
        uploaded_file = st.file_uploader("평면도 업로드", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
        
        if uploaded_file:
            if st.session_state.uploaded_filename != uploaded_file.name:
                img = Image.open(uploaded_file)
                img.thumbnail((500, 500), Image.Resampling.LANCZOS)
                st.session_state.floor_plan_original = img
                st.session_state.floor_plan_marked = img.copy()
                st.session_state.markers = []
                st.session_state.uploaded_filename = uploaded_file.name
            
            b1, b2, b3 = st.columns(3)
            if b1.button("↻ 90도 회전"): 
                w, h = st.session_state.floor_plan_original.size
                st.session_state.floor_plan_original = st.session_state.floor_plan_original.rotate(-90, expand=True)
                st.session_state.markers = [{'x': h - m['y'], 'y': m['x'], 'num': m['num']} for m in st.session_state.markers]
                renumber_and_redraw(); st.rerun()
            if b2.button("↔ 좌우 반전"): 
                w, h = st.session_state.floor_plan_original.size
                st.session_state.floor_plan_original = ImageOps.mirror(st.session_state.floor_plan_original)
                st.session_state.markers = [{'x': w - m['x'], 'y': m['y'], 'num': m['num']} for m in st.session_state.markers]
                renumber_and_redraw(); st.rerun()
            if b3.button("↕ 상하 반전"): 
                w, h = st.session_state.floor_plan_original.size
                st.session_state.floor_plan_original = ImageOps.flip(st.session_state.floor_plan_original)
                st.session_state.markers = [{'x': m['x'], 'y': h - m['y'], 'num': m['num']} for m in st.session_state.markers]
                renumber_and_redraw(); st.rerun()

            st.info("💡 정확한 위치를 클릭하세요.")
            value = streamlit_image_coordinates(st.session_state.floor_plan_marked, key="pil")
            
            if value:
                if not st.session_state.markers or (st.session_state.markers[-1]['x'] != value['x'] or st.session_state.markers[-1]['y'] != value['y']):
                    st.session_state.markers.append({'x': value['x'], 'y': value['y'], 'num': st.session_state.current_window_num})
                    st.session_state.edit_target = None
                    renumber_and_redraw(); st.rerun()

    with col2:
        st.subheader("3. 도면 렌더링")
        all_svg_html_blocks = []
        
        if st.session_state.windows_data:
            groups_dict = {}
            for w in st.session_state.windows_data: groups_dict.setdefault(w.get('group_id', w['num']), []).append(w)
            
            render_cols = st.columns(2)
            groups_list = sorted(groups_dict.items(), key=lambda x: min(w['num'] for w in x[1]))
            
            for g_idx, (gid, win_list) in enumerate(groups_list):
                win_list.sort(key=lambda x: x['num']) 
                group_html = "<div style='display: flex; flex-wrap: wrap; align-items: flex-start; border: 1px solid #ccc; padding: 10px; background: white; margin-bottom: 5px; border-radius:8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); page-break-inside: avoid; max-width: 100%; overflow-x: auto;'>"
                
                columns = []
                for w in win_list:
                    v_join = w.get('join_dir', '옆으로 결합(좌우)')
                    if v_join == '위로 결합(상)' and columns:
                        columns[-1].insert(0, w)
                    elif v_join == '아래로 결합(하)' and columns:
                        columns[-1].append(w)
                    else:
                        columns.append([w])

                def get_cbs_html(cb_list, dh):
                    html = ""
                    total_w_real = 0
                    
                    for cb in cb_list:
                        qty = cb.get('qty', 1)
                        if qty <= 0: continue
                        
                        if "45" in cb['type']: real_w = 45
                        elif "90" in cb['type']: real_w = 45
                        elif "135" in cb['type']: real_w = 135
                        else: real_w = 100 
                        
                        total_w_real += real_w
                        
                        if "45" in cb['type']: w_px = 8
                        elif "90" in cb['type']: w_px = 10
                        elif "135" in cb['type']: w_px = 22
                        else: w_px = 17 
                        
                        color = "#e60012" if ("90" in cb['type'] or "45" in cb['type']) else "#00205b"
                        cb_label = cb['type'].split('(')[0]
                        font_sz = "8" if w_px <= 10 else "10"
                        
                        svg_cb = f"<svg width='{w_px}' height='{dh + 20}' xmlns='http://www.w3.org/2000/svg' style='margin-right:1px; display:block;'>"
                        svg_cb += f"<rect width='{w_px}' height='{dh}' fill='white' />"
                        
                        lines_svg = ""
                        for i in range(-w_px, int(dh), 4):
                            lines_svg += f"<line x1='0' y1='{i}' x2='{w_px}' y2='{i+w_px}' stroke='{color}' stroke-width='1.5' />"
                        svg_cb += lines_svg
                        
                        svg_cb += f"<rect x='0' y='{dh}' width='{w_px}' height='20' fill='white' />"
                        svg_cb += f"<rect width='{w_px}' height='{dh}' fill='none' stroke='black' stroke-width='1'/>"
                        svg_cb += f"<text x='{w_px/2}' y='{dh/2}' dy='.3em' transform='rotate(-90 {w_px/2} {dh/2})' font-size='{font_sz}' font-weight='900' fill='white' stroke='white' stroke-width='2' text-anchor='middle'>{cb_label}</text>"
                        svg_cb += f"<text x='{w_px/2}' y='{dh/2}' dy='.3em' transform='rotate(-90 {w_px/2} {dh/2})' font-size='{font_sz}' font-weight='900' fill='black' text-anchor='middle'>{cb_label}</text>"
                        
                        if qty > 1:
                            svg_cb += f"<text x='{w_px/2}' y='{dh + 14}' font-size='11' font-weight='900' fill='red' text-anchor='middle'>X{qty}</text>"
                            
                        svg_cb += "</svg>"
                        html += svg_cb
                    
                    if total_w_real > 0:
                        return f"<div style='display:flex; flex-direction:column; align-items:center;'><div style='font-size:11px; font-weight:bold; color:#e60012; height:15px; display:flex; align-items:flex-end; padding-bottom:3px; box-sizing:border-box;'>{total_w_real}</div><div style='display:flex;'>{html}</div></div>", total_w_real
                    return "", 0

                group_html += "<div style='display:flex; align-items:flex-start;'>"
                
                for col in columns:
                    group_html += "<div style='display:flex; flex-direction:column; align-items:center; margin: 0 5px;'>"
                    
                    for window in col:
                        draw_h = int(window['h'] * PIXEL_SCALE)
                        draw_w = int(window['w'] * PIXEL_SCALE)
                        
                        cb_l_html, _ = get_cbs_html(window.get('cb_left', []), draw_h)
                        cb_r_html, _ = get_cbs_html(window.get('cb_right', []), draw_h)
                        
                        group_html += f"<div style='display:flex; flex-direction:column; align-items:center; min-width: max-content; margin-bottom: 8px;'>"
                        c_num = get_circled_num(window['num'])
                        group_html += f"<div style='text-align:center; margin-bottom: 2px; min-height:35px;'><div style='font-size: 15px; font-weight:bold; white-space:nowrap; color:#333;'>{c_num}{window.get('loc', '')}({window['shape']})</div><div style='font-size: 13px; color:#777; white-space:nowrap;'>{window['type']}</div></div>"

                        group_html += f"<div style='display:flex; align-items:flex-start;'>"
                        if window.get('cb_left', []): group_html += cb_l_html
                        
                        gls = window.get('glass', '기본(투명)')
                        
                        extra_svg_elements = ""
                        if gls == "모루":
                            # ✨ 모루: 미스트와 차별화되는 모던한 라이트 그레이 톤 
                            bg_fill = "#f4f6f8" 
                            for i in range(4, int(draw_w), 8):
                                extra_svg_elements += f"<rect x='{i}' y='0' width='4' height='{draw_h}' fill='#dfe3e8' />"
                        elif gls == "미스트":
                            # ✨ 미스트: 캡처 버그 우회를 위해 명시적 Line 사용 & 시원한 쿨 블루 톤 적용
                            bg_fill = "#e6f2ff" 
                            for x in range(0, int(draw_w), 4):
                                extra_svg_elements += f"<line x1='{x}' y1='0' x2='{x}' y2='{draw_h}' stroke='#cce5ff' stroke-width='1'/>"
                            for y in range(0, int(draw_h), 4):
                                extra_svg_elements += f"<line x1='0' y1='{y}' x2='{draw_w}' y2='{y}' stroke='#cce5ff' stroke-width='1'/>"
                        else:
                            bg_fill = "#fafafa"

                        svg_str = f"<div style='display:flex; flex-direction:column; align-items:center;'><div style='height:15px;'></div>" 
                        svg_str += f"<div style='position:relative; width:{draw_w}px; height:{draw_h}px;'>"
                        
                        svg_str += f"<svg width='{draw_w}' height='{draw_h}' xmlns='http://www.w3.org/2000/svg' style='display:block;'>"
                        svg_str += f"<rect width='{draw_w}' height='{draw_h}' fill='{bg_fill}' stroke='black' stroke-width='2'/>"
                        svg_str += extra_svg_elements
                        
                        vs_px = int(window.get('v_size', 0) * PIXEL_SCALE) if window.get('v_size', 0) > 0 else 0

                        if "문/" in window['shape']:
                            svg_str += f"<text x='{draw_w/2}' y='{draw_h/2 - 8}' font-size='12' fill='black' font-weight='bold' text-anchor='middle'>{window['shape'].split('/')[0]}</text>"
                            svg_str += f"<text x='{draw_w/2}' y='{draw_h/2 + 8}' font-size='11' fill='#00205b' text-anchor='middle'>{window['shape'].split('/')[1]}</text>"
                            if gls != "기본(투명)":
                                svg_str += f"<text x='{draw_w/2}' y='{draw_h/2 + 25}' font-size='12' fill='#004b9b' font-weight='bold' text-anchor='middle'>{gls}</text>"
                            
                            handle_w, handle_h = 4, 16
                            if "우핸들" in window['shape']:
                                hx, hy = draw_w - 5 - handle_w, draw_h / 2 - handle_h / 2
                                svg_str += f"<rect x='{hx}' y='{hy}' width='{handle_w}' height='{handle_h}' fill='#aaa' stroke='black' rx='2'/>"
                            elif "좌핸들" in window['shape']:
                                hx, hy = 5, draw_h / 2 - handle_h / 2
                                svg_str += f"<rect x='{hx}' y='{hy}' width='{handle_w}' height='{handle_h}' fill='#aaa' stroke='black' rx='2'/>"
                        else:
                            ratio_txt = ""
                            gls_txt = f"<text x='{draw_w/2}' y='{draw_h/2 + 20}' font-size='12' fill='#004b9b' font-weight='bold' text-anchor='middle'>{gls}</text>" if gls != "기본(투명)" else ""

                            if "2W" in window['shape']:
                                if "(1:2)" in window['shape']: ratio_txt = "1:2"
                                vd = window.get('vent_dir', '좌')
                                x = vs_px if "U" in window['shape'] and vd == '좌' else (draw_w - vs_px if "U" in window['shape'] and vd == '우' else (draw_w/3 if "(1:2)" in window['shape'] and vd == '좌' else (draw_w*2/3 if "(1:2)" in window['shape'] and vd == '우' else draw_w/2)))
                                svg_str += f"<line x1='{x}' y1='0' x2='{x}' y2='{draw_h}' stroke='black' stroke-width='2' />{gls_txt}"
                            elif "3W" in window['shape']:
                                if "1:2:1" in window['shape']: ratio_txt = "1:2:1"
                                x1, x2 = (vs_px, draw_w - vs_px) if "U" in window['shape'] and vs_px > 0 else (draw_w/4, draw_w*3/4)
                                svg_str += f"<line x1='{x1}' y1='0' x2='{x1}' y2='{draw_h}' stroke='black' stroke-width='2' /><line x1='{x2}' y1='0' x2='{x2}' y2='{draw_h}' stroke='black' stroke-width='2' />{gls_txt}"
                            elif "4W" in window['shape']:
                                x1, x2, x3 = draw_w/4, draw_w/2, draw_w*3/4
                                svg_str += f"<line x1='{x1}' y1='0' x2='{x1}' y2='{draw_h}' stroke='black' stroke-width='2' /><line x1='{x2}' y1='0' x2='{x2}' y2='{draw_h}' stroke='black' stroke-width='2' /><line x1='{x3}' y1='0' x2='{x3}' y2='{draw_h}' stroke='black' stroke-width='2' />{gls_txt}"
                            elif "FIX" in window['shape'] or window['shape'] in ["2F", "3F", "4F"]:
                                if window['shape'] == "2F":
                                    svg_str += f"<line x1='{draw_w/2}' y1='0' x2='{draw_w/2}' y2='{draw_h}' stroke='black' stroke-width='2' />"
                                    svg_str += f"<text x='{draw_w/4}' y='{draw_h/2}' font-size='12' fill='black' font-weight='bold' text-anchor='middle'>FIX</text>"
                                    svg_str += f"<text x='{draw_w*3/4}' y='{draw_h/2}' font-size='12' fill='black' font-weight='bold' text-anchor='middle'>FIX</text>"
                                elif window['shape'] == "3F":
                                    x1, x2 = draw_w/3, draw_w*2/3
                                    svg_str += f"<line x1='{x1}' y1='0' x2='{x1}' y2='{draw_h}' stroke='black' stroke-width='2' />"
                                    svg_str += f"<line x1='{x2}' y1='0' x2='{x2}' y2='{draw_h}' stroke='black' stroke-width='2' />"
                                    svg_str += f"<text x='{draw_w/6}' y='{draw_h/2}' font-size='12' fill='black' font-weight='bold' text-anchor='middle'>FIX</text>"
                                    svg_str += f"<text x='{draw_w/2}' y='{draw_h/2}' font-size='12' fill='black' font-weight='bold' text-anchor='middle'>FIX</text>"
                                    svg_str += f"<text x='{draw_w*5/6}' y='{draw_h/2}' font-size='12' fill='black' font-weight='bold' text-anchor='middle'>FIX</text>"
                                elif window['shape'] == "4F":
                                    x1, x2, x3 = draw_w/4, draw_w/2, draw_w*3/4
                                    svg_str += f"<line x1='{x1}' y1='0' x2='{x1}' y2='{draw_h}' stroke='black' stroke-width='2' />"
                                    svg_str += f"<line x1='{x2}' y1='0' x2='{x2}' y2='{draw_h}' stroke='black' stroke-width='2' />"
                                    svg_str += f"<line x1='{x3}' y1='0' x2='{x3}' y2='{draw_h}' stroke='black' stroke-width='2' />"
                                    svg_str += f"<text x='{draw_w/8}' y='{draw_h/2}' font-size='12' fill='black' font-weight='bold' text-anchor='middle'>FIX</text>"
                                    svg_str += f"<text x='{draw_w*3/8}' y='{draw_h/2}' font-size='12' fill='black' font-weight='bold' text-anchor='middle'>FIX</text>"
                                    svg_str += f"<text x='{draw_w*5/8}' y='{draw_h/2}' font-size='12' fill='black' font-weight='bold' text-anchor='middle'>FIX</text>"
                                    svg_str += f"<text x='{draw_w*7/8}' y='{draw_h/2}' font-size='12' fill='black' font-weight='bold' text-anchor='middle'>FIX</text>"
                                else:
                                    svg_str += f"<text x='{draw_w/2}' y='{draw_h/2}' font-size='12' fill='black' font-weight='bold' text-anchor='middle'>FIX</text>"
                                svg_str += gls_txt

                        raw_type = window.get('type', '')
                        prod_name = raw_type.split('(')[0].replace('HBF-', '').replace('BF-', '').strip()
                        if prod_name and prod_name != "선택":
                            svg_str += f"<text x='{draw_w/2}' y='22' font-size='15' font-weight='bold' fill='white' stroke='white' stroke-width='4' stroke-linejoin='round' text-anchor='middle'>{prod_name}</text>"
                            svg_str += f"<text x='{draw_w/2}' y='22' font-size='15' font-weight='bold' fill='#000' text-anchor='middle'>{prod_name}</text>"
                            
                        svg_str += "</svg>" 

                        if window['shape'] not in ["FIX", "2F", "3F", "4F"] and "문/" not in window['shape']:
                            v_size_val = window.get('v_size', 0)
                            v_size_html = f"<div style='color:#e60012; font-size:12px; font-weight:bold; margin-top:2px;'>{v_size_val}</div>" if v_size_val > 0 and "U" in window['shape'] else ""
                            
                            def get_overlay_html(dir_val, pos_x, w_shape):
                                scr = window.get('screen', 'Y')
                                arr = "←" if dir_val == '우' else "→"
                                
                                scr_html = ""
                                if scr == 'Y':
                                    scr_html = "<div style='display:flex; align-items:center; justify-content:center; gap:3px; margin-bottom:1px;'><span style='font-size:18px; font-weight:bold; color:#e60012;'>#</span><span style='font-size:12px; font-weight:bold; color:#e60012;'>(망)</span></div>"
                                    
                                if "3W" in w_shape or "4W" in w_shape:
                                    dir_html = f"<span style='font-size:18px; font-weight:bold; color:#e60012;'>{arr}</span>"
                                else:
                                    dir_html = f"<span style='font-size:18px;'>{arr}</span> <span style='font-size:14px; font-weight:bold;'>{dir_val}</span>" if dir_val == '우' else f"<span style='font-size:14px; font-weight:bold;'>{dir_val}</span> <span style='font-size:18px;'>{arr}</span>"
                                    
                                return f"<div style='position:absolute; left:{pos_x}px; top:50%; transform:translate(-50%, -50%); text-align:center; line-height:1.2; z-index:5;'>{scr_html}<div style='display:flex; align-items:center; justify-content:center; gap:2px; color:#e60012;'>{dir_html}</div>{v_size_html}</div>"

                            vd = window.get('vent_dir', '좌')
                            if "3W" in window['shape']:
                                svg_str += get_overlay_html('좌', x1 / 2, window['shape'])
                                svg_str += get_overlay_html('우', x2 + (draw_w - x2) / 2, window['shape'])
                            elif "4W" in window['shape']:
                                svg_str += get_overlay_html('좌', x1 / 2, window['shape'])
                                svg_str += get_overlay_html('우', x3 + (draw_w - x3) / 2, window['shape'])
                            elif "2W" in window['shape']:
                                svg_str += get_overlay_html(vd, x/2 if vd == '좌' else x + (draw_w-x)/2, window['shape'])

                            if ratio_txt: svg_str += f"<div style='position:absolute; left:50%; top:50%; transform:translate(-50%, -50%); font-size:14px; color:#555; font-weight:bold; z-index:1;'>{ratio_txt}</div>"
                            h_pos_val = window.get('h_pos', 0)
                            if h_pos_val > 0: svg_str += f"<div style='position:absolute; left:3px; bottom:15px; border-left:2px solid #e60012; border-bottom:2px solid #e60012; padding:2px; color:#e60012; font-size:11px; font-weight:bold; line-height:1;'>핸들{h_pos_val}</div>"
                        
                        svg_str += f"</div></div>" 
                        
                        group_html += svg_str
                        if window.get('cb_right', []): group_html += cb_r_html
                        
                        group_html += f"</div><div style='font-size: 15px; font-weight: 900; letter-spacing: 0.5px; margin-top: 4px; color:#000;'>{window['w']} * {window['h']}(H)</div></div>" 
                    
                    group_html += "</div>"
                
                group_html += "</div></div>"
                all_svg_html_blocks.append(group_html)
                
                with render_cols[g_idx % 2]:
                    st.markdown(group_html, unsafe_allow_html=True)
                    btn_cols = st.columns(len(win_list))
                    for i, w_item in enumerate(win_list):
                        with btn_cols[i]:
                            bc1, bc2 = st.columns(2)
                            if bc1.button("✏️", key=f"e_{w_item['num']}", help="수정"): st.session_state.edit_target = w_item['num']; st.rerun()
                            if bc2.button("🗑️", key=f"d_{w_item['num']}", help="삭제"): delete_window(w_item['num']); st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)
                
            st.session_state.rendered_svg = "<div style='display: flex; flex-wrap: wrap; gap: 15px; align-items: flex-start;'>" + "".join(all_svg_html_blocks) + "</div>"
        else:
            st.info("우측에서 창호를 설계해 주세요.")

    with col3:
        target_n = st.session_state.edit_target if st.session_state.edit_target else st.session_state.current_window_num
        target_title = f"<span style='color:#0056b3;'>{st.session_state.edit_target}번 창호 수정 중</span>" if st.session_state.edit_target else f"<span style='color:#e60012;'>{st.session_state.current_window_num}번 새 창호 설계</span>"
        st.subheader("4. 창호 상세 입력")
        st.markdown(f"**타겟: {target_title}**", unsafe_allow_html=True)

        has_marker = any(m['num'] == target_n for m in st.session_state.markers)
        
        if not has_marker:
            st.warning(f"👈 도면에서 **[{target_n}]번** 위치를 지정하면 입력창이 열립니다.")
        else:
            edit_data = next((w for w in st.session_state.windows_data if w['num'] == target_n), None) if st.session_state.edit_target else None
            def get_val(key, default): return edit_data.get(key, default) if edit_data else default
            
            default_combine = False
            if st.session_state.edit_target and target_n > 1:
                current_w = next((w for w in st.session_state.windows_data if w['num'] == target_n), None)
                prev_w = next((w for w in st.session_state.windows_data if w['num'] == target_n - 1), None)
                if current_w and prev_w and current_w.get('group_id') == prev_w.get('group_id'): default_combine = True
            
            combine_prev = st.checkbox("🔗 이전 창과 연속 결합 (그룹화)", value=default_combine)
            
            join_dir_options = ["옆으로 결합(좌우)", "위로 결합(상)", "아래로 결합(하)"]
            join_dir = join_dir_options[0]
            if combine_prev and target_n > 1:
                existing_join = get_val('join_dir', '옆으로 결합(좌우)')
                if existing_join not in join_dir_options: existing_join = join_dir_options[0]
                join_dir = st.radio("결합 방향", join_dir_options, index=join_dir_options.index(existing_join), horizontal=True)

            loc_name = st.text_input("설치 위치 (명칭)", value=get_val('loc', ''))
            
            c_c1, c_c2 = st.columns(2)
            cat_options = ["선택", "발코니창/일반창", "고정창", "터닝도어"]
            cat = c_c1.selectbox("창호 구분", cat_options, index=cat_options.index(get_val('cat', '선택')))
            
            type_options = ["선택"]
            if cat == "발코니창/일반창": type_options += ["HBF-141(발코니단창)", "HBF-251(발코니이중창)", "HBF-115(일반단창)", "HBF-230(일반이중창)", "HBF-225TM(공틀단창)"]
            elif cat == "고정창": type_options += ["CB-90 100면유리", "CB-90 45면유리", "PJ-FIX", "BF-115 F", "BF-141 F"]
            elif cat == "터닝도어": type_options += ["터닝도어"]
            win_type = c_c2.selectbox("창호 종류", type_options, index=type_options.index(get_val('type', '선택')) if get_val('type', '선택') in type_options else 0)

            shape_options = ["FIX", "2F", "3F", "4F"] if cat == "고정창" else (["선택", "미는문/우핸들", "미는문/좌핸들", "당기는문/우핸들", "당기는문/좌핸들"] if cat == "터닝도어" else ["선택", "2W", "2W(1:2)", "2WU", "3W(1:2:1)", "3WU", "4W"])
            win_shape = st.selectbox("창 형태", shape_options, index=shape_options.index(get_val('shape', '선택')) if get_val('shape', '선택') in shape_options else 0)

            cv1, cv2 = st.columns(2)
            vent_dir = cv1.radio("벤트 방향", ["좌", "우"], index=["좌", "우"].index(get_val('vent_dir', '좌')), horizontal=True) if "3W" not in win_shape and cat not in ["고정창", "터닝도어"] and "선택" not in win_shape else "없음"
            screen_opt = cv2.radio("방충망", ["Y", "N"], index=["Y", "N"].index(get_val('screen', 'Y')), horizontal=True) if cat not in ["터닝도어", "고정창"] else "N"
            
            gls_options = ["기본(투명)", "미스트", "모루"]
            glass_opt = st.selectbox("특수유리 (투명은 미표기)", gls_options, index=gls_options.index(get_val('glass', '기본(투명)')))

            cw1, cw2 = st.columns(2)
            width = cw1.number_input("가로 (W)", min_value=0, value=get_val('w', 0), step=10)
            height = cw2.number_input("세로 (H)", min_value=0, value=get_val('h', 0), step=10)
            
            cvs1, cvs2 = st.columns(2)
            v_size = cvs1.number_input("V사이즈 (U창)", min_value=0, value=get_val('v_size', 0), step=10) if "U" in win_shape else 0
            h_pos = cvs2.number_input("핸들높이(바닥기준)", min_value=0, value=get_val('h_pos', 0), step=10)

            st.markdown("**■ 통바(CB) 상세 설정**")
            cb_options = ["CB100", "CB90", "CB45", "CB135"]
            cb_left_list, cb_right_list = [], []
            
            c_l, c_r = st.columns(2)
            with c_l:
                cbl_data = get_val('cb_left', [])
                if st.checkbox("◀ 좌측 통바 설정", value=len(cbl_data)>0):
                    cbl_count = st.number_input("좌측 사양 개수", min_value=1, max_value=10, value=max(1, len(cbl_data)), step=1, key="cbl_cnt")
                    for i in range(cbl_count):
                        t_val = cbl_data[i]['type'] if i < len(cbl_data) else "CB100"
                        q_val = cbl_data[i]['qty'] if i < len(cbl_data) else 1
                        t = st.selectbox(f"사양{i+1}", cb_options, index=cb_options.index(t_val), key=f"cl_t_{i}")
                        q = st.number_input(f"전/후수량{i+1}", 1, value=q_val, key=f"cl_q_{i}")
                        cb_left_list.append({"type": t, "qty": q})
            with c_r:
                cbr_data = get_val('cb_right', [])
                if st.checkbox("우측 통바 설정 ▶", value=len(cbr_data)>0):
                    cbr_count = st.number_input("우측 사양 개수", min_value=1, max_value=10, value=max(1, len(cbr_data)), step=1, key="cbr_cnt")
                    for i in range(cbr_count):
                        t_val = cbr_data[i]['type'] if i < len(cbr_data) else "CB100"
                        q_val = cbr_data[i]['qty'] if i < len(cbr_data) else 1
                        t = st.selectbox(f"사양{i+1}", cb_options, index=cb_options.index(t_val), key=f"cr_t_{i}")
                        q = st.number_input(f"전/후수량{i+1}", 1, value=q_val, key=f"cr_q_{i}")
                        cb_right_list.append({"type": t, "qty": q})

            btn_label = "✏️ 도면 수정 적용" if st.session_state.edit_target else "✅ 도면 생성 (저장)"
            if st.button(btn_label, type="primary", use_container_width=True):
                if cat == "선택" or win_type == "선택" or win_shape == "선택": st.error("🚨 구분, 종류, 형태를 선택해주세요!")
                elif width == 0 or height == 0: st.error("🚨 사이즈를 입력해주세요!")
                elif "U" in win_shape and v_size == 0: st.error("🚨 U창의 V사이즈를 입력해주세요!")
                else:
                    gid = get_val('group_id', st.session_state.group_counter)
                    if combine_prev and target_n > 1: gid = next((w['group_id'] for w in st.session_state.windows_data if w['num'] == target_n - 1), gid)
                    
                    new_data = {"num": target_n, "group_id": gid, "join_dir": join_dir, "loc": loc_name, "cat": cat, "type": win_type, "shape": win_shape, "w": width, "h": height, "v_size": v_size, "h_pos": h_pos, "vent_dir": vent_dir, "screen": screen_opt, "glass": glass_opt, "cb_left": cb_left_list, "cb_right": cb_right_list}
                    if st.session_state.edit_target: st.session_state.windows_data = [new_data if w['num'] == target_n else w for w in st.session_state.windows_data]; st.session_state.edit_target = None
                    else: 
                        st.session_state.windows_data.append(new_data)
                        if not combine_prev: st.session_state.group_counter += 1
                        st.session_state.current_window_num += 1
                    st.rerun()

# ==========================================
# TAB 2: 최종 실측지 템플릿 및 인쇄/캡처 출력
# ==========================================
with tab2:
    col_print, col_capture, col_log, col_zoom = st.columns([1, 1.2, 1.2, 3])
    
    with col_print:
        components.html("""
            <button onclick="window.parent.print()" style="padding: 12px; width: 100%; background: #004b9b; color: #fff; border: none; font-weight: 900; border-radius: 5px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-size: 14px;">
                🖨️ PDF 인쇄
            </button>
        """, height=65)
        
    with col_capture:
        components.html("""
            <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
            <button onclick="takeShot()" style="padding: 12px; width: 100%; background: #fee500; color: #000; border: none; font-weight: 900; border-radius: 5px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-size: 14px;">
                📸 다운로드
            </button>
            <script>
                function takeShot() {
                    const target = window.parent.document.getElementById('print-section');
                    const zoomContainer = window.parent.document.getElementById('zoom-container');
                    if(!target) return alert('출력할 도면이 없습니다.');
                    
                    let originalZoom = '';
                    let originalTransform = '';
                    if (zoomContainer) {
                        originalZoom = zoomContainer.style.zoom;
                        originalTransform = zoomContainer.style.transform;
                        zoomContainer.style.zoom = '100%';
                        zoomContainer.style.transform = 'scale(1.0)';
                    }
                    
                    html2canvas(target, { scale: 3, useCORS: true, backgroundColor: '#ffffff', logging: false }).then(canvas => {
                        let link = document.createElement('a');
                        link.download = 'KCC_현장실측지.png';
                        link.href = canvas.toDataURL('image/png');
                        link.click();
                        
                        if (zoomContainer) {
                            zoomContainer.style.zoom = originalZoom;
                            zoomContainer.style.transform = originalTransform;
                        }
                    });
                }
            </script>
        """, height=65)

    with col_log:
        if st.button("📤 작업 완료 (시트 기록)", type="secondary", use_container_width=True):
            try:
                WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzPCOq6oxDMtkmbNQQKvjeuSU5TlUKHC9XHg6jT59RnXBoH7paF7o2ZmeH851UMZ6Ag/exec" 
                
                if WEBHOOK_URL:
                    params = {
                        "user": st.session_state.user_name,
                        "address": info.get('address', '주소 미입력'),
                        "count": len(st.session_state.windows_data)
                    }
                    response = requests.get(WEBHOOK_URL, params=params)
                    if response.status_code == 200:
                        st.success("✅ 본사 서버(구글 시트)로 작업 내역이 전송되었습니다!")
                    else:
                        st.error("전송에 실패했습니다. (서버 응답 오류)")
                else:
                    st.warning("⚠️ 아직 구글 앱스스크립트 URL이 코드에 입력되지 않았습니다.")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

    with col_zoom:
        zoom_level = st.slider("🔍 출력 도면 크기 조절 (창호가 많으면 줄이고, 적으면 키워서 1장에 맞추세요!)", min_value=50, max_value=200, value=100, step=5)
    
    info = st.session_state.site_info
    img_b64 = get_image_base64(st.session_state.floor_plan_marked)
    img_html = f"<img src='data:image/png;base64,{img_b64}' style='width:100%; max-height:450px; object-fit:contain;'/>" if img_b64 else "<div style='height:300px; display:flex; align-items:center; justify-content:center; color:#999;'>도면 없음</div>"
    notes_html = info.get('notes', '').replace('\n', '<br>')
    svg_blocks = st.session_state.get('rendered_svg', '<div style="color:gray;">설계된 창호가 없습니다.</div>')

    print_html = f"""<div id="print-section" style="padding: 10px; background: white; min-width: 1200px;">
<h3 style="margin-top: 0; color: #004b9b; border-bottom: 2px solid #004b9b; padding-bottom: 5px;">최종 현장 실측지 (발주 및 인쇄용)</h3>
<table style="width:100%; border-collapse: collapse; text-align: center; border: 2px solid black; font-family: 'Malgun Gothic', sans-serif; font-size:14px; background: white;">
<tr>
<th style="border: 1px solid black; padding: 4px 8px; width: 10%; background:#f0f0f0; color:#333;">현장주소</th>
<td colspan="5" style="border: 1px solid black; padding: 4px 8px; text-align: left; font-weight:900; font-size:18px; color:#004b9b;">{info.get('address', '')}</td>
<th style="border: 1px solid black; padding: 4px 8px; width: 10%; background:#f0f0f0; color:#333;">시공일</th>
<td style="border: 1px solid black; padding: 4px 8px; width: 15%; font-weight:900; font-size:18px; color:#e60012;">{info.get('date', '')}</td>
</tr>
<tr>
<th style="border: 1px solid black; padding: 4px 8px; width: 10%; background:#f0f0f0; color:#333;">파트너명</th>
<td style="border: 1px solid black; padding: 4px 8px; width: 15%;">{info.get('partner', '')}</td>
<th style="border: 1px solid black; padding: 4px 8px; width: 10%; background:#f0f0f0; color:#333;">담당자명</th>
<td style="border: 1px solid black; padding: 4px 8px; width: 15%;">{info.get('manager_name', '')}</td>
<th style="border: 1px solid black; padding: 4px 8px; width: 10%; background:#f0f0f0; color:#333;">담당자연락처</th>
<td style="border: 1px solid black; padding: 4px 8px; width: 15%;">{info.get('manager_phone', '')}</td>
<th style="border: 1px solid black; padding: 4px 8px; width: 10%; background:#f0f0f0; color:#333;">세대비번</th>
<td style="border: 1px solid black; padding: 4px 8px; width: 15%; font-weight:bold;">{info.get('house_pw', '')}</td>
</tr>
<tr>
<th style="border: 1px solid black; padding: 4px 8px; background:#f0f0f0; color:#333;">시공팀</th>
<td style="border: 1px solid black; padding: 4px 8px;">{info.get('team', '')}</td>
<th style="border: 1px solid black; padding: 4px 8px; background:#f0f0f0; color:#333;">시공팀연락처</th>
<td style="border: 1px solid black; padding: 4px 8px;">{info.get('team_phone', '')}</td>
<th style="border: 1px solid black; padding: 4px 8px; background:#f0f0f0; color:#333;">영업자명</th>
<td style="border: 1px solid black; padding: 4px 8px;">{info.get('salesperson', '')}</td>
<th style="border: 1px solid black; padding: 4px 8px; background:#f0f0f0; color:#333;">공용현관비번</th>
<td style="border: 1px solid black; padding: 4px 8px; font-weight:bold;">{info.get('common_pw', '')}</td>
</tr>
</table>
<div style="display: flex; margin-top: 15px; gap: 15px;">
<div style="width: 22%; display: flex; flex-direction: column; gap: 10px;">
<div style="border: 2px solid black; padding: 10px; background: white;">
<div style="font-weight: bold; margin-bottom: 5px; border-bottom: 1px solid black; padding-bottom: 5px; color:#333;">평면도</div>
{img_html}
</div>
<div style="border: 2px solid black; padding: 10px; background: white; flex-grow: 1; min-height: 120px;">
<div style="font-weight: bold; margin-bottom: 5px; border-bottom: 1px solid black; padding-bottom: 5px; color:#333;">특이사항 및 비고</div>
<div style="font-size: 14px; white-space: pre-wrap; margin-top:10px; color:black;">{notes_html}</div>
</div>
</div>
<div style="width: 78%; border: 2px solid black; padding: 10px; background: white;">
<div id="zoom-container" style="zoom: {zoom_level}%; -moz-transform: scale({zoom_level/100}); -moz-transform-origin: top left;">
{svg_blocks}
</div>
</div>
</div>
</div>"""
    
    st.markdown(print_html, unsafe_allow_html=True)
