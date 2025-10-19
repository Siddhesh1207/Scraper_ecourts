# core.py
import os
import time
import requests
import traceback
from datetime import date
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

NEW_DELHI_COURTS_URL = "https://newdelhi.dcourts.gov.in/cause-list-%e2%81%84-daily-board/"
AJAX_URL = "https://newdelhi.dcourts.gov.in/wp-admin/admin-ajax.php"

# --- PDF Generation (With Advocate Column) ---
def generate_pdf_from_data(scraped_data):
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    judge_name_sanitized = "".join(c for c in scraped_data['judge_name'] if c.isalnum() or c in (' ', '_')).rstrip().replace(" ", "_")
    filename = f"{scraped_data['listing_date']}_{judge_name_sanitized}.pdf"
    filepath = os.path.join(output_dir, filename)
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(scraped_data['court_name'], styles['h1']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>In The Court Of:</b> {scraped_data['judge_name']}", styles['h3']))
    story.append(Paragraph(f"<b>Cause List For:</b> {scraped_data['listing_date']}", styles['h3']))
    story.append(Spacer(1, 24))
    if scraped_data['cases']:
        table_data = [["Sr. No.", "Case Number / Type / Year", "Advocate"]]
        for i, (case_number, advocate) in enumerate(scraped_data['cases'], 1):
            table_data.append([str(i), case_number, advocate or 'N/A'])
        t = Table(table_data)
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey),('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),('ALIGN', (0,0), (-1,-1), 'CENTER'),('VALIGN', (0,0), (-1,-1), 'MIDDLE'),('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),('BOTTOMPADDING', (0,0), (-1,0), 12), ('BACKGROUND', (0,1), (-1,-1), colors.beige),('GRID', (0,0), (-1,-1), 1, colors.black)]))
        story.append(t)
    else:
        story.append(Paragraph("No cases found in the cause list.", styles['Normal']))
    doc.build(story)
    print(f"Successfully generated PDF: {filename}")
    return filename

# --- API-BASED FUNCTIONS (Unchanged) ---
def get_complex_and_establishment_lists():
    try:
        page = requests.get(NEW_DELHI_COURTS_URL)
        soup = BeautifulSoup(page.content, "html.parser")
        complex_list = {opt.text: opt['value'] for opt in soup.select("select#est_code option") if opt.get('value')}
        establishment_list = {opt.text: opt['value'] for opt in soup.select("select#court_establishment option") if opt.get('value')}
        return complex_list, establishment_list
    except Exception as e:
        print(f"Error fetching initial lists: {e}")
        return {}, {}

def get_courts_via_api(est_code, service_type):
    try:
        session = requests.Session()
        session.get(NEW_DELHI_COURTS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        payload = {'est_code': est_code, 'action': 'get_court_lists', 'es_ajax_request': '1', 'service_type': service_type}
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': NEW_DELHI_COURTS_URL}
        response = session.post(AJAX_URL, data=payload, headers=headers)
        response.raise_for_status()
        html_string = response.json()['data']
        soup = BeautifulSoup(html_string, 'html.parser')
        court_list = {opt.text: opt['value'] for opt in soup.select("option") if opt.get('value')}
        return court_list
    except Exception as e:
        print(f"Error fetching courts via API: {e}")
        return {}

# --- SELENIUM FUNCTIONS (Unchanged) ---
def initialize_driver():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.get(NEW_DELHI_COURTS_URL)
    return driver

def get_captcha_image(driver):
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    try:
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, "siwp_img_refresh"))).click()
        time.sleep(1)
    except TimeoutException: pass
    captcha_element = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "siwp_captcha_image_0")))
    captcha_path = os.path.join(output_dir, "captcha.png")
    captcha_element.screenshot(captcha_path)
    return captcha_path

