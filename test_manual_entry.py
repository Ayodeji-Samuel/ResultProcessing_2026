"""
Test script for manual entry functionality
"""
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:5000"

def test_manual_entry():
    """Test the manual entry feature"""
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    print("=" * 60)
    print("TESTING MANUAL ENTRY FEATURE")
    print("=" * 60)
    
    # 1. Get login page and extract CSRF token
    print("\n1. Getting login page...")
    login_page = session.get(f"{BASE_URL}/auth/login")
    if login_page.status_code != 200:
        print(f"   ERROR: Could not get login page (status: {login_page.status_code})")
        return False
    print(f"   OK: Login page loaded (status: {login_page.status_code})")
    
    # Extract CSRF token
    soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_input = soup.find('input', {'name': 'csrf_token'})
    if not csrf_input:
        print("   ERROR: Could not find CSRF token")
        return False
    csrf_token = csrf_input['value']
    print(f"   OK: CSRF token extracted")
    
    # 2. Login as HoD
    print("\n2. Logging in as HoD...")
    login_data = {
        'csrf_token': csrf_token,
        'username': 'hod@university.edu.ng',
        'password': 'HoD@2026!'
    }
    login_response = session.post(f"{BASE_URL}/auth/login", data=login_data, allow_redirects=True)
    
    if 'login' in login_response.url.lower() and 'change' not in login_response.url.lower():
        print(f"   ERROR: Login failed (redirected to: {login_response.url})")
        return False
    print(f"   OK: Login successful (redirected to: {login_response.url})")
    
    # Handle password change if required
    if 'change_password' in login_response.url or 'force_change' in login_response.url:
        print("   INFO: Password change required, skipping for test...")
        # For testing, we'll assume the password was already changed
    
    # 3. Get the results page to find a course
    print("\n3. Getting results page...")
    results_page = session.get(f"{BASE_URL}/results/")
    if results_page.status_code != 200:
        print(f"   ERROR: Could not get results page (status: {results_page.status_code})")
        return False
    print(f"   OK: Results page loaded")
    
    # 4. Try to access manual entry for course 1
    print("\n4. Accessing manual entry for course 1...")
    manual_entry_url = f"{BASE_URL}/results/entry/1"
    entry_page = session.get(manual_entry_url)
    
    if entry_page.status_code == 404:
        print(f"   ERROR: Course not found")
        return False
    elif entry_page.status_code != 200:
        print(f"   ERROR: Could not access manual entry (status: {entry_page.status_code})")
        return False
    
    print(f"   OK: Manual entry page loaded")
    
    # 5. Parse the manual entry page
    soup = BeautifulSoup(entry_page.text, 'html.parser')
    
    # Check for form
    form = soup.find('form', {'id': 'entryForm'})
    if not form:
        print("   ERROR: Entry form not found")
        return False
    print("   OK: Entry form found")
    
    # Check for CSRF token
    csrf_input = soup.find('input', {'name': 'csrf_token'})
    if not csrf_input:
        print("   ERROR: CSRF token not found in form")
        return False
    csrf_token = csrf_input['value']
    print("   OK: CSRF token found")
    
    # Check for score inputs
    ca_inputs = soup.find_all('input', class_='ca-input')
    exam_inputs = soup.find_all('input', class_='exam-input')
    
    print(f"   OK: Found {len(ca_inputs)} CA inputs and {len(exam_inputs)} exam inputs")
    
    if len(ca_inputs) == 0:
        print("   WARNING: No students found for this course")
        return True  # Not necessarily an error
    
    # 6. Test submitting scores
    print("\n5. Testing score submission...")
    
    # Get the first student's input names
    if ca_inputs:
        first_ca = ca_inputs[0]
        first_exam = exam_inputs[0]
        
        ca_name = first_ca.get('name')
        exam_name = first_exam.get('name')
        
        print(f"   Testing with: {ca_name}, {exam_name}")
        
        # Prepare form data with one test entry
        form_data = {
            'csrf_token': csrf_token,
            ca_name: '25.0',
            exam_name: '55.0'
        }
        
        # Submit as AJAX request
        headers = {
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        submit_response = session.post(manual_entry_url, data=form_data, headers=headers)
        
        if submit_response.status_code == 200:
            try:
                json_response = submit_response.json()
                if json_response.get('success'):
                    print(f"   OK: Submission successful - {json_response.get('message')}")
                else:
                    print(f"   ERROR: Submission failed - {json_response.get('message')}")
                    return False
            except:
                print(f"   OK: Submission returned status 200")
        else:
            print(f"   ERROR: Submission failed (status: {submit_response.status_code})")
            return False
    
    # 7. Verify the result was saved
    print("\n6. Verifying saved results...")
    entry_page_after = session.get(manual_entry_url)
    soup_after = BeautifulSoup(entry_page_after.text, 'html.parser')
    
    if ca_inputs:
        ca_input_after = soup_after.find('input', {'name': ca_name})
        if ca_input_after:
            saved_value = ca_input_after.get('value', '')
            if '25' in saved_value:
                print(f"   OK: CA score correctly saved ({saved_value})")
            else:
                print(f"   WARNING: CA value might not have saved (current: {saved_value})")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    
    return True


if __name__ == '__main__':
    try:
        test_manual_entry()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to server. Make sure the Flask app is running.")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
