import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader
import glob
import re

# 1. إعدادات الصفحة وتصميم الواجهة
st.set_page_config(
    page_title="المرشد الأكاديمي لبرامج الماجستير",
    page_icon="🎓",
    layout="centered"
)

# 2. تنسيق CSS لدعم اللغة العربية
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    
    html, body, .stApp {
        font-family: 'Tajawal', sans-serif;
    }
    .main .block-container, section[data-testid="stSidebar"] .block-container {
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

# 3. جلب مفتاح الـ API
api_key = st.secrets.get("GEMINI_API_KEY", "").strip()
if not api_key:
    st.error("⚠️ يرجى إضافة مفتاح GEMINI_API_KEY في إعدادات الموقع (Secrets).")
    st.stop()

client = genai.Client(api_key=api_key)

# 4. قراءة وتقسيم ملفات الـ PDF إلى فقرات صغيرة لسرعة البحث
@st.cache_resource(show_spinner="جاري تجهيز أدلة الماجستير...")
def load_pdf_chunks():
    pdf_files = sorted(glob.glob("*.pdf"))
    chunks = []
    
    for pdf in pdf_files:
        try:
            reader = PdfReader(pdf)
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    chunks.append({
                        "source": pdf,
                        "page": page_num,
                        "text": text.strip()
                    })
        except Exception:
            pass
            
    return chunks, pdf_files

all_chunks, file_names = load_pdf_chunks()

# دالة البحث السريع: تختار أهم الصفحات المرتبطة بالسؤال فقط لتوفير الوقت!
def get_relevant_context(query, chunks, top_k=10):
    if not chunks:
        return "لا توجد نصوص مستخرجة من الملفات."
    
    words = [w for w in re.findall(r'\w+', query) if len(w) > 2]
    scored_chunks = []
    
    for c in chunks:
        score = sum(1 for w in words if w in c["text"] or w in c["source"])
        scored_chunks.append((score, c))
        
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    selected = [x[1] for x in scored_chunks[:top_k]]
    
    context_text = ""
    for item in selected:
        context_text += f"\n--- [المصدر: {item['source']} | صفحة: {item['page']}] ---\n{item['text']}\n"
    return context_text

# 5. القائمة الجانبية لعرض المصادر الموجودة
with st.sidebar:
    st.header("📚 الأدلة والمصادر المعتمدة")
    st.write(f"يعتمد البوت حالياً على **{len(file_names)}** ملفات ({len(all_chunks)} صفحة):")
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

# 9. استقبال السؤال والرد الفوري المتدفق (Streaming)
user_input = st.chat_input("اكتبي سؤالك هنا...")
prompt = quick_question or user_input

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        response_placeholder.markdown("⏳ *جاري استخراج المعلومة...*")
        
        # جلب الصفحات المهمة فقط للسؤال في جزء من الثانية
        relevant_docs = get_relevant_context(prompt, all_chunks, top_k=10)
        
        full_prompt = f"""أنت مرشد أكاديمي رسمي لمرحلة الماجستير في الجامعة.
أجب على سؤال الطالب بالاعتماد حصرياً وفقط على النصوص المرفقة أدناه من الأدلة الرسمية.
- لا تضف أي معلومة من خارج النصوص.
- إذا لم تجد الإجابة، قل: "عذراً، هذه المعلومة غير مذكورة في الأدلة الرسمية المتوفرة."
- اذكر اسم البرنامج أو المصدر عند الإجابة، ونسّق إجابتك في نقاط واضحة.

النصوص المستخرجة من الأدلة الرسمية:
{relevant_docs}

سؤال الطالب: {prompt}"""

        full_answer = ""
        try:
            # استخدام البث المباشر (Stream) مع تقليل وقت التفكير للرد في ثانية واحدة
            stream = client.models.generate_content_stream(
                model="gemini-3.8-flash",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    thinking_config=types.ThinkingConfig(thinking_level="minimal")
                )
            )
            for chunk in stream:
                if chunk.text:
                    full_answer += chunk.text
                    response_placeholder.markdown(full_answer + " ▌")
            
            response_placeholder.markdown(full_answer)
            st.session_state.messages.append({"role": "assistant", "content": full_answer})
            
        except Exception:
            # خطة بديلة فورية في حال عدم قبول إعداد التفكير
            try:
                stream = client.models.generate_content_stream(
                    model="gemini-3.8-flash",
                    contents=full_prompt,
                    config=types.GenerateContentConfig(temperature=0.0)
                )
                for chunk in stream:
                    if chunk.text:
                        full_answer += chunk.text
                        response_placeholder.markdown(full_answer + " ▌")
                
                response_placeholder.markdown(full_answer)
                st.session_state.messages.append({"role": "assistant", "content": full_answer})
            except Exception as e2:
                response_placeholder.error(f"⚠️ الخادم مشغول حالياً، يرجى المحاولة بعد لحظات: {e2}")
