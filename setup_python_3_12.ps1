# Download and install Python 3.12 if not already installed
# (You can skip this step if you already have Python 3.12 installed and on your PATH)

# Create a virtual environment named .venv with Python 3.12
py -3.12 -m venv .venv

# Activate the virtual environment
.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install project requirements
pip install -r requirements.txt

# (Optional) Run your tests to verify the setup
pytest