import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json

st.set_page_config(page_title="Thank You Card API Tester", layout="wide")

st.title("Thank You Card API Tester")

# API Configuration
API_BASE_URL = "https://card-handler-backend.onrender.com/api"
st.sidebar.header("API Configuration")
api_key = st.sidebar.text_input("API Key", type="password")
sandbox_mode = st.sidebar.checkbox("Sandbox Mode", value=True)

# Tab selection
tab1, tab2, tab3 = st.tabs(["Single Card", "Bulk Upload", "Health Check"])

with tab1:
    st.header("Send Single Card")
    
    # Form for single card
    with st.form("single_card_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input("Full Name", "John Doe")
            address_line1 = st.text_input("Address Line 1", "123 Main St")
            city = st.text_input("City", "Anytown")
            state = st.text_input("State", "CA")
            
        with col2:
            zip_code = st.text_input("ZIP Code", "12345")
            country = st.text_input("Country", "USA")
            template_id = st.text_input("Template ID (Optional)")
            delivery_date = st.date_input(
                "Delivery Date (Optional)",
                min_value=datetime.now().date(),
                value=None
            )
            
        message = st.text_area("Thank You Message", "Thank you for your kindness!")
        submit_single = st.form_submit_button("Send Card")

    if submit_single:
        if not api_key:
            st.error("Please enter an API key")
        else:
            payload = {
                "fullName": full_name,
                "address": {
                    "line1": address_line1,
                    "city": city,
                    "state": state,
                    "zip": zip_code,
                    "country": country
                },
                "message": message,
                "templateId": template_id or None,
                "deliveryDate": delivery_date.strftime("%Y-%m-%d") if delivery_date else None
            }

            # Debug information
            st.write("Sending request to:", f"{API_BASE_URL}/send-card{'?sandbox=true' if sandbox_mode else ''}")
            st.write("Headers:", {"api-key": f"{api_key[:3]}...{api_key[-3:]}" if len(api_key) > 6 else "***"})
            st.write("Payload:", payload)

            # First check if server is running
            try:
                health_check = requests.get(f"{API_BASE_URL}/health", timeout=2)
                if health_check.status_code != 200:
                    st.error("Server is not responding properly. Please check if FastAPI server is running.")
                    st.stop()
            except requests.exceptions.RequestException:
                st.error("Cannot connect to server. Please make sure FastAPI server is running on port 8080.")
                st.stop()

            try:
                with st.spinner("Sending request..."):
                    response = requests.post(
                        f"{API_BASE_URL}/send-card",  # Remove sandbox from URL
                        json={
                            **payload,
                            "sandbox": sandbox_mode  # Add sandbox to payload instead
                        },
                        headers={"api-key": api_key},
                        timeout=30  # Increase timeout
                    )
                    
                    # Debug response information
                    st.write("Response Status Code:", response.status_code)
                    try:
                        response_json = response.json()
                        st.json(response_json)
                        
                        if response.status_code == 200:
                            st.success("Card sent successfully!")
                            if response_json.get("sandbox"):
                                st.info("This was a sandbox request - no real card will be sent.")
                    except Exception as e:
                        st.error(f"Failed to parse response as JSON: {response.text}")
                        st.error(f"Parse error: {str(e)}")
                    
            except requests.exceptions.Timeout:
                st.error("Request timed out. The server took too long to respond. Please try again.")
            except requests.exceptions.ConnectionError:
                st.error("Failed to connect to the server. Make sure the FastAPI server is running on port 8000.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.error("Full error details:", exc_info=True)

with tab2:
    st.header("Bulk Upload")
    
    # Store task ID in session state
    if 'task_id' not in st.session_state:
        st.session_state.task_id = None
    
    # Sample Excel template
    st.subheader("Excel Template Format")
    sample_data = {
        "Name": ["John Doe", "Jane Smith"],
        "Address Line 1": ["123 Main St", "456 Oak Ave"],
        "City": ["Anytown", "Springfield"],
        "State": ["CA", "IL"],
        "ZIP": ["12345", "67890"],
        "Country": ["USA", "USA"],
        "Message": ["Thank you!", "Many thanks!"],
        "Template ID": ["template1", "template2"]
    }
    df_sample = pd.DataFrame(sample_data)
    st.dataframe(df_sample)
    
    # Download template button
    if st.button("Download Template"):
        df_sample.to_excel("template.xlsx", index=False)
        with open("template.xlsx", "rb") as f:
            st.download_button(
                "Click to Download",
                f,
                "thank_you_cards_template.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # File upload section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])
        
        if uploaded_file and st.button("Process Bulk Upload"):
            if not api_key:
                st.error("Please enter an API key")
            else:
                try:
                    files = {"file": uploaded_file}
                    response = requests.post(
                        f"{API_BASE_URL}/bulk-upload{'?sandbox=true' if sandbox_mode else ''}",
                        files=files,
                        headers={"api-key": api_key}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.task_id = result['task_id']
                        st.success(f"Upload successful! Task ID: {result['task_id']}")
                        st.json(result)
                    else:
                        st.error(f"Error: {response.status_code}")
                        st.json(response.json())
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Status checking section
    with col2:
        st.subheader("Check Upload Status")
        if st.session_state.task_id:
            st.write(f"Current Task ID: {st.session_state.task_id}")
            
            if st.button("Check Status", key="check_status"):
                try:
                    status_response = requests.get(
                        f"{API_BASE_URL}/bulk-upload/{st.session_state.task_id}"
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        
                        # Show status summary
                        status = status_data.get('status', 'unknown')
                        st.write(f"Status: {status}")
                        
                        if status == "completed":
                            results = status_data.get('results', [])
                            success_count = sum(1 for r in results if r.get('status') == 'confirmed')
                            error_count = sum(1 for r in results if r.get('status') == 'error')
                            
                            st.success(f"Processed {len(results)} cards")
                            st.write(f"✅ Successful: {success_count}")
                            st.write(f"❌ Failed: {error_count}")
                            
                            if status_data.get('sandbox'):
                                st.info("This was processed in sandbox mode")
                        
                        # Show full response in expandable section
                        with st.expander("View Full Response"):
                            st.json(status_data)
                    else:
                        st.error(f"Error checking status: {status_response.status_code}")
                        
                except Exception as e:
                    st.error(f"Error checking status: {str(e)}")
        else:
            st.write("No active task. Upload a file first.")

with tab3:
    st.header("Health Check")
    
    if st.button("Check API Health"):
        try:
            response = requests.get(f"{API_BASE_URL}/health")
            st.json(response.json())
            
            if response.status_code == 200:
                st.success("API is healthy!")
            else:
                st.error("API health check failed!")
                
        except Exception as e:
            st.error(f"Error connecting to API: {str(e)}") 
