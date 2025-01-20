from flask import (
    Flask,
    render_template,
    request,
    send_file,
    flash,
    redirect,
    send_from_directory,
)
import pandas as pd
from io import StringIO, BytesIO
import os
from hyparse import Hy3File
import logging
from werkzeug.utils import secure_filename
import zipfile


UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "results"  # Define this at the top level
ALLOWED_EXTENSIONS = {"hy3"}
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["DOWNLOAD_FOLDER"] = DOWNLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def download(filename):
    return send_from_directory(
        directory=app.config["DOWNLOAD_FOLDER"],
        path=filename,
        as_attachment=True,  # This ensures the file is downloaded rather than displayed
    )


# Configure logging
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s",
)

# Create the uploads and downloads folders if they don't exist
for folder in [UPLOAD_FOLDER, DOWNLOAD_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "hy3_file" not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files["hy3_file"]
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            app.logger.info("Saving uploaded file")
            file.save(file_path)
            file.seek(0)
            app.logger.info(f"Uploaded file saved to {file_path}")
            try:
                app.logger.info(f"Parsing file at {file_path}")
                # Parse the .hy3 file
                hy3_file = Hy3File(file_path)

                # Get meet name
                meet_name = hy3_file.meet_info.meet_name
                app.logger.info(f"Meet name: {meet_name}")

                app.logger.info("Converting results to DataFrames")
                # Convert results to DataFrames
                individual_results_df = hy3_file.individual_results_to_df()
                relay_results_df = hy3_file.relay_results_to_df()

                app.logger.info("Saving results to CSV")
                # Save CSVs to the download folder
                individual_csv_path = os.path.join(
                    app.config["DOWNLOAD_FOLDER"], "individual_results.csv"
                )
                relay_csv_path = os.path.join(
                    app.config["DOWNLOAD_FOLDER"], "relay_results.csv"
                )
                app.logger.info(f"Saved individual resuls to {individual_csv_path}")

                individual_results_df.to_csv(individual_csv_path, index=False)
                relay_results_df.to_csv(relay_csv_path, index=False)

                app.logger.info("Downloading results")
                # Return the first CSV - you might want to zip both files instead
                # Create ZIP file containing both CSVs
                memory_file = BytesIO()

                with zipfile.ZipFile(memory_file, "w") as zf:
                    zf.write(
                        filename=individual_csv_path, arcname="individual_results.csv"
                    )
                    zf.write(filename=relay_csv_path, arcname="relay_results.csv")
                memory_file.seek(0)
                # Remove individual CSV files after zipping
                os.remove(individual_csv_path)
                os.remove(relay_csv_path)
                return send_file(
                    memory_file,
                    mimetype="application/zip",
                    as_attachment=True,
                    download_name=f"{meet_name}_csv.zip",
                )

                # return download(filename="individual_results.csv")

            except Exception as e:
                app.logger.error(f"Error processing file: {e}")
                return f"Error processing file: {e}"

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
