# ENOLA FYP — refined Raspberry Pi prototype

This code expects **Python 3 on a Raspberry Pi**, the correct GPIO hardware,
working RTSP streams, and an authorized Firebase Realtime Database.

## Dependencies
- opencv-python (`cv2`), dlib, numpy, ultralytics, firebase-admin, RPi.GPIO
- `pickle`, `pathlib`, `queue`, `threading`, `logging`, and `time` are standard library modules.
- Install dependencies using versions compatible with your Raspberry Pi OS, Python and CPU architecture. `dlib` and Ultralytics may require special setup on a Pi.

## Private model files (not included)
Place trusted model files under `models/` adjacent to `surveillance.py`:
- `shape_predictor_5_face_landmarks.dat`
- `dlib_face_recognition_resnet_model_v1.dat`
- `best.pt` (custom-trained YOLO model with weapon class labels)
- `face_encodings_dlib.pkl` (trusted local enrollment data only; contains sensitive biometric information)

## Environment
Use `.env.example` as a guide, but **do not commit a real `.env` file**.
The script uses `os.getenv`, so export the variables in your shell or service configuration.

## Security / limitations
- The original camera credentials appeared in chat/source code. Rotate those passwords before any public sharing.
- Remote **lock** is accepted; remote **unlock is intentionally disabled** until an authenticated, server-authorized command mechanism is designed and tested. Firebase RTDB rules must restrict all writes to `door/control`, `door/status`, and `alerts`.
- Relay wiring must be confirmed: this assumes active-low relay and HIGH means locked. Physical safety, emergency egress, network failure and power-loss behavior require independent hardware assessment.
- The weapon hold lasts 30 seconds after a detected weapon; it is not a guarantee of threat absence. False negatives and spoofing remain possible.
- Avoid using live access-control hardware until independently reviewed and tested. Use test footage and a disconnected relay first.
- This source has been syntax-checked but not run on Raspberry Pi hardware or with the project's private models.
