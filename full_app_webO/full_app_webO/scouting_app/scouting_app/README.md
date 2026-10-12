# Badminton Scouting AI — Flutter App

Field scout mobile app for badminton talent discovery.
Connects to the Django backend at `192.168.1.104:8000`.

---

## Project structure

```
lib/
├── main.dart                          ← App entry point
├── core/
│   ├── constants/app_constants.dart   ← API URLs, test types, score bands
│   ├── network/
│   │   ├── api_service.dart           ← All HTTP calls to Django
│   │   └── local_db.dart             ← SQLite offline cache + sync queue
├── shared/
│   └── theme/app_theme.dart          ← Dark navy design system
├── features/
│   ├── auth/
│   │   ├── providers/auth_provider.dart
│   │   ├── screens/login_screen.dart
│   ├── players/
│   │   ├── models/player_model.dart
│   │   ├── providers/player_provider.dart
│   │   ├── screens/player_list_screen.dart
│   │   └── screens/new_player_screen.dart
│   ├── assessments/
│   │   ├── models/assessment_model.dart
│   │   ├── providers/assessment_provider.dart
│   │   ├── screens/dashboard_screen.dart
│   │   ├── screens/new_assessment_screen.dart
│   │   └── screens/assessment_detail_screen.dart
│   ├── tests/
│   │   └── screens/test_upload_screen.dart
│   └── results/
│       └── screens/results_screen.dart
```

---

## Setup

### 1. Install Flutter dependencies

```bash
cd scouting_app
flutter pub get
```

### 2. Verify device is on the same Wi-Fi as the Django server

The backend runs at `192.168.1.104:8000`.
Your phone must be on the same network.

### 3. Start the Django backend first

```bash
cd scouting_backend
python manage.py runserver 0.0.0.0:8000
```

### 4. Run the Flutter app

```bash
# Android (USB connected)
flutter run

# iOS (USB connected, Xcode configured)
flutter run -d iphone

# Specific device
flutter devices       # list devices
flutter run -d <id>
```

---

## App flow

```
Launch → check stored token
    ↓
Login screen (username / password)
    ↓
Dashboard (all assessments, stats)
    ↓
New Assessment → select or register player
    ↓
Assessment Detail (5 test cards)
    ↓
For each test: tap → record or upload video → AI runs
    ↓
Results screen (scores + metrics breakdown)
    ↓
Scout decision: Recommend / Not Recommend
```

---

## Test credentials

```
Username:  scout1
Password:  scout123
Token:     9f7aa007bf4b052f2088742b790f3cbaba15e5a2
```

---

## Offline support

- Videos recorded with no internet are queued in local SQLite
- Players and assessments cached locally after first load
- Sync happens automatically when connection is restored
- Pull-to-refresh on all list screens forces sync

---

## Changing the backend URL

Edit one line in `lib/core/constants/app_constants.dart`:

```dart
static const String baseUrl = 'http://192.168.1.104:8000';
```

---

## Build for release

```bash
# Android APK
flutter build apk --release

# Android App Bundle (Play Store)
flutter build appbundle --release

# iOS (requires Mac + Xcode)
flutter build ios --release
```
