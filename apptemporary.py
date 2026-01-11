import streamlit as st

st.set_page_config(
    page_title="Kriterion Quant - Test",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Kriterion Quant - DMA System")
st.success("✅ Streamlit is working!")

st.info("""
This is a minimal test version to verify Streamlit Cloud deployment.

If you see this message, the basic app is running correctly.

**Next steps:**
1. Verify secrets are configured
2. Test imports
3. Load full app
""")

# Test secrets
st.header("🔐 Secrets Check")

try:
    if 'EODHD_API_KEY' in st.secrets:
        key_length = len(st.secrets['EODHD_API_KEY'])
        st.success(f"✅ EODHD_API_KEY found (length: {key_length})")
    else:
        st.error("❌ EODHD_API_KEY not found in secrets")
        st.info("Add secrets in Settings → Secrets")
except Exception as e:
    st.error(f"Error checking secrets: {e}")

# Test imports
st.header("📦 Import Check")

with st.spinner("Testing imports..."):
    try:
        from config import UNIVERSE
        st.success(f"✅ config imported - {len(UNIVERSE)} tickers")
    except Exception as e:
        st.error(f"❌ config import failed: {e}")

    try:
        from utils import format_number
        st.success("✅ utils imported")
    except Exception as e:
        st.error(f"❌ utils import failed: {e}")

st.divider()
st.caption("Once all checks pass, switch to the full app.py")
