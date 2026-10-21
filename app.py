import streamlit as st
from google import genai
from google.genai import types
import glob
import shutil
import tempfile
import os
import time

# 1. إعدادات الصفحة وتصميم الواجهة
st.set_page_config(
    page_title="المرشد الأكاديمي لبرامج الماجستير",
    page_icon="🎓",
    layout="centered"
)

# 2. تنسيق CSS مخصص ومضبوط لدعم اللغة العربية بدون تشويه القائمة الجانبية
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    
    html, body, .stApp {
        font-family: 'Tajawal', sans-serif;
    }
    .main .block-container {
        direction: rtl;
        text-align: right;
    }
    section[data-testid="stSidebar"] .block-container {
        direction: rtl;
        text-align: right;
    }
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .stChatMessage {
        direction: rtl;
        text-align: right;
    }
</style>

<div class="main-header">
    <h2 style="margin:0; color:white;">🎓 المرشد الأكاديمي لبرامج الماجستير</h2>
    <p style="margin-top:10px; opacity:0.9;">أهلاً بك! اسألني عن أي شيء يخص برامج الماجستير المهني، اللوائح، والخطط الدراسية</p>
</div>
""", unsafe_allow_html=True)

# 3. جلب مفتاح الـ API بأمان
api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
if not api_key:
    st.error("⚠️ يرجى إضافة مفتاح GEMINI_API_KEY في إعدادات الموقع (Secrets).")
    st.stop()

client = genai.Client(api_key=api_key)

# 4. قراءة جميع ملفات الـ PDF
@st.cache_resource(show_spinner="جاري تجهيز وتحليل أدلة الماجستير...")
def load_all_pdfs():
    uploaded_refs = []
    pdf_files = sorted(glob.glob("*.pdf"))
    
    for idx, pdf in enumerate(pdf_files):
        temp_path = os.path.join(tempfile.gettempdir(), f"doc_{idx}.pdf")
        shutil.copyfile(pdf, temp_path)
        
        g_file = client.files.upload(file=temp_path)
        uploaded_refs.append(g_file)
        
        os.remove(temp_path)
        
    return uploaded_refs, pdf_files

gemini_files, file_names = load_all_pdfs()

# 5. القائمة الجانبية لعرض المصادر الموجودة
with st.sidebar:
    st.header("📚 الأدلة والمصادر المعتمدة")
    st.write(f"يعتمد البوت حالياً على **{len(file_names)}** ملفات:")
    for name in file_names:
        st.caption(f"📄 {name}")
    
    st.divider()
    if st.button("🗑️ بدء محادثة جديدة", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# 6. تهيئة سجل المحادثة ورسالة الترحيب
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "مرحباً بك! 👋 أنا مساعدك الأكاديمي الذكي. كيف يمكنني مساعدتك اليوم في برامج الماجستير؟"}
    ]

# 7. أزرار الأسئلة السريعة
st.write("💡 **أسئلة شائعة سريعة:**")
col1, col2, col3 = st.columns(3)
quick_question = None

if col1.button("📌 شروط القبول والتسجيل", use_container_width=True):
    quick_question = "ما هي شروط القبول والتسجيل في برامج الماجستير المرفقة؟"
if col2.button("📘 الخطة الدراسية والساعات", use_container_width=True):
    quick_question = "كم عدد الساعات المعتمدة وما هي تفاصيل الخطة الدراسية؟"
if col3.button("🎯 مجالات العمل والأهداف", use_container_width=True):
    quick_question = "ما هي أهداف البرامج ومجالات العمل بعد التخرج؟"

# 8. عرض المحادثة السابقة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 9. دالة ذكية للتغلب على ضغط الخوادم (503) تلقائياً
def generate_smart_answer(contents, system_instruction):
    # قائمة النماذج بالترتيب في حال كان أحدها مشغولاً
    models_to_try = ["gemini-3.8-flash", "gemini-3.8-pro", "gemini-2.0-flash"]
    
    for attempt in range(3): # 3 محاولات تلقائية
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.0
                    )
                )
                return response.text
            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                    time.sleep(2) # انتظار ثانيتين ثم المحاولة مجدداً
                    continue
                elif "404" in err_str or "NOT_FOUND" in err_str:
                    continue # تجربة النموذج التالي في القائمة
                else:
                    raise e
    raise Exception("الخادم مشغول جداً حالياً، يرجى المحاولة بعد قليل.")

# 10. استقبال سؤال المستخدم وتوليد الإجابة
user_input = st.chat_input("اكتبي سؤالك هنا...")
prompt = quick_question or user_input

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("جاري البحث في الأدلة الرسمية..."):
            try:
                system_instruction = """
                أنت مرشد أكاديمي رسمي لمرحلة الماجستير في الجامعة.
                مهمتك الإجابة على أسئلة الطلاب بالاعتماد حصرياً وفقط على ملفات الـ PDF المرفقة.
                القواعد الصارمة:
                1. لا تؤلف أو تضف أي معلومة من خارج الملفات المرفقة نهائياً.
                2. إذا لم تجد الإجابة في الملفات، قل: "عذراً، هذه المعلومة غير مذكورة في الأدلة الرسمية المتوفرة حالياً."
                3. اذكر اسم البرنامج أو الدليل الذي أخذت منه المعلومة لتكون إجابتك موثقة.
                4. نسّق الإجابة بشكل جميل باستخدام النقاط والعناوين الواضحة.
                """

                contents = gemini_files + [prompt]
                answer = generate_smart_answer(contents, system_instruction)
                
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"⚠️ {e}")
