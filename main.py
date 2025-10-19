# main.py
import streamlit as st
from datetime import date, timedelta
import core

st.set_page_config(page_title="New Delhi Cause List Generator", layout="wide")
st.title("⚖️ New Delhi District Court PDF Cause List Generator")

# --- Initialize the driver at the start ---
if 'driver' not in st.session_state:
    with st.spinner("Initializing browser... Please wait."):
        st.session_state.driver = core.initialize_driver()
driver = st.session_state.driver

# --- Session State Caching ---
if 'complex_list' not in st.session_state:
    st.session_state.complex_list = {}
    st.session_state.establishment_list = {}
    st.session_state.last_primary_id = None
    st.session_state.court_list = {}
    # New state for batch processing
    st.session_state.court_queue = []
    st.session_state.batch_results = []

# --- Fetch initial data using the API method ---
if not st.session_state.complex_list:
    with st.spinner("Fetching court complex and establishment lists..."):
        st.session_state.complex_list, st.session_state.establishment_list = core.get_complex_and_establishment_lists()

# --- UI Layout ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Court Selection")
    search_type_display = st.radio("Search By", ("Court Complex", "Court Establishment"), key="search_type_radio")
    search_type = "courtComplex" if search_type_display == "Court Complex" else "courtEstablishment"

    if search_type == "courtComplex":
        selected_primary_name = st.selectbox("Select Court Complex", st.session_state.complex_list.keys(), key="sb_complex")
        selected_primary_value = st.session_state.complex_list.get(selected_primary_name)
    else:
        selected_primary_name = st.selectbox("Select Court Establishment", st.session_state.establishment_list.keys(), key="sb_establishment")
        selected_primary_value = st.session_state.establishment_list.get(selected_primary_name)
    
    if selected_primary_value and selected_primary_value != st.session_state.last_primary_id:
        with st.spinner("Fetching court list from server..."):
            st.session_state.court_list = core.get_courts_via_api(selected_primary_value, search_type)
            st.session_state.last_primary_id = selected_primary_value
            st.session_state.court_queue = [] # Reset queue if complex changes
            st.session_state.batch_results = []

    if st.session_state.court_list:
        selected_court_name = st.selectbox("Select Specific Court (for single download)", st.session_state.court_list.keys())
        selected_court_value = st.session_state.court_list.get(selected_court_name)
    else:
        st.warning("No courts loaded.")
        selected_court_value = None

with col2:
    st.subheader("2. Details & CAPTCHA")
    today = date.today()
    cause_list_date = st.date_input("Select Cause List Date", today, min_value=today - timedelta(days=30), max_value=today)
    case_type = st.radio("Case Type", ("Civil", "Criminal"), horizontal=True)
    
    st.write("**Enter the CAPTCHA code:**")
    
    # --- CAPTCHA REFRESH LOGIC ---
    # The button is just for manual refresh. The script will auto-refresh during batch processing.
    if st.button("Refresh CAPTCHA"):
        # We don't need to do anything here because the script reruns and calls get_captcha_image below
        pass

    captcha_path = core.get_captcha_image(driver)
    if captcha_path:
        st.image(captcha_path)
    else:
        st.error("Could not load CAPTCHA image. Try refreshing.")
        
    captcha_text = st.text_input("Enter Captcha", label_visibility="collapsed")

# --- Single Download Button ---
st.markdown("---")
st.subheader("3. Single Court Download")

if st.button("Generate PDF for Selected Court", use_container_width=True, disabled=not selected_court_value):
    if captcha_text and selected_court_value and selected_primary_value:
        with st.spinner(f"Submitting form for {selected_court_name}..."):
            result = core.process_cause_list(driver, search_type, selected_primary_value, selected_court_value, cause_list_date, case_type, captcha_text)
        
        if result['status'] == 'success':
            st.success(f"Generated `{result['file']}` in the 'output' folder.")
        else:
            st.error(f"Failed: {result['data']}")
    else:
        st.warning("Please ensure a court is selected and CAPTCHA is entered.")

# --- START: NEW BATCH PROCESSING SECTION ---
st.markdown("---")
st.subheader("4. Batch Download Helper")

# Button to initialize the batch process
if st.button("Start New Batch for All Courts in Complex", use_container_width=True):
    if st.session_state.court_list:
        # Create a queue of courts to process
        st.session_state.court_queue = list(st.session_state.court_list.items())
        st.session_state.batch_results = [] # Clear previous results
        st.info(f"Batch initialized with {len(st.session_state.court_queue)} courts. The next court is ready below.")
    else:
        st.error("No court list is loaded. Please select a complex first.")

# This section is visible only when a batch is active
if st.session_state.court_queue:
    
    # Get the next court from the queue without removing it yet
    next_court_name, next_court_value = st.session_state.court_queue[0]
    
    st.warning(f"**Next in queue:** {next_court_name}")
    st.write(f"Remaining courts to process: {len(st.session_state.court_queue)}")

    # The main action button for processing one court at a time
    if st.button("Process Next Court", use_container_width=True, type="primary"):
        if not captcha_text:
            st.error("Please enter the new CAPTCHA to proceed!")
        else:
            with st.spinner(f"Processing {next_court_name}..."):
                # Actually remove the court from the queue now that we are processing it
                processed_court_name, processed_court_value = st.session_state.court_queue.pop(0)

                result = core.process_cause_list(
                    driver,
                    search_type,
                    selected_primary_value,
                    processed_court_value,
                    cause_list_date,
                    case_type,
                    captcha_text
                )
                
                # Store the result message
                if result['status'] == 'success':
                    st.session_state.batch_results.append(f"✅ **{processed_court_name}:** Generated `{result['file']}`")
                else:
                    st.session_state.batch_results.append(f"❌ **{processed_court_name}:** Failed - {result['data']}")

            # This st.rerun() is key. It forces the page to reload immediately,
            # which will then run the get_captcha_image() function again to show the new CAPTCHA.
            st.rerun()

# Display results from the batch process
if st.session_state.batch_results:
    st.markdown("---")
    st.subheader("Batch Results")
    for res in reversed(st.session_state.batch_results): # Show newest first
        st.markdown(res)

if st.session_state.court_queue == [] and len(st.session_state.batch_results) > 0:
    st.success("🎉 Batch complete! All courts have been processed.")
# --- END: NEW BATCH PROCESSING SECTION ---