# import os

# # Force DeepFace to use your media/deepface_models folder
# custom_deepface_folder = os.path.join(os.path.dirname(__file__), "media", "deepface_models")
# os.environ["DEEPFACE_HOME"] = custom_deepface_folder
# os.makedirs(custom_deepface_folder, exist_ok=True)

# from deepface import DeepFace  # <-- import AFTER setting DEEPFACE_HOME

# print("Downloading Facenet model...")
# DeepFace.build_model("Facenet")
# print("✅ Facenet model downloaded to:", custom_deepface_folder)