import streamlit as st
import gdown
import tempfile
import os

# Google Drive file ID from your link
FILE_ID = "11ICIy_lf6izQ99hiYTIpm2n6dwbn0UOF"
DIRECT_URL = f"https://drive.google.com/uc?id={FILE_ID}"
SHARE_URL = f"https://drive.google.com/file/d/{FILE_ID}/view?usp=sharing"

st.set_page_config(page_title="File Downloader", layout="centered")
st.title("📥 File Downloader")
st.markdown("Click the button below to download the file.")

# We'll use a button to trigger the download attempt
if st.button("⬇️ Download", use_container_width=True):
    try:
        # Create a temporary file to store the downloaded content
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        # Download using gdown (handles large files and confirmation)
        st.info("Downloading file from Google Drive... Please wait.")
        gdown.download(DIRECT_URL, tmp_path, quiet=False)

        # Read the downloaded file into memory
        with open(tmp_path, "rb") as f:
            file_data = f.read()

        # Clean up the temporary file
        os.unlink(tmp_path)

        # Present a second button to actually save the file
        st.success("File downloaded successfully! Click below to save it.")
        st.download_button(
            label="💾 Save file",
            data=file_data,
            file_name="downloaded_file.pdf",   # adjust extension if known
            mime="application/octet-stream",
            use_container_width=True,
        )

    except Exception as e:
        st.error(f"Direct download failed: {e}")
        st.warning("Redirecting you to the Google Drive page to download manually.")
        # Provide a link button that opens the share page in a new tab
        st.link_button("🔗 Open Google Drive", SHARE_URL, use_container_width=True)
