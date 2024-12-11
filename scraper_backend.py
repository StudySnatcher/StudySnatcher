import os
import time
import hashlib
import requests
import re
from datetime import datetime
from urllib.parse import urlparse


BASE_URL = "https://gateway.production-01.studydrive.net"
DOWNLOAD_SECRET = "studydrive-app-download-7>%jsc"


def generate_download_token(document_id):
    """Generates a download token for the specified document ID."""
    return hashlib.md5((DOWNLOAD_SECRET + str(document_id)).encode("ascii")).hexdigest()


def retry_on_rate_limit(session, url, **kwargs):
    """
    Handles rate-limiting by retrying the request after the specified delay.
    """
    while True:
        response = session.get(url, **kwargs)
        if response.status_code == 429:  # Rate limit hit
            retry_after = int(response.headers.get("retry-after", 60))
            print(f"Rate limit reached. Retrying after {
                  retry_after} seconds...")
            time.sleep(retry_after)
            continue
        return response


def get_download_link(document_id, session, pdf_converted):
    """Fetches the download link for the specified document ID."""
    url = f"{BASE_URL}/legacy-api/v1/documents/{document_id}/download"
    params = {
        "converted_file": pdf_converted,
        "download-token": generate_download_token(document_id),
        "preview": "true",
    }
    response = retry_on_rate_limit(
        session, url, params=params, allow_redirects=False)
    location = response.headers.get("Location")
    if not location:
        if pdf_converted == "false":
            print(f"Unexpected response headers: {response.headers}")
            print(f"Response body: {response.text}")
            return None
        else:
            print(
                "Unexpected error with document, downloading it in its original format...")
            return get_download_link(document_id, session, "false")
    return location


def get_course_documents(course_id, session):
    """Retrieves all document IDs for a given course."""
    document_ids = []
    current_page = 0
    has_next_page = True

    while has_next_page:
        url = f"{BASE_URL}/legacy-api/v1/feed/courses/{course_id}/documents"
        params = {
            "page": current_page,
            "reference_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        response = retry_on_rate_limit(
            session, url, params=params)
        data = response.json()

        # TODO: check
        document_ids.extend(f["file_id"]
                            for f in data.get("files", []) if "file_id" in f)
        has_next_page = data.get("last_page", current_page) > current_page
        current_page += 1

    return document_ids


def initialize_session():
    """Initializes and authenticates a session with custom headers."""
    session = requests.session()

    # Fetch cookies
    session.get("https://www.studydrive.net/app-api-version")
    # for c in list(resp.cookies):
    #     session.cookies.set(c.name, c.value)

    # Generate client secret
    seed_response = session.get(f"{BASE_URL}/auth/v1/seed")
    seed = seed_response.json()["seed"]
    seed_key_map = {
        "*5b8v$c8D%&t4Nbf": "CBf&r8WTq#!GMWcKVDXaIkOvxI&bS@IRqadCtPe28MMd*QTA2T2g$*RjUnmbyfl7",
        "54qRT5W5&O!p1AC7": "c1Sv2Xz3IJy^#ljRKmgx#Sf$U1XKMAX4jVzVeS!^eHQP!sRxjjeK2msSt&0!X20Z",
        "84V*x5*x#z9xE7Ic": "eaDA1%7#@*5osw7&uoO176AE$t*dliy*YrXkev4zDQ9PX21808yD4!wVO8MDj7JX",
        "xOt#VgqVC^91e@@J": "lb7QjiGFczZwIlgpHtTb!fa6QkPF$wVXg43^kZt9434Cf%JpZU0SwHY1@SIiWnwe",
        "vxx!%uL0v!1c3@Mm": "C2@X%o3O$#$h*fLCZK*SJVjdp8uNJ%*NVj5NrsCNFZi8TZpDRJpWGJiEDG$BRjFD"
    }
    native_seed = list(seed_key_map.items())[0]
    client_secret = hashlib.sha256(
        (seed + native_seed[1]).encode("ascii")).hexdigest() + "." + native_seed[0]

    session.headers.update({
        "X-SD-Platform": "Android",
        "X-SD-Build": "773",
        "User-Agent": "Studydrive/3.18.1 (com.studydrive.app; build:2019; iOS 17.2.1) Alamofire/5.4.4",
        "Sd-Client-Secret": client_secret,
    })

    return session


def login(username, password):
    """Logs in with the provided username and password."""
    session = initialize_session()
    response = session.post(f"{BASE_URL}/users/v1/auth/login",
                            data={"email": username, "password": password})
    response.raise_for_status()
    session.headers["Authorization"] = "Bearer " + \
        response.json()["access_token"]
    return session


def get_filename_from_url(url):
    """Extracts the filename from a URL."""
    return os.path.basename(urlparse(url).path)


def download_file(url, save_path):
    """Downloads a file from the given URL and saves it to the specified path."""
    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        print(f"File downloaded successfully: {save_path}")
    except requests.RequestException as e:
        print(f"Error downloading file: {e}")


def create_folder(folder_path):
    """Creates a folder, deleting it first if it already exists."""
    # if os.path.exists(folder_path):
    #     print(f"Folder '{folder_path}' exists. Deleting it.")
    #     shutil.rmtree(folder_path)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"New folder created: '{folder_path}'")


def extract_course_info(url):
    # Regular expression to match the course name and number
    pattern = r"/course/([^/]+)/(\d+)"
    match = re.search(pattern, url)
    if match:
        course_name = match.group(1).replace('-', ' ').capitalize()
        course_number = match.group(2)
        return course_name, course_number
    else:
        return None, None


def decode_utf8_hex(string):
    # Regular expression to find hex codes (C3B6 etc.)
    hex_pattern = re.compile(r'[A-F0-9]{4}')
    # hex_pattern = re.compile(r'(?:[A-Fa-f0-9]{2}){2,}')

    # Replace each match with its decoded UTF-8 character
    def replace_hex(match):
        hex_code = match.group(0)  # Extract the matched hex code
        try:
            # Decode to character
            return bytes.fromhex(hex_code).decode('utf-8')
        except UnicodeDecodeError:
            return hex_code  # If decoding fails, return the hex code as is

    return hex_pattern.sub(replace_hex, string)

# Main logic


def run(username, password, course_url, converted_to_pdf):
    session = login(username, password)

    course_name, course_number = extract_course_info(course_url)
    if course_name and course_number:
        print(f"Course Name: {course_name}")
        print(f"Course Number: {course_number}")
    else:
        raise Exception("No course information found in link {course_url}")

    # remove invalid characters
    folder_path = re.sub(r'[<>:"/\\|?*\n\t]', '', course_name)
    create_folder(folder_path)

    for doc_id in get_course_documents(course_number, session):
        url = get_download_link(doc_id, session, converted_to_pdf)
        if not url:
            continue
        filename = get_filename_from_url(url).replace("+", " ").replace("C3B6", "ö").replace(
            "C396", "Ö").replace("C3A4", "ä").replace("C384", "Ä").replace("C3BC", "ü").replace("C39C", "Ü").replace("CC88", "ä")
        #filename = decode_utf8_hex(filename)
        save_path = os.path.join(folder_path, filename)
        if not os.path.exists(save_path):
            download_file(url, save_path)

    print("All files downloaded.")
