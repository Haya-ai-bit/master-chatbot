import streamlit as st
from google import genai
from google.genai import types
import glob
import shutil
import tempfile
import os

# 1. إعدادات الصفحة وتصميم الواجهة
st.set_page_config(
    page_title="المرشد الأكاديمي لبرامج الماجستير",
    page_icon="🎓",
    layout="centered"
)

# 2. تنسيق CSS مخصص لدعم اللغة العربية وتجميل الألوان والخطوط
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Tajawal', sans-serif;
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

# 3. جلب مفتاح الـ API بأمان وتنظيفه من أي مسافات
api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
if not api_key:
    st.error("⚠️ يرجى إضافة مفتاح GEMINI_API_KEY في إعدادات الموقع (Secrets).")
    st.stop()

client = genai.Client(api_key=api_key)

# 4. قراءة جميع ملفات الـ PDF مع حل مشكلة الأسماء العربية
@st.cache_resource(show_spinner="جاري تجهيز وتحليل أدلة الماجستير...")
def load_all_pdfs():
    uploaded_refs = []
    pdf_files = sorted(glob.glob("*.pdf"))
    
    for idx, pdf in enumerate(pdf_files):
        # إنشاء نسخة مؤقتة باسم إنجليزي لتفادي خطأ UnicodeEncodeError عند الرفع
        temp_path = os.path.join(tempfile.gettempdir(), f"doc_{idx}.pdf")
        shutil.copyfile(pdf, temp_path)
        
        g_file = client.files.upload(file=temp_path)
        uploaded_refs.append(g_file)
        
        os.remove(temp_path)
        
    return uploaded_refs, pdf_files

gemini_files, file_names = load_all_pdfs()

# 5. القائمة الجانبية لعرض المصادر الموجودة بأسمائها العربية الأصلية
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

# 9. استقبال سؤال المستخدم وتوليد الإجابة
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

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.0
                    )
                )
                
                answer = response.text
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"حدث خطأ: {e}")
