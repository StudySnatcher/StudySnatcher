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


def matches_filter(data, filters):
    """
    Check if a data entry matches all the filter criteria.

    :param data: A dictionary representing a single data entry.
    :param filters: A dictionary of filter criteria, where keys can represent nested fields (e.g., "user_data.id").
    :return: True if the data entry matches all filter criteria, False otherwise.
    """
    # {
    #     'file_id': <int>,
    #     'file_name': <str>,
    #     'description': <str>,
    #     'uploaded': <str>,
    #     'time': <str>,
    #     'course_id': <int>,
    #     'course_name': <str>,
    #     'course_link': <str>,
    #     'university_id': <int>,
    #     'university_name': <str>,
    #     'semester_id': <int>,
    #     'semester': <str>,
    #     'has_ai_content': <bool>,
    #     'flashcard_set_id': <None or int>,
    #     'study_list_id': <None or int>,
    #     'professor': <str>,
    #     'visibility': <int>,
    #     'file_type': <int>,
    #     'type_name': <str>,
    #     'is_owner': <bool>,
    #     'is_followed': <bool>,
    #     'is_infected': <bool>,
    #     'link': <str>,
    #     'preview_link': <str>,
    #     'uservote': <bool>,
    #     'user_star_vote': <int>,
    #     'avg_star_score': <int>,
    #     'upvotes': <int>,
    #     'downvotes': <int>,
    #     'rating': <int>,
    #     'downloads': <int>,
    #     'questions': <int>,
    #     'user_data': {
    #         'id': <None or int>,
    #         'identity_id': <None or int>,
    #         'name': <str>,
    #         'link': <str>,
    #         'picture': <str>,
    #         'profile_picture': <str>,
    #         'karma_points': <None or int>,
    #         'gamify_avatar_url': <None or str>,
    #         'time': <str>,
    #         'is_deleted': <bool>
    #     }
    # }

    for key, value in filters.items():
        keys = key.split(".")  # Handle nested keys like "user_data.id"
        field = data
        for k in keys:
            if isinstance(field, dict) and k in field:
                field = field[k]
            else:
                return False  # Field does not exist

        if isinstance(field, str):
            if str(value).lower() not in field.lower():
                return False
        else:
            # Perform a direct comparison for non-strings
            if field != value:
                return False
    return True


def get_course_documents(course_id, session, filters):
    """Retrieves all document IDs for a given course."""
    documents = []
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

        files = data.get("files", [])

        documents.extend(
            (file["file_id"], file["file_name"],
             file["uploaded"], file["semester"],
             file["professor"])
            for file in files
            if "file_id" in file and "uploaded" in file
            and "file_name" in file and "semester" in file
            and "professor" in file
            and matches_filter(file, filters)
        )

        has_next_page = data.get("last_page", current_page) > current_page
        current_page += 1

    return documents


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


def change_file_timestamp(file_path, new_timestamp):
    """
    Changes the modification and access time of a file to the given timestamp.

    :param file_path: Path to the file
    :param new_timestamp: Timestamp in the format 'YYYY-MM-DD HH:MM:SS'
    """
    try:
        # Parse the new timestamp string into a datetime object
        new_time = datetime.strptime(new_timestamp, '%Y-%m-%d %H:%M:%S')

        # Convert the datetime object to a Unix timestamp
        new_unix_time = new_time.timestamp()

        # Use os.utime to update the file's access and modification times
        os.utime(file_path, (new_unix_time, new_unix_time))

        # print(f"Timestamp of '{file_path}' changed to {new_timestamp}")
    except Exception as e:
        print(f"An error occurred when trying to change the timestamp of '{
              file_path}' to {new_timestamp}: {e}")


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


def get_unique_filename(filepath):
    """
    Given a file path, return a unique file path by appending a number 
    (e.g. ' (1)', ' (2)', ...) until the name doesn't exist.
    """
    # Split the filepath into name and extension
    base, ext = os.path.splitext(filepath)

    # If there's no conflict, just return the original filepath
    if not os.path.exists(filepath):
        return filepath

    # Otherwise, try appending a counter until you find a name that doesn't exist
    counter = 1
    while True:
        new_filename = f"{base} ({counter}){ext}"
        if not os.path.exists(new_filename):
            return new_filename
        counter += 1


# Main logic
def run(username, password, course_url, converted_to_pdf, filters):
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

    docs = get_course_documents(course_number, session, filters)
    for doc_id, doc_name, upload_time, semester, prof in docs:
        url = get_download_link(doc_id, session, converted_to_pdf)
        if not url:
            continue

        if '.' in doc_name:
            filename = doc_name
        else:
            filename = get_filename_from_url(url).replace("+", " ").replace("C3B6", "ö").replace(
                "C396", "Ö").replace("C3A4", "ä").replace("C384", "Ä").replace("C3BC", "ü").replace("C39C", "Ü").replace("UCC88", "Ü")
            # filename = decode_utf8_hex(filename)

        base, ext = os.path.splitext(filename)
        if str(semester).strip():
            base += " - " + str(semester).replace("/", "-")
        if str(prof).strip():
            base += " Prof " + prof

        filename = base + ext

        save_path = get_unique_filename(os.path.join(folder_path, filename))
        download_file(url, save_path)
        change_file_timestamp(save_path, upload_time)

    print("All files downloaded.")
