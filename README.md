# AI-Based Smart Surveillance and Threat Detection System

### Raspberry Pi | Python | YOLO | Dlib | OpenCV | Firebase | Flutter

An AI-powered smart surveillance and access-control prototype developed as a Final Year Project. The system combines real-time face recognition, weapon detection, Raspberry Pi-based relay control, and cloud-connected monitoring.

## Project Overview

Traditional surveillance systems often depend on continuous human monitoring and manual responses. This project explores automated identity verification, weapon detection, and intelligent access control using edge AI.

The system processes video streams from two IP cameras and uses computer vision to evaluate security conditions before making access-control decisions.

## Key Features

- **Face Recognition:** Uses Dlib's ResNet-based face embeddings to identify registered individuals.
- **Weapon Detection:** Uses a custom YOLO model to detect trained weapon categories.
- **Dual-Camera Monitoring:** Processes separate RTSP camera streams for identity recognition and object detection.
- **Automated Door Control:** Uses Raspberry Pi GPIO and a relay to control electronic access.
- **Firebase Integration:** Synchronizes security alerts and door status with Firebase Realtime Database.
- **Mobile Monitoring:** Supports cloud-based monitoring and command integration through a Flutter application.
- **Edge AI:** Performs computer vision inference locally on Raspberry Pi hardware.
- **Performance Optimization:** Uses frame skipping, image resizing, and asynchronous processing.

## Technologies Used

| Category | Technology |
|---|---|
| Programming | Python |
| Computer Vision | OpenCV |
| Face Detection | Dlib |
| Face Recognition | Dlib ResNet |
| Object Detection | YOLO (Ultralytics) |
| Hardware | Raspberry Pi, GPIO Relay, IP Cameras |
| Database | Firebase Realtime Database |
| Mobile Application | Flutter |
| AI Computing | Raspberry Pi Edge Computing |

## System Workflow

1. IP cameras capture live video streams.
2. OpenCV retrieves camera frames for processing.
3. Dlib detects faces and calculates face embeddings.
4. Registered identities are compared against stored face encodings.
5. YOLO checks camera frames for trained weapon categories.
6. The access-control logic evaluates identity and threat conditions.
7. Raspberry Pi GPIO controls the door relay.
8. Firebase records security alerts and door status.
9. The mobile application can display synchronized monitoring information.

## System Architecture

### System Design

The following diagram illustrates the overall architecture of the AI-powered smart surveillance system.

![FYP System Design](images/FYP%20System%20Design.png)

### Hardware Circuit Diagram

The following diagram shows the hardware connections used in the Raspberry Pi-based security system.

![FYP Circuit Diagram](images/FYP%20Circuit%20Diagram.png)


The prototype consists of four main layers:

**1. Input Layer:** IP cameras and RTSP video streams.

**2. AI Processing Layer:** Face detection, face recognition, and YOLO-based weapon detection.

**3. Control Layer:** Raspberry Pi decision logic, GPIO, and electronic locking relay.

**4. Cloud and Application Layer:** Firebase Realtime Database and Flutter mobile monitoring.

## Security and Implementation Notes

This repository contains a refined prototype implementation. Camera credentials and Firebase service-account keys must be configured privately and must never be committed to the repository.

Remote unlocking is disabled in the refined public implementation until authenticated and authorized command handling is implemented.

The system requires actual Raspberry Pi hardware, compatible IP cameras, trained model files, and an appropriately configured Firebase project to run.

## Future Improvements

- Stronger mobile command authentication and authorization.
- Improved multi-camera threat detection.
- Performance benchmarking on Raspberry Pi.
- Security-event history and analytics.
- Additional testing for false positives, false negatives, and camera disconnections.
- Hardware fail-safe and fail-secure validation.

## Project Type

Final Year Project — Computer Engineering

## Author

**Malik Mahad Asif**

GitHub: https://github.com/MalikMahadAsif

Portfolio: https://malikmahadasif.github.io/

## Disclaimer

This project is an academic research prototype intended for learning and demonstration. It has not been independently validated or certified for deployment as a production security or emergency-response system.
