"""ENOLA smart surveillance prototype (Raspberry Pi).

Requires controlled Firebase RTDB access, pre-trained model assets and authorized
camera streams. Test with a disconnected relay before physical deployment.
"""
import logging
import os
import pickle
import queue
import threading
import time
from collections import deque
from pathlib import Path

import cv2
import dlib
import firebase_admin
import numpy as np
import RPi.GPIO as GPIO
from firebase_admin import credentials, db
from ultralytics import YOLO

LOG = logging.getLogger("enola")
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
RELAY_PIN = 17
UNLOCK_SECONDS = 5
FRAME_SKIP = 6
FACE_SCALE = 0.35
YOLO_IMGSZ = 320
YOLO_CONF = 0.5
FACE_THRESHOLD = 0.5
ALERT_COOLDOWN = 15
DECISION_FRAMES = 5
WEAPON_HOLD_SECONDS = 30
RTSP_BUFFER = 1
WEAPON_LABELS = {"gun", "handgun", "pistol", "rifle", "weapon", "knife"}


def required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


class SurveillanceSystem:
    def __init__(self):
        self.stop_event = threading.Event()
        self.state_lock = threading.RLock()
        self.tasks = queue.Queue(maxsize=200)
        self.last_alert_times = {}
        self.history = deque(maxlen=DECISION_FRAMES)
        self.last_decision = "LOCK"
        self.last_weapon_at = float("-inf")
        self.relock_timer = None
        self.cap_face = None
        self.cap_object = None
        self.listener = None
        self.gpio_ready = False
        self.known_names = []
        self.known_encodings = np.empty((0, 128), dtype=np.float32)

    def initialize(self):
        # Validate required settings before activating GPIO or opening cameras.
        self.face_url = required_env("RTSP_FACE")
        self.object_url = required_env("RTSP_OBJECT")
        firebase_key = required_env("FIREBASE_CREDENTIALS")
        firebase_url = required_env("FIREBASE_DATABASE_URL")
        firebase_admin.initialize_app(credentials.Certificate(firebase_key),
                                      {"databaseURL": firebase_url})

        LOG.info("Loading face and weapon detection models")
        self.detector = dlib.get_frontal_face_detector()
        self.shape_predictor = dlib.shape_predictor(
            str(MODELS_DIR / "shape_predictor_5_face_landmarks.dat"))
        self.face_model = dlib.face_recognition_model_v1(
            str(MODELS_DIR / "dlib_face_recognition_resnet_model_v1.dat"))
        self.yolo = YOLO(str(MODELS_DIR / "best.pt"))
        self.yolo.to("cpu")

        with (MODELS_DIR / "face_encodings_dlib.pkl").open("rb") as handle:
            encodings, names = pickle.load(handle)  # Load trusted, locally generated files only.
        self.known_encodings = np.asarray(encodings, dtype=np.float32).reshape(-1, 128)
        self.known_names = list(names)
        if len(self.known_encodings) != len(self.known_names):
            raise ValueError("Face encodings and names count mismatch")
        if len(self.known_names) == 0:
            LOG.warning("No authorized face encodings loaded; automatic unlock disabled")

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.HIGH)  # Active-low relay; HIGH = locked.
        self.gpio_ready = True
        self.cap_face = self.open_camera(self.face_url)
        self.cap_object = self.open_camera(self.object_url)
        if not self.cap_face.isOpened() or not self.cap_object.isOpened():
            raise RuntimeError("One or both camera streams could not be opened")

        threading.Thread(target=self.firebase_worker, daemon=True).start()
        self.listener = db.reference("door/control").listen(self.on_command)
        self.enqueue(lambda: db.reference("door/status").set("locked"))
        LOG.info("Surveillance system initialized")

    @staticmethod
    def open_camera(url):
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, RTSP_BUFFER)
        return cap

    def enqueue(self, action):
        try:
            self.tasks.put_nowait(action)
        except queue.Full:
            LOG.error("Firebase task queue full; action discarded")

    def firebase_worker(self):
        while not self.stop_event.is_set():
            try:
                action = self.tasks.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                action()
            except Exception:
                LOG.exception("Firebase write failed")
            finally:
                self.tasks.task_done()

    def push_alert(self, title, message, kind, cooldown=True):
        now = time.monotonic()
        with self.state_lock:
            if cooldown and now - self.last_alert_times.get(kind, float("-inf")) < ALERT_COOLDOWN:
                return
            self.last_alert_times[kind] = now
        def write():
            db.reference("alerts").push({
                "title": title, "message": message, "type": kind,
                "timestamp": int(time.time() * 1000), "read": False,
            })
        self.enqueue(write)

    def set_door_status(self, status):
        self.enqueue(lambda: db.reference("door/status").set(status))

    def lock(self):
        with self.state_lock:
            if self.relock_timer is not None:
                self.relock_timer.cancel()
                self.relock_timer = None
            GPIO.output(RELAY_PIN, GPIO.HIGH)
            self.last_decision = "LOCK"
        self.set_door_status("locked")
        LOG.info("Door locked")

    def unlock(self, name):
        with self.state_lock:
            if time.monotonic() - self.last_weapon_at < WEAPON_HOLD_SECONDS:
                LOG.warning("Unlock blocked due to recent weapon detection")
                return
            if self.relock_timer is not None:
                self.relock_timer.cancel()
            GPIO.output(RELAY_PIN, GPIO.LOW)
            self.last_decision = "UNLOCK"
            self.relock_timer = threading.Timer(UNLOCK_SECONDS, self.lock)
            self.relock_timer.daemon = True
            self.relock_timer.start()
        self.set_door_status("unlocked")
        self.push_alert("Door Unlocked", f"Access granted: {name}", "system", cooldown=False)
        LOG.info("Door unlocked for %s", name)

    def on_command(self, event):
        # IMPORTANT: Firebase RTDB security rules MUST restrict door/control writes.
        # A Firebase listener alone does not authenticate the command's author.
        data = event.data
        if not isinstance(data, dict):
            return
        command = data.get("command")
        if command == "lock":
            self.lock()
        elif command == "unlock":
            # Fail-safe default: remote unlock disabled. Implement a trusted
            # server-side authorization workflow before enabling this feature.
            LOG.warning("Remote unlock request ignored: server-side authorization required")

    def detect_face(self, frame):
        if not len(self.known_names):
            return False, "UNKNOWN"
        small = cv2.resize(frame, None, fx=FACE_SCALE, fy=FACE_SCALE)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        for face in self.detector(rgb, 0):
            landmarks = self.shape_predictor(rgb, face)
            encoding = np.asarray(
                self.face_model.compute_face_descriptor(rgb, landmarks), dtype=np.float32)
            distances = np.linalg.norm(self.known_encodings - encoding, axis=1)
            index = int(np.argmin(distances))
            if float(distances[index]) < FACE_THRESHOLD:
                return True, self.known_names[index]
            self.push_alert("Unknown Face", "Unknown person detected", "unknown_face")
        return False, "UNKNOWN"

    def detect_weapon(self, frame):
        found = False
        for result in self.yolo(frame, imgsz=YOLO_IMGSZ, conf=YOLO_CONF,
                                stream=True, verbose=False):
            for box in result.boxes:
                label = str(self.yolo.names[int(box.cls[0])]).lower()
                if label in WEAPON_LABELS:
                    found = True
                    self.push_alert("Weapon Detected", f"{label} detected at entry", "weapon")
        if found:
            with self.state_lock:
                self.last_weapon_at = time.monotonic()
            self.lock()
        return found

    @staticmethod
    def read_frame(cap):
        return cap.read()

    def run(self):
        frame_count = 0
        try:
            self.initialize()
            while not self.stop_event.is_set():
                ok_face, face_frame = self.read_frame(self.cap_face)
                ok_object, object_frame = self.read_frame(self.cap_object)
                if not ok_face or not ok_object:
                    self.history.clear()
                    self.lock()  # Fail locked when either camera is unavailable.
                    time.sleep(0.2)
                    continue
                frame_count += 1
                if frame_count % FRAME_SKIP == 0:
                    verified, name = self.detect_face(face_frame)
                    weapon = self.detect_weapon(object_frame)
                    with self.state_lock:
                        recent_weapon = time.monotonic() - self.last_weapon_at < WEAPON_HOLD_SECONDS
                    decision = "UNLOCK" if verified and not weapon and not recent_weapon else "LOCK"
                    self.history.append(decision)
                    if len(self.history) == DECISION_FRAMES and len(set(self.history)) == 1:
                        if decision == "LOCK":
                            if self.last_decision != "LOCK":
                                self.lock()
                        elif self.last_decision != "UNLOCK":
                            self.unlock(name)
                    LOG.info("Decision: %s", decision)
                cv2.imshow("Face Camera", cv2.resize(face_frame, (320, 240)))
                cv2.imshow("Object Camera", cv2.resize(object_frame, (320, 240)))
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        except KeyboardInterrupt:
            LOG.info("Interrupted by user")
        finally:
            self.shutdown()

    def shutdown(self):
        self.stop_event.set()
        with self.state_lock:
            if self.relock_timer is not None:
                self.relock_timer.cancel()
            if self.gpio_ready:
                GPIO.output(RELAY_PIN, GPIO.HIGH)
        if self.listener is not None:
            try:
                self.listener.close()
            except Exception:
                LOG.exception("Could not close Firebase listener")
        for cap in (self.cap_face, self.cap_object):
            if cap is not None:
                cap.release()
        cv2.destroyAllWindows()
        if self.gpio_ready:
            GPIO.cleanup()
        LOG.info("Shutdown complete; relay set to locked state")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    SurveillanceSystem().run()
