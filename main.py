import re
import os
import random
from flask import Flask, request, jsonify, redirect, url_for, send_from_directory
from flasgger import Swagger, swag_from
import PIL.Image

server_url = os.environ.get(
    'SERVER_URL',
    'http://localhost:5000'
)

app = Flask(__name__, 
           static_url_path='/static',
           static_folder='static') 

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "worldview-api",
        "description": "an api-based country guessing game played on swagger",
        "version": "1.1.0",
        "uiversion": 3
    },
    "servers": [
        {
            "url": server_url,
            "description": "Cloud Run Server"
        }
    ],
    "schemes": ["https", "http"]
}

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec_1",
            "route": "/apispec_1.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/static", 
    "swagger_ui_config": {
        "docExpansion": "none",
        "deepLinking": True,
        "displayOperationId": True,
        "logo": {
            "url": "/static/images/logo.png",
            "backgroundColor": "#000000",
            "altText": "worldview-api logo"
        }
    },
    "swagger_ui_css": "/static/css/swagger-ui.css",
    "swagger_ui_bundle_js": "//unpkg.com/swagger-ui-dist/swagger-ui-bundle.js",
    "swagger_ui_standalone_preset_js": "//unpkg.com/swagger-ui-dist/swagger-ui-standalone-preset.js",
    "favicon": "/static/images/favicon.ico",
}

swagger = Swagger(app, template=swagger_template, config=swagger_config)

# HELPER FUNCTIONS
def get_country_list_from_document(document):
    trs = re.findall(r"<tr>(.*?)</tr>", document, re.DOTALL)

    tds = []
    for tr in trs:
        td_items = re.findall(r"<td>(.*?)</td>", tr, re.DOTALL)
        filtered_td = [item for item in td_items if "</a>" not in item]
        tds.extend(filtered_td)

    return [{"code": pair[0], "name": pair[1]} for pair in zip(tds[::2], tds[1::2])]

def convert_image_to_ascii(image_path):
    img = PIL.Image.open(image_path)

    background = PIL.Image.new('RGBA', img.size, (255, 255, 255, 255))

    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    img = PIL.Image.alpha_composite(background, img)
    
    img = img.convert('RGB')

    width, height = img.size
    aspect_ratio = height / width
    new_width = 120
    new_height = int(aspect_ratio * new_width * 0.55)
    img = img.resize((new_width, new_height))
    img = img.convert("L")

    chars = ["@", "J", "D", "%", "*", "P", "+", "Y", "$", ",", "."]
    pixels = img.getdata()
    new_pixels = [chars[pixel // 25] for pixel in pixels]
    new_pixels = ''.join(new_pixels)

    new_pixels_count = len(new_pixels)
    ascii_image = [new_pixels[index:index + new_width] for index in range(0, new_pixels_count, new_width)]
    ascii_image = "\n".join(ascii_image)

    return ascii_image

# ENDPOINT CONTROLLERS

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route("/")
def home():
    return redirect("/apidocs")

@app.route("/list-all-countries")
@swag_from("docs/list_all_countries.yml")
def list_all_countries():
    try:
        with open("images/all_countries/index.html", "r") as file:
            document = file.read()
        
        countries_list = get_country_list_from_document(document)

        return jsonify({"countries_list": countries_list})
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/game/guess-country")
@swag_from("docs/guess_country.yml")
def guess_country():
    answer_country_index = request.args.get("answer_country_code")
    answer_country_name = request.args.get("answer_country_name")

    if(answer_country_index and answer_country_name):
        try:
            answer_country_index = int(answer_country_index)
            
            with open("images/all_countries/index.html", "r") as file:
                document = file.read()
            
            countries_list = get_country_list_from_document(document)

            if(countries_list[answer_country_index]["name"].lower() == answer_country_name.lower()):
                return jsonify(
                    {
                        "success": True,
                        "message": "You have answered correctly!",
                        "country_code": answer_country_index,
                        "country_name": answer_country_name
                    }, 202
                )
            else:
                return jsonify(
                    {
                        "success":False, 
                        "message": "You guessed incorrectly!!!",
                        "country_code": answer_country_index,
                        "correct_country_name": countries_list[answer_country_index]["name"]
                    }, 202
                )

        except FileNotFoundError:
            return jsonify({"error": "File not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        try:
            folder_path = "images/all_countries"
            all_folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]

            if not all_folders:
                return jsonify({"error": "No folders found in the directory"}), 404

            random_index = random.randint(0, len(all_folders) - 1)

            random_folder = all_folders[random_index]
            selected_folder_path = os.path.join(folder_path, random_folder)
            file_name = "1024.png"
            file_path = os.path.join(selected_folder_path, file_name)

            if not os.path.isfile(file_path):
                return jsonify({"error": f"{file_name} not found in the folder {random_folder}"}), 404
            
            country = convert_image_to_ascii(file_path)

            with open("images/all_countries/index.html", "r") as file:
                document = file.read()
            
            countries_list = get_country_list_from_document(document)

            country_index = next(
                (index for index, country in enumerate(countries_list) 
                 if country["code"].lower() == random_folder.lower()),
                None
            )

            if country_index is None:
                return jsonify({"error": f"Country with code {random_folder} not found in the list"}), 404

            return jsonify(
                {
                    "country_code": country_index,
                    "country_shape": [country.split("\n")]
                }
            )
        except FileNotFoundError:
            return jsonify({"error": "Directory not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0")