# --- START: FINAL, MOST ROBUST SCRAPING FUNCTION ---
def _scrape_and_process_result(driver):
    try:
        wait = WebDriverWait(driver, 45)
        print("Waiting for a response after submission...")

        # THE KEY: Wait for ANY of the three possible outcomes after submitting the form.
        wait.until(EC.any_of(
            EC.visibility_of_element_located((By.ID, "cnrResults")), # Outcome 1: Success (results container appears)
            EC.visibility_of_element_located((By.CLASS_NAME, "siwp_captcha_error_message")), # Outcome 2: CAPTCHA Error
            EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'No Record Found')]")) # Outcome 3: No Records
        ))
        print("...Page has responded.")

        # Now, check which outcome occurred.
        try:
            # Check for CAPTCHA error first.
            error_msg = driver.find_element(By.CLASS_NAME, "siwp_captcha_error_message").text
            return {"status": "error", "data": f"CAPTCHA Error: {error_msg}. Please enter the new CAPTCHA and try again."}
        except NoSuchElementException:
            # If no CAPTCHA error, proceed.
            pass

        try:
            # This is the success path.
            results_container = driver.find_element(By.ID, "cnrResults")
            if "No Record Found" in results_container.text:
                return {"status": "info", "data": "No records found for this court."}

            cases = []
            table_rows = results_container.find_elements(By.CSS_SELECTOR, "table.data-table-1 tbody tr")
            for row in table_rows:
                try:
                    case_number = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) a").text
                    advocate = row.find_element(By.CSS_SELECTOR, "td:nth-child(4)").text
                    cases.append((case_number, advocate))
                except NoSuchElementException:
                    continue
            
            scraped_data = {
                'court_name': results_container.find_element(By.TAG_NAME, "h5").text,
                'judge_name': results_container.find_element(By.XPATH, ".//p[contains(., 'In The Court Of')]").text.replace("In The Court Of : ", ""),
                'listing_date': results_container.find_element(By.XPATH, ".//p[contains(., 'Listed on')]").text.split(' : ')[-1],
                'cases': cases
            }
            pdf_filename = generate_pdf_from_data(scraped_data)
            return {"status": "success", "file": pdf_filename}

        except NoSuchElementException:
             # This can happen if the page loads weirdly.
             return {"status": "error", "data": "The results page did not load correctly. Please try again."}

    except TimeoutException:
        return {"status": "error", "data": "The website took too long to respond."}
    except Exception:
        return {"status": "error", "data": f"An unexpected error occurred: {traceback.format_exc()}"}
# --- END: FINAL, MOST ROBUST SCRAPING FUNCTION ---

# --- FORM FILLING AND PROCESSING (Unchanged) ---
def _fill_out_form(driver, search_by, primary_val, court_val, date_obj, case_type, captcha):
    wait = WebDriverWait(driver, 25)
    print("--- Starting Form Fill ---")
    driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.ID, "chkYes" if search_by == "courtComplex" else "chkNo"))))
    Select(wait.until(EC.element_to_be_clickable((By.ID, "est_code" if search_by == "courtComplex" else "court_establishment")))).select_by_value(primary_val)
    time.sleep(2)
    court_dropdown_element = wait.until(EC.element_to_be_clickable((By.ID, "court")))
    wait.until(lambda d: len(Select(d.find_element(By.ID, "court")).options) > 1)
    Select(court_dropdown_element).select_by_value(court_val)
    date_to_set = date_obj.strftime("%m/%d/%Y")
    js_script = f"""
        let el = document.getElementById('date');
        el.value = '{date_to_set}';
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        el.blur();
    """
    driver.execute_script(js_script)
    time.sleep(1)
    driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.ID, "chkCauseTypeCivil" if case_type == "Civil" else "chkCauseTypeCriminal"))))
    wait.until(EC.visibility_of_element_located((By.ID, "siwp_captcha_value_0"))).send_keys(captcha)
    driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.NAME, "submit"))))
    print("--- Form Submitted ---")

def process_cause_list(driver, search_by, primary_val, court_val, date_obj, case_type, captcha):
    try:
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "chkYes")))
        _fill_out_form(driver, search_by, primary_val, court_val, date_obj, case_type, captcha)
        result = _scrape_and_process_result(driver)
        return result
    except Exception:
        detailed_error = traceback.format_exc()
        return {"status": "error", "data": f"A critical error occurred: {detailed_error}"}
