# mindease

A mental health support platform with emotion detection, AI chat, and community features.

## Installation & Setup

### Prerequisites
- **Python 3.11** (for backend)
- **Node.js 18+** (for frontend)
- **MongoDB** (local or cloud instance)

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a Python 3.11 virtual environment:
   ```bash
   # Windows
   py -3.11 -m venv .venv311

   # macOS/Linux
   python3.11 -m venv .venv311
   ```

3. Activate the virtual environment:
   ```bash
   # Windows
   .venv311\Scripts\activate

   # macOS/Linux
   source .venv311/bin/activate
   ```

4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your settings (MongoDB URL, JWT secret, AI provider keys).

6. Run the backend:
   ```bash
   # Using the provided script (recommended)
   ./run_backend.sh

   # Or manually
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

### Running the Application

1. **Backend**: Runs on `http://localhost:8000`
   - Health check: `http://localhost:8000/health`

2. **Frontend**: Runs on `http://localhost:5173` (default Vite port)

3. Ensure MongoDB is running and accessible.

