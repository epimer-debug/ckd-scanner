import streamlit as st
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv
from PIL import Image

# 載入環境變數
load_dotenv()

st.set_page_config(page_title="CKD 飲食掃描器 (Gemini 2.0)", page_icon="🥗", layout="centered")

# --- 1. 初始化 Google Gemini ---
api_key = os.getenv("GOOGLE_API_KEY")

# 側邊欄輸入 Key
if not api_key:
    with st.sidebar:
        st.divider()
        api_key = st.text_input("🔑 請輸入 Google API Key", type="password")
        st.caption("免費申請 Key: [Google AI Studio](https://aistudio.google.com/app/apikey)")

if not api_key:
    st.warning("👈 請先在左側輸入 Google API Key 才能開始喔！")
    st.stop()

# 設定 Google API
genai.configure(api_key=api_key)

# --- 2. 核心分析函數 ---
def clean_json_string(json_str):
    """
    清理 AI 回傳的字串，移除 Markdown 符號
    """
    if not json_str:
        return ""
    # 移除 ```json 和 ```
    clean_str = json_str.replace("```json", "").replace("```", "").strip()
    return clean_str

def analyze_image_google(image_file, user_stage):
    try:
        # 準備圖片
        image = Image.open(image_file)
        
        # 使用您剛才測試成功的 Gemini 2.0 Flash 模型
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        你是一位台灣的腎臟科專業營養師。使用者狀態：{user_stage}。
        請分析這張食品包裝圖片，並輸出嚴格的 JSON 格式。
        
        需要提取的欄位：
        1. product_name (產品名稱)
        2. nutrients (每份數值，若無標示請填 null): calories, protein, sodium, potassium, phosphorus
        3. warnings (警示): 
           - additives: 列出磷酸鹽(如偏磷酸鈉)或高鉀成分
           - high_sodium: boolean (>400mg)
           - high_potassium: boolean
        4. assessment (評估):
           - color: "Green", "Yellow", "Red"
           - title: 短評
           - explanation: 繁體中文建議 (50字內)
        """
        
        # 發送請求
        response = model.generate_content([prompt, image])
        
        # 除錯：印出原始回應 (若失敗可供檢查)
        # print(response.text) 
        
        # 清理並解析 JSON
        cleaned_text = clean_json_string(response.text)
        return json.loads(cleaned_text)
        
    except Exception as e:
        st.error(f"分析發生錯誤: {e}")
        # 如果失敗，回傳 None
        return None

# --- 3. 網頁介面 ---
st.title("🥗 CKD 飲食掃描器 (Gemini版)")
st.markdown("使用 **Google Gemini 2.0** 快速分析。")

with st.sidebar:
    st.header("⚙️ 個人設定")
    ckd_stage = st.selectbox("腎臟病分期", 
        ["CKD 1-2 期", "CKD 3-4 期 (低蛋白)", "CKD 5 期", "洗腎/透析中"])

uploaded_file = st.file_uploader("📷 上傳照片", type=["jpg", "png", "jpeg"])

if uploaded_file:
    st.image(uploaded_file, caption="預覽圖片", use_container_width=True)
    
    if st.button("🔍 開始分析", type="primary"):
        with st.spinner("AI 正在仔細檢查成分..."):
            result = analyze_image_google(uploaded_file, ckd_stage)
            
            # --- 這裡增加了防呆機制 ---
            if result:
                # 解析結果並顯示
                assess = result.get("assessment", {})
                color = assess.get("color", "Gray")
                
                if color == "Red": st.error(f"🔴 {assess.get('title')}")
                elif color == "Yellow": st.warning(f"🟡 {assess.get('title')}")
                else: st.success(f"🟢 {assess.get('title')}")
                
                st.write(assess.get('explanation'))
                st.divider()
                
                # 顯示警示
                warn = result.get("warnings", {})
                additives = warn.get("additives", [])
                if additives:
                    st.subheader("⚠️ 發現隱形殺手")
                    for ad in additives:
                        st.write(f"- 含有：**{ad}**")
                else:
                    st.info("✅ 未檢測到高風險添加物")
                
                # 顯示數據
                st.subheader("📊 營養數據 (每份)")
                nut = result.get("nutrients", {})
                c1, c2, c3 = st.columns(3)
                c1.metric("熱量", f"{nut.get('calories') or '?'} kcal")
                c2.metric("蛋白質", f"{nut.get('protein') or '?'} g")
                c3.metric("鈉", f"{nut.get('sodium') or '?'} mg")
                
                c4, c5 = st.columns(2)
                c4.metric("鉀", f"{nut.get('potassium') or '未標示'} mg")
                c5.metric("磷", f"{nut.get('phosphorus') or '未標示'} mg")
            else:
                st.error("分析失敗，可能是圖片模糊或 AI 無法讀取，請換一張試試看。")