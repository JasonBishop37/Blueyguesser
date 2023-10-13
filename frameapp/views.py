import base64
import json
import os
import random
import re
from moviepy.editor import *
from django.http import HttpResponse, JsonResponse
import io
from PIL import Image
import numpy as np
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('api_key')
ENCRYPTION_KEY = os.getenv('encryption_key')

folder_path = "Episodes/"
episode_begin = 26 
episode_end = 421
supported_formats = ["mp4","mkv"]

# API_KEY = "v3ry_s3cure_api_key69"
# ENCRYPTION_KEY = 'h-P_xUmVrnXaK0V8fHrBrf10hQte61riRDXmuQUKGZs='

def encrypt_data(data):
    cipher_suite = Fernet(ENCRYPTION_KEY)
    encrypted_data = cipher_suite.encrypt(data.encode())
    return base64.urlsafe_b64encode(encrypted_data).decode()


def decrypt_data_web(request, encrypted_data):
    try:
        api_key = request.META.get('HTTP_AUTHORIZATION', '').split('Bearer ')[1]

        if not(api_key == api_key):
            return JsonResponse({"error": "Invalid api key"})
        
        
        encrypted_data= json.loads(encrypted_data)

        frame_info = {
                "episode_name": decrypt_data(encrypted_data["episode_name"]),
                "episode_number": decrypt_data(encrypted_data["episode_number"]),
                "frame_time": decrypt_data(encrypted_data["frame_time"])     
            }
        return JsonResponse(frame_info)
    except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


def decrypt_data(encrypted_data):
    cipher_suite = Fernet(ENCRYPTION_KEY)
    decrypted_data = cipher_suite.decrypt(base64.urlsafe_b64decode(encrypted_data.encode()))
    return decrypted_data.decode()




def get_episode_name(request):
    api_key = request.META.get('HTTP_AUTHORIZATION', '').split('Bearer ')[1]

    if not(api_key == api_key):
        return JsonResponse({"error": "Invalid api key"})


    try:

        file_names = [
                f
                for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f))
            ]
        
        try:
            ep_number = random.choice(file_names)
        except Exception as e:
            return JsonResponse({"error": str(e) + ". The folder " + folder_path + " is empty"}, status=500)

        frame_time = round(random.uniform(episode_begin, episode_end), 2)
        

        with open("episode_data.json", "r") as file:
            data = json.load(file)

        ep_list = data['episodes']
        
        for i in ep_list:
            if i["season_number"] == int(ep_number[1:3]) and i["episode_number"] == int(ep_number[4:6]):    
                episode_name = (i["perLanguage"][0]["name"])
                break

        
        frame_info = {
            "episode_name": encrypt_data(episode_name),
            "episode_number": encrypt_data(ep_number),
            "frame_time": encrypt_data(str(frame_time))     
        }

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse(frame_info)



def give_image(request, episode_number, frame_time):
    episode_number = decrypt_data(episode_number)
    frame_time = decrypt_data(frame_time)

    api_key = request.META.get('HTTP_AUTHORIZATION', '').split('Bearer ')[1]
    if not(api_key == api_key):
        return HttpResponse({"error": "Invalid api key"})

    if not(episode_number[-3:] in supported_formats):
        return HttpResponse({"error unsupported file type only these are supported " + supported_formats}, status=400)
    elif "/" in episode_number:
        return HttpResponse({"error a '/' was found in episode_number"}, status=400)

    try:

        clip = VideoFileClip(folder_path + episode_number)


        frame = clip.get_frame(float(frame_time))
        image = Image.fromarray(np.uint8(frame))
        buffer = io.BytesIO()

        image.save(buffer, format="JPEG")

        jpeg_bytes = buffer.getvalue()
        buffer.truncate(0)

    except Exception as e:
        return HttpResponse({"error" + str(e)}, status=500)

    return HttpResponse(jpeg_bytes, content_type="image/jpeg")



def search(request, user_input, fuzziness, name_weight, overview_weight):
    api_key = request.META.get('HTTP_AUTHORIZATION', '').split('Bearer ')[1]
    if not(api_key == api_key):
        return JsonResponse({"error": "Invalid api key"})

    try:

        fuzziness = int(fuzziness)
        name_weight = float(name_weight)
        overview_weight = float(overview_weight)
        result = []

        with open("episode_data.json", "r") as file:
            data = json.load(file)
        
        episodes = data['episodes']
    
    
        def custom_name_scoring(query, choice):
            name_score = fuzz.partial_ratio(query, choice)
            total_score = (name_score * name_weight)
            return total_score

        def custom_overview_scoring(query, choice):
            overview_score = fuzz.partial_ratio(query, choice)
            total_score = (overview_score * overview_weight)
            return total_score


        if name_weight != 0:
        # Perform fuzzy search for episode names and get a list of matches sorted by the custom scoring function
            episode_names = [f"{i}+  {episode['perLanguage'][0]['name']}" for i, episode in enumerate(episodes)]
            name_matches = process.extract(user_input, episode_names, scorer=custom_name_scoring, limit=None)

            for match in name_matches:
                if match[1] >= fuzziness:
                    value = re.match(r'^(\d+)', match[0])
                    extracted_number = value.group(1)
                    result.append(episodes[int(extracted_number)])


        if overview_weight != 0:
        # Perform fuzzy search for episode overviews and get a list of matches sorted by the custom scoring function
            episode_overviews = [f"{i}+ {episode['perLanguage'][0]['overview']}" for i, episode in enumerate(episodes)] 
            overview_matches = process.extract(user_input, episode_overviews, scorer=custom_overview_scoring, limit=None)

            for match in overview_matches:
                if match[1] >= fuzziness:
                    value = re.match(r'^(\d+)', match[0])
                    extracted_number = value.group(1)
                    result.append(episodes[int(extracted_number)])

    except Exception as e:
        return JsonResponse({"error" : str(e)}, status=500)
    
    return JsonResponse(result, safe=False)



