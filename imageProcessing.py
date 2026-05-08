from flask import Flask, request, jsonify
from supabase import create_client
from backgroundremover.bg import remove
from dotenv import load_dotenv

import os
from datetime import datetime

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET = "products"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_to_supabase(path, file_bytes, content_type):
    supabase.storage.from_(BUCKET).upload(
        path,
        file_bytes,
        file_options={
            "content-type": content_type
        }
    )


@app.route("/process", methods=["POST"])
def process_image():

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files["file"]

    custom_name = request.form.get("name")

    ext = file.filename.rsplit(".", 1)[-1].lower()

    # add date for uniqueness
    date_str = datetime.now().strftime("%Y-%m-%d")

    # base name logic
    if custom_name:
        base_name = custom_name.replace(" ", "_")
    else:
        base_name = file.filename.rsplit(".", 1)[0]

    final_name = f"{base_name}_{date_str}"

    raw_filename = f"{final_name}.{ext}"
    processed_filename = f"{final_name}.png"

    raw_storage_path = f"images/raw/{raw_filename}"
    processed_storage_path = f"images/processed/{processed_filename}"

    try:

        # read file into memory (NO LOCAL STORAGE)
        input_data = file.read()

        # remove background
        output_data = remove(input_data)

        # ensure bytes (important fix for memoryview outputs)
        if isinstance(output_data, memoryview):
            output_data = output_data.tobytes()

        # upload raw image
        upload_to_supabase(
            raw_storage_path,
            input_data,
            f"image/{ext}"
        )

        # upload processed image
        upload_to_supabase(
            processed_storage_path,
            output_data,
            "image/png"
        )

        # generate URLs
        raw_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{raw_storage_path}"
        processed_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{processed_storage_path}"

        return jsonify({
            "success": True,
            "name": final_name,
            "rawUrl": raw_url,
            "processedUrl": processed_url
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run()
