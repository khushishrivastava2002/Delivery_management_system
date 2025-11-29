# Delivery Application

A comprehensive delivery management system comprising a FastAPI backend and a React Native (Expo) frontend for delivery personnel.

## Project Structure

- **backend/**: FastAPI server handling orders, users, and location tracking.
- **frontend/**: React Native mobile application for delivery persons.

## Features

- **Delivery Person Management**: Registration, Login, Profile, Status (Active/Inactive).
- **Order Management**: View assigned orders, update status (Picked Up, Reached, Delivered), Upload Proof of Delivery.
- **Location Tracking**: Real-time location tracking of delivery personnel.
- **Admin Dashboard**: (API endpoints available) Manage delivery persons and orders.

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: MongoDB (with Motor & Beanie ODM)
- **Authentication**: JWT (JSON Web Tokens)
- **Language**: Python 3.x

### Frontend
- **Framework**: React Native (Expo)
- **Language**: TypeScript
- **Routing**: Expo Router
- **HTTP Client**: Axios

## Getting Started

### Prerequisites
- Node.js & npm/yarn
- Python 3.8+
- MongoDB (Local or Atlas)

### Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Create a `.env` file in the `backend` directory with the following variables:
   ```env
   MONGO_URL=mongodb://localhost:27017
   DB_NAME=delivery_db
   SECRET_KEY=your_secret_key_here
   DOCS_USERNAME=admin
   DOCS_PASSWORD=admin
   ```

5. **Run the server:**
   ```bash
   uvicorn server:app --reload
   ```
   The API will be available at `http://localhost:8000`.
   API Documentation: `http://localhost:8000/docs`

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the `frontend` directory:
   ```env
   EXPO_PUBLIC_BACKEND_URL=http://<YOUR_LOCAL_IP>:8000
   ```
   > **Note:** Use your machine's local IP address (e.g., `192.168.1.x`) instead of `localhost` if testing on a physical device or Android Emulator.

4. **Start the application:**
   ```bash
   npx expo start
   ```

5. **Run on Device/Emulator:**
   - Scan the QR code with the **Expo Go** app on your phone.
   - Press `a` for Android Emulator.
   - Press `i` for iOS Simulator.

## API Documentation

Once the backend server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

This project is licensed under the MIT License.
